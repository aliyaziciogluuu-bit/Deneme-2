"""Veri hazırlama hattı: bültenleri ve İş Yatırım verilerini eşitler, ``Dataset`` kurar.

Araştırma (uzun geçmiş) ve günlük çalışma (son ~2 yıl) aynı fonksiyonları kullanır.
Piyasa verisi depoya konmaz; her şey resmî/kamuya açık kaynaktan çalışma anında indirilir
ve yerel önbellekte tutulur.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .data.bulletin import BulletinStore
from .data.dataset import Dataset, build_dataset
from .data.http import HttpClient
from .data.isystore import IsyStore
from .data.macro import MacroStore
from .data.panel import MarketPanel, build_panel

log = logging.getLogger(__name__)

#: İş Yatırım dosyaları bu kadar günden eskiyse yenilenir (kaynak düzeltmelerini yakalamak için).
HISTORY_MAX_AGE_DAYS = 10
FINANCIALS_MAX_AGE_DAYS = 6
#: Günlük çalışmada mali tablo yenilemesi için geriye bakış (yıl).
FINANCIALS_REFRESH_YEARS = 3


@dataclass
class Stores:
    root: Path
    bulletins: BulletinStore
    isy: IsyStore
    macro: MacroStore


def open_stores(root: Path | str) -> Stores:
    root = Path(root)
    return Stores(
        root=root,
        bulletins=BulletinStore(root / "bulletin", HttpClient(min_interval=0.15)),
        isy=IsyStore(root / "isy", HttpClient(min_interval=0.4)),
        macro=MacroStore(root / "macro", HttpClient(min_interval=0.4)),
    )


def default_cache_dir() -> Path:
    return Path(os.environ.get("BISTBOT_CACHE", Path(__file__).resolve().parent.parent / ".cache"))


def load_panel(stores: Stores, start: dt.date, end: dt.date) -> MarketPanel:
    long = stores.bulletins.load_range(start, end)
    return build_panel(long)


def _age_days(path: Path, now: float) -> float:
    return (now - path.stat().st_mtime) / 86400.0 if path.exists() else float("inf")


def candidate_symbols(panel: MarketPanel, lookback: int = 300, extra: list[str] | None = None) -> list[str]:
    """Son ``lookback`` seansta BIST 100 üyesi olmuş hisseler + ek liste (eldeki pozisyonlar)."""
    recent = panel.bist100.iloc[-lookback:]
    syms = set(recent.columns[recent.any().to_numpy()])
    syms.update(s for s in (extra or []) if s in panel.close.columns)
    return sorted(syms)


def sync_isy(
    stores: Stores,
    panel: MarketPanel,
    symbols: list[str],
    today: dt.date,
    financials_start: dt.date | None = None,
    max_financial_refresh: int | None = None,
    history_start: dt.date | None = None,
) -> dict[str, int]:
    """İş Yatırım verilerini gerektiği kadar yeniler.

    Fiyat geçmişi ve özsermaye olayları şu durumlarda yeniden indirilir: dosya yok; dosyanın
    son gününden sonra bültende özsermaye olayı bayrağı var (geriye dönük katsayılar değişir);
    dosya ``HISTORY_MAX_AGE_DAYS`` günden eski. Mali tablolar eskiyince yenilenir; bir
    çalıştırmada en fazla ``max_financial_refresh`` bayat dosya yenilenir (en eskiler önce);
    hiç dosyası olmayan hisseler bu sınıra bakılmadan indirilir. ``history_start``: fiyat
    geçmişinin başlangıcı (kısa tutmak indirmeyi hızlandırır; katsayılar son güne göre
    olduğundan kısa geçmiş yeterlidir).
    """
    isy = stores.isy
    now = time.time()
    stats = {"history": 0, "actions": 0, "financials": 0, "failed": 0}
    dates = panel.dates

    need_history = []
    for sym in symbols:
        path = isy.path("history", sym)
        refresh = _age_days(path, now) > HISTORY_MAX_AGE_DAYS
        if not refresh:
            hist = isy.load("history", sym)
            if hist is None or hist.empty:
                refresh = _age_days(path, now) > 1.0  # boş yanıt: günde bir yeniden dene
            else:
                last = hist["date"].max()
                flagged = panel.corp_action[sym][dates > last] != ""
                refresh = bool(flagged.any())
        if refresh:
            need_history.append(sym)
    hist_start = history_start or dt.date(2015, 11, 30)
    for kind in ("history", "actions"):
        res = isy.sync(kind, need_history, today, start=hist_start, force=True, workers=2, progress_every=0)
        stats[kind] = res["fetched"] + res["empty"]
        stats["failed"] += res["failed"]

    fin_start = financials_start or dt.date(today.year - FINANCIALS_REFRESH_YEARS, 1, 1)
    missing = [s for s in symbols if not isy.has("financials", s)]
    stale = sorted(
        (s for s in symbols if isy.has("financials", s)
         and _age_days(isy.path("financials", s), now) > FINANCIALS_MAX_AGE_DAYS),
        key=lambda s: -_age_days(isy.path("financials", s), now),
    )
    if max_financial_refresh is not None:
        stale = stale[:max_financial_refresh]
    res = isy.sync("financials", missing + stale, today, start=fin_start, force=True, workers=2, progress_every=0)
    stats["financials"] = res["fetched"] + res["empty"]
    stats["failed"] += res["failed"]
    return stats


def prepare_dataset(stores: Stores, panel: MarketPanel, symbols: list[str]) -> Dataset:
    """Önbellekten ``Dataset`` kurar (ağ erişimi yapmaz)."""
    rf = stores.macro.load_rf()
    if rf.empty:
        raise RuntimeError("risksiz oran önbelleği boş: önce veriyi eşitleyin")
    xu100 = stores.macro.load_index("XU100")
    return build_dataset(panel, stores.isy, rf, symbols, xu100=xu100 if len(xu100) else None)
