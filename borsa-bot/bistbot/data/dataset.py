"""Araştırma ve canlı çalışma için tek veri nesnesi: ``Dataset``.

Bülten paneli (ham fiyat + bayraklar) ile İş Yatırım'dan gelen düzeltme katsayılarını,
temettü stopajını, piyasa değerini ve mali tablo büyüklüklerini aynı ``tarih × sembol``
ızgarasında birleştirir. Buradaki her tablo "o gün kapanıştan sonra bilinen" değeri taşır;
mali tablolar yasal bildirim süresinden uzun, sabit bir gecikmeyle devreye girer.
"""
from __future__ import annotations

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
#: İş Yatırım'ın yıl sonu (12 aylık) satırları, ertesi yılın raporu yayımlanınca o raporun
#: karşılaştırma sütunuyla değiştirilir. Enflasyon muhasebesinde (TMS 29, 2022 yıl sonundan
#: itibaren) bu sütun sonraki yılın satın alma gücüne göre yeniden düzenlenmiştir; yani o
#: tarihte bilinmeyen rakamlardır. Bu yıldan itibaren yıl sonu satırları kullanılmaz; ara
#: dönem satırları ilk yayımlandıkları hâliyle kalır.
RESTATED_ANNUAL_FROM = 2022
#: Hesap dönemi takvim yılı olmayan şirketler: hesap yılının başladığı ay. Kaynak, dönemi
#: "hesap yılının başladığı takvim yılı + hesap yılı içindeki ay" olarak etiketler.
FISCAL_YEAR_START_MONTH = {"BJKAS": 6, "FENER": 6, "GSRAY": 6, "TSPOR": 6, "MAVI": 2}
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
    ni_annual: pd.DataFrame  # son rapordaki yıl içi net kârın yıllıklandırılmışı (gecikmeli)
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
            equity=cut(self.equity), ni_annual=cut(self.ni_annual),
            is_financial=self.is_financial, xu100=cut(self.xu100), usdtry=cut(self.usdtry),
            rf=cut(self.rf), quality=self.quality,
        )


# ------------------------------------------------------------------------------ yardımcılar
def _period_end(year: int, month: int, fy_start_month: int = 1) -> pd.Timestamp:
    """Dönem sonu: hesap yılının başından ``month`` ay sonra biten ayın son günü."""
    start = pd.Timestamp(year=int(year), month=int(fy_start_month), day=1)
    return start + pd.DateOffset(months=int(month)) - pd.Timedelta(days=1)


def point_in_time_fundamentals(fin: pd.DataFrame, fy_start_month: int = 1) -> pd.DataFrame:
    """Dönemsel mali tablo satırlarını "kullanılabilirlik tarihi" dizinli tabloya çevirir.

    Girdi: ``year, period, group, equity, net_income`` (net kâr yıl içi kümülatif).
    Çıktı dizini ``available`` (dönem sonu + gecikme); sütunlar ``period_end``, ``equity``,
    ``ni_annual``.

    Her satır yalnızca kendi raporundaki rakamları kullanır: net kâr, aynı raporun yıl içi
    kümülatif kârının 12 aya oranlanmasıdır. Farklı raporların rakamları toplanıp çıkarılmaz;
    çünkü enflasyon muhasebesinde her rapor kendi tarihinin satın alma gücüyle yazılır ve
    kaynak, eski yıl sonu rakamlarını sonradan yeniden düzenlenmiş hâlleriyle değiştirir.
    Yeniden düzenlenmiş yıl sonu satırları (``RESTATED_ANNUAL_FROM`` ve sonrası) atlanır.
    """
    cols = ["period_end", "equity", "ni_annual"]
    empty = pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], name="available"))
    if fin is None or fin.empty:
        return empty
    rows = []
    for rec in fin.drop_duplicates(["year", "period"], keep="first").itertuples(index=False):
        year, month = int(rec.year), int(rec.period)
        if month not in (3, 6, 9, 12) or not np.isfinite(rec.equity):
            continue
        if month == 12 and year >= RESTATED_ANNUAL_FROM:
            continue
        end = _period_end(year, month, fy_start_month)
        lag = ANNUAL_LAG_DAYS if month == 12 else INTERIM_LAG_DAYS
        ni = rec.net_income
        rows.append(
            {
                "available": end + pd.Timedelta(days=lag),
                "period_end": end,
                "equity": float(rec.equity),
                "ni_annual": float(ni) * 12.0 / month if np.isfinite(ni) else np.nan,
            }
        )
    if not rows:
        return empty
    out = pd.DataFrame(rows).sort_values(["available", "period_end"])
    # Aynı gün iki tablo kullanılabilir olursa daha yeni dönem geçerlidir.
    out = out.drop_duplicates("available", keep="last").set_index("available")
    # Daha eski bir dönem, daha yenisinden sonra "kullanılabilir" olamaz.
    out = out[out["period_end"] >= out["period_end"].cummax()]
    return out[cols]


def _daily_from_steps(steps: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Her güne, o gün kullanılabilir olan EN SON tablonun satırını bütün olarak taşır.

    Satır bütün taşınır: yeni tablonun eksik bir kalemi eski tablodan doldurulmaz. Dönem
    sonu ``STALE_DAYS`` günden eskiyse o gün için temel veri yok sayılır.
    """
    out = pd.DataFrame(np.nan, index=dates, columns=["equity", "ni_annual"])
    if steps.empty:
        return out
    pos = np.searchsorted(steps.index.values, dates.values, side="right") - 1
    valid = pos >= 0
    row = np.clip(pos, 0, None)
    period_end = steps["period_end"].to_numpy()[row]
    fresh = valid & ((dates.values - period_end) <= np.timedelta64(STALE_DAYS, "D"))
    for col in ("equity", "ni_annual"):
        out[col] = np.where(fresh, steps[col].to_numpy(dtype=float)[row], np.nan)
    return out


def _fix_early_share_switch(shares: pd.Series, factor: pd.Series) -> pd.Series:
    """Kaynak, bedelsiz/bölünmelerde pay adedini bazen hak kullanım gününden bir seans önce
    değiştirir (fiyat hâlâ eski): o gün piyasa değeri katlanmış görünür. Pay adedi, fiyatın
    değiştiği güne (katsayı basamağına) kadar eski değerinde tutulur.
    """
    step = factor.shift(1) / factor
    out = shares.copy()
    values = shares.to_numpy(dtype=float)
    for pos in np.flatnonzero(((step - 1.0).abs() > 0.02).to_numpy()):
        if pos < 2:
            continue
        before, cum_day, ex_day = values[pos - 2], values[pos - 1], values[pos]
        if not all(np.isfinite(x) and x > 0 for x in (before, cum_day, ex_day)):
            continue
        if abs(cum_day / ex_day - 1.0) < 0.01 and abs(before / ex_day - 1.0) > 0.02:
            out.iloc[pos - 1] = before
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
    ni_annual = pd.DataFrame(np.nan, index=dates, columns=all_syms)
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
                shares = _fix_early_share_switch(shares, f)
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
            steps = point_in_time_fundamentals(fin, FISCAL_YEAR_START_MONTH.get(sym, 1))
            daily = _daily_from_steps(steps, dates)
            equity[sym] = daily["equity"].where(panel.listed[sym])
            ni_annual[sym] = daily["ni_annual"].where(panel.listed[sym])
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
        equity=equity, ni_annual=ni_annual, is_financial=is_fin,
        xu100=index_series, usdtry=median_series(usd_parts), rf=rf_daily,
        quality=pd.DataFrame.from_dict(quality, orient="index"),
    )
