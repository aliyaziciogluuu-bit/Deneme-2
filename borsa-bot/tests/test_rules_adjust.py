import numpy as np
import pandas as pd
import pytest

from bistbot import rules
from bistbot.data.adjust import align_factor, factor_steps, limit_violations, repair_missing_steps, stepwise_factor


def test_price_limit_changes_on_2020_03_13():
    assert rules.price_limit(pd.Timestamp("2020-03-12")) == 0.20
    assert rules.price_limit(pd.Timestamp("2020-03-13")) == 0.10
    assert rules.price_limit(pd.Timestamp("2026-11-13")) == 0.10


@pytest.mark.parametrize(
    "price,tick",
    [(5.0, 0.01), (19.99, 0.01), (20.0, 0.02), (49.98, 0.02), (50.0, 0.05), (100.0, 0.10),
     (250.0, 0.25), (500.0, 0.50), (1000.0, 1.00), (2500.0, 2.50)],
)
def test_tick_table(price, tick):
    assert rules.tick_size(price) == tick


def test_limit_prices_round_inward():
    # Baz 43,70 TL: ham sınırlar 48,07 / 39,33; 0,02 adımla tavan aşağı, taban yukarı yuvarlanır.
    floor, ceiling = rules.limit_prices(43.70, pd.Timestamp("2026-01-05"))
    assert (floor, ceiling) == (39.34, 48.06)


def test_round_to_tick_directions():
    assert rules.round_to_tick(123.47, "down") == 123.40
    assert rules.round_to_tick(123.47, "up") == 123.50
    with pytest.raises(ValueError):
        rules.round_to_tick(0.0)


def _series(values, start="2022-01-03"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_stepwise_factor_recovers_exact_steps_despite_rounding():
    rng = np.random.default_rng(0)
    raw = _series(np.round(10 * np.cumprod(1 + rng.normal(0, 0.02, 300)), 2))
    true = pd.Series(1.0, index=raw.index)
    true.iloc[:200] = 0.5  # 200. günde %100 bedelsiz
    true.iloc[:100] *= 0.97  # 100. günde %3 temettü
    adj = (raw * true).round(4)  # kaynağın 4 ondalık yuvarlaması
    est = stepwise_factor(raw, adj)
    assert np.allclose(est.to_numpy(), true.to_numpy(), rtol=2e-4)
    steps = factor_steps(est)
    assert list(steps.index) == [raw.index[100], raw.index[200]]
    assert est.iloc[-1] == pytest.approx(1.0, abs=1e-12)


def test_stepwise_factor_is_flat_without_events():
    raw = _series(np.linspace(0.50, 0.90, 120).round(2))  # düşük fiyat: yuvarlama gürültüsü büyük
    est = stepwise_factor(raw, (raw * 1.0).round(4))
    assert est.nunique() == 1


def test_align_factor_extends_to_bulletin_dates():
    f = _series([0.5, 0.5, 1.0, 1.0], start="2022-01-05")
    dates = pd.bdate_range("2022-01-03", periods=8)
    out = align_factor(f, dates)
    assert out.iloc[0] == 0.5 and out.iloc[-1] == 1.0 and not out.isna().any()


def _bars(closes, prev_field=None):
    close = _series(closes)
    prev = close.shift(1) if prev_field is None else pd.Series(prev_field, index=close.index, dtype=float)
    return prev, close * 1.0, close * 1.01, close * 0.99, close


def test_repair_leaves_correct_vendor_step_alone():
    # 3. gün %100 bedelsiz: ham fiyat yarıya iner, kaynak bunu doğru düzeltmiş.
    prev, open_, high, low, close = _bars([10.0, 10.2, 5.15, 5.2])
    factor = pd.Series([0.5, 0.5, 1.0, 1.0], index=close.index)
    flagged = pd.Series([False, False, True, False], index=close.index)
    limit = pd.Series(0.10, index=close.index)
    out, repairs = repair_missing_steps(factor, prev, open_, high, low, close, flagged, limit)
    assert repairs == [] and out.equals(factor)


def test_repair_infers_missing_rights_issue_from_price_band():
    # Kaynak bedelliyi atlamış: katsayı sabit, düzeltilmiş getiri -%48 görünüyor.
    idx = pd.bdate_range("2021-07-30", periods=4)
    close = pd.Series([3.99, 4.00, 2.07, 2.08], index=idx)
    prev = close.shift(1)
    open_ = pd.Series([3.98, 3.96, 2.30, 2.07], index=idx)
    high = pd.Series([4.05, 4.00, 2.30, 2.12], index=idx)
    low = pd.Series([3.93, 3.82, 2.02, 2.05], index=idx)
    factor = pd.Series(1.0, index=idx)
    flagged = pd.Series([False, False, True, False], index=idx)
    limit = pd.Series(0.10, index=idx)
    out, repairs = repair_missing_steps(factor, prev, open_, high, low, close, flagged, limit)
    assert len(repairs) == 1 and repairs[0]["how"] == "band"
    adj = close * out
    ret = adj.iloc[2] / adj.iloc[1] - 1
    assert abs(ret) <= 0.10  # artık fiyat marjı içinde
    assert limit_violations(out, close, limit).empty
    assert out.iloc[2] == 1.0 and out.iloc[3] == 1.0  # olay sonrası katsayı değişmez


def test_repair_prefers_official_base_price_from_bulletin():
    # 2016 biçimi: bülten "önceki kapanış" alanında resmî baz fiyatı verir (19,99 → 9,995).
    close = _series([19.34, 19.99, 9.98, 9.84], start="2016-05-23")
    prev = pd.Series([np.nan, 19.34, 9.995, 9.98], index=close.index)
    open_, high, low = close * 1.0, close * 1.01, close * 0.99
    factor = pd.Series(1.0, index=close.index)  # kaynak olayı hiç düzeltmemiş olsun
    flagged = pd.Series([False, False, True, False], index=close.index)
    limit = pd.Series(0.20, index=close.index)
    out, repairs = repair_missing_steps(factor, prev, open_, high, low, close, flagged, limit)
    assert repairs[0]["how"] == "official"
    assert out.iloc[1] == pytest.approx(0.5, rel=1e-3)
    assert (close * out).pct_change().iloc[2] == pytest.approx(9.98 / 9.995 - 1, abs=1e-9)


def test_unflagged_days_are_never_repaired():
    prev, open_, high, low, close = _bars([10.0, 10.2, 5.15, 5.2])
    factor = pd.Series(1.0, index=close.index)
    flagged = pd.Series(False, index=close.index)
    limit = pd.Series(0.10, index=close.index)
    out, repairs = repair_missing_steps(factor, prev, open_, high, low, close, flagged, limit)
    assert repairs == [] and len(limit_violations(out, close, limit)) == 1
