"""Telegram ile onay: emir listesini gönderir, yalnızca yetkili kişiden gelen kodu kabul eder.

Güvenlik kuralları:

* Yanıt yalnızca ayarlı sohbetten VE yetkili kullanıcıdan gelirse dikkate alınır
  (bir grupta başkasının yazdığı kod işe yaramaz).
* Her onay isteğinin tek kullanımlık, o isteğe özel bir kodu vardır; eski bir "onay" mesajı
  yeni bir emir listesini onaylayamaz. Hata yanıtlarında kod yinelenmez.
* İstekten ÖNCE yazılmış mesajlar yok sayılır.
* Son söz geçerlidir: koddan sonra "RED", "İPTAL", "DUR" ... yazılmışsa emir gönderilmez;
  onaydan sonra da bu sözcüklerin hepsi gönderimi durdurur.
* Ağ hatası hiçbir zaman onay sayılmaz.
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
#: Onayı reddeden ve (onaydan sonra) gönderimi durduran sözcükler.
REJECT_WORDS = frozenset({"RED", "REDDET", "HAYIR", "IPTAL", "DUR", "DURDUR", "STOP", "VAZGEC"})
PAGE = 100
_PUNCT = " .,!?;:…-_*\"'()[]"


class TelegramError(RuntimeError):
    """Telegram'a ulaşılamadı ya da bot yapılandırması hatalı.

    ``permanent``: yeniden denemekle düzelmeyecek hata (geçersiz anahtar, yanlış sohbet, botu
    başka bir programın dinlemesi).
    """

    def __init__(self, message: str, permanent: bool = False, conflict: bool = False):
        super().__init__(message)
        self.permanent = permanent
        self.conflict = conflict


def normalize(text: str) -> str:
    """Karşılaştırma için sadeleştirir: boşlukları atar, büyütür, Türkçe harfleri düzleştirir."""
    table = str.maketrans("ıiİşŞğĞüÜöÖçÇ", "IIISSGGUUOOCC")
    return "".join(text.split()).translate(table).upper()


def command(text: str) -> str:
    """Sözcük karşılaştırması için: baştaki ``/``, sondaki ``@botadı`` ve noktalama atılır
    ("/dur@bot", "Dur.", "İptal!" hepsi anlaşılır). Kod karşılaştırmasında KULLANILMAZ."""
    word = normalize(text).lstrip("/").split("@", 1)[0]
    return word.strip(_PUNCT)


def is_code_like(word: str) -> bool:
    return word.isdigit() or word.strip("ONAYEVTK").isdigit()


@dataclass
class Decision:
    status: str  # "approved" | "rejected" | "timeout"
    detail: str = ""
    #: Reddi kullanıcı mı istedi (yoksa bir güvenlik kontrolü mü).
    by_user: bool = False

    @property
    def approved(self) -> bool:
        return self.status == "approved"


class Telegram:
    """Küçük bir Telegram Bot API istemcisi (yalnızca gönder ve güncellemeleri oku)."""

    def __init__(self, token: str, chat_id: str, approver_id: str | None = None, http=requests, monotonic=time.monotonic):
        self._token = token
        self.chat_id = str(chat_id)
        self.approver_id = str(approver_id or chat_id)
        self._http = http
        self._offset: int | None = None
        self._monotonic = monotonic
        self._stop_retry_at = float("-inf")

    @property
    def is_group(self) -> bool:
        return self.chat_id.startswith("-")

    def _call(self, method: str, http_timeout: float = 15.0, **params) -> dict:
        try:
            resp = self._http.post(f"{API}/bot{self._token}/{method}", data=params, timeout=http_timeout)
        except requests.RequestException as exc:
            # İstisna metni adresi (ve anahtarı) içerebilir: yalnızca türü aktarılır.
            raise TelegramError(f"Telegram'a ulaşılamadı ({type(exc).__name__})") from None
        code = resp.status_code
        if code == 409:
            raise TelegramError(
                "Telegram botu başka bir program tarafından dinleniyor ya da webhook ayarlı; "
                "onay okunamıyor (aynı anda tek dinleyici olabilir)", permanent=True, conflict=True)
        if code in (401, 404):
            raise TelegramError("Telegram bot anahtarı geçersiz", permanent=True)
        if code in (400, 403):
            raise TelegramError("Telegram sohbet numarası hatalı ya da bot bu sohbete yazamıyor", permanent=True)
        if code != 200:
            raise TelegramError(f"Telegram hatası: HTTP {code}")
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

    def deliver(self, text: str, patience: float = 300.0, clock=time.time, sleep=time.sleep) -> bool:
        """Önemli bildirim (rapor, durdurma, uyarı): geçici hatalarda ``patience`` saniye boyunca yeniden dener."""
        end, attempt = clock() + patience, 0
        while True:
            try:
                self.send(text)
                return True
            except TelegramError as exc:
                attempt += 1
                log.warning("Telegram bildirimi gönderilemedi (%d): %s", attempt, exc)
                wait = min(60.0, 5.0 * attempt)
                if exc.permanent or clock() + wait > end:
                    return False
                sleep(wait)

    def can_read_group_messages(self) -> bool | None:
        """Grup sohbetinde bot düz mesajları görebiliyor mu (gizlilik kipi kapalı mı)? Bilinmiyorsa ``None``."""
        try:
            me = self._call("getMe").get("result") or {}
        except TelegramError:
            return None
        value = me.get("can_read_all_group_messages")
        return value if isinstance(value, bool) else None

    def updates(self, wait: int = 25) -> list[dict]:
        """Yeni güncellemeleri okur ve okunanları bir daha getirmemek üzere işaretler."""
        params = {"timeout": wait, "limit": PAGE, "allowed_updates": '["message"]'}
        if self._offset is not None:
            params["offset"] = self._offset
        # Uzun yoklamada HTTP süresi yoklama süresinden biraz uzun, anlık okumada kısa tutulur.
        http_timeout = wait + 10.0 if wait > 0 else 5.0
        result = self._call("getUpdates", http_timeout=http_timeout, **params).get("result") or []
        for item in result:
            if isinstance(item, dict) and isinstance(item.get("update_id"), int):
                self._offset = max(self._offset or 0, item["update_id"] + 1)
        return [u for u in result if isinstance(u, dict)]

    def authorised_texts(self, since: int, wait: int = 25, max_pages: int = 20) -> list[str]:
        """``since`` anından sonra, yetkili kişiden ve ayarlı sohbetten gelen mesaj metinleri.

        Kuyrukta bir sayfadan (100) fazla güncelleme varsa hepsi okunur; böylece yabancıların
        yığdığı mesajlar yetkili kişinin yazdığını geciktiremez.
        """
        texts: list[str] = []
        for page in range(max_pages):
            batch = self.updates(wait if page == 0 else 0)
            for update in batch:
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
            if len(batch) < PAGE:
                break
        return texts

    def stop_requested(self, since: int = 0, backoff: float = 10.0) -> bool:
        """Onaydan sonra yetkili kişi durdurma/vazgeçme sözcüğü yazdı mı (beklemeden bakar).

        "DUR", "RED", "İPTAL", "HAYIR", "VAZGEÇ", "/dur" ... hepsi durdurur. Anlaşılmayan bir
        mesaja yanıt verilir ki kullanıcı durdurduğunu sanmasın. Ağ hatasında ``False`` döner ve
        Telegram'a ulaşılamıyorken her emirde yeniden beklememek için kısa süre yoklanmaz.
        """
        now = self._monotonic()
        if now < self._stop_retry_at:
            return False
        try:
            texts = self.authorised_texts(since, wait=0)
        except TelegramError:
            self._stop_retry_at = now + backoff
            return False
        if any(command(t) in REJECT_WORDS for t in texts):
            return True
        if texts:
            self.try_send("Anlaşılmadı. Emirler gönderilmek üzere ya da gönderiliyor; durdurmak için DUR yazın.")
        return False


def new_code() -> str:
    return f"{secrets.randbelow(10_000):04d}"


def request_approval(
    tg: Telegram, text: str, code: str, deadline: float, clock=time.time, sleep=time.sleep, poll: int = 25,
    label: str = "en son",
) -> Decision:
    """Onay isteğini gönderir ve ``deadline`` (Unix saniyesi) gelene kadar yanıt bekler.

    Onay için yetkili kişinin kodu yazması gerekir ("ONAY 1234" da olur). "RED", "HAYIR",
    "İPTAL" ya da "DUR" isteği reddeder; aynı anda hem kod hem vazgeçme yazılmışsa vazgeçme
    geçerlidir. Süre dolarsa emir gönderilmez. ``label`` hata yanıtlarında hangi listeden söz
    edildiğini belirtir (kodun kendisi yinelenmez).
    """
    def permanent(exc: TelegramError) -> Decision:
        if exc.conflict:
            tg.try_send(f"⛔ Onay yanıtınız okunamıyor: {exc}. Emirler GÖNDERİLMEDİ.")
        return Decision("timeout", f"Telegram kullanılamıyor: {exc}")

    # İnternet kısa süre yoksa hemen vazgeçilmez; süre dolana kadar yeniden denenir.
    sent_at, attempt = None, 0
    while sent_at is None:
        try:
            tg.updates(wait=0)  # eski mesajları tüket
            sent_at = tg.send(text) or int(clock())
        except TelegramError as exc:
            if exc.permanent:
                return permanent(exc)
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

    codes = (code, "ONAY" + code, "EVET" + code, "OK" + code)
    wrong, failures = 0, 0
    while clock() < deadline:
        wait = int(max(0, min(poll, deadline - clock())))
        try:
            texts = tg.authorised_texts(sent_at, wait=wait)
            failures = 0
        except TelegramError as exc:
            if exc.permanent:
                return permanent(exc)
            failures += 1
            log.warning("Telegram okunamadı (%d): %s", failures, exc)
            if failures == 3:
                tg.try_send(f"⚠️ Onay yanıtınız okunamıyor ({exc}). Sorun sürerse emirler gönderilmeyecek.")
            sleep(min(30.0, 3.0 * failures))
            continue
        # Karar tüm yığına bakılarak verilir: vazgeçme sözcüğü, koddan önce de sonra da yazılsa geçerlidir.
        if any(command(t) in REJECT_WORDS for t in texts):
            return Decision("rejected", "kullanıcı reddetti", by_user=True)
        if any(normalize(t) in codes for t in texts):
            try:
                late = tg.authorised_texts(sent_at, wait=0)  # koddan hemen sonra yazılmış bir vazgeçme var mı
            except TelegramError:
                late = []
            if any(command(t) in REJECT_WORDS for t in late):
                return Decision("rejected", "kullanıcı koddan sonra vazgeçti", by_user=True)
            return Decision("approved", "kod doğrulandı")
        for raw in texts:
            if is_code_like(normalize(raw)):
                wrong += 1
                if wrong >= MAX_WRONG:
                    tg.try_send("Kod çok kez yanlış yazıldı. Emirler GÖNDERİLMEDİ.")
                    return Decision("rejected", "kod çok kez yanlış yazıldı")
                tg.try_send(f"Kod hatalı: bu kod {label} onay mesajına ait değil. Kodu o mesajdan yazın; "
                            "vazgeçmek için RED yazın.")
            else:
                tg.try_send(f"Anlaşılmadı. Onaylamak için {label} onay mesajındaki kodu yazın; vazgeçmek için RED yazın.")
        if not texts and wait == 0:
            sleep(1.0)
    return Decision("timeout", "süre doldu")
