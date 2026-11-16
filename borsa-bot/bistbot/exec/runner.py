"""Emir çalıştırıcısı: fiş → kontroller → Telegram onayı → gönderim → izleme → rapor.

Akış (hepsi İstanbul saatiyle):

1. Fiş bugünün seansı için mi, taze mi, sınırların içinde mi? Değilse hiçbir emir gitmez.
2. Hesaptaki gerçek pozisyonlar okunur; satışlar eldeki lotla sınırlanır.
3. Emir listesi Telegram'a gönderilir; yetkili kişi tek kullanımlık kodu yazmadan emir gitmez.
4. Emirler ilk uygun pencerede gönderilir: açılış seansı (09:40-09:55) ya da sürekli işlem.
   Önce satışlar, sonra alışlar. Her emir gönderilmeden ÖNCE günlüğe yazılır; aynı emir
   iki kez gönderilmez. Yanıtı alınamayan bir emir olursa gönderim durur.
5. Gerçekleşmeler izlenir. Satışlar gerçekleştiyse parası yetmediği için ertelenen ya da
   reddedilen alışlar bir kez daha denenir ("ikinci tur").
6. Sonuç Telegram'a raporlanır.

``.emir/DUR`` adlı bir dosya ya da Telegram'dan yazılan "DUR", sıradaki emirleri durdurur.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

from .base import Broker, BrokerError, NotSent, OrderRequest, OrderState
from .guard import COST_MARGIN, Plan, build_plan, check_ticket, session_problems, trading_days_between
from .journal import RETRY, Journal
from .settings import ExecSettings, Schedule
from .telegram import Decision, Telegram, new_code, request_approval
from .ticket import Ticket

log = logging.getLogger(__name__)

#: Türkiye 2016'dan beri yıl boyu UTC+3'tür (Windows'ta saat dilimi veritabanı gerekmesin diye sabit).
IST = dt.timezone(dt.timedelta(hours=3), "TRT")
#: Açılış fiyatı 09:55-10:00 arasında belirlenir; açılış seansında gönderilen emirler en az buna kadar izlenir.
OPENING_PRINT = dt.time(10, 2, 0)
STOP_FILE = "DUR"
LOCK_FILE = "kilit"
STATE_FILE = "durum.json"
OUTBOX_FILE = "iletilemeyen.jsonl"

SIDE_TR = {"buy": "AL ", "sell": "SAT"}
STATUS_TR = {
    "filled": "gerçekleşti", "partial": "kısmen gerçekleşti", "accepted": "bekliyor", "rejected": "REDDEDİLDİ",
    "cancelled": "iptal", "unknown": "BELİRSİZ",
}


class Clock:
    def now(self) -> dt.datetime:
        return dt.datetime.now(IST)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class AlreadyRunning(RuntimeError):
    pass


class RunLock:
    """Aynı anda iki çalıştırmanın emir göndermesini önleyen kilit.

    Kilit dosyası açık tutulur ve işletim sistemi düzeyinde kilitlenir (Windows'ta ``msvcrt.locking``,
    diğerlerinde ``flock``). Süreç hangi nedenle biterse bitsin kilidi işletim sistemi bırakır;
    "bayat kilit" tahmini ya da dosya silme yarışı yoktur.
    """

    def __init__(self, folder: Path):
        self.path = Path(folder) / LOCK_FILE
        self._fh = None

    def __enter__(self) -> "RunLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.path, "a+b")
        try:
            if os.name == "nt":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            raise AlreadyRunning(
                f"başka bir emir çalıştırması sürüyor (kilit: {self.path}). O çalıştırma bitince yeniden deneyin; "
                "emin değilseniz Matriks IQ'da emirlerinizi kontrol edin."
            ) from None
        self._fh = fh
        try:  # bilgi amaçlı: kilidi kim, ne zaman aldı
            fh.seek(1 if os.name == "nt" else 0)
            fh.truncate()
            fh.write(f" {os.getpid()} {dt.datetime.now(IST).isoformat(timespec='seconds')}\n".encode())
            fh.flush()
        except OSError:
            pass
        return self

    def __exit__(self, *exc) -> None:
        fh, self._fh = self._fh, None
        if fh is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


def load_state(folder: Path) -> dict:
    path = Path(folder) / STATE_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(folder: Path, state: dict) -> None:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / (STATE_FILE + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, folder / STATE_FILE)


def _outbox(folder: Path) -> list[dict]:
    try:
        raw = (Path(folder) / OUTBOX_FILE).read_bytes()
    except OSError:
        return []
    out = []
    for line in raw.split(b"\n"):
        try:
            entry = json.loads(line.decode("utf-8", errors="replace"))
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("text"):
            out.append(entry)
    return out


def _write_outbox(folder: Path, entries: list[dict]) -> None:
    folder = Path(folder)
    path = folder / OUTBOX_FILE
    if not entries:
        path.unlink(missing_ok=True)
        return
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / (OUTBOX_FILE + ".tmp")
    tmp.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")
    os.replace(tmp, path)


def keep_undelivered(folder: Path, text: str) -> str:
    """Önemli bildirimi gönderilmeden ÖNCE saklar (süreç gönderim sırasında kesilse de kaybolmasın);
    kaydın kimliğini döndürür."""
    ident = secrets.token_hex(6)
    entries = _outbox(folder)
    entries.append({"id": ident, "ts": dt.datetime.now(IST).isoformat(timespec="seconds"), "text": text})
    _write_outbox(folder, entries)
    return ident


def drop_undelivered(folder: Path, ident: str) -> None:
    _write_outbox(folder, [e for e in _outbox(folder) if e.get("id") != ident])


def flush_undelivered(folder: Path, tg: Telegram) -> None:
    """Önceki çalıştırmalardan iletilemeyen bildirimleri gönderir; gönderilemeyenler saklı kalır."""
    entries = _outbox(folder)
    left = []
    for i, entry in enumerate(entries):
        text = f"📮 Daha önce iletilemeyen bildirim ({str(entry.get('ts', ''))[:16]}):\n{entry['text']}"
        if not tg.try_send(text):
            left = entries[i:]
            break
    if len(left) != len(entries):
        _write_outbox(folder, left)


def sent_totals(journal: Journal, session: dt.date) -> tuple[float, float]:
    """Bu seansta daha önce gönderilmiş (reddedilmemiş) alış ve satışların limit fiyattan toplam tutarı."""
    rows: dict[str, tuple[str, float]] = {}
    for e in journal.entries():
        if e.get("event") == "sending" and e.get("session") == session.isoformat():
            rows[e.get("key", "")] = (e.get("side", ""), float(e.get("lots") or 0) * float(e.get("limit") or 0))
    buys = sum(v for k, (side, v) in rows.items() if side == "buy" and journal.was_sent(k))
    sells = sum(v for k, (side, v) in rows.items() if side == "sell" and journal.was_sent(k))
    return buys, sells


def account_fingerprint(brokage_id: str, account_id: str) -> str:
    return hashlib.sha256(f"{brokage_id}|{account_id}".encode()).hexdigest()[:12]


def journal_path(s: ExecSettings) -> Path:
    """Her kipin günlüğü ayrıdır: deneme kayıtları gerçek emirlerin gönderilmesini engellemesin."""
    return Path(s.klasor) / f"gunluk-{s.mod}.jsonl"


# ------------------------------------------------------------------------------- metinler
def tl(value: float, digits: int = 0) -> str:
    return f"{value:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def order_line(o: OrderRequest) -> str:
    bound = "≥" if o.side == "sell" else "≤"
    return f"{SIDE_TR[o.side]} {o.symbol:<6} {o.lots} lot {bound} {tl(o.limit_price, 2)}  (≈{tl(o.value)} TL)"


def approval_text(s: ExecSettings, ticket: Ticket, plan: Plan, broker: Broker, cash: float | None, code: str,
                  deadline: dt.datetime) -> str:
    head = "🔐 GERÇEK EMİR ONAYI" if s.live else "🧪 DENEME — gerçek emir GÖNDERİLMEYECEK"
    where = broker.describe() if hasattr(broker, "describe") else broker.name
    lines = [f"{head} — {ticket.session:%d.%m.%Y} seansı", f"Hesap: {where}", ""]
    lines += [order_line(o) for o in plan.orders]
    lines += ["", f"Toplam satış ≈ {tl(plan.sell_total)} TL, toplam alış ≈ {tl(plan.buy_total)} TL (limit fiyatlardan)."]
    if cash is not None and cash == cash:
        lines.append(f"Kullanılabilir bakiye: {tl(cash)} TL.")
    for note in plan.skipped:
        lines.append(f"• Gönderilmeyecek — {note}")
    for note in plan.notes:
        lines.append(f"• {note}")
    lines += [
        "",
        f"Onaylamak için {code} yazın. Vazgeçmek için RED yazın.",
        f"Onay {deadline:%H:%M}'e kadar geçerli. Emirler onaydan sonraki ilk uygun pencerede, limitli ve günlük "
        f"olarak gönderilir (açılış seansı {s.zaman.acilis_baslangic:%H:%M}-{s.zaman.acilis_bitis:%H:%M}, "
        f"sonrasında sürekli işlem). Onaydan sonra vazgeçerseniz ya da gönderimi durdurmak isterseniz DUR yazın.",
        "Bugün borsa tatil ya da yarım günse RED yazın.",
    ]
    return "\n".join(lines)


def state_line(order: OrderRequest, st: OrderState) -> str:
    text = STATUS_TR.get(st.status, st.status)
    head = f"{SIDE_TR[order.side]} {order.symbol:<6} {order.lots} lot: {text}"
    if st.filled_lots:
        price = f" @ {tl(st.avg_price, 2)}" if st.avg_price else ""
        head += f" {st.filled_lots}/{order.lots}{price}"
    elif st.status == "accepted":
        head += f" (limit {tl(order.limit_price, 2)})"
    if st.status in ("rejected", "unknown") and st.message:
        head += f" — {st.message}"
    return head


@dataclass
class RunResult:
    status: str
    message: str = ""
    states: dict[str, OrderState] = field(default_factory=dict)
    orders: dict[str, OrderRequest] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in ("done", "no_orders", "not_today", "already_done", "rejected", "timeout")


def report_text(s: ExecSettings, ticket: Ticket, res: RunResult, extra: list[str]) -> str:
    live = s.live
    title = "📨 Emir raporu" if live else "🧪 Deneme raporu (gerçek emir gönderilmedi)"
    lines = [f"{title} — {ticket.session:%d.%m.%Y}"]
    lines += [state_line(res.orders[k], st) for k, st in res.states.items()]
    lines += [f"• {e}" for e in extra]
    if live and any(st.status in ("accepted", "partial") for st in res.states.values()):
        lines.append("Bekleyen emirler gün sonuna kadar geçerlidir; gerçekleşmezse kendiliğinden düşer. "
                     "Hepsini iptal etmek için bilgisayarda: bistbot emir --iptal")
    if any(st.status == "unknown" for st in res.states.values()):
        lines.append("⚠️ BELİRSİZ emir var: Matriks IQ'da emirlerinizi kontrol edin. Bot bu emri yeniden GÖNDERMEZ.")
    return "\n".join(lines)


# ------------------------------------------------------------------------------- zamanlama
def send_window(now: dt.datetime, z: Schedule) -> tuple[dt.datetime | None, str]:
    """Emir gönderilebilecek en erken an ve o anın seansı (``acilis`` | ``surekli`` | ``kapali``)."""
    at = lambda t: dt.datetime.combine(now.date(), t, now.tzinfo)  # noqa: E731
    if now < at(z.acilis_baslangic):
        return at(z.acilis_baslangic), "acilis"
    if now <= at(z.acilis_bitis):
        return now, "acilis"
    if now < at(z.surekli_baslangic):
        return at(z.surekli_baslangic), "surekli"
    if now <= at(z.surekli_bitis):
        return now, "surekli"
    return None, "kapali"


class _Halt(Exception):
    """Gönderimi durduran neden (kullanıcı DUR dedi, bağlantı koptu, belirsiz emir ...)."""


class _Batch:
    """Tek bir fişin gönderimi boyunca taşınan durum."""

    def __init__(self, s: ExecSettings, ticket: Ticket, broker: Broker, tg: Telegram | None, journal: Journal,
                 clock: Clock):
        self.s, self.ticket, self.broker, self.tg, self.journal, self.clock = s, ticket, broker, tg, journal, clock
        self.states: dict[str, OrderState] = {}
        self.orders: dict[str, OrderRequest] = {}
        self.notes: list[str] = []
        self.recoveries = 0
        self.stop_warned = False
        #: Her emir için görülen en büyük gerçekleşme (bir kez gerçekleşen emir yeniden denenmez).
        self.max_filled: dict[str, int] = {}
        #: Gönderimden hemen önce hesapta lot kalmadığı için çıkarılan satışlar (açık iş sayılır).
        self.dropped_sells: list[OrderRequest] = []
        #: Onay öncesinde okunan pozisyonlar (gönderim anındaki okumayla karşılaştırılır).
        self.positions_at_plan: dict[str, int] = {}

    # -- yardımcılar -------------------------------------------------------------------
    def say(self, text: str, important: bool = False) -> None:
        """Bildirim gönderir. Önemli olanlar (rapor, durdurma, uyarı) geçici ağ hatasında birkaç dakika
        yeniden denenir; yine iletilemezse saklanır ve sonraki çalıştırmanın başında gönderilir."""
        log.info("%s", text.replace("\n", " | "))
        if self.tg is None:
            return
        if not important:
            self.tg.try_send(text)
            return
        ident = None
        try:
            ident = keep_undelivered(self.s.klasor, text)  # önce sakla: gönderim sırasında kesilirse kaybolmasın
        except OSError:
            log.exception("bildirim saklanamadı")
        try:
            ok = self.tg.deliver(text, clock=lambda: self.clock.now().timestamp(), sleep=self.clock.sleep)
        except Exception:  # bildirim hatası akışı bozmasın
            log.exception("bildirim gönderilemedi")
            ok = False
        if ok and ident is not None:
            try:
                drop_undelivered(self.s.klasor, ident)
            except OSError:
                log.exception("saklanan bildirim silinemedi")

    def stop_reason(self) -> str | None:
        if (Path(self.s.klasor) / STOP_FILE).exists():
            return f"{STOP_FILE} dosyası bulundu"
        if self.tg is not None:
            if self.tg.stop_requested(0):
                return "Telegram'dan durdurma istendi"
            if self.tg.stop_failures >= 3 and not self.stop_warned:
                # Mesajlar okunamıyor: kullanıcı DUR yazdığında işe yaramayacağını bilmeli.
                self.stop_warned = True
                self.tg.try_send(f"⚠️ Telegram mesajlarınız şu an okunamıyor; DUR yazmanız işe yaramayabilir. Durdurmak "
                                 f"için bilgisayarda {Path(self.s.klasor) / STOP_FILE} adlı boş bir dosya oluşturun.")
        return None

    def wait_until(self, when: dt.datetime) -> None:
        """``when`` anına kadar bekler; arada durdurma isteğini yoklar."""
        while True:
            remaining = (when - self.clock.now()).total_seconds()
            if remaining <= 0:
                return
            reason = self.stop_reason()
            if reason:
                raise _Halt(reason)
            self.clock.sleep(min(remaining, 20.0))

    def wait_for_window(self) -> str:
        when, phase = send_window(self.clock.now(), self.s.zaman)
        if when is None:
            raise _Halt("seans kapandı; emirler gönderilmedi")
        self.wait_until(when)
        if self.clock.now().date() != self.ticket.session:
            raise _Halt("gün değişti; emirler gönderilmedi")
        return phase

    def place(self, order: OrderRequest) -> OrderState:
        """Tek emri gönderir. Günlüğe ÖNCE niyet, sonra sonuç yazılır."""
        reason = self.stop_reason()
        if reason:
            raise _Halt(reason)
        if self.wait_for_window() == "kapali":
            raise _Halt("seans kapandı")
        # Son savunma hattı: günlükte bu emir (ilk deneme ya da ikinci tur) gönderilmiş görünüyorsa gönderme.
        base = order.key[:-len(RETRY)] if order.key.endswith(RETRY) else order.key
        if self.journal.was_sent(order.key) or (order.key == base and self.journal.was_sent(base + RETRY)):
            raise _Halt(f"{order.symbol} emri günlükte zaten gönderilmiş görünüyor; ikinci kez gönderilmedi")
        self.orders[order.key] = order
        self.journal.record("sending", order.key, symbol=order.symbol, side=order.side, lots=order.lots,
                            limit=order.limit_price, digest=self.ticket.digest, session=str(self.ticket.session),
                            as_of=str(self.ticket.as_of))
        try:
            state = self.broker.place(order)
        except NotSent as exc:
            # Bağlantı daha gönderimden önce yoktu: emir kesinlikle gitmedi, "belirsiz" sayılmaz.
            self.record("not_sent", order.key, message=str(exc))
            raise _Halt(f"{order.symbol} emri gönderilemedi (hiçbir şey gitmedi): {exc}") from exc
        except BrokerError as exc:
            # Yön uyuşmazlığında emrin gerçek akıbeti (iptal/gerçekleşti/çalışıyor) hatayla birlikte gelir.
            state = getattr(exc, "state", None) or OrderState(order.key, "unknown", message=str(exc))
            self.states[order.key] = state
            self.record(state.status, order.key, broker_id=state.broker_id, filled=state.filled_lots,
                        avg=state.avg_price, message=str(exc))
            raise _Halt(str(exc)) from exc
        except Exception as exc:
            # Beklenmeyen hata (ör. tanınmayan bir yanıt biçimi): emir gitmiş olabilir, akıbeti belirsiz.
            log.exception("emir gönderilirken beklenmeyen hata")
            text = f"beklenmeyen hata ({type(exc).__name__}: {exc})"
            self.states[order.key] = OrderState(order.key, "unknown", message=text)
            self.record("unknown", order.key, message=text)
            raise _Halt(f"{order.symbol} emrinde {text}") from exc
        self.states[order.key] = state
        self.max_filled[order.key] = max(self.max_filled.get(order.key, 0), state.filled_lots)
        self.record(state.status, order.key, broker_id=state.broker_id, filled=state.filled_lots,
                    avg=state.avg_price, message=state.message)
        if state.status == "unknown":
            raise _Halt(f"{order.symbol} emrinin akıbeti belirsiz: {state.message}")
        self.clock.sleep(0.25)
        return state

    def record(self, event: str, key: str, **data) -> None:
        """Emir gönderildikten SONRAKİ günlük kaydı: dosya yazılamasa da akış ve rapor sürer."""
        try:
            self.journal.record(event, key, **data)
        except OSError as exc:
            note = f"⚠️ Emir günlüğüne yazılamadı ({type(exc).__name__}); durumları Matriks IQ'dan kontrol edin."
            if note not in self.notes:
                self.notes.append(note)

    def sync(self) -> bool:
        """Aracı kurumdan emir durumlarını sorgular (kaçan bildirimlere karşı). Başarısızsa not düşer."""
        fn = getattr(self.broker, "sync", None)
        if fn is None:
            return True
        try:
            fn()
            return True
        except BrokerError as exc:
            self.lost(exc)
            return False

    def lost(self, exc: Exception) -> None:
        note = (f"⚠️ Emir durumları İZLENEMEDİ ({exc}). Aşağıdaki durumlar ESKİ olabilir; gerçekleşmeleri "
                "Matriks IQ'dan kontrol edin.")
        if note not in self.notes:
            self.notes.append(note)

    def recover(self) -> bool:
        """İzleme koptuğunda (ör. Matriks IQ yeniden başlatıldı) bağlantıyı bir kez yeniden kurmayı dener."""
        if self.recoveries >= 3:
            return False
        self.recoveries += 1
        try:
            ready = getattr(self.broker, "ensure_ready", None)
            if ready is None:
                return False
            ready()
            sync = getattr(self.broker, "sync", None)
            if sync is not None:
                sync()
            return True
        except BrokerError:
            return False

    def poll(self) -> bool:
        """Bitmemiş emirlerin durumunu bir kez okur; izleme koptuysa ``False`` döner."""
        for key in [k for k, st in self.states.items() if not st.done and st.status != "unknown"]:
            try:
                try:
                    new = self.broker.refresh(self.states[key])
                except BrokerError:
                    if not self.recover():
                        raise
                    new = self.broker.refresh(self.states[key])
            except BrokerError as exc:
                self.lost(exc)
                return False
            old = self.states[key]
            if (new.status, new.filled_lots, new.broker_id) != (old.status, old.filled_lots, old.broker_id):
                self.record(new.status, key, broker_id=new.broker_id, filled=new.filled_lots,
                            avg=new.avg_price, message=new.message)
            self.states[key] = new
            self.max_filled[key] = max(self.max_filled.get(key, 0), new.filled_lots)
        return True

    def monitor(self, until: dt.datetime) -> None:
        """Bitmemiş emirlerin durumunu ``until`` anına kadar izler; yarım dakikada bir ve en sonda
        durumları aracı kurumdan ayrıca sorgular."""
        working = lambda: any(not st.done and st.status != "unknown" for st in self.states.values())  # noqa: E731
        last_sync = self.clock.now()
        while True:
            if not self.poll() or not working():
                return
            now = self.clock.now()
            if now >= until:
                break
            if (now - last_sync).total_seconds() >= 30.0:
                last_sync = now
                if not self.sync():
                    return
            self.clock.sleep(2.0)
        if self.sync():
            self.poll()

    def monitor_end(self, phase: str) -> dt.datetime:
        now = self.clock.now()
        end = now + dt.timedelta(minutes=self.s.zaman.izleme_dakika)
        if phase == "acilis":
            end = max(end, dt.datetime.combine(now.date(), OPENING_PRINT, now.tzinfo))
        return end

    # -- gönderim ----------------------------------------------------------------------
    def read_cash(self) -> float | None:
        """Harcanabilir bakiye: aracı kurumdan okunan tutardan, botun bugün gönderdiği ve hâlâ bekleyen
        alışların gerçekleşmemiş kısmı düşülür (aracı kurumun bunu zaten düşüp düşmediği bilinmediği
        için temkinli tarafta kalınır)."""
        try:
            cash = self.broker.cash()
        except BrokerError:
            return None
        if cash is None or cash != cash:
            return None
        return cash - self.journal.working_buys(str(self.ticket.session)) * (1.0 + COST_MARGIN)

    def prepare(self, plan: Plan) -> None:
        """Göndermeden hemen önce (onay saatler önce verilmiş olabilir): bağlantı ve oturum yerinde mi,
        satılacak lotlar hâlâ hesapta mı? Satışlar yalnızca küçültülür; hiçbir emir büyütülmez."""
        try:
            ready = getattr(self.broker, "ensure_ready", None)
            if ready is not None:
                ready()
            held = self.broker.positions()
        except BrokerError as exc:
            raise _Halt(f"gönderimden önce aracı kurum bağlantısı doğrulanamadı: {exc}") from exc
        if not held and self.positions_at_plan and any(o.side == "sell" for o in plan.orders):
            # Onay öncesinde lotlar görünüyordu, şimdi liste bomboş: büyük olasılıkla pozisyonlar henüz
            # yüklenmedi (ör. Matriks IQ yeniden başladı). Satışsız alışa girmek yerine hiçbir şey gönderme.
            raise _Halt("hesaptaki lotlar şu an okunamıyor (pozisyon listesi boş döndü); hiçbir emir gönderilmedi")
        checked: list[OrderRequest] = []
        for order in plan.orders:
            if order.side == "sell":
                have = int(held.get(order.symbol, 0))
                if have <= 0:
                    self.notes.append(f"{order.symbol} satışı gönderilmedi: hesapta artık satılabilir lot yok.")
                    self.dropped_sells.append(order)
                    continue
                if have < order.lots:
                    self.notes.append(f"{order.symbol}: hesapta {have} lot kaldığı için {order.lots} yerine {have} lot satılıyor.")
                    order = OrderRequest(order.key, order.symbol, order.side, have, order.limit_price)
            checked.append(order)
        plan.orders[:] = checked

    def send_all(self, plan: Plan, cash_known: bool) -> None:
        deferred: list[OrderRequest] = []
        phase = self.wait_for_window()
        self.prepare(plan)
        # Bakiye de gönderimden hemen önce yeniden okunur (onaydan bu yana değişmiş olabilir).
        budget = self.read_cash() if cash_known else None
        if cash_known and budget is None:
            raise _Halt("bakiye yeniden okunamadı; emirler gönderilmedi")
        for order in plan.orders:
            if order.side == "buy" and budget is not None:
                need = order.value * (1.0 + COST_MARGIN)
                if need > budget:
                    deferred.append(order)
                    self.journal.record("deferred", order.key, symbol=order.symbol, lots=order.lots)
                    continue
                budget -= need
            self.place(order)
        self.monitor(self.monitor_end(phase))
        self.second_round(plan, deferred)

    def second_round(self, plan: Plan, deferred: list[OrderRequest]) -> None:
        """Satışlar gerçekleştiyse, parası yetmediği için bekleyen/reddedilen alışları bir kez daha dener.

        Bakiye biliniyorsa yeniden okunur ve yalnızca paraya sığan alışlar gönderilir; bakiye
        okunamıyorsa ertelenen alışlar gönderilmez.
        """
        rejected = [o for o in plan.orders if o.side == "buy" and o.key in self.states
                    and self.states[o.key].status == "rejected" and self.max_filled.get(o.key, 0) == 0]
        waiting = {o.key for o in deferred} | {o.key for o in rejected}
        candidates = [o for o in plan.orders if o.key in waiting]  # fişteki öncelik sırası korunur
        if not candidates:
            return
        names = ", ".join(o.symbol for o in candidates)
        if not self.s.zaman.ikinci_tur:
            self.notes.append(f"Gönderilmeyen alışlar: {names} (ikinci tur kapalı).")
            return
        sells = [o for o in plan.orders if o.side == "sell"]
        if sells and not any(self.states.get(o.key) and self.states[o.key].filled_lots > 0 for o in sells):
            self.notes.append(f"Satışlar gerçekleşmediği için şu alışlar gönderilmedi: {names}.")
            return
        when, phase = send_window(self.clock.now(), self.s.zaman)
        if when is None:
            self.notes.append(f"Seans kapandığı için şu alışlar gönderilmedi: {names}.")
            return
        if phase == "acilis":  # açılış fiyatı belirlenmeden satış parası kullanılamaz
            at = dt.datetime.combine(when.date(), self.s.zaman.surekli_baslangic, when.tzinfo)
            self.wait_until(at)
        budget = None
        if deferred:
            budget = self.read_cash()
            if budget is None:
                self.notes.append("Bakiye yeniden okunamadığı için şu alışlar gönderilmedi: "
                                  + ", ".join(o.symbol for o in deferred) + ".")
                candidates = [o for o in candidates if o not in deferred]
        short: list[str] = []
        for order in candidates:
            retry = OrderRequest(order.key + RETRY, order.symbol, order.side, order.lots, order.limit_price)
            if self.journal.was_sent(retry.key):
                self.notes.append(f"{order.symbol} alışı daha önce ikinci turda gönderilmişti; yeniden gönderilmedi.")
                continue
            if budget is not None:
                need = order.value * (1.0 + COST_MARGIN)
                if need > budget:
                    short.append(order.symbol)
                    continue
                budget -= need
            self.place(retry)
        if short:
            self.notes.append("Bakiye yetmediği için şu alışlar gönderilmedi: " + ", ".join(short) + ".")
        end = self.clock.now() + dt.timedelta(minutes=min(self.s.zaman.izleme_dakika, 5.0))
        self.monitor(end)


def describe_done(journal: Journal, key: str) -> str:
    """Daha önce gönderilmiş bir emrin onay mesajındaki açıklaması (günlükteki son duruma göre)."""
    last = journal.last_events()
    events = [last[k]["event"] for k in (key, key + RETRY) if k in last]
    if any(e in ("sending", "unknown") for e in events):
        return ("önceki çalıştırmada akıbeti BELİRSİZ kaldı; Matriks IQ'da kontrol edin, gerekiyorsa elle girin "
                "(bot yeniden göndermeyecek)")
    if "cancelled" in events:
        return "daha önce gönderildi ve iptal edildi"
    return "daha önce gönderildi"


def run_batch(s: ExecSettings, ticket: Ticket, broker: Broker, tg: Telegram | None, journal: Journal,
              clock: Clock | None = None) -> RunResult:
    """Bir emir fişini baştan sona işler. Çağıran ``RunLock`` almış olmalıdır."""
    clock = clock or Clock()
    batch = _Batch(s, ticket, broker, tg, journal, clock)
    now = clock.now()
    digest = ticket.digest

    if tg is not None:
        flush_undelivered(s.klasor, tg)
    if not ticket.orders:
        return RunResult("no_orders", "Bugün için emir yok.")
    if journal.batch_done(digest):
        return RunResult("already_done", "Bu emir fişi daha önce işlendi.")
    if (Path(s.klasor) / STOP_FILE).exists():
        return RunResult("stopped", f"Durduruldu: {Path(s.klasor) / STOP_FILE} dosyası var. Devam etmek için silin.")

    calendar = session_problems(ticket, now, s.tatiller)
    if calendar:
        # Olağan durum (ör. fiş yarınki seans için): sessizce çık.
        return RunResult("not_today", "Bugün gönderilecek emir yok: " + "; ".join(calendar) + ".")
    keys = [ticket.order_key(o) for o in ticket.orders]
    done = {k: describe_done(journal, k) for k in keys if journal.order_sent(k)}
    sent_buy, sent_sell = sent_totals(journal, ticket.session)
    problems = check_ticket(ticket, now, s.sinirlar, set(done), sent_buy, sent_sell)
    when, _ = send_window(now, s.zaman)
    deadline = dt.datetime.combine(now.date(), s.zaman.onay_son, now.tzinfo)
    if when is None or now >= deadline:
        problems.append("bugünkü gönderim/onay süresi geçti")
    if problems:
        text = "⛔ Emirler GÖNDERİLMEDİ — güvenlik kontrolü:\n" + "\n".join(f"• {p}" for p in problems)
        # Aynı fiş için aynı uyarı yalnızca bir kez bildirilir.
        seen = any(e.get("event") == "blocked" and e.get("digest") == digest and e.get("problems") == problems
                   for e in journal.entries())
        journal.record("blocked", digest=digest, problems=problems)
        if not seen:
            batch.say(text, important=True)
        return RunResult("blocked", text)

    try:
        broker.connect()
        positions = broker.positions()
        cash = broker.cash()
    except BrokerError as exc:
        journal.record("error", digest=digest, message=str(exc))
        text = f"⛔ Emirler GÖNDERİLMEDİ — aracı kurum bağlantısı: {exc}"
        batch.say(text, important=True)
        return RunResult("error", text)
    cash = cash if cash is not None and cash == cash else None

    plan = build_plan(ticket, positions, cash, done)
    batch.positions_at_plan = dict(positions)
    if plan.unsellable and any(o.side == "buy" for o in plan.orders):
        plan.notes.insert(0, "⚠️ Satış gönderilemeyeceği için alışların parası eksik kalabilir. Lotlarınız hesapta "
                             "görünmüyorsa RED yazın, Matriks IQ'da girişinizi kontrol edip yeniden çalıştırın.")
    between = trading_days_between(ticket, s.tatiller)
    if between:
        plan.notes.insert(0, (
            f"⚠️ Bu fiş {ticket.as_of:%d.%m.%Y} verisine dayanıyor; arada işlem günü var "
            f"({', '.join(f'{d:%d.%m}' for d in between[:3])}). Bülten gecikmiş olabilir; emin değilseniz RED yazın. "
            "(O gün tatil idiyse emir-ayar.toml içindeki tatiller listesine ekleyin.)"))
    if not plan.orders:
        text = "Gönderilecek emir yok.\n" + "\n".join(f"• {n}" for n in plan.skipped + plan.notes)
        if plan.unsellable:
            # Satılacak lot hesapta görünmüyor (pozisyonlar henüz yüklenmemiş olabilir): fiş "işlendi"
            # sayılmaz, yeniden çalıştırılabilir.
            text = "⚠️ " + text + "\nHesaptaki lotlar görünmüyorsa Matriks IQ'da girişinizi kontrol edip yeniden çalıştırın."
            seen = any(e.get("event") == "nothing_sendable" and e.get("digest") == digest for e in journal.entries())
            journal.record("nothing_sendable", digest=digest)
            if not seen:
                batch.say(text, important=True)
            return RunResult("nothing_sendable", text)
        journal.record("batch_done", digest=digest, note="gönderilecek emir kalmadı")
        batch.say(text)
        return RunResult("done", text)

    journal.record("batch_start", digest=digest, mode=s.mod, orders=len(plan.orders))
    if tg is not None:
        if tg.is_group and tg.can_read_group_messages() is False:
            plan.notes.append("⚠️ Bot bu grupta düz mesajları göremiyor (gizlilik kipi açık). Kodu bu mesaja YANIT olarak "
                              "yazın; durdurmak için /dur yazın. Kalıcı çözüm: BotFather → /setprivacy → Disable.")
        code = new_code()
        text = approval_text(s, ticket, plan, broker, cash, code, deadline)
        label = f"{ticket.session:%d.%m.%Y} {'GERÇEK' if s.live else 'DENEME'} ({len(plan.orders)} emir)"
        journal.record("approval_requested", digest=digest)
        decision = request_approval(tg, text, code, deadline.timestamp(), clock=lambda: clock.now().timestamp(),
                                    sleep=clock.sleep, label=label)
    elif s.live:
        return RunResult("error", "Gerçek emir kipi Telegram onayı olmadan çalışmaz.")
    else:
        decision = Decision("approved", "deneme kipi, Telegram ayarlı değil")
        log.info("Telegram ayarlı değil; deneme kipinde onay beklenmeden devam ediliyor")
    journal.record(decision.status, digest=digest, detail=decision.detail)
    if not decision.approved:
        if decision.by_user:
            text = "Emirler GÖNDERİLMEDİ: vazgeçtiniz."
        elif decision.status == "rejected":
            text = f"Emirler GÖNDERİLMEDİ: onay verilmedi ({decision.detail})."
        else:
            text = f"Emirler GÖNDERİLMEDİ: onay gelmedi ({decision.detail})."
        batch.say(text, important=True)
        return RunResult(decision.status, text)

    halted = None
    try:
        if tg is not None:
            batch.say("Onay alındı. Emirler ilk uygun pencerede gönderilecek. Vazgeçerseniz DUR yazın.")
        if clock.now().date() != ticket.session:
            raise _Halt("gün değişti")
        batch.send_all(plan, cash is not None)
    except _Halt as exc:
        halted = str(exc)
    except Exception as exc:  # beklenmeyen her hata: kullanıcı yine de neyin gidip neyin gitmediğini öğrenmeli
        log.exception("emir gönderimi beklenmeyen bir hatayla kesildi")
        halted = f"beklenmeyen hata ({type(exc).__name__}: {exc})"
    if halted:
        batch.record("halt", "", digest=digest, reason=halted)
        try:
            batch.monitor(clock.now() + dt.timedelta(seconds=20))
        except Exception:  # izleme başarısız olsa da rapor verilmeli
            log.exception("durdurma sonrası izleme başarısız")
    try:
        broker.close()
    except Exception:
        log.debug("bağlantı kapatılırken hata", exc_info=True)

    result = RunResult("halted" if halted else "done", states=batch.states, orders=batch.orders)
    extra = [f"Gönderilmedi — {n}" for n in plan.skipped] + batch.notes
    unsent = [o for o in plan.orders if o.key not in batch.states and (o.key + RETRY) not in batch.states]
    name = lambda o: f"{o.symbol} ({'alış' if o.side == 'buy' else 'satış'})"  # noqa: E731
    final = lambda o: batch.states.get(o.key + RETRY) or batch.states.get(o.key)  # noqa: E731
    refused = [o for o in plan.orders if final(o) is not None and final(o).status == "rejected"]
    if halted:
        extra.insert(0, f"⛔ Gönderim DURDU: {halted}")
        if unsent:
            extra.append("Gönderilmeyen emirler: " + ", ".join(name(o) for o in unsent))
    elif unsent or refused or batch.dropped_sells or plan.unsellable:
        # Fiş "tamamlandı" sayılmaz: nedeni giderilince yeniden çalıştırılırsa bu emirler yeni onayla denenir.
        # Hesapta lot görünmediği için gönderilemeyen satışlar da açık iş sayılır.
        open_orders = [name(o) for o in unsent + refused + batch.dropped_sells]
        if plan.unsellable:
            open_orders.append(f"hesapta lot görünmediği için planlanamayan {plan.unsellable} satış")
        extra.append("Gönderilmeyen ya da reddedilen emirler var: " + ", ".join(dict.fromkeys(open_orders))
                     + ". Yeniden denemek için programı bir kez daha çalıştırın (yeniden onay istenir) ya da elle girin.")
    else:
        batch.record("batch_done", "", digest=digest)
    result.message = report_text(s, ticket, result, extra)
    batch.say(result.message, important=True)
    return result
