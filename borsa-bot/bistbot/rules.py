"""Borsa İstanbul Pay Piyasası kuralları: fiyat marjı, fiyat adımı, işlem görebilirlik.

Kurallar tarihe bağlıdır; sabit yerine tarihli fonksiyon olarak tutulur.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

#: Günlük fiyat marjı 13.03.2020'de ±%20'den ±%10'a indirildi. Tarih, resmî bültenlerde
#: özsermaye olayı olmayan günlerde %10,5'i aşan son hareketin 12.03.2020 olmasından
#: doğrulanmıştır.
LIMIT_CHANGE_DATE = pd.Timestamp("2020-03-13")
LIMIT_BEFORE = 0.20
LIMIT_AFTER = 0.10

#: Fiyat adımı tablosu (06.11.2023'ten beri): (alt sınır, adım).
TICK_TABLE = (
    (2500.0, 2.50),
    (1000.0, 1.00),
    (500.0, 0.50),
    (250.0, 0.25),
    (100.0, 0.10),
    (50.0, 0.05),
    (20.0, 0.02),
    (0.0, 0.01),
)

#: Sürekli işlem yöntemi ve ana pazarlar (Yıldız = Z, Ana = N).
CONTINUOUS_METHOD = "SI"
MAIN_MARKETS = ("Z", "N")


def price_limit(date: pd.Timestamp) -> float:
    """Verilen gün geçerli günlük fiyat marjı (ör. 0.10)."""
    return LIMIT_BEFORE if pd.Timestamp(date) < LIMIT_CHANGE_DATE else LIMIT_AFTER


def price_limit_series(dates: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(np.where(dates < LIMIT_CHANGE_DATE, LIMIT_BEFORE, LIMIT_AFTER), index=dates)


def tick_size(price: float) -> float:
    """Fiyat seviyesine göre fiyat adımı."""
    for floor, tick in TICK_TABLE:
        if price >= floor:
            return tick
    return 0.01


def round_to_tick(price: float, direction: str = "nearest") -> float:
    """Fiyatı geçerli fiyat adımına yuvarlar (``down``, ``up`` veya ``nearest``)."""
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"geçersiz fiyat: {price}")
    tick = tick_size(price)
    steps = price / tick
    if direction == "down":
        n = math.floor(steps + 1e-9)
    elif direction == "up":
        n = math.ceil(steps - 1e-9)
    else:
        n = round(steps)
    n = max(n, 1)
    return round(n * tick, 2)


def limit_prices(base_price: float, date: pd.Timestamp) -> tuple[float, float]:
    """Baz fiyata göre (taban, tavan). Tavan aşağı, taban yukarı adıma yuvarlanır."""
    limit = price_limit(date)
    ceiling = round_to_tick(base_price * (1.0 + limit), "down")
    floor = round_to_tick(base_price * (1.0 - limit), "up")
    return floor, ceiling
