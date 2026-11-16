"""Matriks IQ "Dışarıdan Emir Kabulü" bağlantısı.

Protokol, Matriks'in resmî belgesinden ("MatriksIQ Dışarıdan Emir Kabulü API Dokümanı", sürüm 1.6)
ve yayımladığı örnek istemcilerden (github.com/MatriksIQ: ApiClient, ClientDemoApp, PythonClient)
çıkarılmıştır:

* Matriks IQ açıkken aynı bilgisayarda ``127.0.0.1:18890`` adresini dinler (şifresiz TCP).
* Her ileti bir JSON nesnesidir ve dikey sekme karakteriyle (``0x0B``) biter; kodlama UTF-8.
* İstekte ``ApiCommands`` komutu (0 hesaplar, 1 pozisyonlar, 2 bekleyen emirler, 3 yeni emir,
  4 iptal, 6 canlılık, 7 hesap bilgisi, 8 gerçekleşenler, 9 iptal edilenler), yanıtta yanıt
  türünü (0 hesaplar, 1 pozisyonlar, 2 emirler, 3 emir değişti, 4 pozisyon değişti, 5 giriş,
  6 çıkış, 7 canlılık, 8 hesap bilgisi, 9 gerçekleşenler, 10 iptal edilenler) taşır.
* Yeni emirde yön ``OrderSide``: alış 1, satış 2 (belgedeki Tablo 4.6; örnek uygulamada Haziran
  2022'den beri böyle, öncesinde 0/1 idi). Yanıtlarda ise aynı alan belgedeki örneklerde 0
  görünür ve örnek uygulama 0'ı alış sayar ("Side" tablosu: 0 alış, 1 satış); bu yüzden yanıttaki
  değer sabit bir kodla değil, yön testinde öğrenilen değerle karşılaştırılır.
* Emir tipi ``'2'`` limit, süre ``'0'`` günlük, işlem tipi ``'1'`` normal. Emir durumu
  ``OrdStatus`` FIX kodlarıdır (``'0'`` bekliyor, ``'1'`` kısmi, ``'2'`` gerçekleşti,
  ``'4'`` iptal, ``'8'`` reddedildi ...); yeni emrin ilk yanıtında boş (``\u0000``) gelebilir.
* Alan adlarının harf büyüklüğü belgede ve kütüphanede farklıdır (``OrderID`` / ``OrderId``,
  ``ExchangeID`` / ``ExchangeId``); gelen iletiler büyük/küçük harf ayrımı olmadan okunur.
* Yanıtlarda miktar ``OrderQty``, ``Quantity`` ya da ``LeavesQty`` alanlarından birinde olabilir
  ve istemci emir kimliği (``ClientOrderId``) geri gelmeyebilir; emirler önce kimlikle, olmazsa
  içerikle (hesap, sembol, adet, fiyat) eşleştirilir.

Bu modül gerçek Matriks IQ ile DENENEMEMİŞTİR (program Windows'ta, lisanslı ve aracı kurum
girişiyle çalışır). O yüzden iki ek güvence vardır: ``emir --yon-testi`` ile 1 lotluk emirle
yön kodları kullanıcı gözetiminde doğrulanmadan gerçek kip açılmaz ve her emrin yanıtındaki
yön, doğrulanmış değerle karşılaştırılır; uyuşmazlıkta emir iptal edilip gönderim durdurulur.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import random
import re
import socket
import threading
import time
from dataclasses import dataclass, field

from .base import BrokerError, NotSent, OrderRequest, OrderState
from .settings import MatriksSettings

log = logging.getLogger(__name__)

TERMINATOR = b"\x0b"
MAX_MESSAGE = 32 * 1024 * 1024

# İstek komutları (ApiCommands).
LIST_ACCOUNTS, LIST_POSITIONS, LIST_ORDERS, NEW_ORDER, CANCEL_ORDER, EDIT_ORDER, KEEP_ALIVE = range(7)
ACCOUNT_INFO, LIST_FILLED, LIST_CANCELED = 7, 8, 9
# Yanıt türleri (ClientCommands).
R_ACCOUNTS, R_POSITIONS, R_ORDERS, R_ORDER_CHANGED, R_POSITION_CHANGED, R_LOGIN, R_LOGOUT, R_KEEP_ALIVE = range(8)
R_ACCOUNT_INFO, R_FILLED, R_CANCELED = 8, 9, 10

ORDER_TYPE_LIMIT = "2"
TIF_DAY = "0"
TRANSACTION_NORMAL = "1"
STATUS_NEW = "0"

#: FIX ``OrdStatus`` -> botun durum sözlüğü.
STATUS_MAP = {
    "0": "accepted", "1": "partial", "2": "filled", "4": "cancelled", "5": "accepted", "6": "accepted",
    "7": "accepted", "8": "rejected", "9": "accepted", "A": "accepted", "C": "cancelled", "D": "accepted",
    "E": "accepted", "Z": "cancelled",
}
STATUS_TEXT = {
    "0": "bekliyor", "1": "kısmen gerçekleşti", "2": "gerçekleşti", "4": "iptal", "5": "düzeltildi",
    "6": "iptal bekliyor", "7": "durduruldu", "8": "reddedildi", "9": "beklemeye alındı",
    "A": "iletilmeyi bekliyor", "C": "süresi doldu", "D": "düzeltme bekliyor", "E": "düzeltme isteği gönderildi",
    "Z": "silindi",
}
_SYMBOL = re.compile(r"^[A-Z0-9]{3,6}$")
_NET_EPOCH_SECONDS = 62_135_596_800  # 0001-01-01 ile 1970-01-01 arası
_NET_MIN_DATE = "0001-01-01T00:00:00"


class Msg(dict):
    """Gelen JSON nesnesi: anahtarlar büyük/küçük harf ayrımı olmadan okunur (``OrderID`` = ``OrderId``)."""

    def __init__(self, data=()):
        super().__init__(data)
        self._index = {k.strip().lower(): k for k in self if isinstance(k, str)}

    def _real(self, key):
        if isinstance(key, str) and not dict.__contains__(self, key):
            return self._index.get(key.strip().lower(), key)
        return key

    def __getitem__(self, key):
        return super().__getitem__(self._real(key))

    def __contains__(self, key):
        return super().__contains__(self._real(key))

    def get(self, key, default=None):
        key = self._real(key)
        return super().get(key, default)

    def __setitem__(self, key, value):
        key = self._real(key)
        super().__setitem__(key, value)
        if isinstance(key, str):
            self._index[key.strip().lower()] = key


#: Emrin bittiğini gösteren durum kodları.
FINAL_CODES = frozenset({"2", "4", "8", "C", "Z"})


def _status_code(msg: dict) -> str:
    return str(msg.get("OrdStatus") or "").strip(" \x00") if msg else ""


def _order_qty(msg: dict) -> float:
    """Emrin toplam adedi: yanıtlarda ``OrderQty`` ya da ``Quantity`` sıfır gelebilir."""
    for name in ("OrderQty", "Quantity"):
        value = _number(msg.get(name))
        if value > 0:
            return value
    return _number(msg.get("LeavesQty")) + _number(msg.get("FilledQty"))


class SideMismatch(BrokerError):
    """Matriks IQ'nun bildirdiği emir yönü beklenenle uyuşmuyor: gönderim durdurulmalı.

    ``state`` emrin bilinen son durumudur (iptal edildi mi, gerçekleşti mi, hâlâ çalışıyor mu).
    """

    def __init__(self, message: str, state: OrderState | None = None):
        super().__init__(message)
        self.state = state


def client_order_id(now: float | None = None) -> str:
    """Matriks örnek uygulamasındaki biçim: .NET "tick" sayısı + rastgele, 20 haneye tamamlanır."""
    ticks = int(((time.time() if now is None else now) + _NET_EPOCH_SECONDS) * 10_000_000)
    return f"{ticks + random.randrange(1_000_000):020d}"


def _number(value, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(" ", "").replace(" ", "")
        if not text:
            return default
        if "," in text and "." in text:
            # Son gelen ayırıcı ondalıktır: "1.234,56" (Türkçe) ya da "1,234.56".
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:  # yalnız virgül: ondalık virgül ("1234,56")
            text = text.replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return default
    return default


def mask(account: str) -> str:
    """Hesap numarasını bildirimlerde gizler: yalnızca son üç hane gösterilir."""
    account = str(account)
    return "…" + account[-3:] if len(account) > 3 else "…"


class MatriksWire:
    """Soket, çerçeveleme (0x0B), okuma iş parçacığı ve canlılık iletileri.

    Her bağlantının kendi "kapandı" işareti vardır; eski bir bağlantının iş parçacıkları
    yeniden bağlanıldıktan sonra yeni bağlantıya dokunamaz.
    """

    def __init__(self, host: str, port: int, timeout: float = 15.0, json_mode: bool = True, keepalive: float = 30.0):
        self.host, self.port, self.timeout = host, port, timeout
        self.json_mode, self.keepalive = json_mode, keepalive
        self._sock: socket.socket | None = None
        self._send_lock = threading.Lock()
        self._cond = threading.Condition()
        self._inbox: list[dict] = []
        self._listeners: list = []
        self._closed = threading.Event()
        self._closed.set()
        self.error: str | None = None

    # -- bağlantı ---------------------------------------------------------------------
    def connect(self) -> None:
        self.close()
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as exc:
            raise BrokerError(
                f"Matriks IQ'ya bağlanılamadı ({self.host}:{self.port}): {type(exc).__name__}. Program açık mı, "
                "'Dışarıdan Emir Kabulü' lisansı etkin mi?"
            ) from exc
        sock.settimeout(1.0)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        closed = threading.Event()
        self._sock, self._closed, self.error = sock, closed, None
        for target in (self._read_loop, self._keepalive_loop):
            threading.Thread(target=target, args=(sock, closed), daemon=True).start()
        if self.json_mode:
            # Belgeye göre ilk iş mesajlaşma tipi seçilir: sonlandırıcısız "SetMessageType0" (JSON).
            self._raw_send(b"SetMessageType0")
            time.sleep(0.3)

    def close(self) -> None:
        closed, sock = self._closed, self._sock
        closed.set()
        self._sock = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        with self._cond:
            self._cond.notify_all()

    @property
    def connected(self) -> bool:
        return self._sock is not None and not self._closed.is_set()

    # -- gönderme ---------------------------------------------------------------------
    def _raw_send(self, data: bytes) -> None:
        sock, closed = self._sock, self._closed
        if sock is None or closed.is_set():
            # Tek bayt bile yazılmadı: ileti kesinlikle gitmedi.
            raise NotSent("Matriks IQ bağlantısı kapalı" + (f": {self.error}" if self.error else ""))
        with self._send_lock:
            try:
                sock.sendall(data)
            except OSError as exc:
                self._fail(f"gönderim hatası ({type(exc).__name__})", closed)
                raise BrokerError("Matriks IQ'ya ileti gönderilirken bağlantı koptu") from exc

    def send(self, payload: dict) -> None:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        self._raw_send(text.encode("utf-8") + TERMINATOR)

    # -- alma -------------------------------------------------------------------------
    def _fail(self, reason: str, closed: threading.Event) -> None:
        """``closed`` işaretli bağlantıyı hatayla kapatır; güncel bağlantı değilse ona dokunmaz."""
        if closed is not self._closed:
            closed.set()
            return
        if not closed.is_set():
            self.error = reason
            log.warning("Matriks IQ bağlantısı koptu: %s", reason)
        self.close()

    def _read_loop(self, sock: socket.socket, closed: threading.Event) -> None:
        buffer = bytearray()
        while not closed.is_set():
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                continue
            except OSError as exc:
                self._fail(f"okuma hatası ({type(exc).__name__})", closed)
                return
            if not chunk:
                self._fail("Matriks IQ bağlantıyı kapattı", closed)
                return
            buffer.extend(chunk)
            if len(buffer) > MAX_MESSAGE:
                self._fail("ileti çok büyük", closed)
                return
            while True:
                cut = buffer.find(TERMINATOR)
                if cut < 0:
                    break
                raw, buffer = bytes(buffer[:cut]), buffer[cut + 1:]
                self._handle(raw)

    def _handle(self, raw: bytes) -> None:
        text = raw.decode("utf-8", errors="replace").strip().lstrip("﻿")
        if not text:
            return
        # Bazı sürümler JSON'dan önce düz metin yazabilir; ilk süslü parantezden başla.
        start = text.find("{")
        if start < 0:
            return
        try:
            message = json.loads(text[start:], object_hook=Msg)
        except ValueError:
            log.debug("Matriks IQ'dan çözülemeyen ileti (%d bayt)", len(raw))
            return
        if not isinstance(message, Msg):
            return
        message["_rx"] = time.monotonic()
        for listener in list(self._listeners):
            try:
                listener(message)
            except Exception:  # dinleyici hatası okuma döngüsünü durdurmasın
                log.exception("ileti dinleyicisi hata verdi")
        with self._cond:
            self._inbox.append(message)
            if len(self._inbox) > 5000:
                del self._inbox[:1000]
            self._cond.notify_all()

    def _keepalive_loop(self, sock: socket.socket, closed: threading.Event) -> None:
        while not closed.wait(self.keepalive):
            if sock is not self._sock:
                return
            try:
                now = dt.datetime.now(dt.timezone(dt.timedelta(hours=3)))
                self.send({"KeepAliveDate": now.isoformat(), "ApiCommands": KEEP_ALIVE})
            except BrokerError:
                return

    def add_listener(self, fn) -> None:
        self._listeners.append(fn)

    def wait_for(self, kind: int, predicate=None, timeout: float | None = None, since: float = 0.0) -> dict:
        """``kind`` türünde, ``since`` anından sonra gelen ve koşulu sağlayan ilk iletiyi bekler."""
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        with self._cond:
            while True:
                for i, msg in enumerate(self._inbox):
                    if msg.get("ApiCommands") == kind and msg["_rx"] >= since and (predicate is None or predicate(msg)):
                        return self._inbox.pop(i)
                if self._closed.is_set():
                    raise BrokerError("Matriks IQ bağlantısı koptu" + (f": {self.error}" if self.error else ""))
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise BrokerError("Matriks IQ zamanında yanıt vermedi")
                self._cond.wait(min(remaining, 0.5))


@dataclass
class _Track:
    order: OrderRequest
    client_id: str
    sent_at: float
    code: int
    order_id: str | None = None
    raw: dict = field(default_factory=dict)
    events: int = 0
    matched_by: str = ""


class MatriksBroker:
    """``Broker`` arayüzünün Matriks IQ uygulaması."""

    name = "Matriks IQ"

    def __init__(self, settings: MatriksSettings, echo_buy: int | None = None, wire: MatriksWire | None = None):
        self.s = settings
        #: Yön testinde, alış emrinin yanıtında görülen ``OrderSide`` değeri (bilinmiyorsa None).
        self.echo_buy = echo_buy
        self.wire = wire or MatriksWire(settings.host, settings.port, settings.zaman_asimi, settings.json_kipi_gonder)
        self.brokage_id = settings.araci_kurum_id
        self.account_id = settings.hesap_id
        self.brokage_name = ""
        self._lock = threading.Lock()
        self._tracks: list[_Track] = []
        self._changed = threading.Condition(self._lock)
        self.logged_out = False
        #: Sunucunun istemci emir kimliğini (ClientOrderId) geri gönderdiği görüldü mü.
        self._ids_echoed = False
        self._quiet_queries: set[str] = set()
        self.wire.add_listener(self._on_message)

    # -- bağlantı ve hesap -------------------------------------------------------------
    def connect(self) -> None:
        if not self.wire.connected:
            self.wire.connect()
        self._select_account(self.accounts())
        self.logged_out = False

    def ensure_ready(self) -> None:
        """Emir göndermeden hemen önce: bağlantı ya da oturum düştüyse yeniden kurar, kuramazsa hata verir."""
        if not self.wire.connected or self.logged_out:
            self.connect()

    def close(self) -> None:
        self.wire.close()

    def describe(self) -> str:
        label = self.brokage_name or f"kurum {self.brokage_id}"
        return f"Matriks IQ · {label} · hesap {mask(self.account_id)}"

    def accounts(self) -> list[dict]:
        since = time.monotonic()
        self.wire.send({"ApiCommands": LIST_ACCOUNTS})
        reply = self.wire.wait_for(R_ACCOUNTS, since=since)
        out = []
        for broker in reply.get("Accounts") or []:
            if not isinstance(broker, dict):
                continue
            for acc in broker.get("AccountIdList") or []:
                if isinstance(acc, dict) and acc.get("AccountId") is not None:
                    out.append({
                        "BrokageId": str(broker.get("BrokageId", "")), "BrokageName": str(broker.get("BrokageName", "")),
                        "AccountId": str(acc["AccountId"]), "ExchangeId": acc.get("ExchangeId"),
                    })
        return out

    def _select_account(self, accounts: list[dict]) -> None:
        match = [a for a in accounts if a["ExchangeId"] == self.s.borsa_id]
        if self.s.hesap_id:
            match = [a for a in match if a["AccountId"] == self.s.hesap_id]
        if self.s.araci_kurum_id:
            match = [a for a in match if a["BrokageId"] == self.s.araci_kurum_id]
        if not match:
            raise BrokerError(
                "Matriks IQ'da uygun BIST hesabı bulunamadı. Aracı kurum girişi yapılmış mı? "
                "(ayarlı hesap/kurum numarasını 'emir --hesap' çıktısıyla karşılaştırın)"
            )
        if len({(a["BrokageId"], a["AccountId"]) for a in match}) > 1:
            raise BrokerError(
                "Birden çok BIST hesabı var; emir-ayar.toml içinde [matriks] araci_kurum_id ve hesap_id yazın "
                "('emir --hesap' ile listeleyin)"
            )
        self.brokage_id, self.account_id = match[0]["BrokageId"], match[0]["AccountId"]
        self.brokage_name = match[0]["BrokageName"]

    def _request(self, command: int, reply_kind: int, timeout: float | None = None) -> dict:
        since = time.monotonic()
        payload = {"BrokageId": self.brokage_id, "AccountId": self.account_id, "ExchangeId": self.s.borsa_id,
                   "ApiCommands": command}
        self.wire.send(payload)
        mine = lambda m: str(m.get("AccountId", self.account_id)) == self.account_id  # noqa: E731
        return self.wire.wait_for(reply_kind, mine, timeout=timeout, since=since)

    def raw_positions(self) -> list[dict]:
        reply = self._request(LIST_POSITIONS, R_POSITIONS)
        return [p for p in reply.get("PositionResponseList") or [] if isinstance(p, dict)]

    def positions(self) -> dict[str, int]:
        """Satılabilir lotlar. Alan bulunamazsa o hisse 0 sayılır (fazla satmaktansa hiç satma)."""
        out: dict[str, int] = {}
        for row in self.raw_positions():
            symbol = str(row.get("Symbol") or "").strip().upper()
            if not _SYMBOL.match(symbol) or row.get("IsSymbol") is False:
                continue
            if row.get("ExchangeId") not in (None, self.s.borsa_id):
                continue
            lots = 0.0
            for name in self.s.lot_alanlari:
                if row.get(name) is not None:
                    lots = _number(row.get(name))
                    break
            if lots >= 1:
                out[symbol] = out.get(symbol, 0) + int(lots + 1e-9)
        return out

    def account_info(self) -> list[dict]:
        since = time.monotonic()
        self.wire.send({"BrokageId": self.brokage_id, "AccountId": self.account_id, "ExchangeType": self.s.borsa_id,
                        "ApiCommands": ACCOUNT_INFO})
        reply = self.wire.wait_for(R_ACCOUNT_INFO, since=since)
        return [i for i in reply.get("Informations") or [] if isinstance(i, dict)]

    def cash(self) -> float | None:
        wanted = self.s.nakit_anahtari.strip().casefold()
        if not wanted:
            return None
        try:
            info = self.account_info()
        except BrokerError as exc:
            log.warning("hesap bilgisi okunamadı: %s", exc)
            return None
        for item in info:
            names = {str(item.get("Key") or "").strip().casefold(), str(item.get("Code") or "").strip().casefold()}
            if wanted in names:
                value = item.get("Value")
                if value is None or (isinstance(value, str) and not value.strip()):
                    return None
                return _number(value, default=float("nan"))
        return None

    def open_orders(self, timeout: float | None = None) -> list[dict]:
        reply = self._request(LIST_ORDERS, R_ORDERS, timeout)
        return [o for o in reply.get("OrderApiModels") or [] if isinstance(o, dict)]

    def filled_orders(self, timeout: float | None = None) -> list[dict]:
        reply = self._request(LIST_FILLED, R_FILLED, timeout)
        return [o for o in reply.get("FilledOrderApiModels") or [] if isinstance(o, dict)]

    def canceled_orders(self, timeout: float | None = None) -> list[dict]:
        reply = self._request(LIST_CANCELED, R_CANCELED, timeout)
        return [o for o in reply.get("CanceledOrderApiModels") or [] if isinstance(o, dict)]

    def sync(self) -> None:
        """Emir durumlarını sorgularla tazeler (kaçan bildirimlere karşı). Yalnızca emir numarası ya da
        istemci kimliğiyle eşleşen kayıtlar işlenir; içerik benzerliğiyle eşleştirme yapılmaz.

        Liste boşken Matriks IQ hiç yanıt vermeyebilir; bağlantı ayaktaysa yanıtsızlık "kayıt yok"
        sayılır. Bağlantı ya da oturum düşmüşse hata verilir.
        """
        if not self.wire.connected or self.logged_out:
            raise BrokerError("Matriks IQ bağlantısı ya da aracı kurum oturumu düştü")
        for fetch in (self.open_orders, self.filled_orders, self.canceled_orders):
            # Bir sorgu bir kez yanıtsız kaldıysa sonraki turlarda onun için uzun beklenmez.
            quiet = fetch.__name__ in self._quiet_queries
            try:
                items = fetch(timeout=0.5 if quiet else min(self.s.zaman_asimi, 3.0))
            except BrokerError:
                if not self.wire.connected:
                    raise
                self._quiet_queries.add(fetch.__name__)
                continue
            self._quiet_queries.discard(fetch.__name__)
            for item in items:
                msg = item if isinstance(item, Msg) else Msg(item)
                msg["_rx"] = time.monotonic()
                self._apply(msg, allow_content=False)

    # -- emirler ----------------------------------------------------------------------
    def _mine(self, msg: dict) -> bool:
        return str(msg.get("AccountId", self.account_id)) == self.account_id

    def _on_message(self, msg: dict) -> None:
        kind = msg.get("ApiCommands")
        # Oturum bildirimi hesabı açıkça taşımalıdır (canlılık yanıtı da 6 koduyla gelebilir).
        session = msg.get("AccountId") is not None and "KeepAliveDate" not in msg and self._mine(msg)
        if kind == R_LOGOUT and session:
            self.logged_out = True
        elif kind == R_LOGIN and session:
            self.logged_out = False
        if kind == R_ORDER_CHANGED:
            self._apply(msg, allow_content=True)

    def _apply(self, msg: dict, allow_content: bool) -> None:
        with self._changed:
            track = self._match(msg, allow_content)
            if track is None:
                return
            # Bitmiş bir emrin (gerçekleşti/iptal/red) üzerine, geç gelen durumsuz bir ileti yazılmaz.
            if not (_status_code(track.raw) in FINAL_CODES and _status_code(msg) not in FINAL_CODES):
                track.raw = msg
            track.events += 1
            if msg.get("OrderId"):
                track.order_id = str(msg["OrderId"])
            self._changed.notify_all()

    def _match(self, msg: dict, allow_content: bool = True) -> _Track | None:
        coid, oid = str(msg.get("ClientOrderId") or "").strip(), str(msg.get("OrderId") or "").strip()
        if coid:
            for t in self._tracks:
                if coid == t.client_id:
                    self._ids_echoed = True
                    t.matched_by = t.matched_by or "kimlik"
                    return t
        if oid:
            for t in self._tracks:
                if t.order_id == oid:
                    return t
        # Buradan sonrası yedek yol: Matriks IQ istemci kimliğini geri göndermiyorsa emir içeriğiyle
        # (hesap, sembol, adet, fiyat) eşleştirilir. Başka bir kimlik taşıyan ileti başkasının emridir;
        # sunucunun kimlikleri geri gönderdiği bir kez görüldüyse kimliksiz iletiler de bizim sayılmaz.
        if not allow_content or coid or self._ids_echoed or not self._mine(msg):
            return None
        symbol = str(msg.get("Symbol") or "").upper()
        qty, price = _order_qty(msg), _number(msg.get("Price"))
        candidates = [
            t for t in self._tracks
            if t.order_id is None and _status_code(t.raw) not in FINAL_CODES and t.order.symbol == symbol
            and int(qty + 1e-9) == t.order.lots and abs(price - t.order.limit_price) < 1e-6
            and msg["_rx"] >= t.sent_at
        ]
        # Yön burada bilerek aranmaz: içeriği aynı, yönü ters bir ileti büyük olasılıkla bizim emrimizin
        # ters yorumlanmış hâlidir; emre yazılır ki yön denetimi onu görüp iptal etsin ve gönderimi durdursun.
        if len(candidates) != 1:
            return None  # belirsiz: hiçbir emre yazılmaz, gönderen taraf "belirsiz" olarak ele alır
        candidates[0].matched_by = "içerik"
        return candidates[0]

    def _state(self, track: _Track) -> OrderState:
        raw = track.raw
        if not raw:
            return OrderState(track.order.key, "unknown", message="Matriks IQ emri doğrulamadı")
        code = _status_code(raw)
        status = STATUS_MAP.get(code, "accepted")
        filled = int(_number(raw.get("FilledQty")) + 1e-9)
        avg = _number(raw.get("AvgPx")) or None
        note = STATUS_TEXT.get(code, "iletildi, durum bekleniyor" if not code else f"durum {code!r}")
        explanation = str(raw.get("Explanation") or "").strip()
        if explanation:
            note += f" — {explanation[:200]}"
        if status == "accepted" and 0 < filled < track.order.lots:
            status = "partial"
        return OrderState(track.order.key, status, broker_id=track.order_id, filled_lots=filled, avg_price=avg,
                          message=note, raw=Msg({k: v for k, v in raw.items() if k != "_rx"}))

    def _payload(self, order: OrderRequest, code: int, client_id: str) -> dict:
        """Belgedeki "Yeni Emir İsteği" örnek sorgusu ve örnek istemcinin ``OrderRequest`` nesnesi (tüm alanlarla)."""
        lots = int(order.lots)
        return {
            "Symbol": order.symbol, "AccountId": self.account_id, "BrokageId": self.brokage_id,
            "Price": float(order.limit_price), "Quantity": lots, "OrderSide": code,
            "OrderId": None, "OrderId2": None, "OrderID": None, "OrderID2": None, "ClientOrderId": client_id,
            "OrderQty": lots,
            "OrdStatus": STATUS_NEW, "LeavesQty": lots, "FilledQty": 0, "AvgPx": 0,
            "TradeDate": _NET_MIN_DATE, "TransactTime": "00:00:00", "StopPx": 0, "Explanation": None,
            "ExpireDate": _NET_MIN_DATE, "IncludeAfterSession": False, "TimeInForce": TIF_DAY,
            "OrderType": ORDER_TYPE_LIMIT, "TransactionType": TRANSACTION_NORMAL, "ApiCommands": NEW_ORDER,
        }

    def _wait(self, track: _Track, done, timeout: float | None = None) -> None:
        """``done(track)`` doğru olana, bağlantı kopana ya da süre dolana kadar bekler."""
        deadline = time.monotonic() + (self.s.zaman_asimi if timeout is None else timeout)
        with self._changed:
            while not done(track) and time.monotonic() < deadline and self.wire.connected:
                self._changed.wait(0.25)

    def place(self, order: OrderRequest) -> OrderState:
        # Gönderimden ÖNCE anlaşılan engeller "kesinlikle gitmedi" olarak bildirilir (NotSent).
        if self.logged_out:
            raise NotSent("Matriks IQ'da aracı kurum oturumu kapalı")
        if not self.account_id or not self.brokage_id:
            raise NotSent("hesap seçilmedi (önce connect)")
        if not self.wire.connected:
            raise NotSent("Matriks IQ bağlantısı kapalı" + (f": {self.wire.error}" if self.wire.error else ""))
        code = self.s.alis_kodu if order.side == "buy" else self.s.satis_kodu
        track = _Track(order, client_order_id(), time.monotonic(), code)
        with self._lock:
            self._tracks.append(track)
        try:
            self.wire.send(self._payload(order, code, track.client_id))
        except NotSent:
            with self._lock:
                self._tracks.remove(track)
            raise
        self._wait(track, lambda t: t.events > 0)
        with self._lock:
            state = self._state(track)
        if state.status != "unknown":
            self._check_side(track)
        return state

    def _check_side(self, track: _Track) -> None:
        """Yanıttaki yön, yön testinde doğrulanan değerle uyuşmalı; uyuşmuyorsa emri iptal et ve dur."""
        if self.echo_buy is None or not self.s.yon_yanit_denetimi:
            return
        echo = track.raw.get("OrderSide")
        if echo is None:
            return
        is_buy = track.order.side == "buy"
        if (echo == self.echo_buy) == is_buy:
            return
        # İptal için emir numarası gerekir; henüz gelmediyse kısa süre beklenir.
        self._wait(track, lambda t: t.order_id is not None or _status_code(t.raw) in FINAL_CODES)
        with self._lock:
            state = self._state(track)
        if state.done:
            outcome = (f"emir GERÇEKLEŞTİ ({state.filled_lots} lot): ters yönde işlem yapılmış olabilir"
                       if state.filled_lots else f"emir çalışmıyor ({state.message})")
        else:
            # Emir hâlâ çalışıyorsa (kısmen gerçekleşmiş olsa bile) kalanı iptal edilir.
            try:
                state = self.cancel(state)
                rest = "kalan iptal edildi" if state.done else "kalan İPTAL DOĞRULANAMADI, hâlâ çalışıyor olabilir"
            except BrokerError as exc:
                rest = f"kalan İPTAL EDİLEMEDİ ({exc}), hâlâ çalışıyor olabilir"
            outcome = (f"{state.filled_lots} lot GERÇEKLEŞTİ (ters yönde olabilir); {rest}" if state.filled_lots
                       else rest.replace("kalan", "emir", 1))
        raise SideMismatch(
            f"{track.order.symbol}: gönderilen yön {'ALIŞ' if is_buy else 'SATIŞ'} ama Matriks IQ farklı bildirdi "
            f"(OrderSide={echo!r}); {outcome}. Gönderim durduruldu; Matriks IQ'da emirlerinizi kontrol edin. "
            "Emir orada doğru yönde görünüyorsa yanıttaki yön alanı güvenilir değildir: emir-ayar.toml içinde "
            "[matriks] yon_yanit_denetimi = false yapın.",
            state,
        )

    def _track_of(self, state: OrderState) -> _Track | None:
        with self._lock:
            for t in self._tracks:
                if t.order.key == state.key:
                    return t
        return None

    def refresh(self, state: OrderState) -> OrderState:
        """Emrin bilinen son durumu. Bağlantı ya da oturum düştüyse bildirimler gelmez; bu durumda
        eski durumu güncelmiş gibi göstermek yerine hata verilir."""
        track = self._track_of(state)
        if track is None:
            return state
        with self._lock:
            current = self._state(track)
        if not current.done and (not self.wire.connected or self.logged_out):
            raise BrokerError("Matriks IQ bağlantısı ya da aracı kurum oturumu düştü; emir durumları izlenemiyor")
        return current

    def _request_side(self, raw: dict, known: int | None = None) -> int:
        """İptal isteğinde yön, yeni emirdeki kodlamayla gönderilir (belgedeki örnek sorgu)."""
        if known is not None:
            return known
        echo = raw.get("OrderSide")
        if self.echo_buy is not None and echo is not None:
            return self.s.alis_kodu if echo == self.echo_buy else self.s.satis_kodu
        return echo if isinstance(echo, int) else self.s.alis_kodu

    def cancel_raw(self, raw: dict, side_code: int | None = None) -> None:
        """Bekleyen bir emri iptal eder. Yük, belgedeki "Emir İptal İsteği" örneğinin biçimindedir."""
        raw = raw if isinstance(raw, Msg) else Msg(raw)
        order_id, order_id2 = raw.get("OrderId"), raw.get("OrderId2")
        if not order_id:
            raise BrokerError("iptal için emir numarası (OrderID) yok")
        leaves = _number(raw.get("LeavesQty")) or (_order_qty(raw) - _number(raw.get("FilledQty")))
        self.wire.send({
            "OrderSide": self._request_side(raw, side_code),
            "OrderId": order_id, "OrderId2": order_id2, "OrderID": order_id, "OrderID2": order_id2,
            "ClientOrderId": raw.get("ClientOrderId"),
            "OrderQty": _order_qty(raw), "OrdStatus": _status_code(raw) or STATUS_NEW,
            "LeavesQty": leaves, "FilledQty": _number(raw.get("FilledQty")), "AvgPx": _number(raw.get("AvgPx")),
            "TradeDate": raw.get("TradeDate") or _NET_MIN_DATE, "TransactTime": raw.get("TransactTime") or "00:00:00",
            "StopPx": _number(raw.get("StopPx")), "Explanation": None,
            "ExpireDate": raw.get("ExpireDate") or _NET_MIN_DATE,
            "Symbol": raw.get("Symbol"), "Price": _number(raw.get("Price")), "Quantity": leaves,
            "IncludeAfterSession": bool(raw.get("IncludeAfterSession") or False),
            "TimeInForce": str(raw.get("TimeInForce") or "").strip(" \x00") or TIF_DAY,
            "OrderType": ORDER_TYPE_LIMIT, "TransactionType": TRANSACTION_NORMAL,
            "AccountId": raw.get("AccountId") or self.account_id, "BrokageId": raw.get("BrokageId") or self.brokage_id,
            "ApiCommands": CANCEL_ORDER,
        })

    def cancel(self, state: OrderState) -> OrderState:
        track = self._track_of(state)
        if track is None or not track.raw:
            raise BrokerError("iptal için emrin Matriks IQ kaydı yok")
        if track.order_id is None:
            self._wait(track, lambda t: t.order_id is not None or _status_code(t.raw) in FINAL_CODES)
        with self._lock:
            current = self._state(track)
            raw = Msg({k: v for k, v in track.raw.items() if k != "_rx"})
        if current.done:
            return current
        if track.order_id is None:
            raise BrokerError("emir numarası henüz gelmedi; iptal gönderilemedi")
        raw["OrderId"] = track.order_id
        self.cancel_raw(raw, track.code)
        self._wait(track, lambda t: _status_code(t.raw) in FINAL_CODES)
        with self._lock:
            return self._state(track)
