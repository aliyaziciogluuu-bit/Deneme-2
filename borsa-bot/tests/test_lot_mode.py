"""Lot kipi: tam lot, nakit temettü, bedelsiz ve nakde göre emir boyutu."""
import numpy as np
import pandas as pd
import pytest

from bistbot.backtest.engine import is_share_event, plan_orders, run_backtest
from bistbot.config import Config
from bistbot.signals import compute_features, universe_mask
from conftest import make_dataset

FREE = {"commission": 0.0, "bsmv": 0.0, "slippage": 0.0, "cash_yield_share": 0.0}
PORT = {"n_holdings": 4, "hold_rank": 8, "buy_headroom": 0.0}


def _run(ds, cfg, **kw):
    feats = compute_features(ds, cfg.signal)
    return run_backtest(ds, cfg, feats, universe_mask(ds, feats, cfg.universe), **kw)


def _lots(res, ds):
    f = ds.factor
    return res.trades.apply(lambda t: t["shares"] * f.at[t["date"], t["symbol"]], axis=1)


def _apply_event(ds, sym, i, step, code, tax=0.0):
    """i. günde hak kullanımı: ham fiyatlar o günden itibaren ``step`` ile çarpılır,
    önceki günlerin katsayısı ``step`` olur (düzeltilmiş seri sürekli kalır)."""
    later = ds.dates >= ds.dates[i]
    for name in ("open", "high", "low", "close", "vwap"):
        getattr(ds.panel, name).loc[later, sym] *= step
    ds.panel.prev_close.loc[ds.dates > ds.dates[i], sym] *= step
    ds.factor.loc[~later, sym] = step
    ds.panel.corp_action.loc[ds.dates[i], sym] = code
    if tax:
        ds.div_tax.loc[ds.dates[i], sym] = tax


def test_event_codes():
    assert is_share_event("03") and is_share_event("01&03") and is_share_event("3") and is_share_event("04")
    assert not is_share_event("06") and not is_share_event("01") and not is_share_event("") and not is_share_event("6")


def test_only_whole_lots_trade_and_cash_is_never_negative():
    ds = make_dataset(n_days=400)
    cfg = Config().with_overrides(portfolio={"n_holdings": 5, "hold_rank": 8})
    res = _run(ds, cfg, start=ds.dates[300], lot_mode=True)
    lots = _lots(res, ds)
    assert np.allclose(lots, lots.round(), atol=1e-6) and (lots >= 1).all()
    assert (res.cash >= -1e-6).all()
    for sym, q in res.positions.items():
        assert q * ds.factor[sym].iloc[-1] == pytest.approx(round(q * ds.factor[sym].iloc[-1]), abs=1e-6)


def test_cash_dividend_goes_to_cash_and_lots_stay_the_same():
    cfg = Config().with_overrides(cost=FREE, portfolio=PORT)
    probe = make_dataset(n_days=335)
    start = probe.dates[300]
    sym = list(_run(probe, cfg, start=start, lot_mode=True).trades["symbol"])[0]
    ds = make_dataset(n_days=335)
    _apply_event(ds, sym, 310, step=0.96, code="06", tax=0.006)  # %4 brüt temettü, %15 stopaj
    res = _run(ds, cfg, start=start, end=ds.dates[315], lot_mode=True)
    buy = res.trades[res.trades["symbol"] == sym].iloc[0]
    lots = round(buy["shares"] * ds.factor.at[buy["date"], sym])
    ev = [e for e in res.events if e["symbol"] == sym]
    assert len(ev) == 1 and ev[0]["kind"] == "temettü"
    assert ev[0]["lots_before"] == pytest.approx(lots) and ev[0]["lots_after"] == pytest.approx(lots)
    prev_close_raw = ds.panel.close.at[ds.dates[309], sym]
    assert ev[0]["cash"] == pytest.approx(lots * prev_close_raw * (0.04 - 0.006), rel=1e-9)
    # Araştırma kipiyle (temettü yeniden yatırılır) aynı toplam değer: fark yalnızca tam lot kısıtı.
    reinvest = _run(ds, cfg, start=start, end=ds.dates[315], lot_mode=False)
    assert res.equity.iloc[-1] == pytest.approx(reinvest.equity.iloc[-1], rel=2e-3)


def test_bonus_issue_multiplies_lots_and_keeps_value():
    cfg = Config().with_overrides(cost=FREE, portfolio=PORT)
    probe = make_dataset(n_days=335)
    start = probe.dates[300]
    sym = list(_run(probe, cfg, start=start, lot_mode=True).trades["symbol"])[0]
    ds = make_dataset(n_days=335)
    _apply_event(ds, sym, 310, step=0.5, code="03")  # %100 bedelsiz
    res = _run(ds, cfg, start=start, end=ds.dates[315], lot_mode=True)
    ev = [e for e in res.events if e["symbol"] == sym][0]
    assert ev["kind"] == "bedelsiz" and ev["lots_after"] == pytest.approx(2 * ev["lots_before"]) and ev["cash"] == 0
    base = _run(make_dataset(n_days=335), cfg, start=start, end=probe.dates[315], lot_mode=True)
    assert res.equity.iloc[-1] == pytest.approx(base.equity.iloc[-1], rel=1e-9)  # bölünme değeri değiştirmez


def test_rights_issue_credits_theoretical_value_as_cash():
    cfg = Config().with_overrides(cost=FREE, portfolio=PORT)
    probe = make_dataset(n_days=335)
    start = probe.dates[300]
    sym = list(_run(probe, cfg, start=start, lot_mode=True).trades["symbol"])[0]
    ds = make_dataset(n_days=335)
    _apply_event(ds, sym, 310, step=0.7, code="01")
    res = _run(ds, cfg, start=start, end=ds.dates[315], lot_mode=True)
    ev = [e for e in res.events if e["symbol"] == sym][0]
    assert ev["kind"] == "bedelli" and ev["lots_after"] == pytest.approx(ev["lots_before"])
    assert ev["cash"] == pytest.approx(ev["lots_before"] * ds.panel.close.at[ds.dates[309], sym] * 0.3, rel=1e-9)


def test_buys_are_scaled_pro_rata_to_available_cash():
    targets = pd.Series({"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25})
    prices = {s: 10.0 for s in "ABCDX"}
    # Elde X var (10.000 TL), nakit 80.000: toplam 90.000 → hedefler 4 × 22.500 = 90.000.
    orders = plan_orders({"X": 10_000.0}, {"X": 1000.0}, prices, 90_000.0, targets, band=0.25,
                         cash=80_000.0, cost_rate=0.01, headroom=0.03)
    buys = [o for o in orders if o.side == "buy"]
    available = 80_000 + 10_000 * (1 - 0.01 - 0.03)  # satış da limit fiyattan (%3 aşağıdan) sayılır
    assert sum(o.shares * 10.0 for o in buys) * 1.04 == pytest.approx(available)  # alımlar limit fiyattan da sığar
    assert len({round(o.shares, 6) for o in buys}) == 1  # hepsi aynı oranda küçültüldü
    # Para yetiyorsa dokunulmaz.
    roomy = plan_orders({}, {}, prices, 100_000.0, targets * 0.5, band=0.25, cash=100_000.0, cost_rate=0.01)
    assert all(o.shares == pytest.approx(1250.0) for o in roomy)
