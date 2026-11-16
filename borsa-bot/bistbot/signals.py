"""Sinyaller: evren filtresi, özellikler ve bileşik puan.

Her tablonun ``t`` satırı yalnızca ``t`` günü kapanışına kadar bilinen veriyi kullanır;
kararlar ``t`` kapanışından sonra verilir, işlemler ``t+1`` seansında yapılır.

Dört sütun (hepsi BIST üzerine yayımlanmış kesitsel bulgulara dayanır):

* **Değer**: özkaynak / piyasa değeri (düşük PD/DD) ve kâr / piyasa değeri (düşük F/K).
* **Kârlılık**: yıllıklandırılmış net kâr / özkaynak (aynı mali tablodan).
* **Düşük risk**: düşük oynaklık, düşük beta, düşük "piyango" eğilimi (son ayın en yüksek
  günlük getirileri).
* **Momentum**: 12 aylık getiri, son ay hariç.

Sütun puanları evren içi yüzdelik sıralardır ve eşit ağırlıkla birleştirilir.

Hibrit mod için iki ek (varsayılanda kapalı) parça vardır:

* **Teknik sütun** (``w_technical``): nakde göre fiyatın 200 günlük ortalamaya uzaklığı,
  50/200 günlük ortalama oranı ve 52 haftalık zirveye yakınlık.
* **Yükseliş eğilimi** (``uptrend``): nakde göre fiyat 200 günlük ortalamasının üstünde mi;
  portföy tarafındaki teknik onay kapısı bu sütunu kullanır.

"Temel" katman değer + kârlılık, "teknik" katman momentum + düşük risk (+ teknik sütun)
sütunlarıdır; ``fundamental`` ve ``tech`` sütunları bu iki katmanın ortalama puanıdır.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import SignalConfig, UniverseConfig
from .data.dataset import Dataset
from .rules import CONTINUOUS_METHOD, MAIN_MARKETS
from .technical import excess_price, trend_measures

PILLARS = ("value", "quality", "lowrisk", "momentum", "technical")
FUNDAMENTAL_PILLARS = ("value", "quality")
TECHNICAL_PILLARS = ("lowrisk", "momentum", "technical")
SCORE_COLUMNS = [*PILLARS, "fundamental", "tech", "uptrend", "score", "rank"]


@dataclass
class Features:
    """Tüm tarihler için özellik tabloları (``tarih × sembol``)."""

    vol: pd.DataFrame
    beta: pd.DataFrame
    lottery: pd.DataFrame
    momentum: pd.DataFrame
    book_to_market: pd.DataFrame
    earnings_yield: pd.DataFrame
    roe: pd.DataFrame
    history: pd.DataFrame
    traded_60: pd.DataFrame
    adv_20: pd.DataFrame
    #: Nakde göre fiyatın uzun ortalamaya uzaklığı, kısa/uzun ortalama oranı − 1, zirveye oran.
    trend: pd.DataFrame
    ma_cross: pd.DataFrame
    high_52w: pd.DataFrame


def _rolling_top_mean(values: np.ndarray, window: int, top_n: int, min_obs: int) -> np.ndarray:
    """Her sütunda son ``window`` gözlemin en büyük ``top_n`` tanesinin ortalaması."""
    n_rows, n_cols = values.shape
    out = np.full((n_rows, n_cols), np.nan)
    if n_rows < window:
        return out
    view = np.lib.stride_tricks.sliding_window_view(values, window, axis=0)  # (T-w+1, N, w)
    valid = np.isfinite(view)
    count = valid.sum(axis=2)
    filled = np.where(valid, view, -np.inf)
    top = np.partition(filled, window - top_n, axis=2)[:, :, window - top_n:]
    finite = np.isfinite(top)
    n_top = finite.sum(axis=2)
    total = np.where(finite, top, 0.0).sum(axis=2)
    mean = np.divide(total, n_top, out=np.full(total.shape, np.nan), where=n_top > 0)
    mean[count < max(min_obs, top_n)] = np.nan
    out[window - 1:] = mean
    return out


def compute_features(ds: Dataset, cfg: SignalConfig, symbols: list[str] | None = None) -> Features:
    cols = list(symbols) if symbols is not None else list(ds.symbols)
    ret = ds.returns[cols]
    px = ds.adjusted("close")[cols].ffill().where(ds.panel.listed[cols])
    traded = ds.panel.close[cols].notna() & ds.factor[cols].notna()

    min_vol = int(cfg.vol_window * 0.8)
    vol = ret.rolling(cfg.vol_window, min_periods=min_vol).std()

    market = ds.xu100.pct_change()
    m = pd.DataFrame(
        np.where(ret.notna().to_numpy(), market.to_numpy()[:, None], np.nan), index=ret.index, columns=cols
    )
    min_beta = int(cfg.beta_window * 0.8)
    roll = lambda df: df.rolling(cfg.beta_window, min_periods=min_beta).mean()  # noqa: E731
    e_r, e_m, e_rm, e_mm = roll(ret.where(m.notna())), roll(m), roll(ret * m), roll(m * m)
    var_m = e_mm - e_m * e_m
    beta = (e_rm - e_r * e_m) / var_m.where(var_m > 1e-12)

    lottery = pd.DataFrame(
        _rolling_top_mean(ret.to_numpy(dtype=float), cfg.max_window, cfg.max_top_n, int(cfg.max_window * 0.7)),
        index=ret.index, columns=cols,
    )
    momentum = px.shift(cfg.mom_skip) / px.shift(cfg.mom_lookback) - 1.0

    trend, ma_cross, high_52w = trend_measures(excess_price(ds, px), cfg.trend_window, cfg.trend_short_window)

    mcap = ds.mcap[cols].where(ds.mcap[cols] > 0)
    equity, ni = ds.equity[cols], ds.ni_annual[cols]
    return Features(
        vol=vol, beta=beta, lottery=lottery, momentum=momentum,
        book_to_market=equity / mcap,
        earnings_yield=ni / mcap,
        roe=ni / equity.where(equity > 0),
        history=traded.cumsum(),
        traded_60=traded.rolling(60, min_periods=1).sum(),
        adv_20=ds.panel.value[cols].rolling(20, min_periods=10).median(),
        trend=trend, ma_cross=ma_cross, high_52w=high_52w,
    )


def universe_mask(ds: Dataset, feats: Features, cfg: UniverseConfig) -> pd.DataFrame:
    """Her gün alınabilir hisseler: resmî BIST 100 üyesi, sürekli işlemde, tedbirsiz, yeterli geçmişli."""
    cols = list(feats.vol.columns)
    p = ds.panel
    mask = (
        (p.method[cols] == CONTINUOUS_METHOD)
        & ~p.gross[cols]
        & ~p.suspended[cols]
        & p.close[cols].notna()
        & ds.factor[cols].notna()
        & (feats.history >= cfg.min_history)
        & (feats.traded_60 >= cfg.min_traded_days_60)
    )
    if cfg.require_bist100:
        # Endeks üyeliği yeterlidir; pazar kodu aranmaz (2020'ye kadar GYO'lar ve yatırım
        # ortaklıkları BIST 100 üyesi olsalar da bültende ayrı bir pazar koduyla yer alır).
        mask &= p.bist100[cols]
    else:
        mask &= p.market[cols].isin(MAIN_MARKETS)
    return mask


def _pct_rank(values: pd.Series) -> pd.Series:
    """[0, 1] aralığında yüzdelik sıra (büyük değer → 1). NaN, NaN kalır."""
    valid = values.dropna()
    if len(valid) <= 1:
        return pd.Series(np.where(values.notna(), 0.5, np.nan), index=values.index)
    ranks = valid.rank(method="average")
    return ((ranks - 1.0) / (len(valid) - 1.0)).reindex(values.index)


def _grouped_rank(values: pd.Series, groups: pd.Series, min_size: int) -> pd.Series:
    out = pd.Series(np.nan, index=values.index)
    small: list = []
    for _, idx in groups.groupby(groups).groups.items():
        if values.loc[idx].notna().sum() >= min_size:
            out.loc[idx] = _pct_rank(values.loc[idx])
        else:
            small.extend(idx)
    if small:
        # Küçük grup: tüm evrene göre sırala.
        out.loc[small] = _pct_rank(values).loc[small]
    return out


def score_date(
    ds: Dataset, feats: Features, universe: pd.Series, date: pd.Timestamp, cfg: SignalConfig
) -> pd.DataFrame:
    """``date`` günü evrendeki hisselerin sütun puanları, bileşik puanı ve sırası.

    Dönen tablo sembol dizinlidir ve bileşik puana göre (en iyi önce) sıralıdır;
    ``rank`` 1'den başlar. Yeterli verisi olmayan hisseler tabloda yer almaz.
    """
    members = list(universe.index[universe.to_numpy(dtype=bool)])
    if not members:
        return pd.DataFrame(columns=SCORE_COLUMNS)
    row = lambda df: df.loc[date, members].astype(float)  # noqa: E731
    group = ds.is_financial.reindex(members).fillna(False)

    def frank(values: pd.Series) -> pd.Series:
        if cfg.group_neutral:
            return _grouped_rank(values, group, cfg.min_group_size)
        return _pct_rank(values)

    value = pd.concat([frank(row(feats.book_to_market)), frank(row(feats.earnings_yield))], axis=1).mean(axis=1)
    quality = frank(row(feats.roe))
    lowrisk = pd.concat(
        [_pct_rank(-row(feats.vol)), _pct_rank(-row(feats.beta)), _pct_rank(-row(feats.lottery))], axis=1
    ).mean(axis=1)
    momentum = _pct_rank(row(feats.momentum))
    trend = row(feats.trend)
    technical = pd.concat(
        [_pct_rank(trend), _pct_rank(row(feats.ma_cross)), _pct_rank(row(feats.high_52w))], axis=1
    ).mean(axis=1)

    table = pd.DataFrame(
        {"value": value, "quality": quality, "lowrisk": lowrisk, "momentum": momentum, "technical": technical}
    )
    weights = pd.Series(
        {"value": cfg.w_value, "quality": cfg.w_quality, "lowrisk": cfg.w_lowrisk, "momentum": cfg.w_momentum,
         "technical": cfg.w_technical}
    )
    active = weights[weights > 0]
    if active.empty:
        raise ValueError("en az bir sinyal sütununun ağırlığı pozitif olmalı")
    part = table[active.index]
    weighted = part.mul(active, axis=1)
    available = part.notna().mul(active, axis=1).sum(axis=1)
    score = weighted.sum(axis=1, min_count=1) / available.where(available > 0)
    enough = part.notna().sum(axis=1) >= min(cfg.min_pillars, len(active))
    table["fundamental"] = table[list(FUNDAMENTAL_PILLARS)].mean(axis=1)
    table["tech"] = table[[c for c in TECHNICAL_PILLARS if c != "technical" or cfg.w_technical > 0]].mean(axis=1)
    # Eğilimi hesaplanamayan hisse (yetersiz geçmiş) yükselişte sayılmaz.
    table["uptrend"] = (trend > 0) & trend.notna()
    table["score"] = score.where(enough)
    table = table.dropna(subset=["score"])
    # Belirleyici sıralama: puan (azalan), eşitlikte sembol adı.
    table = table.assign(_sym=table.index).sort_values(["score", "_sym"], ascending=[False, True]).drop(columns="_sym")
    table["rank"] = np.arange(1, len(table) + 1)
    return table[SCORE_COLUMNS]
