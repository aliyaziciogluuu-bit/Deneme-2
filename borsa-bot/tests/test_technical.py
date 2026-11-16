import numpy as np
import pandas as pd
import pytest

from bistbot.portfolio import cash_index
from bistbot.technical import average_true_range, compute_technicals, macd_histogram, rsi
from conftest import make_dataset


def _frame(values):
    return pd.DataFrame({"X": values}, index=pd.bdate_range("2024-01-01", periods=len(values)), dtype=float)


def test_rsi_extremes_and_known_value():
    up = _frame(np.arange(1, 40))
    assert rsi(up)["X"].iloc[-1] == 100.0
    down = _frame(np.arange(40, 1, -1))
    assert rsi(down)["X"].iloc[-1] == pytest.approx(0.0)
    flat = _frame(np.full(40, 5.0))
    assert np.isnan(rsi(flat)["X"].iloc[-1])  # hareket yoksa tanımsız
    # Dönüşümlü +1 / -0.5 hareketler: ortalama kazanç / ortalama kayıp = 2 -> RSI ≈ 66,7
    # (son adımın yönüne göre birkaç puan oynar).
    steps = np.tile([1.0, -0.5], 200)
    assert rsi(_frame(100 + np.cumsum(steps)))["X"].iloc[-1] == pytest.approx(66.67, abs=2.5)
    assert rsi(up)["X"].iloc[:13].isna().all()


def test_macd_sign_and_atr():
    rising = _frame(100 * 1.01 ** np.arange(120))
    assert macd_histogram(rising)["X"].iloc[-1] > -1e-9
    turn = _frame(np.concatenate([100 * 1.01 ** np.arange(100), 100 * 1.01 ** 99 * 0.98 ** np.arange(1, 21)]))
    assert macd_histogram(turn)["X"].iloc[-1] < 0  # düşüşe dönünce histogram eksiye geçer
    close = _frame(np.full(60, 10.0))
    atr = average_true_range(close + 0.3, close - 0.2, close)
    assert atr["X"].iloc[-1] == pytest.approx(0.5)


def test_technicals_shapes_trend_and_no_lookahead():
    ds = make_dataset(n_days=420)
    t = compute_technicals(ds)
    assert t.trend.shape == ds.panel.close.shape
    assert t.trend.iloc[:150].isna().all().all() and t.trend.iloc[-1].notna().all()
    last = ds.dates[-1]
    # Eğilim nakde göre fiyattan hesaplanır (fiyat / gecelik faiz endeksi).
    px = ds.adjusted("close")["S00"] / cash_index(ds.rf)
    assert t.trend.loc[last, "S00"] == pytest.approx(px.iloc[-1] / px.iloc[-200:].mean() - 1)
    assert (t.uptrend.loc[last] == (t.trend.loc[last] > 0)).all()
    assert t.high_52w.loc[last].between(0, 1.0 + 1e-9).all() and t.rsi.loc[last].between(0, 100).all()
    day = ds.dates[350]
    cut = compute_technicals(ds.as_of(day))
    for name in ("trend", "ma_cross", "rsi", "macd_hist", "atr_pct", "high_52w", "volume_ratio"):
        pd.testing.assert_series_equal(getattr(t, name).loc[day], getattr(cut, name).loc[day])


def test_split_does_not_create_fake_downtrend():
    """Bedelsiz sonrası ham fiyat yarıya iner; düzeltilmiş seride eğilim değişmemelidir."""
    base = make_dataset(n_days=420)
    split = make_dataset(n_days=420)
    later = split.dates >= split.dates[400]
    for name in ("open", "high", "low", "close", "vwap"):
        getattr(split.panel, name).loc[later, "S03"] *= 0.5
    split.factor.loc[~later, "S03"] = 0.5
    a, b = compute_technicals(base), compute_technicals(split)
    assert b.trend["S03"].iloc[-1] == pytest.approx(a.trend["S03"].iloc[-1])
    assert b.rsi["S03"].iloc[-1] == pytest.approx(a.rsi["S03"].iloc[-1])


def test_uptrend_is_measured_against_cash():
    """Yılda %30 yükselen hisse, faiz %60 iken yükseliş eğiliminde sayılmaz."""
    ds = make_dataset(n_days=420)
    days = np.arange(len(ds.dates))
    for name in ("open", "high", "low", "close", "vwap"):
        getattr(ds.panel, name)["S01"] = 10.0 * 1.30 ** (days / 252)
    ds.rf[:] = 0.20
    assert compute_technicals(ds).uptrend["S01"].iloc[-1]
    ds.rf[:] = 0.60
    assert not compute_technicals(ds).uptrend["S01"].iloc[-1]
