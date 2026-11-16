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
import re
import secrets
import time
from dataclasses import dataclass

import requests

from ..live.notify import split_message

log = logging.getLogger(__name__)

API = "https://api.telegram.org"
#: Yanlış kod bu kadar kez yazılırsa istek reddedilmiş sayılır.
MAX_WRONG = 5
#: Bilgisayar saati ile Telegram sunucu saati arasında izin verilen en büyük fark (saniye). Gönderim
#: pencerelerinin kenar payları 15-30 saniyedir; saat bundan fazla şaşıyorsa emir gönderilmez.
MAX_CLOCK_SKEW = 10.0
#: Onayı reddeden ve (onaydan sonra) gönderimi durduran sözcükler; mesajın herhangi bir sözcüğü olabilir.
REJECT_WORDS = frozenset({"RED", "REDDET", "HAYIR", "IPTAL", "DUR", "DURDUR", "STOP", "VAZGEC", "GONDERME", "YAPMA"})
#: Bu öneklerle başlayan sözcükler de vazgeçme sayılır ("vazgeçtim", "iptal et", "durdurun", "reddediyorum").
REJECT_PREFIXES = ("VAZGEC", "IPTAL", "DURDUR", "REDDE", "GONDERME")
#: Kodun yanında yazılabilecek onay sözcükleri ("ONAY 1234", "evet 1234").
CONFIRM_WORDS = frozenset({"ONAY", "ONAYLA", "ONAYLIYORUM", "EVET", "OK", "TAMAM", "KOD"})
PAGE = 100
_CODE_WORD = re.compile(r"(?:ONAYLIYORUM|ONAYLA|ONAY|EVET|TAMAM|OK|KOD)?(\d+)")
_TR = str.maketrans("ıiİşŞğĞüÜöÖçÇ", "IIISSGGUUOOCC")


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
    return "".join(text.split()).translate(_TR).upper()


def tokens(text: str) -> list[str]:
    """Mesajın sözcükleri: büyük harf, Türkçe harfler düzleştirilmiş, noktalama atılmış. Komut biçimleri
    de anlaşılır: "/dur", "/dur@BotAdı" -> "DUR"; "@BotAdı dur" -> "DUR"; "1234." -> "1234"."""
    out = []
    for part in re.split(r"[^0-9A-Z@/]+", text.translate(_TR).upper()):
        word = part.lstrip("/").split("@", 1)[0]
        if word:
            out.append(word)
    return out


def is_reject(text: str) -> bool:
    """Mesajda bir vazgeçme/durdurma sözcüğü var mı ("hayır dur", "iptal et", "vazgeçtim", "/dur" ...)."""
    return any(word in REJECT_WORDS or word.startswith(REJECT_PREFIXES) for word in tokens(text))


def command(text: str) -> str:
    """Tek sözcüklü mesajın sözcüğü (yoksa boş): ``tokens`` ile aynı sadeleştirme."""
    words = tokens(text)
    return words[0] if len(words) == 1 else ""


def classify(text: str, code: str) -> str:
    """Onay beklerken gelen mesajın türü: ``reject`` | ``code`` | ``wrong_code`` | ``other``.

    Kod yalnızca tam olarak yazılmışsa (yanında en çok "onay", "evet" gibi sözcüklerle) kabul edilir;
    "/1234", "1234." ve "48 21" yazımları da geçerlidir. Başka sözcük içeren mesaj onay sayılmaz.
    """
    if is_reject(text):
        return "reject"
    digits = []
    for word in tokens(text):
        if word in CONFIRM_WORDS:
            continue
        match = _CODE_WORD.fullmatch(word)  # "1234" ya da bitişik yazılmış "ONAY1234"
        if match is None:
            return "other"
        digits.append(match.group(1))
    if not digits:
        return "other"
    return "code" if "".join(digits) == code else "wrong_code"


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
        #: Durdurma yoklamasının art arda kaç kez başarısız olduğu (kanal kapalıysa kullanıcı uyarılır).
        self.stop_failures = 0

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

    def _send_parts(self, parts: list[str], done: int = 0) -> tuple[int, int]:
        """``done`` sayıda parça önceden gönderilmişse kalanları yollar; ``(gönderilen parça, sunucu saati)``."""
        stamp = 0
        for part in parts[done:]:
            body = self._call("sendMessage", chat_id=self.chat_id, text=part, disable_web_page_preview="true")
            stamp = int((body.get("result") or {}).get("date") or 0)
            done += 1
        return done, stamp

    def send(self, text: str) -> int:
        """Metni gönderir; son parçanın sunucu saatini (Unix) döndürür."""
        return self._send_parts(split_message(text))[1]

    def try_send(self, text: str) -> bool:
        try:
            self.send(text)
            return True
        except TelegramError as exc:
            log.warning("Telegram bildirimi gönderilemedi: %s", exc)
            return False

    def deliver(self, text: str, patience: float = 300.0, clock=time.time, sleep=time.sleep) -> bool:
        """Önemli bildirim (rapor, durdurma, uyarı): geçici hatalarda ``patience`` saniye boyunca yeniden
        dener. Uzun mesajın gönderilmiş parçaları yinelenmez; yalnızca kalan parçalar yeniden denenir."""
        parts = split_message(text)
        end, attempt, done = clock() + patience, 0, 0
        while True:
            try:
                while done < len(parts):
                    self._call("sendMessage", chat_id=self.chat_id, text=parts[done], disable_web_page_preview="true")
                    done += 1
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
            try:
                batch = self.updates(wait if page == 0 else 0)
            except TelegramError:
                if page == 0:
                    raise
                break  # önceki sayfalarda okunanlar kaybolmasın; kalanı sonraki yoklamada okunur
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
        """Onaydan sonra yetkili kişi durdurma/vazgeçme yazdı mı (beklemeden bakar).

        "DUR", "RED", "İPTAL", "hayır dur", "vazgeçtim", "/dur" ... hepsi durdurur. Anlaşılmayan bir
        mesaja yanıt verilir ki kullanıcı durdurduğunu sanmasın. Ağ hatasında ``False`` döner;
        Telegram yavaşsa (hata saniyeler sürdüyse) her emirde yeniden beklememek için kısa süre yoklanmaz.
        """
        started = self._monotonic()
        if started < self._stop_retry_at:
            return False
        try:
            texts = self.authorised_texts(since, wait=0)
        except TelegramError:
            self.stop_failures += 1
            ended = self._monotonic()
            if ended - started >= 1.0:  # anında dönen hata (ör. tek bir 502) sonraki yoklamayı geciktirmez
                self._stop_retry_at = ended + backoff
            return False
        self.stop_failures = 0
        if any(is_reject(t) for t in texts):
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

    def fatal(exc: TelegramError, conflicts: int) -> bool:
        """Kalıcı hata mı? Tek seferlik 409 (ör. başka bir yerden bir kez getUpdates çağrılması) geçicidir."""
        return exc.permanent and (not exc.conflict or conflicts >= 3)

    # İnternet kısa süre yoksa hemen vazgeçilmez; süre dolana kadar yeniden denenir.
    sent_at, attempt, conflicts = None, 0, 0
    before = after = clock()
    while sent_at is None:
        try:
            tg.updates(wait=0)  # eski mesajları tüket
            before = clock()
            sent_at = tg.send(text) or int(clock())
            after = clock()
        except TelegramError as exc:
            conflicts = conflicts + 1 if exc.conflict else 0
            if fatal(exc, conflicts):
                return permanent(exc)
            attempt += 1
            log.warning("Telegram'a ulaşılamadı (%d): %s", attempt, exc)
            if clock() + 30.0 >= deadline:
                return Decision("timeout", f"Telegram'a ulaşılamadı: {exc}")
            sleep(min(60.0, 5.0 * attempt))
    # Saat farkı: sunucu saati, isteğin gönderilmeden önceki ve sonraki yerel saatinin arasında olmalı
    # (ağ gecikmesi farka katılmaz). Gönderim pencereleri bilgisayarın saatine göre hesaplanır.
    skew = max(before - (sent_at + 1), sent_at - after, 0.0)
    if skew > MAX_CLOCK_SKEW:
        tg.try_send(f"⛔ Bilgisayarın saati Telegram saatinden yaklaşık {int(skew)} saniye farklı. Saati düzeltin "
                    "(Windows: Ayarlar → Saat ve dil → Şimdi eşitle); emirler GÖNDERİLMEDİ.")
        return Decision("rejected", f"bilgisayar saati yanlış ({int(skew)} sn fark)")

    wrong, failures, conflicts = 0, 0, 0
    while clock() < deadline:
        wait = int(max(0, min(poll, deadline - clock())))
        try:
            texts = tg.authorised_texts(sent_at, wait=wait)
            failures = conflicts = 0
        except TelegramError as exc:
            conflicts = conflicts + 1 if exc.conflict else 0
            if fatal(exc, conflicts):
                return permanent(exc)
            failures += 1
            log.warning("Telegram okunamadı (%d): %s", failures, exc)
            if failures == 3:
                tg.try_send(f"⚠️ Onay yanıtınız okunamıyor ({exc}). Sorun sürerse emirler gönderilmeyecek.")
            sleep(min(30.0, 3.0 * failures))
            continue
        # Karar tüm yığına bakılarak verilir: vazgeçme, koddan önce de sonra da yazılsa geçerlidir.
        kinds = [classify(t, code) for t in texts]
        if "reject" in kinds:
            return Decision("rejected", "kullanıcı reddetti", by_user=True)
        if "code" in kinds:
            unclear = any(k != "code" for k in kinds)
            if not unclear:
                try:
                    late = tg.authorised_texts(sent_at, wait=0)  # koddan hemen sonra yazılmış bir şey var mı
                except TelegramError:
                    late = []
                if any(is_reject(t) for t in late):
                    return Decision("rejected", "kullanıcı koddan sonra vazgeçti", by_user=True)
                unclear = any(classify(t, code) != "code" for t in late)
            if not unclear:
                return Decision("approved", "kod doğrulandı")
            # Kodla birlikte anlaşılmayan bir şey yazılmış (ör. "bekle", "sonra"): onay sayılmaz.
            tg.try_send("Kodu aldım ama birlikte yazdığınızı anlamadım; emirler GÖNDERİLMEDİ. Onaylıyorsanız "
                        "yalnızca kodu yeniden yazın; vazgeçtiyseniz RED yazın.")
            continue
        for kind in kinds:
            if kind == "wrong_code":
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
