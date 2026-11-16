"""Araştırma ve canlı çalışma için tek veri nesnesi: ``Dataset``.

Bülten paneli (ham fiyat + bayraklar) ile İş Yatırım'dan gelen düzeltme katsayılarını,
temettü stopajını, piyasa değerini ve mali tablo büyüklüklerini aynı ``tarih × sembol``
ızgarasında birleştirir. Buradaki her tablo "o gün kapanıştan sonra bilinen" değeri taşır;
mali tablolar yasal bildirim süresinden uzun, sabit bir gecikmeyle devreye girer.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..rules import price_limit_series
from .adjust import align_factor, limit_violations, repair_missing_steps, stepwise_factor
from .isystore import IsyStore
from .panel import MarketPanel

log = logging.getLogger(__name__)

#: Bir mali tablonun kullanılabilir sayıldığı gecikme (dönem sonundan itibaren gün).
#: Yasal süreler: ara dönem 30-50 gün, yıllık 60-70 gün; enflasyon muhasebesine geçişte
#: (2023 yıllık, 2024 ara dönemler) SPK ek süre verdi. Güvenli tarafta kalmak için
#: yasal sürelerin epey üstünde tutulur; değer sinyalleri yavaş değiştiğinden maliyeti azdır.
INTERIM_LAG_DAYS = 75
ANNUAL_LAG_DAYS = 145
#: Son mali tablo bu kadar günden eskiyse temel veriler "yok" sayılır.
STALE_DAYS = 460
#: Endeks / kur serisinde boşluk en fazla bu kadar seans taşınır (ör. 2023 deprem kapanışı 5 seans).
INDEX_MAX_GAP = 7
#: İş Yatırım ile bülten kapanışı arasında kabul edilen uyuşmazlık oranı.
MAX_CLOSE_MISMATCH = 0.02


@dataclass
class Dataset:
    panel: MarketPanel
    factor: pd.DataFrame  # düzeltme katsayısı (NaN: veri yok)
    div_tax: pd.DataFrame  # hak kullanım gününde stopaj kaynaklı getiri kaybı (>= 0)
    mcap: pd.DataFrame  # piyasa değeri, TL
    equity: pd.DataFrame  # ana ortaklığa ait özkaynak (gecikmeli)
    ni_ttm: pd.DataFrame  # son 12 ay net kâr (gecikmeli)
    equity_prev: pd.DataFrame  # bir yıl önceki özkaynak (gecikmeli)
    is_financial: pd.Series  # sembol -> banka/sigorta mali tablo grubu mu
    xu100: pd.Series
    usdtry: pd.Series
    rf: pd.Series  # yıllık basit oran (ondalık), günlük
    quality: pd.DataFrame = field(default_factory=pd.DataFrame)  # sembol bazında veri kalite raporu

    # -- türetilmiş seriler -------------------------------------------------------
    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.panel.dates

    @property
    def symbols(self) -> pd.Index:
        return self.panel.symbols

    def adjusted(self, name: str) -> pd.DataFrame:
        """Düzeltilmiş fiyat tablosu (``open``, ``high``, ``low``, ``close``, ``vwap``)."""
        return getattr(self.panel, name) * self.factor

    @property
    def returns(self) -> pd.DataFrame:
        """Günlük toplam getiri (brüt temettü dahil). İşlem olmayan gün 0; veri yoksa NaN.

        Kapanış boş günlerde son kapanış taşınır; böylece işlem görmeyen (durdurulan) bir
        payın getirisi yeniden işlem gördüğü gün tek seferde yansır.
        """
        px = self.adjusted("close")
        filled = px.ffill()
        ret = filled / filled.shift(1) - 1.0
        return ret.where(self.panel.listed)

    def as_of(self, date: pd.Timestamp) -> "Dataset":
        """``date`` (dahil) sonrasını atarak kesilmiş kopya: ileriye bakma testleri için."""
        def cut(obj):
            return obj.loc[:date]

        p = self.panel
        panel = MarketPanel(
            **{
                name: cut(getattr(p, name))
                for name in (
                    "open", "high", "low", "close", "vwap", "prev_close", "value", "volume",
                    "bist100", "bist30", "gross", "suspended", "short_ok",
                    "market", "method", "corp_action", "listed",
                )
            },
            names=p.names,
            renames=p.renames,
        )
        return Dataset(
            panel=panel,
            factor=cut(self.factor), div_tax=cut(self.div_tax), mcap=cut(self.mcap),
            equity=cut(self.equity), ni_ttm=cut(self.ni_ttm), equity_prev=cut(self.equity_prev),
            is_financial=self.is_financial, xu100=cut(self.xu100), usdtry=cut(self.usdtry),
            rf=cut(self.rf), quality=self.quality,
        )


# ------------------------------------------------------------------------------ yardımcılar
def _period_end(year: int, month: int) -> pd.Timestamp:
    return pd.Timestamp(dt.date(year, month, 31 if month in (3, 12) else 30))


def point_in_time_fundamentals(fin: pd.DataFrame) -> pd.DataFrame:
    """Dönemsel mali tablo satırlarını "kullanılabilirlik tarihi" dizinli tabloya çevirir.

    Girdi: ``year, period, equity, net_income`` (net kâr yıl içi kümülatif).
    Çıktı dizini ``available`` (dönem sonu + gecikme); sütunlar ``period_end``, ``equity``,
    ``ni_ttm`` (son 12 ay), ``equity_prev`` (bir yıl önceki aynı dönem özkaynağı).
    """
    cols = ["period_end", "equity", "ni_ttm", "equity_prev"]
    if fin is None or fin.empty:
        return pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], name="available"))
    f = fin.drop_duplicates(["year", "period"], keep="first").set_index(["year", "period"]).sort_index()
    rows = []
    for (year, month), rec in f.iterrows():
        equity = rec["equity"]
        if not np.isfinite(equity):
            continue
        ni = rec["net_income"]
        if month == 12:
            ni_ttm = ni
        else:
            prev_full = f["net_income"].get((year - 1, 12), np.nan)
            prev_same = f["net_income"].get((year - 1, month), np.nan)
            ni_ttm = ni + prev_full - prev_same
        end = _period_end(int(year), int(month))
        lag = ANNUAL_LAG_DAYS if month == 12 else INTERIM_LAG_DAYS
        rows.append(
            {
                "available": end + pd.Timedelta(days=lag),
                "period_end": end,
                "equity": equity,
                "ni_ttm": ni_ttm,
                "equity_prev": f["equity"].get((year - 1, month), np.nan),
            }
        )
    if not rows:
        return pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], name="available"))
    out = pd.DataFrame(rows).sort_values(["available", "period_end"])
    # Aynı gün iki tablo kullanılabilir olursa daha yeni dönem geçerlidir.
    out = out.drop_duplicates("available", keep="last").set_index("available")
    # Daha eski bir dönem, daha yenisinden sonra "kullanılabilir" olamaz.
    out = out[out["period_end"] >= out["period_end"].cummax()]
    return out[cols]


def _daily_from_steps(steps: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Basamak tablosunu günlük dizine taşır; bayat veriyi NaN yapar."""
    if steps.empty:
        return pd.DataFrame(np.nan, index=dates, columns=["equity", "ni_ttm", "equity_prev"])
    daily = steps.reindex(steps.index.union(dates)).ffill().reindex(dates)
    stale = (dates - pd.DatetimeIndex(daily["period_end"])).days > STALE_DAYS
    out = daily[["equity", "ni_ttm", "equity_prev"]].astype(float)
    out[np.asarray(stale) | daily["period_end"].isna().to_numpy()] = np.nan
    return out


def _symbol_factor(panel: MarketPanel, sym: str, hist: pd.DataFrame | None) -> tuple[pd.Series, dict]:
    """Bir sembolün bülten tarihlerine hizalı katsayısı ve kalite ölçüleri."""
    dates = panel.dates
    listed = panel.listed[sym]
    info = {
        "has_history": False, "overlap": 0, "close_mismatch": np.nan, "steps": 0, "factor_ok": False,
        "repaired": 0, "violations": 0,
    }
    if hist is None or hist.empty:
        return pd.Series(np.nan, index=dates), info
    h = hist.drop_duplicates("date", keep="last").set_index("date").sort_index()
    info["has_history"] = True
    close = panel.close[sym]
    both = pd.concat([close, h["raw_close"]], axis=1, keys=["b", "i"]).dropna()
    info["overlap"] = len(both)
    if len(both):
        tol = np.maximum(0.006, both["b"].abs() * 2e-4)
        info["close_mismatch"] = float(((both["b"] - both["i"]).abs() > tol).mean())
    factor = stepwise_factor(h["raw_close"], h["adj_close"])
    info["steps"] = int((factor.diff().abs() > 1e-12).sum())
    ok = len(both) >= 1 and info["close_mismatch"] <= MAX_CLOSE_MISMATCH
    info["factor_ok"] = bool(ok)
    if not ok:
        return pd.Series(np.nan, index=dates), info
    aligned = align_factor(factor, dates).where(listed)
    limit = price_limit_series(dates)
    aligned, repairs = repair_missing_steps(
        aligned, panel.prev_close[sym], panel.open[sym], panel.high[sym], panel.low[sym], close,
        panel.corp_action[sym] != "", limit,
    )
    info["repaired"] = len(repairs)
    info["repaired_official"] = sum(1 for r in repairs if r["how"] == "official")
    info["violations"] = int(len(limit_violations(aligned, close, limit)))
    return aligned, info


def build_dataset(
    panel: MarketPanel,
    isy: IsyStore,
    rf: pd.Series,
    symbols: list[str] | None = None,
    xu100: pd.Series | None = None,
) -> Dataset:
    """Panel + İş Yatırım önbelleğinden ``Dataset`` kurar (ağ erişimi yapmaz).

    ``xu100`` verilirse BIST 100 serisi olarak o kullanılır (günlük çalışmada endeks ayrıca
    indirilir); verilmezse hisse geçmiş dosyalarındaki endeks sütunundan türetilir. Endeks
    en fazla ``INDEX_MAX_GAP`` seans taşınır; daha eski veri "yok" sayılır ki bayat endeksle
    karar verilmesin.
    """
    dates = panel.dates
    all_syms = list(panel.symbols)
    use = [s for s in (symbols or all_syms) if s in panel.close.columns]

    factor = pd.DataFrame(np.nan, index=dates, columns=all_syms)
    div_tax = pd.DataFrame(0.0, index=dates, columns=all_syms)
    mcap = pd.DataFrame(np.nan, index=dates, columns=all_syms)
    equity = pd.DataFrame(np.nan, index=dates, columns=all_syms)
    ni_ttm = pd.DataFrame(np.nan, index=dates, columns=all_syms)
    equity_prev = pd.DataFrame(np.nan, index=dates, columns=all_syms)
    is_fin = pd.Series(False, index=all_syms)
    xu_parts, usd_parts, quality = [], [], {}

    for sym in use:
        hist = isy.load("history", sym)
        f, info = _symbol_factor(panel, sym, hist)
        factor[sym] = f
        if hist is not None and not hist.empty:
            h = hist.drop_duplicates("date", keep="last").set_index("date").sort_index()
            if info["factor_ok"]:
                # Pay adedi = piyasa değeri / ham kapanış; kaynak tarihleri arasında ve
                # sonrasında pay adedi taşınır, güncel bülten kapanışıyla çarpılır.
                shares = (h["mcap"] / h["raw_close"]).where((h["mcap"] > 0) & (h["raw_close"] > 0))
                shares = shares.reindex(shares.index.union(dates)).ffill().reindex(dates)
                mcap[sym] = (shares * panel.close[sym].ffill()).where(panel.listed[sym])
                # Kaynağın son gününden sonra bültende özsermaye olayı varsa katsayı ve pay
                # adedi bayattır: yeniden indirilene kadar bu pay için veri "yok" sayılır.
                after = dates > h.index.max()
                if (panel.corp_action[sym][after] != "").any():
                    first_bad = dates[after][(panel.corp_action[sym][after] != "").to_numpy()][0]
                    factor.loc[factor.index >= first_bad, sym] = np.nan
                    mcap.loc[mcap.index >= first_bad, sym] = np.nan
                    info["needs_refresh"] = True
            if len(xu_parts) < 25 and len(h) > 0.9 * len(dates):
                xu_parts.append(h["xu100"])
                usd_parts.append(h["usdtry"])

        actions = isy.load("actions", sym)
        if actions is not None and not actions.empty and info["factor_ok"]:
            a = actions[(actions["price_factor"] > 0) & (actions["div_gross_pct"] > actions["div_net_pct"])]
            a = a[a["date"].isin(dates)]
            prev = panel.close[sym].ffill().shift(1)
            for _, ev in a.iterrows():
                base = prev.get(ev["date"], np.nan)
                if np.isfinite(base) and base > 0:
                    # Oranlar 1 TL nominal üzerinden yüzdedir: stopaj (TL/pay) = fark / 100.
                    div_tax.at[ev["date"], sym] += (ev["div_gross_pct"] - ev["div_net_pct"]) / 100.0 / base

        fin = isy.load("financials", sym)
        if fin is not None and not fin.empty:
            is_fin[sym] = bool(fin["group"].isin(["UFRS", "UFRS_K"]).mean() > 0.5)
            daily = _daily_from_steps(point_in_time_fundamentals(fin), dates)
            equity[sym] = daily["equity"].where(panel.listed[sym])
            ni_ttm[sym] = daily["ni_ttm"].where(panel.listed[sym])
            equity_prev[sym] = daily["equity_prev"].where(panel.listed[sym])
            info["fin_periods"] = len(fin)
        else:
            info["fin_periods"] = 0
        quality[sym] = info

    def on_dates(s: pd.Series) -> pd.Series:
        s = s.where(s > 0).dropna()
        s = s[~s.index.duplicated(keep="last")].sort_index()
        return s.reindex(s.index.union(dates)).ffill(limit=INDEX_MAX_GAP).reindex(dates)

    def median_series(parts: list[pd.Series]) -> pd.Series:
        if not parts:
            return pd.Series(np.nan, index=dates)
        return on_dates(pd.concat(parts, axis=1).median(axis=1))

    index_series = on_dates(xu100) if xu100 is not None and len(xu100) else median_series(xu_parts)

    rf_daily = rf.reindex(rf.index.union(dates)).ffill().reindex(dates) if len(rf) else pd.Series(np.nan, index=dates)
    return Dataset(
        panel=panel, factor=factor, div_tax=div_tax.clip(lower=0.0, upper=0.2), mcap=mcap,
        equity=equity, ni_ttm=ni_ttm, equity_prev=equity_prev, is_financial=is_fin,
        xu100=index_series, usdtry=median_series(usd_parts), rf=rf_daily,
        quality=pd.DataFrame.from_dict(quality, orient="index"),
    )
