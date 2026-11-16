"""Emir fişi: bulut tarafının ürettiği ``latest.json`` içindeki emir listesinin doğrulanmış hâli."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import requests

_SYMBOL = re.compile(r"^[A-Z0-9]{3,6}$")


class TicketError(ValueError):
    """Emir fişi okunamadı ya da beklenen biçimde değil."""


@dataclass(frozen=True)
class TicketOrder:
    symbol: str
    side: str
    lots: int
    limit_price: float
    ref_price: float


@dataclass(frozen=True)
class Ticket:
    as_of: dt.date  # kararın dayandığı son seans
    session: dt.date  # emirlerin girileceği en erken seans
    generated_at: str
    equity: float  # kâğıt portföy değeri (TL)
    orders: tuple[TicketOrder, ...]
    positions: dict[str, int]  # kâğıt portföydeki lotlar

    @property
    def digest(self) -> str:
        """Fişin içeriğine bağlı kimlik: aynı fiş iki kez uygulanmasın diye."""
        key = [str(self.as_of), str(self.session)] + [
            [o.symbol, o.side, o.lots, round(o.limit_price, 4)] for o in self.orders
        ]
        return hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]

    def order_key(self, order: TicketOrder) -> str:
        """Emrin kimliği kararın dayandığı gündür: aynı karar başka bir seans için yeniden
        yayımlanırsa (ör. bülten gecikince) aynı emir ikinci kez gönderilmez."""
        return f"{self.as_of}|{order.symbol}|{order.side}"


def _num(value, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TicketError(f"{what} sayı değil: {value!r}")
    return float(value)


def parse_ticket(payload: dict) -> Ticket:
    """``latest.json`` içeriğini sıkı biçimde doğrular. Şüpheli her şey hata sayılır."""
    if not isinstance(payload, dict):
        raise TicketError("fiş bir JSON nesnesi olmalı")
    try:
        as_of = dt.date.fromisoformat(payload["as_of"])
        session = dt.date.fromisoformat(payload["next_session"])
        raw_orders = payload["orders"]
        raw_positions = payload["positions"]
    except (KeyError, TypeError, ValueError) as exc:
        raise TicketError(f"fişte eksik ya da hatalı alan: {exc}") from exc
    if session <= as_of:
        raise TicketError("emir seansı, karar gününden sonra olmalı")
    if not isinstance(raw_orders, list) or not isinstance(raw_positions, list):
        raise TicketError("emirler ve pozisyonlar liste olmalı")

    orders, seen = [], set()
    for o in raw_orders:
        if not isinstance(o, dict):
            raise TicketError("emir satırı nesne olmalı")
        symbol, side = o.get("symbol"), o.get("side")
        if not isinstance(symbol, str) or not _SYMBOL.match(symbol):
            raise TicketError(f"geçersiz sembol: {symbol!r}")
        if side not in ("buy", "sell"):
            raise TicketError(f"geçersiz yön: {side!r}")
        lots = o.get("lots")
        if isinstance(lots, bool) or not isinstance(lots, int) or lots < 1:
            raise TicketError(f"{symbol}: lot pozitif tam sayı olmalı ({lots!r})")
        limit_price, ref_price = _num(o.get("limit_price"), f"{symbol} limit"), _num(o.get("ref_price"), f"{symbol} fiyat")
        if not (limit_price > 0 and ref_price > 0):
            raise TicketError(f"{symbol}: fiyatlar pozitif olmalı")
        if (symbol, side) in seen:
            raise TicketError(f"{symbol} için aynı yönde iki emir var")
        seen.add((symbol, side))
        orders.append(TicketOrder(symbol, side, lots, limit_price, ref_price))
    if {s for s, side in seen if side == "buy"} & {s for s, side in seen if side == "sell"}:
        raise TicketError("aynı hisse için hem alış hem satış emri var")

    positions = {}
    for p in raw_positions:
        if not isinstance(p, dict) or not isinstance(p.get("symbol"), str):
            raise TicketError("pozisyon satırı hatalı")
        lots = p.get("lots")
        if isinstance(lots, bool) or not isinstance(lots, int) or lots < 0:
            raise TicketError(f"{p.get('symbol')}: pozisyon lotu hatalı")
        positions[p["symbol"]] = lots
    equity = _num(payload.get("equity"), "portföy değeri")
    if not equity > 0:
        # Oran sınırları portföy değerine göre hesaplanır; sıfır/eksi değer bu sınırları boşa çıkarırdı.
        raise TicketError(f"portföy değeri pozitif olmalı: {equity!r}")
    return Ticket(
        as_of=as_of, session=session, generated_at=str(payload.get("generated_at", "")),
        equity=equity, orders=tuple(orders), positions=positions,
    )


def load_ticket(source: str, timeout: float = 30.0) -> Ticket:
    """Fişi dosyadan ya da ``https://`` adresinden okur."""
    try:
        if source.startswith("https://"):
            resp = requests.get(source, params={"t": dt.datetime.now().timestamp()}, timeout=timeout,
                                headers={"Cache-Control": "no-cache"})
            if resp.status_code != 200:
                raise TicketError(f"fiş indirilemedi: HTTP {resp.status_code}")
            payload = resp.json()
        elif source.startswith("http://"):
            raise TicketError("fiş yalnızca https adresinden ya da yerel dosyadan okunur")
        else:
            payload = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, ValueError, requests.RequestException) as exc:
        if isinstance(exc, TicketError):
            raise
        raise TicketError(f"fiş okunamadı: {type(exc).__name__}") from exc
    return parse_ticket(payload)
