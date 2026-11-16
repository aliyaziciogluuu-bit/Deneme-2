import numpy as np
import pandas as pd
import pytest

from bistbot.backtest import benchmarks as bm
from bistbot.backtest.engine import Order, plan_orders, run_backtest
from bistbot.backtest.metrics import cagr, daily_rf, drawdown, summarize, yearly_returns
from bistbot.config import Config
from bistbot.signals import compute_features, universe_mask
from conftest import make_dataset

FREE = {"commission": 0.0, "bsmv": 0.0, "slippage": 0.0, "cash_yield_share": 0.0}


def _run(ds, cfg, **kw):
    feats = compute_features(ds, cfg.signal)
    return run_backtest(ds, cfg, feats, universe_mask(ds, feats, cfg.universe), **kw)


def test_plan_orders_exits_enters_and_respects_band():
    targets = pd.Series({"A": 0.25, "B": 0.25, "C": 0.25})
    values = {"A": 26_000.0, "B": 10_000.0, "X": 5_000.0}
    shares = {"A": 2600.0, "B": 1000.0, "X": 500.0}
    prices = {"A": 10.0, "B": 10.0, "C": 20.0, "X": 10.0}
    orders = plan_orders(values, shares, prices, 100_000.0, targets, band=0.25)
    by = {o.symbol: o for o in orders}
    assert by["X"].side == "sell" and by["X"].exit and by["X"].shares == 500.0
    assert "A" not in by  # %4 sapma bant içinde
    assert by["B"].side == "buy" and by["B"].shares == pytest.approx(1500.0)
    assert by["C"].side == "buy" and by["C"].shares == pytest.approx(1250.0)
    assert [o.side for o in orders] == ["sell", "buy", "buy"]  # önce satışlar


def test_orders_fill_next_session_at_open_never_same_day():
    ds = make_dataset(n_days=330)
    cfg = Config().with_overrides(cost=FREE, portfolio={"n_holdings": 4, "hold_rank": 8})
    start = ds.dates[300]
    res = _run(ds, cfg, start=start)
    assert res.n_positions.iloc[0] == 0 and res.equity.iloc[0] == cfg.capital  # karar günü hâlâ nakitte
    first = res.trades[res.trades["date"] == ds.dates[301]]
    assert len(first) == 4 and (first["side"] == "buy").all()
    for _, t in first.iterrows():
        assert t["price"] == pytest.approx(ds.panel.open.at[ds.dates[301], t["symbol"]])
    assert res.trades["date"].min() == ds.dates[301]


def test_costs_reduce_equity_by_expected_amount():
    ds = make_dataset(n_days=330)
    start = ds.dates[300]
    port = {"n_holdings": 4, "hold_rank": 8}
    free = _run(ds, Config().with_overrides(cost=FREE, portfolio=port), start=start, end=ds.dates[305])
    paid_cfg = Config().with_overrides(
        cost={"commission": 0.002, "bsmv": 0.05, "slippage": 0.001, "cash_yield_share": 0.0}, portfolio=port
    )
    paid = _run(ds, paid_cfg, start=start, end=ds.dates[305])
    assert paid_cfg.cost.per_side == pytest.approx(0.0031)
    bought = paid.trades["value"].sum()
    assert paid.total_costs() == pytest.approx(bought * 0.0031)
    assert paid.equity.iloc[-1] < free.equity.iloc[-1]


def test_cash_earns_overnight_interest_on_calendar_days():
    ds = make_dataset(n_days=330)
    ds.panel.bist100.loc[:, :] = False  # evren boş: hep nakitte
    cfg = Config().with_overrides(cost={**FREE, "cash_yield_share": 1.0})
    res = _run(ds, cfg, start=ds.dates[300])
    days = (ds.dates[-1] - ds.dates[300]).days
    assert res.trades.empty and res.n_positions.max() == 0
    assert res.equity.iloc[-1] == pytest.approx(cfg.capital * np.prod(
        1 + 0.20 * np.diff(ds.dates[300:].values).astype("timedelta64[D]").astype(float) / 365))
    assert res.equity.iloc[-1] > cfg.capital * (1 + 0.20 * days / 365) * 0.999


def test_limit_up_open_blocks_buy_and_limit_down_open_carries_sell():
    ds = make_dataset(n_days=335)
    cfg = Config().with_overrides(cost=FREE, portfolio={"n_holdings": 3, "hold_rank": 5})
    start = ds.dates[300]
    base = _run(ds, cfg, start=start)
    bought = list(base.trades[base.trades["date"] == ds.dates[301]]["symbol"])
    sym = bought[0]
    # Alış günü hisse tavandan açılsın.
    ds2 = make_dataset(n_days=335)
    ds2.panel.open.loc[ds2.dates[301], sym] = ds2.panel.close.at[ds2.dates[300], sym] * 1.10
    res = _run(ds2, cfg, start=start)
    assert sym not in set(res.trades[res.trades["date"] == ds2.dates[301]]["symbol"])
    assert ((res.unfilled["symbol"] == sym) & (res.unfilled["reason"] == "tavan")).any()


def _with_forced_exit(n_days, sym_holder):
    """Bir hisseyi alındıktan sonra BIST 100'den çıkararak satış emri doğurur."""
    ds = make_dataset(n_days=n_days)
    if sym_holder:
        ds.panel.bist100.loc[ds.dates >= ds.dates[310], sym_holder[0]] = False
    return ds


def test_blocked_sell_is_retried_until_filled():
    cfg = Config().with_overrides(cost=FREE, portfolio={"n_holdings": 3, "hold_rank": 5})
    probe = make_dataset(n_days=380)
    start = probe.dates[300]
    sym = list(_run(probe, cfg, start=start).trades["symbol"])[0]
    base = _run(_with_forced_exit(380, [sym]), cfg, start=start)
    sells = base.trades[(base.trades["symbol"] == sym) & (base.trades["side"] == "sell")]
    assert len(sells) == 1 and sells.iloc[0]["reason"] == "çıkış"
    day = sells.iloc[0]["date"]
    i = probe.dates.get_loc(day)
    ds2 = _with_forced_exit(380, [sym])
    ds2.panel.open.loc[day, sym] = ds2.panel.close.at[ds2.dates[i - 1], sym] * 0.90  # tabandan açılış
    res = _run(ds2, cfg, start=start)
    assert ((res.unfilled["symbol"] == sym) & (res.unfilled["reason"] == "taban") & (res.unfilled["date"] == day)).any()
    retry = res.trades[(res.trades["symbol"] == sym) & (res.trades["side"] == "sell")]
    assert list(retry["date"]) == [ds2.dates[i + 1]]


def test_untraded_or_suspended_stock_cannot_be_bought():
    ds = make_dataset(n_days=335)
    cfg = Config().with_overrides(cost=FREE, portfolio={"n_holdings": 3, "hold_rank": 5})
    start = ds.dates[300]
    sym = list(_run(ds, cfg, start=start).trades["symbol"])[0]
    ds2 = make_dataset(n_days=335)
    ds2.panel.suspended.loc[ds2.dates[301], sym] = True
    res = _run(ds2, cfg, start=start)
    assert sym not in set(res.trades[res.trades["date"] == ds2.dates[301]]["symbol"])


def test_delisted_holding_is_cashed_out_at_last_close():
    ds = make_dataset(n_days=340)
    cfg = Config().with_overrides(cost=FREE, portfolio={"n_holdings": 3, "hold_rank": 5})
    start = ds.dates[300]
    sym = list(_run(ds, cfg, start=start).trades["symbol"])[0]
    ds2 = make_dataset(n_days=340)
    gone = ds2.dates >= ds2.dates[310]
    ds2.panel.listed.loc[gone, sym] = False
    for name in ("open", "high", "low", "close", "vwap"):
        getattr(ds2.panel, name).loc[gone, sym] = np.nan
    ds2.factor.loc[gone, sym] = np.nan
    res = _run(ds2, cfg, start=start)
    out = res.trades[res.trades["reason"] == "kottan çıkış"]
    assert list(out["symbol"]) == [sym] and out.iloc[0]["date"] == ds2.dates[310]
    assert out.iloc[0]["price"] == pytest.approx(ds2.panel.close.at[ds2.dates[309], sym])
    assert np.isfinite(res.equity).all()


def test_dividend_withholding_reduces_position_value():
    ds = make_dataset(n_days=335)
    cfg = Config().with_overrides(cost=FREE, portfolio={"n_holdings": 3, "hold_rank": 5})
    start = ds.dates[300]
    base = _run(ds, cfg, start=start, end=ds.dates[310])
    sym = list(base.trades["symbol"])[0]
    ds2 = make_dataset(n_days=335)
    ds2.div_tax.loc[ds2.dates[305], sym] = 0.01
    res = _run(ds2, cfg, start=start, end=ds2.dates[310])
    held_value = base.trades.iloc[0]["shares"] * ds.panel.close.at[ds.dates[305], sym]
    assert base.equity.loc[ds.dates[305]] - res.equity.loc[ds.dates[305]] == pytest.approx(held_value * 0.01, rel=1e-6)


def test_participation_cap_limits_order_size():
    ds = make_dataset(n_days=335)
    ds.panel.value.loc[:, :] = 1e5  # çok sığ hisseler
    cfg = Config().with_overrides(cost=FREE, portfolio={"n_holdings": 3, "hold_rank": 5, "max_participation": 0.05})
    res = _run(ds, cfg, start=ds.dates[300], end=ds.dates[303])
    assert (res.trades["value"] <= 0.05 * 1e5 + 1e-6).all()
    assert (res.unfilled["reason"] == "hacim sınırı").any()


def test_execution_delay_must_be_positive_and_cash_never_negative():
    ds = make_dataset(n_days=400)
    cfg = Config().with_overrides(portfolio={"n_holdings": 5, "hold_rank": 8})
    with pytest.raises(ValueError):
        _run(ds, cfg, start=ds.dates[300], execution_delay=0)
    res = _run(ds, cfg, start=ds.dates[300])
    assert (res.cash >= -1e-6).all() and (res.invested <= 1.0 + 1e-9).all()
    start = ds.dates[305]  # izleyen iki gün ay başı değil: plan araya giren yeni kararla değişmez
    delayed = _run(ds, cfg, start=start, execution_delay=2)
    assert delayed.trades["date"].min() == ds.dates[307]


def test_metrics_basic_identities():
    idx = pd.bdate_range("2023-01-02", periods=505)
    eq = pd.Series(100 * 1.001 ** np.arange(505), index=idx)
    rf = pd.Series(0.0, index=idx)
    assert summarize(eq, rf)["max_drawdown"] == 0
    noisy = pd.Series(100 * np.cumprod(1 + np.random.default_rng(5).normal(0.001, 0.01, 505)), index=idx)
    s = summarize(noisy, rf, benchmark=noisy)
    assert s["excess_cagr"] == pytest.approx(0) and s["beta"] == pytest.approx(1.0)
    assert s["alpha_annual"] == pytest.approx(0, abs=1e-9) and s["tracking_error"] == pytest.approx(0, abs=1e-12)
    assert cagr(eq) == pytest.approx((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (idx[-1] - idx[0]).days) - 1)
    dip = eq.copy(); dip.iloc[100:120] *= 0.8
    assert drawdown(dip).min() == pytest.approx(-0.2, abs=0.02)
    yr = yearly_returns({"a": eq})
    assert list(yr.index) == [2023, 2024]
    d = daily_rf(pd.Series(0.365, index=idx), idx)
    assert d.iloc[0] == 0 and d.iloc[1] == pytest.approx(0.001) and d.iloc[5] == pytest.approx(0.003)


def test_equal_weight_benchmark_uses_lagged_membership():
    ds = make_dataset(n_days=50)
    uni = pd.DataFrame(True, index=ds.dates, columns=ds.symbols)
    b = bm.equal_weight_universe(ds, uni)
    expected = (1 + ds.returns.iloc[1:].mean(axis=1)).cumprod()
    assert b.iloc[-1] == pytest.approx(expected.iloc[-1])
    assert b.iloc[0] == 1.0
