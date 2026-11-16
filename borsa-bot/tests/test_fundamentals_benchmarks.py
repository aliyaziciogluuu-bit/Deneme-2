import numpy as np
import pandas as pd
import pytest

from bistbot.backtest import benchmarks as bm
from bistbot.backtest.engine import run_backtest
from bistbot.config import Config
from bistbot.data import dataset as dsmod
from bistbot.data.dataset import _daily_from_steps, _fix_early_share_switch, _period_end, point_in_time_fundamentals
from bistbot.research import Lab
from bistbot.signals import compute_features, universe_mask
from conftest import make_dataset


def _fin(rows, group="XI_29"):
    return pd.DataFrame(
        [{"year": y, "period": p, "group": group, "equity": e, "net_income": n} for y, p, e, n in rows]
    )


def test_each_statement_uses_only_its_own_figures_annualised():
    fin = _fin([(2020, 3, 100.0, 5.0), (2020, 6, 110.0, 12.0), (2020, 9, 120.0, 21.0), (2020, 12, 130.0, 40.0)])
    pit = point_in_time_fundamentals(fin)
    assert list(pit["ni_annual"]) == [20.0, 24.0, 28.0, 40.0]  # ×4, ×2, ×4/3, ×1
    assert list(pit["equity"]) == [100.0, 110.0, 120.0, 130.0]
    assert pit.index[0] == pd.Timestamp("2020-03-31") + pd.Timedelta(days=dsmod.INTERIM_LAG_DAYS)
    assert pit.index[-1] == pd.Timestamp("2020-12-31") + pd.Timedelta(days=dsmod.ANNUAL_LAG_DAYS)


def test_restated_year_end_rows_are_never_used():
    """2022'den itibaren yıl sonu satırı, sonradan yeniden düzenlenmiş rakamdır: atlanır."""
    fin = _fin([(2022, 9, 10.6, 3.0), (2022, 12, 57.7, 9.0), (2023, 3, 26.1, 1.0), (2021, 12, 8.0, 2.0)])
    pit = point_in_time_fundamentals(fin)
    assert 57.7 not in set(pit["equity"]) and 8.0 in set(pit["equity"])
    daily = _daily_from_steps(pit, pd.bdate_range("2023-05-01", "2023-07-31"))
    assert daily.loc["2023-06-01", "equity"] == 10.6  # yıl sonu yerine hâlâ 9 aylık tablo
    assert daily.loc["2023-06-14", "equity"] == 26.1  # 31 Mart + 75 gün


def test_new_statement_with_missing_profit_does_not_inherit_old_profit():
    fin = _fin([(2020, 3, 100.0, 5.0), (2020, 6, 110.0, np.nan)])
    daily = _daily_from_steps(point_in_time_fundamentals(fin), pd.bdate_range("2020-06-01", "2020-10-30"))
    assert daily.loc["2020-07-01", "ni_annual"] == 20.0
    assert daily.loc["2020-10-01", "equity"] == 110.0 and np.isnan(daily.loc["2020-10-01", "ni_annual"])


def test_stale_statements_expire():
    fin = _fin([(2019, 6, 100.0, 5.0)])
    daily = _daily_from_steps(point_in_time_fundamentals(fin), pd.bdate_range("2019-09-01", "2021-01-29"))
    assert daily.loc["2019-10-01", "equity"] == 100.0
    assert np.isnan(daily.loc["2020-11-02", "equity"])  # dönem sonundan 460+ gün sonra


def test_non_calendar_fiscal_years():
    assert _period_end(2024, 3) == pd.Timestamp("2024-03-31")
    assert _period_end(2024, 12) == pd.Timestamp("2024-12-31")
    assert _period_end(2024, 3, 6) == pd.Timestamp("2024-08-31")  # haziran-mayıs hesap yılı
    assert _period_end(2024, 12, 6) == pd.Timestamp("2025-05-31")
    assert _period_end(2026, 6, 2) == pd.Timestamp("2026-07-31")  # şubat-ocak hesap yılı
    assert dsmod.FISCAL_YEAR_START_MONTH["GSRAY"] == 6
    club = point_in_time_fundamentals(_fin([(2024, 9, 5.0, 1.0)]), 6)
    assert club.index[0] == pd.Timestamp("2025-02-28") + pd.Timedelta(days=dsmod.INTERIM_LAG_DAYS)


def test_share_count_switched_one_session_early_is_moved_to_ex_date():
    idx = pd.bdate_range("2026-05-11", periods=5)
    factor = pd.Series([0.5, 0.5, 0.5, 1.0, 1.0], index=idx)  # bölünme 4. gün
    early = pd.Series([600.0, 600.0, 1200.0, 1200.0, 1200.0], index=idx)  # kaynak 3. gün değiştirmiş
    fixed = _fix_early_share_switch(early, factor)
    assert list(fixed) == [600.0, 600.0, 600.0, 1200.0, 1200.0]
    on_time = pd.Series([600.0, 600.0, 600.0, 1200.0, 1200.0], index=idx)
    assert list(_fix_early_share_switch(on_time, factor)) == list(on_time)


def test_daily_benchmark_keeps_members_through_a_market_closure():
    ds = make_dataset(n_days=60)
    uni = pd.DataFrame(True, index=ds.dates, columns=ds.symbols)
    uni.iloc[30:35] = False  # beş seans piyasa kapalı: evren boş
    b = bm.equal_weight_universe(ds, uni)
    reopening = b.iloc[35] / b.iloc[34] - 1
    assert reopening == pytest.approx(ds.returns.iloc[35].mean())  # açılış günü getirisi kaybolmaz
    members = bm.lagged_membership(uni)
    assert members.iloc[35].all() and members.iloc[31].all() and not members.iloc[0].any()


def test_periodic_basket_is_buy_and_hold_between_decisions():
    ds = make_dataset(n_days=40)
    syms = list(ds.symbols[:4])
    d0, d1 = ds.dates[5], ds.dates[20]
    out = bm.periodic_equal_weight(ds, {d0: syms, d1: syms[:2]})
    assert out.index[0] == d0 and out.iloc[0] == 1.0
    px = ds.adjusted("close")
    first = (px.loc[d1, syms] / px.loc[d0, syms]).mean()
    assert out.loc[d1] == pytest.approx(first)
    second = (px.loc[ds.dates[-1], syms[:2]] / px.loc[d1, syms[:2]]).mean()
    assert out.iloc[-1] == pytest.approx(first * second)


def test_empty_universe_on_decision_day_postpones_instead_of_liquidating():
    ds = make_dataset(n_days=400)
    cfg = Config().with_overrides(portfolio={"n_holdings": 4, "hold_rank": 8})
    start = ds.dates[300]
    month_start = next(d for d in ds.dates[302:] if d.month != ds.dates[ds.dates.get_loc(d) - 1].month)
    i = ds.dates.get_loc(month_start)
    ds.panel.suspended.iloc[i : i + 3] = True  # ay başında üç seans tüm piyasa durdu
    feats = compute_features(ds, cfg.signal)
    res = run_backtest(ds, cfg, feats, universe_mask(ds, feats, cfg.universe), start=start)
    assert res.n_positions.iloc[res.equity.index.get_loc(ds.dates[i + 5])] == 4  # portföy boşaltılmadı
    assert month_start not in res.weights and ds.dates[i + 3] in res.weights  # karar ilk açık güne kaldı


def test_random_portfolios_keep_their_scores_so_turnover_stays_low():
    ds = make_dataset(n_days=420, n_symbols=30)
    lab = Lab(ds, str(ds.dates[300].date()), symbols=list(ds.symbols))
    cfg = Config().with_overrides(portfolio={"n_holdings": 5, "hold_rank": 10})
    score = pd.Series(np.random.default_rng(1).random(30), index=ds.symbols)

    def scorer(_day, tbl):
        out = tbl.copy()
        out["score"] = score.reindex(out.index).to_numpy()
        out = out.sort_values("score", ascending=False)
        out["rank"] = np.arange(1, len(out) + 1)
        return out

    res = lab.run(cfg, scorer=scorer)
    assert set(res.trades["side"]) == {"buy"} and len(res.trades) == 5  # sıralar sabit: yeniden alım-satım yok
    bench = lab.benchmarks(cfg)
    assert set(bench) == {"ew", "ew_daily", "xu100", "cash"} and bench["ew"].iloc[0] == 1.0
