"""Emir göndermeyen aracı kurum taklitleri: deneme ve salt-okunur kipleri için."""
from __future__ import annotations

from .base import Broker, OrderRequest, OrderState


class DryRunBroker:
    """Hiçbir yere bağlanmaz. Pozisyonlar fişteki kâğıt portföyden alınır; her emir
    limit fiyatından gerçekleşmiş sayılır ve yalnızca kayda geçer."""

    name = "Deneme"

    def __init__(self, positions: dict[str, int], cash: float | None = None):
        self._positions = dict(positions)
        self._cash = cash
        self.placed: list[OrderRequest] = []

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass

    def describe(self) -> str:
        return "DENEME (hiçbir yere bağlanılmadı; pozisyonlar kâğıt portföyden)"

    def positions(self) -> dict[str, int]:
        return dict(self._positions)

    def cash(self) -> float | None:
        return self._cash

    def place(self, order: OrderRequest) -> OrderState:
        self.placed.append(order)
        return OrderState(order.key, "filled", broker_id=f"deneme-{len(self.placed)}", filled_lots=order.lots,
                          avg_price=order.limit_price, message="deneme: gönderilmedi")

    def refresh(self, state: OrderState) -> OrderState:
        return state

    def cancel(self, state: OrderState) -> OrderState:
        return state


class ReadOnlyBroker:
    """Gerçek hesabı okur (pozisyon, bakiye) ama emir GÖNDERMEZ."""

    def __init__(self, inner: Broker):
        self.inner = inner
        self.name = f"{inner.name} (salt-okunur)"
        self.placed: list[OrderRequest] = []

    def connect(self) -> None:
        self.inner.connect()

    def close(self) -> None:
        self.inner.close()

    def describe(self) -> str:
        inner = self.inner.describe() if hasattr(self.inner, "describe") else self.inner.name
        return f"{inner} — SALT-OKUNUR (emir gönderilmez)"

    def positions(self) -> dict[str, int]:
        return self.inner.positions()

    def cash(self) -> float | None:
        return self.inner.cash()

    def place(self, order: OrderRequest) -> OrderState:
        self.placed.append(order)
        return OrderState(order.key, "accepted", broker_id=None, message="salt-okunur: gönderilmedi")

    def refresh(self, state: OrderState) -> OrderState:
        return state

    def cancel(self, state: OrderState) -> OrderState:
        return state
