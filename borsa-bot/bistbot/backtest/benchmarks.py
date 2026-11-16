"""Kıyas serileri: BIST 100 endeksi, eşit ağırlıklı evren, nakit."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.dataset import Dataset
from ..portfolio import cash_index


def equal_weight_universe(ds: Dataset, universe: pd.DataFrame) -> pd.Series:
    """Evrendeki hisselerin eşit ağırlıklı, her gün yeniden dengelenen toplam getiri endeksi.

    ``t`` günü getirisi, ``t-1`` günü evrende olan hisselerin ``t`` getirilerinin ortalamasıdır
    (üyelik bir gün gecikmeli kullanılır). Temettü stopajı düşülür, işlem maliyeti düşülmez;
    yani "aynı havuzdan rastgele seçim" için maliyetsiz, zorlu bir kıyastır.
    """
    cols = list(universe.columns)
    ret = ds.returns[cols] - ds.div_tax[cols]
    members = universe.shift(1).fillna(False).astype(bool)
    daily = ret.where(members).mean(axis=1).fillna(0.0)
    return (1.0 + daily).cumprod().rename("eşit ağırlıklı BIST 100")


def xu100_index(ds: Dataset) -> pd.Series:
    """BIST 100 fiyat endeksi (temettü içermez; al-tut getirisini yılda ~%2-3 eksik gösterir)."""
    s = ds.xu100.dropna()
    return (s / s.iloc[0]).rename("BIST 100")


def cash(ds: Dataset, share: float = 1.0) -> pd.Series:
    return cash_index(ds.rf, share).rename("gecelik faiz")
