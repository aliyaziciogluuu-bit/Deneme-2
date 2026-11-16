import numpy as np
import pandas as pd
import pytest

from bistbot.backtest import stats


def test_probabilistic_sharpe_matches_normal_approximation():
    rng = np.random.default_rng(11)
    x = rng.normal(0.001, 0.01, 2500)
    sr = x.mean() / x.std(ddof=1)
    psr = stats.probabilistic_sharpe(x, 0.0)
    assert 0.99 < psr <= 1.0  # t ≈ sr·√n ≈ 5
    assert stats.probabilistic_sharpe(x, sr) == pytest.approx(0.5, abs=1e-9)
    assert stats.probabilistic_sharpe(-x, 0.0) < 0.01
    assert np.isnan(stats.probabilistic_sharpe(np.zeros(100)))


def test_expected_max_sharpe_grows_with_trials():
    v = 1.0 / 2500  # yeteneksiz stratejinin günlük Sharpe varyansı ≈ 1/n
    e10, e50, e1000 = (stats.expected_max_sharpe(v, n) for n in (10, 50, 1000))
    assert 0 < e10 < e50 < e1000
    # 10 yıllık günlük veride yıllıklandırılmış değerler ~0,5 / ~0,7 / ~1,0 olmalı.
    ann = lambda e: e * np.sqrt(252)  # noqa: E731
    assert ann(e10) == pytest.approx(0.50, abs=0.05) and ann(e50) == pytest.approx(0.72, abs=0.05)
    assert ann(e1000) == pytest.approx(1.03, abs=0.06)
    assert stats.expected_max_sharpe(v, 1) == 0.0


def test_deflated_sharpe_is_never_above_plain_psr():
    rng = np.random.default_rng(2)
    x = rng.normal(0.0006, 0.01, 2500)
    trials = rng.normal(0.0, 0.02, 40)
    assert stats.deflated_sharpe(x, trials) <= stats.probabilistic_sharpe(x, 0.0)
    assert stats.deflated_sharpe(x, np.array([0.01])) == stats.probabilistic_sharpe(x, 0.0)


def test_bootstrap_is_deterministic_and_brackets_the_estimate():
    rng = np.random.default_rng(4)
    frame = pd.DataFrame({"r": rng.normal(0.001, 0.01, 1500)})
    stat = lambda f: f["r"].mean() / f["r"].std() * np.sqrt(252)  # noqa: E731
    a = stats.bootstrap_ci(frame, stat, n_boot=300, seed=1)
    b = stats.bootstrap_ci(frame, stat, n_boot=300, seed=1)
    assert a == b
    assert a["p05"] < stat(frame) < a["p95"] and a["p_positive"] > 0.9


def test_stationary_bootstrap_indices_are_valid_blocks():
    idx = stats.stationary_bootstrap_indices(1000, 20, np.random.default_rng(0))
    assert idx.min() >= 0 and idx.max() < 1000
    consecutive = (np.diff(idx) % 1000 == 1).mean()
    assert 0.90 < consecutive < 0.99  # ortalama blok ~20 gün


def test_pbo_is_about_half_for_noise_and_low_for_real_edge():
    rng = np.random.default_rng(9)
    noise = pd.DataFrame(rng.normal(0, 0.01, (2000, 20)))
    assert 0.25 < stats.cscv_pbo(noise, 10)["pbo"] < 0.75
    skilled = noise.copy()
    skilled[0] += 0.002  # tek gerçek üstün deneme
    out = stats.cscv_pbo(skilled, 10)
    assert out["pbo"] < 0.05 and out["n_splits"] == 252
    assert np.isnan(stats.cscv_pbo(noise.iloc[:, :1], 10)["pbo"])


def test_percentile_of():
    assert stats.percentile_of(3.0, np.array([1.0, 2.0, 4.0, 5.0])) == 0.5
    assert np.isnan(stats.percentile_of(1.0, np.array([np.nan])))
