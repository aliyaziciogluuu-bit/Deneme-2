"""Aracı kurum bağlantıları için ortak arayüz ve veri tipleri."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

#: Bir emrin bitmiş sayıldığı durumlar (artık değişmez).
TERMINAL = frozenset({"filled", "rejected", "cancelled"})
STATUSES = frozenset({"planned", "sending", "accepted", "partial", "unknown"}) | TERMINAL


class BrokerError(RuntimeError):
    """Aracı kurum bağlantısında ya da yanıtında hata."""


class NotSent(BrokerError):
    """Emir kesinlikle GÖNDERİLMEDİ (bağlantı ya da oturum daha gönderimden önce yoktu).

    Bu hatayı alan emir "belirsiz" sayılmaz; sonraki çalıştırmada yeniden gönderilebilir.
    """


@dataclass(frozen=True)
class OrderRequest:
    """Gönderilecek tek bir limitli emir. ``key`` aynı emrin iki kez gönderilmesini önler."""

    key: str
    symbol: str
    side: str  # "buy" | "sell"
    lots: int
    limit_price: float

    def __post_init__(self) -> None:
        if self.side not in ("buy", "sell"):
            raise ValueError(f"geçersiz yön: {self.side}")
        if not isinstance(self.lots, int) or isinstance(self.lots, bool) or self.lots < 1:
            raise ValueError(f"lot pozitif tam sayı olmalı: {self.lots!r}")
        if not (self.limit_price > 0):
            raise ValueError(f"limit fiyat pozitif olmalı: {self.limit_price!r}")

    @property
    def value(self) -> float:
        return self.lots * self.limit_price


@dataclass
class OrderState:
    key: str
    status: str
    broker_id: str | None = None
    filled_lots: int = 0
    avg_price: float | None = None
    message: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def done(self) -> bool:
        return self.status in TERMINAL


class Broker(Protocol):
    """Bir aracı kurum bağlantısının sağlaması gerekenler.

    Uygulamalar ağ/protokol hatalarında ``BrokerError`` fırlatır. ``place`` bir emrin kabul
    edilip edilmediğinden emin olamadığında durumu ``unknown`` döndürmelidir; çağıran taraf
    böyle bir emri asla körlemesine yeniden göndermez.
    """

    name: str

    def connect(self) -> None: ...

    def close(self) -> None: ...

    def positions(self) -> dict[str, int]:
        """Satılabilir lotlar: ``{sembol: lot}``."""

    def cash(self) -> float | None:
        """Kullanılabilir TL bakiye; alınamıyorsa ``None``."""

    def place(self, order: OrderRequest) -> OrderState: ...

    def refresh(self, state: OrderState) -> OrderState:
        """Emrin güncel durumunu sorgular."""

    def cancel(self, state: OrderState) -> OrderState: ...
