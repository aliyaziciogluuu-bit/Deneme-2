"""Portföy kuralları: hisse seçimi, hedef ağırlıklar, yeniden dengeleme takvimi, rejim filtresi.

Bu modüldeki fonksiyonlar hem backtest motoru hem günlük (canlı) çalıştırıcı tarafından
aynen kullanılır; böylece geçmiş testi ile canlı kararlar aynı kuraldan çıkar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import PortfolioConfig


def select_holdings(scores: pd.DataFrame, current: list[str], cfg: PortfolioConfig) -> list[str]:
    """Bantlı seçim: eldeki hisse sırası ``hold_rank`` içindeyse kalır, boşalan yerlere en iyi
    sıradaki yeni hisseler alınır. Puan tablosunda olmayan (evrenden çıkan) hisseler bırakılır.
    """
    if scores.empty:
        return []
    rank = scores["rank"]
    keep = sorted((s for s in current if s in rank.index and rank[s] <= cfg.hold_rank), key=lambda s: rank[s])
    keep = keep[: cfg.n_holdings]
    kept = set(keep)
    slots = cfg.n_holdings - len(keep)
    newcomers = [s for s in rank.sort_values().index if s not in kept][: max(slots, 0)]
    return keep + newcomers


def target_weights(holdings: list[str], exposure: float, cfg: PortfolioConfig) -> pd.Series:
    """Eşit ağırlık: her hisse ``exposure / n_holdings``. Hisse sayısı eksikse kalan nakittir."""
    if not holdings:
        return pd.Series(dtype=float)
    return pd.Series(exposure / cfg.n_holdings, index=holdings)


def rebalance_dates(dates: pd.DatetimeIndex, cfg: PortfolioConfig) -> pd.DatetimeIndex:
    """Karar günleri. Yalnızca geçmiş takvim bilgisine dayanır:

    * ``monthly``: her ayın ``offset + 1``'inci seansı,
    * ``weekly``: her haftanın ``offset + 1``'inci seansı.

    Karar o günün kapanışından sonra verilir, işlemler izleyen seansta yapılır.
    """
    if cfg.frequency == "monthly":
        key = dates.year * 12 + dates.month
    elif cfg.frequency == "weekly":
        iso = dates.isocalendar()
        key = (iso["year"].to_numpy() * 100 + iso["week"].to_numpy())
    else:
        raise ValueError(f"bilinmeyen sıklık: {cfg.frequency}")
    key = np.asarray(key)
    order = pd.Series(np.arange(len(dates))).groupby(key).cumcount().to_numpy()
    return dates[order == cfg.offset]


def is_rebalance_day(dates: pd.DatetimeIndex, cfg: PortfolioConfig) -> bool:
    """``dates`` dizisinin son günü karar günü mü (canlı çalıştırıcı için)."""
    if len(dates) == 0:
        return False
    return dates[-1] in rebalance_dates(dates, cfg)


def cash_index(rf: pd.Series, share: float = 1.0) -> pd.Series:
    """Gecelik faizle büyüyen nakit endeksi (takvim günü, basit faiz/365, günlük bileşik).

    ``rf`` yıllık basit orandır (ondalık). ``t`` günündeki değer, ``t``'den önceki son
    seansta geçerli oranın aradaki takvim günleri kadar işletilmesiyle bulunur.
    """
    dates = rf.index
    days = np.diff(dates.values).astype("timedelta64[D]").astype(float)
    growth = 1.0 + rf.to_numpy()[:-1] * share * days / 365.0
    growth = np.where(np.isfinite(growth), growth, 1.0)
    return pd.Series(np.concatenate([[1.0], np.cumprod(growth)]), index=dates)


def regime_exposure(xu100: pd.Series, rf: pd.Series, cfg: PortfolioConfig) -> pd.Series:
    """Rejim filtresine göre günlük hisse ağırlığı (0-1).

    ``trend``: BIST 100'ün son 12 aylık getirisi aynı dönemdeki gecelik faiz getirisini
    aşıyorsa tam ağırlık, aşmıyorsa ``regime_off_exposure``. Türk lirasında nominal fiyatlar
    enflasyonla yükseldiği için karşılaştırma sıfıra değil nakit getirisine göre yapılır.
    """
    if cfg.regime == "none":
        return pd.Series(1.0, index=xu100.index)
    if cfg.regime != "trend":
        raise ValueError(f"bilinmeyen rejim filtresi: {cfg.regime}")
    lookback = cfg.regime_lookback
    cash = cash_index(rf)
    index_ret = xu100 / xu100.shift(lookback)
    cash_ret = cash / cash.shift(lookback)
    on = index_ret > cash_ret
    exposure = pd.Series(np.where(on, 1.0, cfg.regime_off_exposure), index=xu100.index)
    # Yeterli geçmiş yokken filtre uygulanmaz.
    return exposure.where(index_ret.notna() & cash_ret.notna(), 1.0)
