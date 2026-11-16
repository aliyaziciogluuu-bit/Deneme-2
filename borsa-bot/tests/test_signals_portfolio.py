import numpy as np
import pandas as pd
import pytest

from bistbot.config import Config, PortfolioConfig, load_config
from bistbot.portfolio import (cash_index, is_rebalance_day, rebalance_dates, regime_exposure, select_holdings,
                               target_weights)
from bistbot.signals import _grouped_rank, _pct_rank, _rolling_top_mean, compute_features, score_date, universe_mask
from conftest import make_dataset


def test_pct_rank_bounds_and_nan():
    r = _pct_rank(pd.Series([3.0, 1.0, np.nan, 2.0]))
    assert r.iloc[0] == 1.0 and r.iloc[1] == 0.0 and r.iloc[3] == 0.5 and np.isnan(r.iloc[2])


def test_grouped_rank_falls_back_to_pooled_for_small_groups():
    v = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=list("abcde"))
    g = pd.Series([True, False, False, False, False], index=list("abcde"))
    r = _grouped_rank(v, g, min_size=3)
    assert r["b"] == 0.0 and r["e"] == 1.0  # dörtlük grup kendi içinde
    assert r["a"] == 0.0  # tek kişilik grup: tüm evrene göre


def test_rolling_top_mean_matches_bruteforce():
    rng = np.random.default_rng(3)
    x = rng.normal(0, 0.02, (60, 4))
    x[5:9, 1] = np.nan
    out = _rolling_top_mean(x, window=21, top_n=5, min_obs=15)
    for t in (20, 37, 59):
        for j in range(4):
            w = x[t - 20 : t + 1, j]
            w = w[np.isfinite(w)]
            assert out[t, j] == pytest.approx(np.sort(w)[-5:].mean())
    assert np.isnan(out[:20]).all()


def test_features_and_scores_have_no_lookahead():
    """t günü puanı, t'den sonraki veriler silinse de değişmemeli."""
    ds = make_dataset(n_days=420)
    cfg = Config()
    feats = compute_features(ds, cfg.signal)
    uni = universe_mask(ds, feats, cfg.universe)
    for day in (ds.dates[300], ds.dates[355], ds.dates[410]):
        cut = ds.as_of(day)
        f2 = compute_features(cut, cfg.signal)
        u2 = universe_mask(cut, f2, cfg.universe)
        full = score_date(ds, feats, uni.loc[day], day, cfg.signal)
        trunc = score_date(cut, f2, u2.loc[day], day, cfg.signal)
        pd.testing.assert_frame_equal(full, trunc)


def test_future_shock_does_not_change_past_scores():
    ds = make_dataset(n_days=420)
    cfg = Config()
    day = ds.dates[330]
    base = score_date(ds, compute_features(ds, cfg.signal), universe_mask(ds, compute_features(ds, cfg.signal), cfg.universe).loc[day], day, cfg.signal)
    shocked = make_dataset(n_days=420)
    later = shocked.dates > day
    for name in ("open", "high", "low", "close", "vwap"):
        getattr(shocked.panel, name).loc[later] *= 3.0
    shocked.mcap.loc[later] *= 3.0
    shocked.xu100.loc[later] *= 0.5
    f = compute_features(shocked, cfg.signal)
    after = score_date(shocked, f, universe_mask(shocked, f, cfg.universe).loc[day], day, cfg.signal)
    pd.testing.assert_frame_equal(base, after)


def test_universe_excludes_flagged_and_young_stocks():
    ds = make_dataset(n_days=320)
    day = ds.dates[-1]
    ds.panel.gross.loc[day, "S01"] = True
    ds.panel.suspended.loc[day, "S02"] = True
    ds.panel.method.loc[day, "S03"] = "TF"
    ds.panel.market.loc[day, "S04"] = "K"  # endeks üyesiyse pazar kodu engel değildir
    ds.panel.bist100.loc[day, "S05"] = False
    ds.factor.loc[day, "S06"] = np.nan
    ds.panel.close.loc[ds.dates[:200], "S07"] = np.nan  # geç halka arz: 120 seans geçmiş
    cfg = Config()
    feats = compute_features(ds, cfg.signal)
    uni = universe_mask(ds, feats, cfg.universe).loc[day]
    assert not uni[["S01", "S02", "S03", "S05", "S06", "S07"]].any()
    assert uni[["S00", "S04", "S08", "S09"]].all()
    # Endeks şartı kapalıyken yalnızca ana pazarlar alınır.
    from bistbot.config import UniverseConfig
    loose = universe_mask(ds, feats, UniverseConfig(require_bist100=False)).loc[day]
    assert not loose["S04"] and loose["S05"]


def test_score_table_is_sorted_and_deterministic():
    ds = make_dataset()
    cfg = Config()
    feats = compute_features(ds, cfg.signal)
    day = ds.dates[-1]
    t1 = score_date(ds, feats, universe_mask(ds, feats, cfg.universe).loc[day], day, cfg.signal)
    assert list(t1["rank"]) == list(range(1, len(t1) + 1))
    assert t1["score"].is_monotonic_decreasing and t1["score"].between(0, 1).all()
    assert len(t1) == 12


def test_select_holdings_hysteresis():
    scores = pd.DataFrame({"rank": range(1, 11)}, index=list("ABCDEFGHIJ"))
    cfg = PortfolioConfig(n_holdings=3, hold_rank=6)
    # F (6.) bant içinde kalır, J (10.) çıkar, boş yerlere en iyi iki yeni hisse girer.
    assert select_holdings(scores, ["F", "J"], cfg) == ["F", "A", "B"]
    # Evrenden çıkan hisse (tabloda yok) bırakılır.
    assert select_holdings(scores, ["ZZZ"], cfg) == ["A", "B", "C"]
    # Bantta kalan fazla hisse varsa en iyiler tutulur.
    assert select_holdings(scores, ["D", "E", "F", "B"], cfg) == ["B", "D", "E"]
    assert select_holdings(scores.iloc[:0], ["A"], cfg) == []


def test_target_weights_leave_cash_when_names_are_missing():
    cfg = PortfolioConfig(n_holdings=4)
    w = target_weights(["A", "B"], 1.0, cfg)
    assert w.sum() == pytest.approx(0.5) and (w == 0.25).all()
    assert target_weights([], 1.0, cfg).empty


def test_rebalance_dates_monthly_and_weekly():
    dates = pd.bdate_range("2024-01-01", "2024-03-29")
    monthly = rebalance_dates(dates, PortfolioConfig(frequency="monthly"))
    assert list(monthly) == [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01"), pd.Timestamp("2024-03-01")]
    second = rebalance_dates(dates, PortfolioConfig(frequency="monthly", offset=1))
    assert list(second)[:2] == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-02-02")]
    weekly = rebalance_dates(dates, PortfolioConfig(frequency="weekly"))
    assert all(d.weekday() == 0 for d in weekly) and len(weekly) == 13
    assert is_rebalance_day(dates[dates <= "2024-02-01"], PortfolioConfig())
    assert not is_rebalance_day(dates[dates <= "2024-02-02"], PortfolioConfig())


def test_cash_index_compounds_calendar_days():
    dates = pd.DatetimeIndex(["2024-01-05", "2024-01-08", "2024-01-09"])  # Cuma, Pazartesi, Salı
    idx = cash_index(pd.Series(0.365, index=dates))
    assert idx.iloc[1] == pytest.approx(1.003)  # 3 takvim günü × %0,1
    assert idx.iloc[2] == pytest.approx(1.003 * 1.001)


def test_regime_filter_compares_index_with_cash():
    dates = pd.bdate_range("2022-01-03", periods=600)
    rf = pd.Series(0.40, index=dates)
    weak = pd.Series(100 * 1.0005 ** np.arange(600), index=dates)  # yılda ~%13: nakdin altında
    strong = pd.Series(100 * 1.003 ** np.arange(600), index=dates)  # yılda ~%110: nakdin üstünde
    cfg = PortfolioConfig(regime="trend", regime_off_exposure=0.25)
    assert regime_exposure(weak, rf, cfg).iloc[-1] == 0.25
    assert regime_exposure(strong, rf, cfg).iloc[-1] == 1.0
    assert regime_exposure(weak, rf, cfg).iloc[100] == 1.0  # yeterli geçmiş yokken filtre yok
    assert (regime_exposure(weak, rf, PortfolioConfig()) == 1.0).all()


def test_config_overrides_and_validation(tmp_path):
    cfg = Config().with_overrides(portfolio={"n_holdings": 15}, capital=250000)
    assert cfg.portfolio.n_holdings == 15 and cfg.capital == 250000 and cfg.signal.mom_skip == 21
    f = tmp_path / "ayar.toml"
    f.write_text("capital = 50000\n[cost]\ncommission = 0.001\n", encoding="utf-8")
    loaded = load_config(f)
    assert loaded.capital == 50000 and loaded.cost.commission == 0.001
    assert loaded.cost.per_side == pytest.approx(0.001 * 1.05 + 0.001)
    f.write_text("[cost]\nkomisyon = 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(f)
    assert load_config(tmp_path / "yok.toml") == Config()
