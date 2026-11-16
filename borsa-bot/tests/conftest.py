"""Testler için küçük, tümüyle sentetik veri seti (ağ erişimi yok)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bistbot.data.dataset import Dataset
from bistbot.data.panel import MarketPanel


def make_dataset(n_days: int = 420, n_symbols: int = 12, seed: int = 1, start: str = "2021-01-04") -> Dataset:
    """Rastgele yürüyüşlü fiyatlarla ``Dataset``. Katsayılar 1, tüm hisseler BIST 100 üyesi."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=n_days)
    symbols = [f"S{i:02d}" for i in range(n_symbols)]
    drift = rng.normal(0.0008, 0.0006, n_symbols)
    vol = rng.uniform(0.012, 0.035, n_symbols)
    rets = np.clip(rng.normal(drift, vol, (n_days, n_symbols)), -0.095, 0.095)
    close = 20.0 * np.cumprod(1.0 + rets, axis=0)
    prev_close = np.vstack([np.full(n_symbols, np.nan), close[:-1]])
    gap = np.clip(rng.normal(0, 0.004, (n_days, n_symbols)), -0.02, 0.02)
    open_ = np.where(np.isfinite(prev_close), prev_close * (1.0 + gap), close)
    high = np.maximum(open_, close) * 1.003
    low = np.minimum(open_, close) * 0.997

    def frame(values, dtype=float):
        return pd.DataFrame(values, index=dates, columns=symbols).astype(dtype)

    ones = np.ones((n_days, n_symbols), dtype=bool)
    panel = MarketPanel(
        open=frame(open_), high=frame(high), low=frame(low), close=frame(close), vwap=frame((high + low) / 2),
        prev_close=frame(prev_close), value=frame(rng.uniform(5e7, 5e8, (n_days, n_symbols))),
        volume=frame(rng.uniform(1e6, 1e7, (n_days, n_symbols))),
        bist100=frame(ones, bool), bist30=frame(~ones, bool), gross=frame(~ones, bool),
        suspended=frame(~ones, bool), short_ok=frame(ones, bool),
        market=frame(np.full((n_days, n_symbols), "Z"), object),
        method=frame(np.full((n_days, n_symbols), "SI"), object),
        corp_action=frame(np.full((n_days, n_symbols), ""), object),
        listed=frame(ones, bool),
        names={s: s for s in symbols},
    )
    market = pd.Series(1000.0 * np.cumprod(1.0 + rets.mean(axis=1)), index=dates)
    equity = frame(rng.uniform(1e9, 5e9, (1, n_symbols)).repeat(n_days, axis=0))
    return Dataset(
        panel=panel,
        factor=frame(np.ones((n_days, n_symbols))),
        div_tax=frame(np.zeros((n_days, n_symbols))),
        mcap=frame(close * 1e8),
        equity=equity,
        ni_annual=equity * rng.uniform(-0.1, 0.4, n_symbols),
        is_financial=pd.Series([i % 3 == 0 for i in range(n_symbols)], index=symbols),
        xu100=market,
        usdtry=pd.Series(np.linspace(8.0, 20.0, n_days), index=dates),
        rf=pd.Series(0.20, index=dates),
    )


@pytest.fixture()
def dataset() -> Dataset:
    return make_dataset()
