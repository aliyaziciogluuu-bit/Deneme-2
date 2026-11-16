"""Aşırı uyum (overfitting) ve şans faktörüne karşı istatistikler.

* Olasılıksal Sharpe (PSR) ve Sönümlenmiş Sharpe (DSR): Bailey & López de Prado.
* Durağan blok bootstrap (Politis & Romano) ile güven aralıkları.
* CSCV ile "backtest aşırı uyum olasılığı" (PBO): Bailey, Borwein, López de Prado, Zhu.
* Rastgele portföy testi: aynı evrenden rastgele seçilen portföylere göre yüzdelik.
"""
from __future__ import annotations

import itertools
import math
from statistics import NormalDist

import numpy as np
import pandas as pd

_NORM = NormalDist()
EULER_GAMMA = 0.5772156649015329


def _moments(excess: np.ndarray) -> tuple[float, float, float, int]:
    x = np.asarray(excess, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    mu, sd = x.mean(), x.std(ddof=1)
    if sd <= 0 or n < 3:
        return float("nan"), 0.0, 3.0, n
    z = (x - mu) / x.std(ddof=0)
    return mu / sd, float((z**3).mean()), float((z**4).mean()), n


def probabilistic_sharpe(excess: np.ndarray, benchmark_sr: float = 0.0) -> float:
    """Gerçek (dönemlik) Sharpe'ın ``benchmark_sr``'yi aşma olasılığı.

    ``excess``: dönemlik (günlük) fazla getiriler. ``benchmark_sr`` aynı birimdedir
    (yıllık değil).
    """
    sr, skew, kurt, n = _moments(excess)
    if not np.isfinite(sr):
        return float("nan")
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom <= 0:
        return float("nan")
    return _NORM.cdf((sr - benchmark_sr) * math.sqrt(n - 1.0) / math.sqrt(denom))


def expected_max_sharpe(sr_variance: float, n_trials: int) -> float:
    """Yeteneksiz ``n_trials`` denemenin en iyisinden beklenen Sharpe (dönemlik birim)."""
    if n_trials <= 1 or sr_variance <= 0:
        return 0.0
    a = _NORM.inv_cdf(1.0 - 1.0 / n_trials)
    b = _NORM.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(sr_variance) * ((1.0 - EULER_GAMMA) * a + EULER_GAMMA * b)


def deflated_sharpe(excess: np.ndarray, trial_sharpes: np.ndarray) -> float:
    """Sönümlenmiş Sharpe: denenen tüm yapılandırmaların en iyisi şansla açıklanabilir mi?

    ``trial_sharpes``: denenen tüm yapılandırmaların dönemlik (günlük) Sharpe oranları
    (seçilen dahil). Dönen değer, seçilen stratejinin gerçek Sharpe'ının, şansla beklenen
    en iyi Sharpe'ı aşma olasılığıdır.
    """
    trials = np.asarray(trial_sharpes, dtype=float)
    trials = trials[np.isfinite(trials)]
    if len(trials) < 2:
        return probabilistic_sharpe(excess, 0.0)
    sr0 = expected_max_sharpe(float(trials.var(ddof=1)), len(trials))
    return probabilistic_sharpe(excess, sr0)


def stationary_bootstrap_indices(n: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano durağan bootstrap için ``n`` uzunlukta yeniden örnekleme dizini."""
    p = 1.0 / max(mean_block, 1.0)
    idx = np.empty(n, dtype=np.int64)
    idx[0] = rng.integers(n)
    jumps = rng.random(n) < p
    starts = rng.integers(n, size=n)
    for t in range(1, n):
        idx[t] = starts[t] if jumps[t] else (idx[t - 1] + 1) % n
    return idx


def bootstrap_ci(
    frame: pd.DataFrame,
    statistic,
    n_boot: int = 2000,
    mean_block: float = 20.0,
    seed: int = 7,
    levels: tuple[float, ...] = (0.05, 0.5, 0.95),
) -> dict:
    """``statistic(frame_yeniden_örneklenmiş) -> float`` için bootstrap dağılımı.

    Satırlar birlikte örneklenir (strateji ve kıyas aynı günlerle eşleşik kalır).
    Dönüş: yüzdelikler ve ``p_positive`` (istatistiğin > 0 olma oranı).
    """
    rng = np.random.default_rng(seed)
    values = frame.to_numpy(dtype=float)
    n = len(values)
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx = stationary_bootstrap_indices(n, mean_block, rng)
        out[b] = statistic(pd.DataFrame(values[idx], columns=frame.columns))
    out = out[np.isfinite(out)]
    result = {f"p{int(q * 100):02d}": float(np.quantile(out, q)) for q in levels}
    result["p_positive"] = float((out > 0).mean())
    return result


def cscv_pbo(trial_returns: pd.DataFrame, n_blocks: int = 10) -> dict:
    """Kombinatoryal simetrik çapraz doğrulama ile aşırı uyum olasılığı (PBO).

    ``trial_returns``: ``gün × deneme`` fazla getiri matrisi. Veri ``n_blocks`` ardışık bloğa
    bölünür; blokların yarısı "örnek içi", kalanı "örnek dışı" olacak tüm seçimler denenir.
    Her seçimde örnek içi en iyi denemenin örnek dışı sırası bulunur. PBO, bu sıranın
    medyanın altında kalma oranıdır (0.5 = yazı-tura; küçük olması iyidir).
    """
    m = trial_returns.dropna(how="any")
    n_trials = m.shape[1]
    if n_trials < 2 or n_blocks % 2 or len(m) < n_blocks * 20:
        return {"pbo": float("nan"), "n_splits": 0, "n_trials": n_trials}
    values = m.to_numpy(dtype=float)
    blocks = np.array_split(np.arange(len(values)), n_blocks)
    sums = np.array([values[b].sum(axis=0) for b in blocks])
    sq = np.array([(values[b] ** 2).sum(axis=0) for b in blocks])
    counts = np.array([len(b) for b in blocks], dtype=float)

    def sharpe_of(sel: tuple[int, ...]) -> np.ndarray:
        n = counts[list(sel)].sum()
        mean = sums[list(sel)].sum(axis=0) / n
        var = sq[list(sel)].sum(axis=0) / n - mean**2
        return mean / np.sqrt(np.where(var > 0, var, np.nan))

    logits = []
    all_blocks = set(range(n_blocks))
    for is_sel in itertools.combinations(range(n_blocks), n_blocks // 2):
        oos_sel = tuple(sorted(all_blocks - set(is_sel)))
        sr_is, sr_oos = sharpe_of(is_sel), sharpe_of(oos_sel)
        if not np.isfinite(sr_is).any():
            continue
        best = int(np.nanargmax(sr_is))
        rank = (sr_oos < sr_oos[best]).sum() + 0.5 * ((sr_oos == sr_oos[best]).sum() - 1) + 1.0
        omega = rank / (n_trials + 1.0)
        logits.append(math.log(omega / (1.0 - omega)))
    logits = np.array(logits)
    return {
        "pbo": float((logits <= 0).mean()) if len(logits) else float("nan"),
        "n_splits": int(len(logits)),
        "n_trials": int(n_trials),
        "median_logit": float(np.median(logits)) if len(logits) else float("nan"),
    }


def percentile_of(value: float, sample: np.ndarray) -> float:
    """``value``'nun ``sample`` içindeki yüzdeliği (0-1)."""
    sample = np.asarray(sample, dtype=float)
    sample = sample[np.isfinite(sample)]
    if len(sample) == 0:
        return float("nan")
    return float((sample < value).mean() + 0.5 * (sample == value).mean())
