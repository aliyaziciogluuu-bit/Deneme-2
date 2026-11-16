"""İş Yatırım verilerinin disk önbelleği (fiyat geçmişi, özsermaye olayları, mali tablolar)."""
from __future__ import annotations

import datetime as dt
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from . import isyatirim as isy
from .http import HttpClient

log = logging.getLogger(__name__)

HISTORY_START = dt.date(2015, 11, 30)


class EmptyResponse(RuntimeError):
    """Kaynak boş yanıt verdi; önbellekteki dolu dosya korundu."""


def quarter_ends(start: dt.date, end: dt.date) -> list[tuple[int, int]]:
    """``[start, end]`` aralığında biten mali dönemler: (yıl, ay) ay ∈ {3, 6, 9, 12}."""
    out = []
    for year in range(start.year, end.year + 1):
        for month in (3, 6, 9, 12):
            last_day = dt.date(year, month, 31 if month in (3, 12) else 30)
            if start <= last_day <= end:
                out.append((year, month))
    return out


class IsyStore:
    """``<root>/history/SYM.csv``, ``<root>/actions/SYM.csv``, ``<root>/financials/SYM.csv``."""

    def __init__(self, root: Path, client: HttpClient | None = None) -> None:
        self.root = Path(root)
        self.client = client or HttpClient(min_interval=0.35)
        for sub in ("history", "actions", "financials"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def path(self, kind: str, symbol: str) -> Path:
        return self.root / kind / f"{symbol}.csv"

    # -- okuma ------------------------------------------------------------------
    def load(self, kind: str, symbol: str) -> pd.DataFrame | None:
        p = self.path(kind, symbol)
        if not p.exists():
            return None
        dtype = {"type_code": str} if kind == "actions" else None
        try:
            df = pd.read_csv(p, dtype=dtype)
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
        if kind in ("history", "actions") and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
            df = df.dropna(subset=["date"])
        return df

    def has(self, kind: str, symbol: str) -> bool:
        return self.path(kind, symbol).exists()

    # -- indirme ----------------------------------------------------------------
    def _write(self, kind: str, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        """Dosyayı atomik yazar. Kaynak boş yanıt verdiyse ve elde dolu bir dosya varsa
        eskisi korunur: geçici bir kesinti, iyi veriyi silmemelidir.
        """
        path = self.path(kind, symbol)
        if df.empty and path.exists():
            old = self.load(kind, symbol)
            if old is not None and not old.empty:
                raise EmptyResponse(f"{kind} {symbol}: kaynak boş yanıt verdi, eldeki veri korundu")
        tmp = path.with_suffix(f".{threading.get_ident()}.tmp")
        df.to_csv(tmp, index=False)
        os.replace(tmp, path)
        return df

    def fetch_history(self, symbol: str, end: dt.date, start: dt.date = HISTORY_START) -> pd.DataFrame:
        return self._write("history", symbol, isy.fetch_history(self.client, symbol, start, end))

    def fetch_actions(self, symbol: str) -> pd.DataFrame:
        return self._write("actions", symbol, isy.fetch_corporate_actions(self.client, symbol))

    def fetch_financials(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        """Tüm dönemleri getirir; mevcut dosyadaki dönemleri korur, yenileriyle birleştirir."""
        periods = quarter_ends(start, end)
        if not periods:
            return pd.DataFrame(columns=isy.FINANCIAL_COLUMNS)
        # Hangi mali tablo grubunda veri olduğunu, döneme yayılmış 4 örnekle yokla
        # (kottan çıkmış payların son dönemleri boştur; yalnızca son 4 döneme bakılmaz).
        step = max(1, len(periods) // 4)
        probe = sorted(set(periods[::step][:3] + [periods[-1]]))
        groups = []
        for group in ("XI_29", "UFRS_K", "UFRS"):
            if not isy.fetch_financials(self.client, symbol, group, probe).empty:
                groups.append(group)
                if group == "XI_29":
                    break
        frames = []
        for group in groups:
            for i in range(0, len(periods), 4):
                frames.append(isy.fetch_financials(self.client, symbol, group, periods[i : i + 4]))
        old = self.load("financials", symbol)
        if old is not None and not old.empty:
            frames.append(old)
        frames = [f for f in frames if f is not None and not f.empty]
        if frames:
            df = pd.concat(frames, ignore_index=True)
            # Aynı dönem birden çok grupta varsa öncelik: XI_29 > UFRS_K > UFRS; yeni veri eskiyi ezer.
            order = {"XI_29": 0, "UFRS_K": 1, "UFRS": 2}
            df["_o"] = df["group"].map(order).fillna(9)
            df = (
                df.sort_values(["year", "period", "_o"], kind="stable")
                .drop_duplicates(["year", "period"], keep="first")
                .drop(columns="_o")
                .reset_index(drop=True)
            )
        else:
            df = pd.DataFrame(columns=isy.FINANCIAL_COLUMNS)
        return self._write("financials", symbol, df)

    def sync(
        self,
        kind: str,
        symbols: list[str],
        end: dt.date,
        start: dt.date = HISTORY_START,
        force: bool = False,
        workers: int = 2,
        progress_every: int = 25,
    ) -> dict[str, int]:
        """Eksik (veya ``force`` ise tüm) sembolleri indirir. Tek sembol hatası diğerlerini durdurmaz."""
        todo = [s for s in symbols if force or not self.has(kind, s)]
        stats = {"fetched": 0, "empty": 0, "failed": 0}

        def job(sym: str) -> tuple[str, str]:
            try:
                if kind == "history":
                    df = self.fetch_history(sym, end, start)
                elif kind == "actions":
                    df = self.fetch_actions(sym)
                elif kind == "financials":
                    df = self.fetch_financials(sym, start, end)
                else:
                    raise ValueError(kind)
                return sym, ("empty" if df.empty else "fetched")
            except Exception as exc:
                log.warning("%s alınamadı %s: %s", kind, sym, exc)
                return sym, "failed"

        done = 0
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            for fut in as_completed([pool.submit(job, s) for s in todo]):
                _, status = fut.result()
                stats[status] += 1
                done += 1
                if progress_every and done % progress_every == 0:
                    log.info("%s eşitleme: %d/%d", kind, done, len(todo))
        return stats
