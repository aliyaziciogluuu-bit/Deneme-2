"""Teknik göstergeler (düzeltilmiş günlük fiyatlardan, ``tarih × sembol`` tabloları).

Her tablonun ``t`` satırı yalnızca ``t`` günü kapanışına kadarki veriyi kullanır. Hesaplar
düzeltilmiş (temettü/bölünme arındırılmış) fiyatlarla yapılır; aksi hâlde bir bedelsiz
sermaye artırımı sahte bir "düşüş trendi" üretir.

Eğilim ölçüleri **nakde göre** fiyatla hesaplanır (fiyat / gecelik faiz endeksi). Yüksek
enflasyonda TL fiyatların neredeyse hepsi 200 günlük ortalamasının üstündedir; "yükseliş
eğilimi" ancak hisse faizden fazla kazandırıyorsa anlam taşır.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data.dataset import Dataset
from .portfolio import cash_index

HIGH_WINDOW = 252


@dataclass
class Technicals:
    #: Nakde göre fiyatın uzun hareketli ortalamaya (varsayılan 200 gün) oranı − 1.
    trend: pd.DataFrame
    #: Nakde göre fiyat uzun ortalamanın üstünde mi (yükseliş eğilimi).
    uptrend: pd.DataFrame
    #: Kısa ortalamanın (50) uzun ortalamaya (200) oranı − 1 ("altın kesişim" ölçüsü).
    ma_cross: pd.DataFrame
    #: Nakde göre fiyatın son 252 günün en yüksek kapanışına oranı (1 = zirvede).
    high_52w: pd.DataFrame
    #: Wilder RSI (0-100), ekranda görülen (nominal) fiyattan.
    rsi: pd.DataFrame
    #: MACD histogramı / fiyat (12-26-9).
    macd_hist: pd.DataFrame
    #: Ortalama gerçek aralık / fiyat (ATR yüzdesi).
    atr_pct: pd.DataFrame
    #: Son 20 günün ortalama işlem hacminin son 120 güne oranı (ilgi artışı).
    volume_ratio: pd.DataFrame


def _wilder(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Wilder düzeltmesi: ``alpha = 1/window`` üstel ortalama."""
    return df.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def rsi(close: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    delta = close.diff()
    gain = _wilder(delta.clip(lower=0.0), window)
    loss = _wilder((-delta).clip(lower=0.0), window)
    rs = gain / loss.where(loss > 0)
    out = 100.0 - 100.0 / (1.0 + rs)
    # Hiç düşüş yoksa RSI 100'dür; hiç hareket yoksa tanımsız kalır.
    return out.where(loss > 0, 100.0).where(gain.notna() & loss.notna() & ((gain > 0) | (loss > 0)))


def macd_histogram(close: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=slow).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd = ema_fast - ema_slow
    return macd - macd.ewm(span=signal, adjust=False, min_periods=signal).mean()


def average_true_range(high: pd.DataFrame, low: pd.DataFrame, close: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    prev = close.shift(1)
    tr = np.maximum(high - low, np.maximum((high - prev).abs(), (low - prev).abs()))
    return _wilder(tr, window)


def excess_price(ds: Dataset, price: pd.DataFrame) -> pd.DataFrame:
    """Fiyatı gecelik faiz endeksine böler: faizi aşan getiri "yükseliş" sayılır."""
    cash = cash_index(ds.rf).reindex(price.index).ffill()
    return price.div(cash, axis=0)


def trend_measures(
    price: pd.DataFrame, long_window: int = 200, short_window: int = 50, high_window: int = HIGH_WINDOW
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """``(trend, ma_cross, high_52w)``: uzun ortalamaya uzaklık, kısa/uzun ortalama oranı − 1,
    son ``high_window`` günün zirvesine oran."""
    sma_long = price.rolling(long_window, min_periods=int(long_window * 0.8)).mean()
    sma_short = price.rolling(short_window, min_periods=int(short_window * 0.8)).mean()
    peak = price.rolling(high_window, min_periods=int(high_window * 0.8)).max()
    return price / sma_long - 1.0, sma_short / sma_long - 1.0, price / peak


def compute_technicals(
    ds: Dataset, symbols: list[str] | None = None, trend_window: int = 200, short_window: int = 50
) -> Technicals:
    cols = list(symbols) if symbols is not None else list(ds.symbols)
    listed = ds.panel.listed[cols]
    close = ds.adjusted("close")[cols].ffill().where(listed)
    high = ds.adjusted("high")[cols].fillna(close)
    low = ds.adjusted("low")[cols].fillna(close)
    value = ds.panel.value[cols].where(listed)

    trend, ma_cross, high_52w = trend_measures(excess_price(ds, close), trend_window, short_window)
    vol_short = value.rolling(20, min_periods=15).mean()
    vol_long = value.rolling(120, min_periods=90).mean()
    return Technicals(
        trend=trend,
        uptrend=(trend > 0) & trend.notna(),
        ma_cross=ma_cross,
        high_52w=high_52w,
        rsi=rsi(close),
        macd_hist=macd_histogram(close) / close,
        atr_pct=average_true_range(high, low, close) / close,
        volume_ratio=vol_short / vol_long.where(vol_long > 0),
    )
