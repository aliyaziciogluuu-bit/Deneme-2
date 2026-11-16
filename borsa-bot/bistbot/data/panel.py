"""Bültenlerden geniş (tarih × sembol) piyasa paneli.

Uzun biçimli günlük bülten satırlarını alır, kod değişikliklerini (ör. KOZAL → TRALT)
tek bir güncel sembol altında birleştirir ve her alan için bir geniş tablo üretir.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PRICE_FIELDS = ("open", "high", "low", "close", "vwap", "prev_close")
NUM_FIELDS = PRICE_FIELDS + ("value", "volume")
FLAG_FIELDS = ("bist100", "bist30", "gross", "suspended", "short_ok")
TEXT_FIELDS = ("market", "method", "corp_action")


def detect_renames(
    long: pd.DataFrame, name_gap_sessions: int = 3, price_band: float = 0.105
) -> dict[str, str]:
    """Bültenlerden kod değişikliklerini bulur: ``{eski_kod: yeni_kod}``.

    Kod değiştiren pay eski koduyla son kez göründüğü seansın hemen ardından yeni koduyla
    görünür (yeni kodun ilk gününde bülten "önceki kapanış" alanı boştur). İki kural:

    1. **Aynı bülten adı**: yeni kod, en fazla ``name_gap_sessions`` seans önce kaybolan
       bir kodla aynı adı taşıyorsa kod değişikliğidir (KOZAL → TRALT gibi).
    2. **Fiyat sürekliliği**: adı da aynı gün değişmişse (GUSGR → TURSG gibi), bir önceki
       seansta kaybolan ve 1. kuralla eşleşmemiş kodlar arasında, yeni kodun ilk açılışı
       eskinin son kapanışının günlük fiyat marjı içinde olan *tek* aday varsa ve bu aday
       için de tek uygun yeni kod buysa eşleştirilir.

    Birleşmeler (pay başka bir şirketin payına dönüşür) bilerek eşleştirilmez; onlar kottan
    çıkış olarak kalır.
    """
    if long.empty:
        return {}
    sessions = np.sort(long["date"].unique())
    pos = {d: i for i, d in enumerate(sessions)}
    ordered = long.sort_values(["symbol", "date"])
    grp = ordered.groupby("symbol", sort=False)
    first = grp.head(1).set_index("symbol")
    last = grp.tail(1).set_index("symbol")
    last_close = ordered.dropna(subset=["close"]).groupby("symbol", sort=False)["close"].last()

    started = first[first["date"] > sessions[0]]
    ended = last[last["date"] < sessions[-1]]
    start_pos = started["date"].map(pos)
    end_pos = ended["date"].map(pos)

    renames: dict[str, str] = {}
    # 1) Aynı ad, yakın tarih.
    for new_sym, sp in start_pos.items():
        gap = sp - end_pos
        cands = [
            old for old in gap[(gap > 0) & (gap <= name_gap_sessions)].index
            if old != new_sym and ended.at[old, "name"] and ended.at[old, "name"] == started.at[new_sym, "name"]
        ]
        if len(cands) == 1 and cands[0] not in renames:
            renames[cands[0]] = new_sym

    # 2) Ardışık seans + fiyat sürekliliği + karşılıklı teklik.
    used_new = set(renames.values())
    pairs: list[tuple[str, str]] = []
    for new_sym, sp in start_pos.items():
        if new_sym in used_new:
            continue
        open_px = started.at[new_sym, "open"]
        if not np.isfinite(open_px):
            continue
        for old in end_pos[end_pos == sp - 1].index:
            if old == new_sym or old in renames or old not in last_close.index:
                continue
            if abs(open_px / last_close[old] - 1.0) <= price_band:
                pairs.append((old, new_sym))
    old_count = pd.Series([o for o, _ in pairs]).value_counts() if pairs else pd.Series(dtype=int)
    new_count = pd.Series([n for _, n in pairs]).value_counts() if pairs else pd.Series(dtype=int)
    for old, new_sym in pairs:
        if old_count[old] == 1 and new_count[new_sym] == 1:
            renames[old] = new_sym
    return renames


def resolve_chain(renames: dict[str, str]) -> dict[str, str]:
    """Zincirleme değişiklikleri (A→B, B→C) son koda indirger (A→C, B→C)."""
    out = {}
    for old in renames:
        cur, seen = old, {old}
        while cur in renames and renames[cur] not in seen:
            cur = renames[cur]
            seen.add(cur)
        out[old] = cur
    return out


@dataclass
class MarketPanel:
    """Her alan için ``tarih × sembol`` tablosu. Fiyatlar hamdır (düzeltilmemiş)."""

    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    vwap: pd.DataFrame
    prev_close: pd.DataFrame
    value: pd.DataFrame
    volume: pd.DataFrame
    bist100: pd.DataFrame
    bist30: pd.DataFrame
    gross: pd.DataFrame
    suspended: pd.DataFrame
    short_ok: pd.DataFrame
    market: pd.DataFrame
    method: pd.DataFrame
    corp_action: pd.DataFrame
    listed: pd.DataFrame  # o gün bültende satırı var mı
    names: dict[str, str] = field(default_factory=dict)
    renames: dict[str, str] = field(default_factory=dict)  # eski kod -> güncel kod

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.close.index

    @property
    def symbols(self) -> pd.Index:
        return self.close.columns

    def old_codes(self, symbol: str) -> list[str]:
        return [old for old, new in self.renames.items() if new == symbol]


def build_panel(long: pd.DataFrame, renames: dict[str, str] | None = None) -> MarketPanel:
    """Uzun bülten tablosundan paneli kurar."""
    if long.empty:
        raise ValueError("bülten verisi boş")
    if renames is None:
        renames = detect_renames(long)
    chain = resolve_chain(renames)
    df = long.copy()
    df["symbol"] = df["symbol"].map(lambda s: chain.get(s, s))
    dup = df.duplicated(["date", "symbol"], keep=False)
    if dup.any():
        # Aynı gün hem eski hem yeni kod görünüyorsa eşleştirme hatalıdır.
        bad = sorted(df.loc[dup, "symbol"].unique())
        raise ValueError(f"kod birleştirme çakışması: {bad[:10]}")

    dates = pd.DatetimeIndex(np.sort(df["date"].unique()))
    symbols = pd.Index(sorted(df["symbol"].unique()))

    def wide(col: str) -> pd.DataFrame:
        return df.pivot(index="date", columns="symbol", values=col).reindex(index=dates, columns=symbols)

    tables: dict[str, pd.DataFrame] = {}
    for col in NUM_FIELDS:
        tables[col] = wide(col).astype(float)
    tables["value"] = tables["value"].fillna(0.0)
    tables["volume"] = tables["volume"].fillna(0.0)
    for col in FLAG_FIELDS:
        tables[col] = wide(col).fillna(0).astype(bool)
    for col in TEXT_FIELDS:
        tables[col] = wide(col).fillna("").astype(object)
    listed = df.assign(_one=True).pivot(index="date", columns="symbol", values="_one")
    tables["listed"] = listed.reindex(index=dates, columns=symbols).fillna(False).astype(bool)

    names = df.sort_values("date").groupby("symbol")["name"].last().to_dict()
    return MarketPanel(names=names, renames=chain, **tables)
