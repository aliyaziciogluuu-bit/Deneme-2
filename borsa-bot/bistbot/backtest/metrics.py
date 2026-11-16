"""Performans ölçüleri. Tüm Sharpe benzeri oranlar gecelik TL faizinin ÜZERİNDEKİ getiriyle
hesaplanır; Türkiye'de risksiz faiz %10-50 arasında gezdiği için sıfır faiz varsayımı yanıltır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_rf(rf: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Yıllık basit oran serisinden, ``index`` günlerine düşen günlük nakit getirisi.

    ``t`` gününün getirisi, bir önceki seansta geçerli oranın aradaki takvim günü kadar
    işletilmesidir (hafta sonu ve tatiller dahil).
    """
    aligned = rf.reindex(rf.index.union(index)).ffill().reindex(index)
    days = pd.Series(index, index=index).diff().dt.days.fillna(0.0)
    return (aligned.shift(1) * days / 365.0).fillna(0.0)


def drawdown(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def max_drawdown_duration(equity: pd.Series) -> int:
    """En uzun "zirvenin altında kalma" süresi (takvim günü)."""
    peak = equity.cummax()
    under = equity < peak
    longest, start = 0, None
    for day, flag in under.items():
        if flag and start is None:
            start = day
        elif not flag and start is not None:
            longest = max(longest, (day - start).days)
            start = None
    if start is not None:
        longest = max(longest, (equity.index[-1] - start).days)
    return int(longest)


def cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0 or equity.iloc[0] <= 0:
        return float("nan")
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0)


def sharpe(returns: pd.Series, rf_daily: pd.Series | None = None) -> float:
    excess = returns - (rf_daily if rf_daily is not None else 0.0)
    sd = excess.std()
    return float(excess.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")


def sortino(returns: pd.Series, rf_daily: pd.Series | None = None) -> float:
    excess = returns - (rf_daily if rf_daily is not None else 0.0)
    downside = np.sqrt((np.minimum(excess, 0.0) ** 2).mean())
    return float(excess.mean() / downside * np.sqrt(TRADING_DAYS)) if downside > 0 else float("nan")


def _hac_tstat(y: np.ndarray, x: np.ndarray, lags: int = 10) -> tuple[float, float, float]:
    """``y = a + b·x + e`` regresyonu; ``a`` için Newey-West (HAC) t-istatistiği.

    Dönüş: (alfa, beta, alfa t-istatistiği).
    """
    n = len(y)
    X = np.column_stack([np.ones(n), x])
    xtx_inv = np.linalg.inv(X.T @ X)
    coef = xtx_inv @ X.T @ y
    resid = y - X @ coef
    xe = X * resid[:, None]
    s = xe.T @ xe
    for lag in range(1, min(lags, n - 1) + 1):
        w = 1.0 - lag / (lags + 1.0)
        gamma = xe[lag:].T @ xe[:-lag]
        s += w * (gamma + gamma.T)
    cov = xtx_inv @ s @ xtx_inv
    se = np.sqrt(max(cov[0, 0], 1e-300))
    return float(coef[0]), float(coef[1]), float(coef[0] / se)


def summarize(
    equity: pd.Series, rf: pd.Series, benchmark: pd.Series | None = None
) -> dict[str, float]:
    """Bir değer serisinin özet ölçüleri. ``benchmark`` verilirse göreli ölçüler eklenir."""
    equity = equity.dropna()
    ret = equity.pct_change().dropna()
    rfd = daily_rf(rf, equity.index).reindex(ret.index)
    dd = drawdown(equity)
    out = {
        "years": (equity.index[-1] - equity.index[0]).days / 365.25,
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1.0),
        "cagr": cagr(equity),
        "volatility": float(ret.std() * np.sqrt(TRADING_DAYS)),
        "sharpe": sharpe(ret, rfd),
        "sortino": sortino(ret, rfd),
        "max_drawdown": float(dd.min()),
        "max_dd_days": max_drawdown_duration(equity),
        "cash_cagr": cagr((1.0 + rfd).cumprod()),
        "worst_day": float(ret.min()),
        "best_day": float(ret.max()),
    }
    out["calmar"] = out["cagr"] / abs(out["max_drawdown"]) if out["max_drawdown"] < 0 else float("nan")
    if benchmark is not None:
        bench = benchmark.reindex(equity.index).ffill()
        bret = bench.pct_change().reindex(ret.index).fillna(0.0)
        active = ret - bret
        te = active.std() * np.sqrt(TRADING_DAYS)
        alpha, beta, t_alpha = _hac_tstat((ret - rfd).to_numpy(), (bret - rfd).to_numpy())
        out.update(
            {
                "bench_cagr": cagr(bench),
                "excess_cagr": cagr(equity) - cagr(bench),
                "tracking_error": float(te),
                "information_ratio": float(active.mean() * TRADING_DAYS / te) if te > 0 else float("nan"),
                "beta": beta,
                "alpha_annual": alpha * TRADING_DAYS,
                "alpha_tstat": t_alpha,
            }
        )
    return out


def yearly_returns(series: dict[str, pd.Series]) -> pd.DataFrame:
    """Takvim yılı getirileri: her seri için yıl sonu / önceki yıl sonu − 1."""
    cols = {}
    for name, s in series.items():
        s = s.dropna()
        year_end = s.groupby(s.index.year).last()
        prev = year_end.shift(1)
        prev.iloc[0] = s.iloc[0]
        cols[name] = year_end / prev - 1.0
    return pd.DataFrame(cols)


def deflate(equity: pd.Series, index: pd.Series) -> pd.Series:
    """Bir TL serisini başka bir endekse böler (ör. USD/TRY ile dolar bazı, nakit endeksiyle
    nakde göre değer) ve 1'e normalize eder."""
    idx = index.reindex(equity.index).ffill()
    out = equity / idx
    return out / out.dropna().iloc[0]
