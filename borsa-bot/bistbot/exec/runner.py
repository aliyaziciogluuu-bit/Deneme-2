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
import time
from dataclasses import dataclass, field
from pathlib import Path

from .base import Broker, BrokerError, OrderRequest, OrderState
from .guard import COST_MARGIN, Plan, build_plan, check_ticket, session_problems
from .journal import Journal
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
    """Aynı anda iki çalıştırmanın emir göndermesini önleyen kilit dosyası."""

    def __init__(self, folder: Path, stale_hours: float = 12.0):
        self.path = Path(folder) / LOCK_FILE
        self.stale = stale_hours * 3600.0

    def __enter__(self) -> "RunLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in (1, 2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                age = time.time() - self.path.stat().st_mtime
                if attempt == 1 and age > self.stale:
                    self.path.unlink(missing_ok=True)  # eski, yarıda kalmış çalıştırmanın kilidi
                    continue
                raise AlreadyRunning(
                    f"başka bir emir çalıştırması sürüyor (kilit: {self.path}). Emin değilseniz Matriks IQ'da "
                    "emirlerinizi kontrol edin; çalışan başka program yoksa bu dosyayı silin."
                ) from None
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(f"{os.getpid()} {dt.datetime.now(IST).isoformat(timespec='seconds')}\n")
            return self
        raise AlreadyRunning("kilit alınamadı")

    def __exit__(self, *exc) -> None:
        self.path.unlink(missing_ok=True)


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
        f"sonrasında sürekli işlem). Gönderim sırasında durdurmak için DUR yazın.",
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

    # -- yardımcılar -------------------------------------------------------------------
    def say(self, text: str) -> None:
        log.info("%s", text.replace("\n", " | "))
        if self.tg is not None:
            self.tg.try_send(text)

    def stop_reason(self) -> str | None:
        if (Path(self.s.klasor) / STOP_FILE).exists():
            return f"{STOP_FILE} dosyası bulundu"
        if self.tg is not None and self.tg.stop_requested(0):
            return "Telegram'dan DUR yazıldı"
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
        self.orders[order.key] = order
        self.journal.record("sending", order.key, symbol=order.symbol, side=order.side, lots=order.lots,
                            limit=order.limit_price, digest=self.ticket.digest)
        try:
            state = self.broker.place(order)
        except BrokerError as exc:
            state = OrderState(order.key, "unknown", message=str(exc))
            self.states[order.key] = state
            self.journal.record("unknown", order.key, message=str(exc))
            raise _Halt(str(exc)) from exc
        self.states[order.key] = state
        self.journal.record(state.status, order.key, broker_id=state.broker_id, filled=state.filled_lots,
                            avg=state.avg_price, message=state.message)
        if state.status == "unknown":
            raise _Halt(f"{order.symbol} emrinin akıbeti belirsiz: {state.message}")
        self.clock.sleep(0.25)
        return state

    def monitor(self, until: dt.datetime) -> None:
        """Bitmemiş emirlerin durumunu ``until`` anına kadar izler."""
        while True:
            open_keys = [k for k, st in self.states.items() if not st.done and st.status != "unknown"]
            for key in open_keys:
                try:
                    new = self.broker.refresh(self.states[key])
                except BrokerError as exc:
                    self.notes.append(f"Emir durumu izlenemedi: {exc}")
                    return
                old = self.states[key]
                if (new.status, new.filled_lots) != (old.status, old.filled_lots):
                    self.journal.record(new.status, key, broker_id=new.broker_id, filled=new.filled_lots,
                                        avg=new.avg_price, message=new.message)
                self.states[key] = new
            if not any(not st.done and st.status != "unknown" for st in self.states.values()):
                return
            if self.clock.now() >= until:
                return
            self.clock.sleep(2.0)

    def monitor_end(self, phase: str) -> dt.datetime:
        now = self.clock.now()
        end = now + dt.timedelta(minutes=self.s.zaman.izleme_dakika)
        if phase == "acilis":
            end = max(end, dt.datetime.combine(now.date(), OPENING_PRINT, now.tzinfo))
        return end

    # -- gönderim ----------------------------------------------------------------------
    def send_all(self, plan: Plan, cash: float | None) -> None:
        budget = cash if cash is not None and cash == cash else None
        deferred: list[OrderRequest] = []
        phase = self.wait_for_window()
        for order in plan.orders:
            if order.side == "buy" and budget is not None:
                need = order.value * (1.0 + COST_MARGIN)
                if need > budget:
                    deferred.append(order)
                    self.orders[order.key] = order
                    self.journal.record("deferred", order.key, symbol=order.symbol, lots=order.lots)
                    continue
                budget -= need
            self.place(order)
        self.monitor(self.monitor_end(phase))
        self.second_round(plan, deferred)

    def second_round(self, plan: Plan, deferred: list[OrderRequest]) -> None:
        """Satışlar gerçekleştiyse, parası yetmediği için bekleyen/reddedilen alışları bir kez daha dener."""
        rejected = [o for o in plan.orders if o.side == "buy" and o.key in self.states
                    and self.states[o.key].status == "rejected" and self.states[o.key].filled_lots == 0]
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
        for order in candidates:
            retry = OrderRequest(order.key + "|2", order.symbol, order.side, order.lots, order.limit_price)
            if self.journal.was_sent(retry.key):
                continue
            self.place(retry)
        end = self.clock.now() + dt.timedelta(minutes=min(self.s.zaman.izleme_dakika, 5.0))
        self.monitor(end)


def run_batch(s: ExecSettings, ticket: Ticket, broker: Broker, tg: Telegram | None, journal: Journal,
              clock: Clock | None = None) -> RunResult:
    """Bir emir fişini baştan sona işler. Çağıran ``RunLock`` almış olmalıdır."""
    clock = clock or Clock()
    batch = _Batch(s, ticket, broker, tg, journal, clock)
    now = clock.now()
    digest = ticket.digest

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
    problems = check_ticket(ticket, now, s.sinirlar)
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
            batch.say(text)
        return RunResult("blocked", text)

    try:
        broker.connect()
        positions = broker.positions()
        cash = broker.cash()
    except BrokerError as exc:
        journal.record("error", digest=digest, message=str(exc))
        text = f"⛔ Emirler GÖNDERİLMEDİ — aracı kurum bağlantısı: {exc}"
        batch.say(text)
        return RunResult("error", text)

    keys = [ticket.order_key(o) for o in ticket.orders]
    last = journal.last_events()
    done = {k for k in keys if journal.was_sent(k)}
    plan = build_plan(ticket, positions, cash, done)
    for key in sorted(done):
        if last.get(key, {}).get("event") in ("sending", "unknown"):
            plan.notes.append(f"{key.split('|')[1]}: önceki çalıştırmada akıbeti BELİRSİZ kaldı; Matriks IQ'da kontrol "
                              "edin, gerekiyorsa elle girin. Bot yeniden göndermeyecek.")
    if not plan.orders:
        text = "Gönderilecek emir kalmadı.\n" + "\n".join(f"• {n}" for n in plan.skipped + plan.notes)
        journal.record("batch_done", digest=digest, note="gönderilecek emir yok")
        batch.say(text)
        return RunResult("done", text)

    journal.record("batch_start", digest=digest, mode=s.mod, orders=len(plan.orders))
    if tg is not None:
        code = new_code()
        text = approval_text(s, ticket, plan, broker, cash, code, deadline)
        journal.record("approval_requested", digest=digest)
        decision = request_approval(tg, text, code, deadline.timestamp(), clock=lambda: clock.now().timestamp(),
                                    sleep=clock.sleep)
    elif s.live:
        return RunResult("error", "Gerçek emir kipi Telegram onayı olmadan çalışmaz.")
    else:
        decision = Decision("approved", "deneme kipi, Telegram ayarlı değil")
        log.info("Telegram ayarlı değil; deneme kipinde onay beklenmeden devam ediliyor")
    journal.record(decision.status, digest=digest, detail=decision.detail)
    if not decision.approved:
        text = ("Emirler GÖNDERİLMEDİ: " + ("reddettiniz." if decision.status == "rejected" else
                                            f"onay gelmedi ({decision.detail})."))
        batch.say(text)
        return RunResult(decision.status, text)

    halted = None
    try:
        if tg is not None:
            batch.say("Onay alındı. Emirler ilk uygun pencerede gönderilecek.")
        if clock.now().date() != ticket.session:
            raise _Halt("gün değişti")
        batch.send_all(plan, cash)
    except _Halt as exc:
        halted = str(exc)
        journal.record("halt", digest=digest, reason=halted)
        try:
            batch.monitor(clock.now() + dt.timedelta(seconds=20))
        except Exception:  # izleme başarısız olsa da rapor verilmeli
            log.exception("durdurma sonrası izleme başarısız")
    finally:
        try:
            broker.close()
        except Exception:
            log.debug("bağlantı kapatılırken hata", exc_info=True)

    result = RunResult("halted" if halted else "done", states=batch.states, orders=batch.orders)
    extra = [f"Gönderilmedi — {n}" for n in plan.skipped] + batch.notes
    unsent = [o for o in plan.orders if o.key not in batch.states and (o.key + "|2") not in batch.states]
    if halted:
        extra.insert(0, f"⛔ Gönderim DURDU: {halted}")
        if unsent:
            extra.append("Gönderilmeyen emirler: " + ", ".join(f"{o.symbol} ({'alış' if o.side == 'buy' else 'satış'})"
                                                              for o in unsent))
    else:
        journal.record("batch_done", digest=digest)
    result.message = report_text(s, ticket, result, extra)
    batch.say(result.message)
    return result
