"""Kıyas serileri: aynı havuzun eşit ağırlıklı sepeti, BIST 100 endeksi, nakit."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.dataset import Dataset
from ..portfolio import cash_index


def _net_returns(ds: Dataset, cols: list[str]) -> pd.DataFrame:
    """Günlük toplam getiri, temettü stopajı düşülmüş."""
    return ds.returns[cols] - ds.div_tax[cols]


def lagged_membership(universe: pd.DataFrame) -> pd.DataFrame:
    """``t`` günü için geçerli üyelik: ``t``'den önceki son BOŞ OLMAYAN evren satırı.

    Piyasa birkaç seans kapalı kaldığında (ör. Şubat 2023) o günlerin evreni boştur; açılış
    günü getirisi, kapanıştan önceki son üyelere yazılır. Aksi hâlde kıyas, portföyün
    yaşadığı açılış günü hareketini hiç görmez.
    """
    values = universe.to_numpy(dtype=bool)
    lagged = np.zeros_like(values)
    last_valid: np.ndarray | None = None
    for i in range(len(values)):
        if last_valid is not None:
            lagged[i] = last_valid
        if values[i].any():
            last_valid = values[i]
    return pd.DataFrame(lagged, index=universe.index, columns=universe.columns)


def equal_weight_universe(ds: Dataset, universe: pd.DataFrame) -> pd.Series:
    """Evrenin eşit ağırlıklı, her gün yeniden dengelenen toplam getiri endeksi (maliyetsiz).

    İkincil kıyastır: her gün eşit ağırlığa dönmek, art arda taban yapan hisseleri almaya
    devam etmek demektir ve gerçek bir portföyün yapabileceğinden farklıdır.
    """
    cols = list(universe.columns)
    members = lagged_membership(universe)
    daily = _net_returns(ds, cols).where(members).mean(axis=1).fillna(0.0)
    return (1.0 + daily).cumprod().rename("eşit ağırlık (günlük)")


def periodic_equal_weight(ds: Dataset, baskets: dict[pd.Timestamp, list[str]]) -> pd.Series:
    """Karar günlerinde yenilenen, arada dokunulmayan eşit ağırlıklı sepet (maliyetsiz).

    ``baskets``: ``{karar günü: hisse listesi}``. Sepet karar günü kapanışında eşit ağırlıkla
    kurulur ve bir sonraki karar gününe kadar al-tut olarak taşınır. Stratejinin seçim yaptığı
    havuzun ve takvimin aynısını kullandığı için "seçim ne kattı?" sorusunun doğru kıyasıdır.
    """
    dates = ds.dates
    decision_days = sorted(d for d in baskets if d in dates)
    if not decision_days:
        return pd.Series(dtype=float)
    cols = sorted({s for d in decision_days for s in baskets[d]})
    growth = (1.0 + _net_returns(ds, cols).fillna(0.0)).to_numpy()
    col_pos = {s: j for j, s in enumerate(cols)}
    start = dates.get_loc(decision_days[0])
    level = np.ones(len(dates))
    value = 1.0
    bounds = [dates.get_loc(d) for d in decision_days] + [len(dates) - 1]
    for k, day in enumerate(decision_days):
        lo, hi = bounds[k], bounds[k + 1]
        members = [col_pos[s] for s in baskets[day]]
        if not members or hi <= lo:
            level[lo : hi + 1] = value
            continue
        path = np.cumprod(growth[lo + 1 : hi + 1][:, members], axis=0).mean(axis=1)
        level[lo + 1 : hi + 1] = value * path
        value = float(level[hi])
    out = pd.Series(level, index=dates).iloc[start:]
    return out.rename("eşit ağırlık (aylık)")


def xu100_index(ds: Dataset) -> pd.Series:
    """BIST 100 fiyat endeksi (temettü içermez; al-tut getirisini yılda ~%2-3 eksik gösterir)."""
    s = ds.xu100.dropna()
    return (s / s.iloc[0]).rename("BIST 100")


def cash(ds: Dataset, share: float = 1.0) -> pd.Series:
    return cash_index(ds.rf, share).rename("gecelik faiz")
