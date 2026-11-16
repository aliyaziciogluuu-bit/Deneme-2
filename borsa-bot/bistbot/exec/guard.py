"""İşlem öncesi kontroller: emir fişi sınırları aşıyorsa hiçbir emir gönderilmez.

İki aşama vardır:

* ``check_ticket``: fişin kendisi güvenli mi (tarih, tazelik, tutar ve fiyat sınırları)?
  Tek bir ihlal bile tüm fişi durdurur; "kısmen güvenli" fiş yoktur.
* ``build_plan``: fiş, hesaptaki gerçek pozisyonlarla karşılaştırılır. Satışlar eldeki
  satılabilir lotla sınırlanır (açığa satış asla oluşmaz); farklar onay mesajında gösterilir.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .base import OrderRequest
from .settings import Limits
from .ticket import Ticket

#: Alışlarda komisyon/vergi için bırakılan pay (limit fiyat üzerinden).
COST_MARGIN = 0.003
#: Fiyat adımı tablosu (Pay Piyasası, 06.11.2023'ten beri): (alt sınır, adım).
TICKS = ((2500.0, 2.50), (1000.0, 1.00), (500.0, 0.50), (250.0, 0.25), (100.0, 0.10), (50.0, 0.05), (20.0, 0.02), (0.0, 0.01))


def tick_size(price: float) -> float:
    for floor, tick in TICKS:
        if price >= floor:
            return tick
    return 0.01


def round_down_to_tick(price: float) -> float:
    tick = tick_size(price)
    return round(max(int(price / tick + 1e-9), 1) * tick, 2)


def on_tick(price: float) -> bool:
    steps = price / tick_size(price)
    return abs(steps - round(steps)) < 1e-6


def _tl(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def ticket_age_hours(ticket: Ticket, now: dt.datetime) -> float | None:
    try:
        made = dt.datetime.fromisoformat(ticket.generated_at)
    except ValueError:
        return None
    if made.tzinfo is None:
        made = made.replace(tzinfo=dt.timezone.utc)
    return (now - made).total_seconds() / 3600.0


#: Tarihi her yıl aynı olan resmî tatiller (ay, gün). Dinî bayramlar yıla göre değişir;
#: onlar ``emir-ayar.toml`` içindeki ``tatiller`` listesine yazılır.
FIXED_HOLIDAYS = frozenset({(1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 29)})


def session_problems(ticket: Ticket, now: dt.datetime, holidays: tuple[str, ...] = ()) -> list[str]:
    """Fiş bugün gönderilebilir mi (takvim açısından)? Olağan durumlardır; alarm sayılmaz."""
    problems: list[str] = []
    today = now.date()
    if today.weekday() >= 5:
        problems.append("bugün hafta sonu; seans yok")
    elif (today.month, today.day) in FIXED_HOLIDAYS or today.isoformat() in holidays:
        problems.append("bugün resmî tatil; seans yok")
    if ticket.session > today:
        problems.append(f"fiş {ticket.session:%d.%m.%Y} seansı için; henüz erken")
    elif ticket.session < today:
        problems.append(f"fiş eski ({ticket.session:%d.%m.%Y} seansı içindi); bugünün fişi henüz üretilmemiş")
    return problems


def check_ticket(ticket: Ticket, now: dt.datetime, limits: Limits) -> list[str]:
    """Fişi durduran sınır ihlallerinin listesi (boşsa fiş gönderilebilir). ``now`` saat dilimli olmalı."""
    problems: list[str] = []
    age = ticket_age_hours(ticket, now)
    if age is None:
        problems.append("fişin üretim zamanı okunamadı")
    elif age > limits.azami_fis_yasi_saat:
        problems.append(f"fiş {age:.0f} saat önce üretilmiş (sınır {limits.azami_fis_yasi_saat:.0f} saat)")
    elif age < -0.25:
        problems.append("fişin üretim zamanı gelecekte görünüyor (bilgisayar saati yanlış olabilir)")
    if (ticket.session - ticket.as_of).days > 10:
        problems.append("fişin dayandığı veri 10 günden eski")
    if len(ticket.orders) > limits.azami_emir_sayisi:
        problems.append(f"fişte {len(ticket.orders)} emir var (sınır {limits.azami_emir_sayisi})")

    buys = sells = 0.0
    for o in ticket.orders:
        value = o.lots * o.limit_price
        if o.side == "buy":
            buys += value
        else:
            sells += value
        if value > limits.azami_emir_tl:
            problems.append(f"{o.symbol}: emir tutarı {_tl(value)} TL, tek emir sınırı {_tl(limits.azami_emir_tl)} TL")
        if ticket.equity > 0 and value > ticket.equity * limits.azami_emir_orani:
            problems.append(
                f"{o.symbol}: emir, portföyün %{value / ticket.equity * 100:.0f}'i (sınır %{limits.azami_emir_orani * 100:.0f})"
            )
        drift = o.limit_price / o.ref_price - 1.0
        if abs(drift) > limits.azami_fiyat_sapmasi + 1e-9:
            problems.append(f"{o.symbol}: limit fiyat son kapanıştan %{drift * 100:+.1f} uzakta")
        if (o.side == "buy" and drift < -1e-9) or (o.side == "sell" and drift > 1e-9):
            problems.append(f"{o.symbol}: limit fiyat emrin yönüyle uyumsuz")
        if not on_tick(o.limit_price):
            problems.append(f"{o.symbol}: limit fiyat ({o.limit_price}) fiyat adımına uymuyor")
    if buys > limits.azami_alis_tl:
        problems.append(f"alışların toplamı {_tl(buys)} TL, sınır {_tl(limits.azami_alis_tl)} TL")
    if sells > limits.azami_satis_tl:
        problems.append(f"satışların toplamı {_tl(sells)} TL, sınır {_tl(limits.azami_satis_tl)} TL")
    if ticket.equity > 0 and buys > ticket.equity * 1.10:
        problems.append("alışların toplamı kâğıt portföy değerini aşıyor")
    return problems


@dataclass
class Plan:
    #: Gönderim sırasıyla emirler: önce satışlar, sonra alışlar (fişteki öncelik sırasıyla).
    orders: list[OrderRequest] = field(default_factory=list)
    #: Onay mesajında gösterilecek notlar.
    notes: list[str] = field(default_factory=list)
    #: Gönderilmeyecek emirler ve nedenleri.
    skipped: list[str] = field(default_factory=list)

    @property
    def buy_total(self) -> float:
        return sum(o.value for o in self.orders if o.side == "buy")

    @property
    def sell_total(self) -> float:
        return sum(o.value for o in self.orders if o.side == "sell")


def build_plan(ticket: Ticket, positions: dict[str, int], cash: float | None, done: set[str] | None = None) -> Plan:
    """Fişi hesaptaki gerçek pozisyonlara uyarlar. ``done``: daha önce gönderilmiş emir anahtarları."""
    done = done or set()
    plan = Plan()
    sells = [o for o in ticket.orders if o.side == "sell"]
    buys = [o for o in ticket.orders if o.side == "buy"]
    for o in sells + buys:
        key = ticket.order_key(o)
        if key in done:
            plan.skipped.append(f"{o.symbol} {'satış' if o.side == 'sell' else 'alış'}: daha önce gönderildi")
            continue
        lots = o.lots
        if o.side == "sell":
            have = int(positions.get(o.symbol, 0))
            if have <= 0:
                plan.skipped.append(f"{o.symbol} satış: hesapta satılabilir lot yok (fişte {o.lots} lot)")
                continue
            if have < lots:
                plan.notes.append(f"{o.symbol}: fişte {o.lots} lot satış var, hesapta satılabilir {have} lot; {have} lot satılacak.")
                lots = have
        plan.orders.append(OrderRequest(key, o.symbol, o.side, lots, o.limit_price))

    # Kâğıt portföy ile gerçek hesap arasındaki farklar (bilgi amaçlı).
    diffs = []
    for sym in sorted(set(ticket.positions) | {o.symbol for o in sells}):
        paper, real = int(ticket.positions.get(sym, 0)), int(positions.get(sym, 0))
        if paper != real:
            diffs.append(f"{sym} kâğıtta {paper}, hesapta {real} lot")
    if diffs:
        more = f" (+{len(diffs) - 6} hisse daha)" if len(diffs) > 6 else ""
        plan.notes.append("Kâğıt portföy ile hesabınız farklı: " + "; ".join(diffs[:6]) + more + ".")

    if cash is not None and cash == cash:
        need = plan.buy_total * (1.0 + COST_MARGIN)
        if need > cash + plan.sell_total * (1.0 - COST_MARGIN):
            plan.notes.append(
                f"Alışlar için gereken tutar ({_tl(need)} TL), bakiye ({_tl(cash)} TL) ile satışların toplamını "
                f"({_tl(plan.sell_total)} TL) aşıyor; aracı kurum sondaki alışları reddedebilir."
            )
    return plan
