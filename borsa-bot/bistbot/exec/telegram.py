"""Telegram ile onay: emir listesini gönderir, yalnızca yetkili kişiden gelen kodu kabul eder.

Güvenlik kuralları:

* Yanıt yalnızca ayarlı sohbetten VE yetkili kullanıcıdan gelirse dikkate alınır
  (bir grupta başkasının yazdığı kod işe yaramaz).
* Her onay isteğinin tek kullanımlık, o isteğe özel bir kodu vardır; eski bir "onay" mesajı
  yeni bir emir listesini onaylayamaz.
* İstekten ÖNCE yazılmış mesajlar yok sayılır.
* Bot anahtarı hiçbir zaman günlüğe ya da hata metnine yazılmaz.
"""
from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass

import requests

from ..live.notify import split_message

log = logging.getLogger(__name__)

API = "https://api.telegram.org"
#: Yanlış kod bu kadar kez yazılırsa istek reddedilmiş sayılır.
MAX_WRONG = 5
#: Bilgisayar saati ile Telegram sunucu saati arasında izin verilen en büyük fark (saniye).
MAX_CLOCK_SKEW = 180.0
REJECT_WORDS = frozenset({"RED", "REDDET", "HAYIR", "IPTAL", "DUR", "STOP", "VAZGEC"})
STOP_WORDS = frozenset({"DUR", "STOP"})


class TelegramError(RuntimeError):
    """Telegram'a ulaşılamadı ya da bot yapılandırması hatalı."""


def normalize(text: str) -> str:
    """Karşılaştırma için sadeleştirir: boşlukları atar, büyütür, Türkçe harfleri düzleştirir."""
    table = str.maketrans("ıiİşŞğĞüÜöÖçÇ", "IIISSGGUUOOCC")
    return "".join(text.split()).translate(table).upper()


@dataclass
class Decision:
    status: str  # "approved" | "rejected" | "timeout"
    detail: str = ""

    @property
    def approved(self) -> bool:
        return self.status == "approved"


class Telegram:
    """Küçük bir Telegram Bot API istemcisi (yalnızca gönder ve güncellemeleri oku)."""

    def __init__(self, token: str, chat_id: str, approver_id: str | None = None, http=requests, timeout: float = 35.0):
        self._token = token
        self.chat_id = str(chat_id)
        self.approver_id = str(approver_id or chat_id)
        self._http = http
        self._timeout = timeout
        self._offset: int | None = None

    def _call(self, method: str, **params) -> dict:
        try:
            resp = self._http.post(f"{API}/bot{self._token}/{method}", data=params, timeout=self._timeout)
        except requests.RequestException as exc:
            # İstisna metni adresi (ve anahtarı) içerebilir: yalnızca türü aktarılır.
            raise TelegramError(f"Telegram'a ulaşılamadı ({type(exc).__name__})") from None
        if resp.status_code == 409:
            raise TelegramError(
                "Telegram botu başka bir program tarafından dinleniyor ya da webhook ayarlı; "
                "onay okunamıyor (aynı anda tek dinleyici olabilir)"
            )
        if resp.status_code in (401, 404):
            raise TelegramError("Telegram bot anahtarı geçersiz")
        if resp.status_code != 200:
            raise TelegramError(f"Telegram hatası: HTTP {resp.status_code}")
        try:
            body = resp.json()
        except ValueError:
            raise TelegramError("Telegram yanıtı okunamadı") from None
        if not isinstance(body, dict) or not body.get("ok"):
            raise TelegramError("Telegram isteği reddetti")
        return body

    def send(self, text: str) -> int:
        """Metni gönderir; son parçanın sunucu saatini (Unix) döndürür."""
        stamp = 0
        for part in split_message(text):
            body = self._call("sendMessage", chat_id=self.chat_id, text=part, disable_web_page_preview="true")
            stamp = int((body.get("result") or {}).get("date") or 0)
        return stamp

    def try_send(self, text: str) -> bool:
        try:
            self.send(text)
            return True
        except TelegramError as exc:
            log.warning("Telegram bildirimi gönderilemedi: %s", exc)
            return False

    def updates(self, wait: int = 25) -> list[dict]:
        """Yeni güncellemeleri okur ve okunanları bir daha getirmemek üzere işaretler."""
        params = {"timeout": wait, "allowed_updates": '["message"]'}
        if self._offset is not None:
            params["offset"] = self._offset
        result = self._call("getUpdates", **params).get("result") or []
        for item in result:
            if isinstance(item, dict) and isinstance(item.get("update_id"), int):
                self._offset = max(self._offset or 0, item["update_id"] + 1)
        return [u for u in result if isinstance(u, dict)]

    def authorised_texts(self, since: int, wait: int = 25) -> list[str]:
        """``since`` anından sonra, yetkili kişiden ve ayarlı sohbetten gelen mesaj metinleri."""
        texts = []
        for update in self.updates(wait):
            msg = update.get("message")
            if not isinstance(msg, dict):
                continue
            chat, sender = msg.get("chat") or {}, msg.get("from") or {}
            if str(chat.get("id")) != self.chat_id or str(sender.get("id")) != self.approver_id:
                continue
            if sender.get("is_bot") or int(msg.get("date") or 0) < since:
                continue
            if isinstance(msg.get("text"), str):
                texts.append(msg["text"])
        return texts

    def stop_requested(self, since: int) -> bool:
        """Yetkili kişi "DUR" yazdı mı (beklemeden bakar). Ağ hatasında ``False``."""
        try:
            return any(normalize(t) in STOP_WORDS for t in self.authorised_texts(since, wait=0))
        except TelegramError:
            return False


def new_code() -> str:
    return f"{secrets.randbelow(10_000):04d}"


def request_approval(
    tg: Telegram, text: str, code: str, deadline: float, clock=time.time, sleep=time.sleep, poll: int = 25,
) -> Decision:
    """Onay isteğini gönderir ve ``deadline`` (Unix saniyesi) gelene kadar yanıt bekler.

    Onay için yetkili kişinin kodu yazması gerekir ("ONAY 1234" da olur). "RED", "HAYIR",
    "İPTAL" ya da "DUR" isteği reddeder. Süre dolarsa emir gönderilmez.
    """
    # İnternet kısa süre yoksa hemen vazgeçilmez; süre dolana kadar yeniden denenir.
    sent_at, attempt = None, 0
    while sent_at is None:
        try:
            tg.updates(wait=0)  # eski mesajları tüket
            sent_at = tg.send(text) or int(clock())
        except TelegramError as exc:
            attempt += 1
            log.warning("Telegram'a ulaşılamadı (%d): %s", attempt, exc)
            if clock() + 30.0 >= deadline:
                return Decision("timeout", f"Telegram'a ulaşılamadı: {exc}")
            sleep(min(60.0, 5.0 * attempt))
    skew = abs(sent_at - clock())
    if skew > MAX_CLOCK_SKEW:
        # Gönderim pencereleri bilgisayarın saatine göre hesaplanır; saat yanlışsa emir gönderilmez.
        tg.try_send(f"⛔ Bilgisayarın saati Telegram saatinden {int(skew / 60)} dakika farklı. Saati düzeltin; "
                    "emirler GÖNDERİLMEDİ.")
        return Decision("rejected", f"bilgisayar saati yanlış ({int(skew)} sn fark)")
    wrong, failures = 0, 0
    while clock() < deadline:
        wait = int(max(0, min(poll, deadline - clock())))
        try:
            texts = tg.authorised_texts(sent_at, wait=wait)
            failures = 0
        except TelegramError as exc:
            failures += 1
            log.warning("Telegram okunamadı (%d): %s", failures, exc)
            if failures == 3:
                tg.try_send(f"⚠️ Onay yanıtınız okunamıyor ({exc}). Sorun sürerse emirler gönderilmeyecek.")
            sleep(min(30.0, 3.0 * failures))
            continue
        for raw in texts:
            word = normalize(raw)
            if word in (code, "ONAY" + code, "EVET" + code, "OK" + code):
                return Decision("approved", "kod doğrulandı")
            if word in REJECT_WORDS:
                return Decision("rejected", "kullanıcı reddetti")
            if word.strip("ONAYEVTK").isdigit() or word.isdigit():
                wrong += 1
                if wrong >= MAX_WRONG:
                    tg.try_send("Kod çok kez yanlış yazıldı. Emirler GÖNDERİLMEDİ.")
                    return Decision("rejected", "kod çok kez yanlış yazıldı")
                tg.try_send(f"Kod hatalı. Onay için {code} yazın; vazgeçmek için RED yazın.")
            else:
                tg.try_send(f"Anlaşılmadı. Onay için {code} yazın; vazgeçmek için RED yazın.")
        if not texts and wait == 0:
            sleep(1.0)
    return Decision("timeout", "süre doldu")
