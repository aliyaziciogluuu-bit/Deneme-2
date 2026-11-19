"""Halka arz keşfi: yeni halka arz olan paylarda, piyasadan sonradan alan biri için
tekrarlanan ve kazandıran bir kalıp var mı?

ÖN KAYIT (18.11.2026) — bu metin, halka arz sonrası getirilere HİÇ bakılmadan önce yazıldı
----------------------------------------------------------------------------------------
Aşağıdaki tanımlar, kural ailesi, yöntem ve geçme ölçütleri sonuçlar görülmeden sabitlendi.
Sonradan yapılan her değişiklik "keşif sonrası" sayılır ve raporda öyle etiketlenir.
Tek serbestlik: halka arzların *saptanması* (hangi yeni kod gerçek bir halka arzdır) ilk işlem
günü verisine ve bilinen yıllık halka arz sayılarına bakılarak ayarlanabilir; sonraki
getirilere bakılarak ayarlanamaz.

Veri: Borsa İstanbul resmî Pay Piyasası günlük bültenleri (30.11.2015'ten beri). Günlük getiri
``kapanış / önceki kapanış`` ile hesaplanır; bültendeki "önceki kapanış" özsermaye olaylarına
göre düzeltilmiş baz fiyat olduğundan bedelli, bedelsiz ve temettü getiriyi bozmaz.

Tanımlar
* Halka arz: 01.06.2016'dan sonra bültende ilk kez görünen, kod değişikliği / birleşme /
  pazar geçişi olmayan, ana pazarlarda işlem gören pay.
* Kilitli gün: bütün işlemlerin tavan fiyatından geçtiği gün (en düşük = en yüksek = tavan).
  O gün dışarıdan biri gerçekçi olarak alım yapamaz.
* Açılma günü (T): payın tavanın altında işlem gördüğü ilk gün; yani dışarıdan birinin
  alabileceği ilk gün. S: T'den önceki kilitli gün sayısı (tavan serisinin uzunluğu).
* Giriş: sinyal gününü izleyen seansın açılış fiyatı (karar kapanıştan sonra verilir).
  Giriş günü pay tavanda kilitliyse işlem yapılmamış sayılır.
* Çıkış: girişten H seans sonra kapanış fiyatı; o gün pay tabanda kilitliyse satılabildiği
  ilk seansın kapanışı.
* Ölçü: anormal getiri = payın getirisi − aynı günlerde ana pazarlardaki bütün payların eşit
  ağırlıklı getirisi. "Net" rakamlar komisyon (binde 2 + BSMV) ve kaymayı (binde 1) iki
  yönde düşer.

Kural ailesi: 6 sinyal × 3 elde tutma süresi (5, 20, 60 seans) = 18 deneme
  A  Her halka arz, açılma günü T'de.
  B  Tavan serisi yapmış (S ≥ 1) ve T günü önceki kapanışının üstünde ya da aynı kapatmış.
  C  Tavan serisi yapmış (S ≥ 1) ve T günü önceki kapanışının altında kapatmış.
  D  Hiç tavan serisi yapmamış (S = 0).
  E  Uzun tavan serisi yapmış (S ≥ 4).
  F  Dipten alım: T'den sonraki 60 seans içinde kapanışın, işlem görmeye başladığından beri
     görülen en yüksek kapanışın %30 altına ilk kez indiği gün.

Yöntem
1. Keşif örneklemi: ilk işlem günü 01.01.2024'ten önce olan halka arzlar. Doğrulama
   örneklemi: 01.01.2024 ve sonrası. Doğrulama örneklemine 3. adıma kadar bakılmaz.
2. Keşif örnekleminde 18 denemenin her biri için ortalama anormal getiri ve giriş ayına göre
   kümelenmiş t-istatistiği hesaplanır. Aday olmak için: en az 30 işlem, kümelenmiş t ≥ 3,0
   (18 deneme için düzeltilmiş eşik) ve masraflar düşüldükten sonra artı ortalama getiri.
   Aday çıkmazsa sonuç "keşif yok"tur; doğrulama örneklemi yalnızca bilgi için raporlanır.
3. Aday varsa t-istatistiği en yüksek olan tek kural seçilir ve doğrulama örnekleminde BİR KEZ
   sınanır. Geçme ölçütleri: ortalama anormal getiri artı ve kümelenmiş t ≥ 2,0; net ortalama
   getiri aynı günlerdeki gecelik faizden yüksek; medyan anormal getiri artı (sonuç birkaç
   uç değere dayanmıyor).
4. Yalnızca geçen kural bot uyarısına dönüştürülür. Geri kalan her şey "keşif amaçlı" diye
   raporlanır ve işlem kuralı olarak sunulmaz.

SONUÇ (18.11.2026, ön kayıttan sonra eklendi)
---------------------------------------------
261 halka arz (keşif 173, doğrulama 88). Keşif örnekleminde hiçbir kural aday eşiğini geçemedi
(en yüksek kümelenmiş t: B/5 için 2,35 ve A/60 için 2,25): sonuç "keşif yok". Doğrulama
örneklemi kural gereği yalnızca bilgi için incelendi; orada ortanca anormal getiri hemen her
kuralda eksi. Ortalamalar birkaç büyük kazanana dayanıyor (A/60: ortalama anormal getiri %12,2,
en iyi 10 işlem çıkarılınca %0,7).

Ön kayıttan sapmalar ve ek sınamalar:
* Halka arz pazarları ilk gün verisine bakılarak Z, N, K ve G olarak belirlendi (ön kayıtta
  izin verilen tek ayar).
* Duyarlılık: kıyas, işlem görmeye başlayalı 60 seans olmamış paylar dışarıda tutularak
  yeniden hesaplandı (``market_returns(min_sessions=60)``); sonuç değişmedi.
* İlk gün baz fiyat bültende olmadığından, ilk günü tek fiyattan geçen pay tavanda kilitli
  sayılır (tabanda kilitli bir ilk gün ayırt edilemez; çok enderdir).
* DÜZELTME: ön kayıttaki "bültendeki önceki kapanış düzeltilmiş baz fiyattır" varsayımı
  yanlıştı (2017'den beri bu alan hamdır). Getiriler ve tavan/taban baz fiyatı artık İş
  Yatırım düzeltme katsayılarıyla hesaplanıyor (``quotes``); kıyas da özsermaye olayı
  günlerini dışarıda tutuyor. Halka arzdan sonraki ilk 60 seansta özsermaye olayı ender
  olduğundan etkisi küçük kaldı: 20 seanslık 251 işlemin 1'inde, 60 seanslık 248 işlemin
  9'unda getiri 1 puandan fazla değişti; hiçbir kuralın sonucu değişmedi.
"""
from __future__ import annotations

#: İlk işlem günü bu tarihten önce olan kodlar halka arz sayılmaz (veri başlangıcı payı).
FIRST_EVENT_DATE = "2016-06-01"
#: Keşif / doğrulama ayrımı.
HOLDOUT_START = "2024-01-01"
#: Elde tutma süreleri (seans).
HORIZONS = (5, 20, 60)
#: Sinyaller (ön kayıtlı aile).
SIGNALS = ("A", "B", "C", "D", "E", "F")
#: F sinyali: zirveden düşüş eşiği ve T'den sonra aranacak seans sayısı.
DIP_DRAWDOWN = 0.30
DIP_WINDOW = 60
#: Aday ve geçme eşikleri.
MIN_TRADES = 30
DISCOVERY_T = 3.0
HOLDOUT_T = 2.0

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import CostConfig
from .data.panel import MarketPanel
from .rules import MAIN_MARKETS, price_limit

#: Tavan / taban kilidi saptanırken fiyat adımı yuvarlaması için bırakılan pay.
LIMIT_SLACK = 0.01
#: Halka arzların işlem görmeye başladığı pazarlar: Yıldız (Z), Ana (N), Kolektif Yatırım
#: Ürünleri (K, gayrimenkul yatırım ortaklıkları) ve Gelişen İşletmeler (G). Piyasa Öncesi
#: İşlem Platformu (S) ve nitelikli yatırımcı pazarı (T) halka arz değildir. Bu süzgeçle
#: bulunan yıllık sayılar (2018: 9, 2019: 6, 2020: 8, 2021: 52, 2024: 33) bilinen halka arz
#: sayılarıyla örtüşür.
IPO_MARKETS = ("Z", "N", "K", "G")


# ---------------------------------------------------------------------------------------------
# Halka arzların saptanması
# ---------------------------------------------------------------------------------------------
def find_listings(panel: MarketPanel, first: str = FIRST_EVENT_DATE) -> pd.DataFrame:
    """Bültende ilk kez görünen kodlar (kod değişiklikleri panelde zaten birleştirilmiştir).

    Her satır bir yeni kod: ilk gün, o günkü pazar, ilk gün baz fiyatı (halka arz fiyatı;
    bültende yoksa NaN) ve ilk gün fiyatları.
    """
    listed = panel.listed
    first_pos = listed.to_numpy().argmax(axis=0)
    ever = listed.to_numpy().any(axis=0)
    rows = []
    for j, sym in enumerate(panel.symbols):
        i = int(first_pos[j])
        # Panelin ilk gününde zaten işlem gören pay yeni değildir.
        if not ever[j] or i == 0 or panel.dates[i] < pd.Timestamp(first):
            continue
        rows.append({
            "symbol": sym, "name": panel.names.get(sym, ""), "first_day": panel.dates[i], "pos": i,
            "market": panel.market.iat[i, j], "method": panel.method.iat[i, j],
            "base": panel.prev_close.iat[i, j], "open": panel.open.iat[i, j],
            "close": panel.close.iat[i, j], "value": panel.value.iat[i, j],
            "sessions": int(listed.iloc[i:, j].sum()),
        })
    out = pd.DataFrame(rows).sort_values("first_day").reset_index(drop=True)
    return out[out["market"].isin(IPO_MARKETS)].reset_index(drop=True)


# ---------------------------------------------------------------------------------------------
# Olay tablosu: tavan serisi, açılma günü, sinyaller
# ---------------------------------------------------------------------------------------------
@dataclass
class Market:
    """Kıyas: ana pazarlardaki bütün payların eşit ağırlıklı günlük getirisi."""

    close_to_close: pd.Series   # kapanış / önceki kapanış − 1
    open_to_close: pd.Series    # kapanış / açılış − 1 (giriş günü için)


def market_returns(panel: MarketPanel, min_sessions: int = 0) -> Market:
    """Ana pazarların eşit ağırlıklı getirisi (ön kayıtlı kıyas: ``min_sessions=0``).

    ``min_sessions`` verilirse işlem görmeye başlayalı bu kadar seans olmamış paylar kıyasın
    dışında tutulur. Duyarlılık sınaması içindir: tavan serisindeki yeni halka arzların
    alınamayan getirileri kıyası yukarı çeker.
    """
    main = panel.market.isin(MAIN_MARKETS)
    if min_sessions > 0:
        main &= panel.listed.cumsum() > min_sessions
    # Özsermaye olayı günlerinde ham "önceki kapanış" baz fiyat değildir: o günler dışarıda.
    c2c = (panel.close / panel.prev_close - 1.0).where(main & (panel.corp_action == ""))
    o2c = (panel.close / panel.open - 1.0).where(main)
    # Bayraksız kalmış olay ya da veri hatasından gelen uç değerler ortalamayı bozmasın.
    c2c = c2c.where(c2c.abs() < 0.25)
    o2c = o2c.where(o2c.abs() < 0.25)
    return Market(c2c.mean(axis=1).fillna(0.0), o2c.mean(axis=1).fillna(0.0))


def _locked_up(low: float, base: float, limit: float) -> bool:
    return np.isfinite(low) and np.isfinite(base) and low / base - 1.0 >= limit - LIMIT_SLACK


def _locked_down(high: float, base: float, limit: float) -> bool:
    return np.isfinite(high) and np.isfinite(base) and high / base - 1.0 <= -(limit - LIMIT_SLACK)


@dataclass
class Quotes:
    """Bir payın günlük dizileri: ham fiyatlar, düzeltilmiş kapanış ve o günün baz fiyatı.

    Bültendeki "önceki kapanış" hamdır: bedelsiz, bedelli ve temettü günlerinde o günün baz
    fiyatı değildir. ``adj`` (ham kapanış × düzeltme katsayısı, boş günlerde son değer taşınır)
    getiriyi, ``base`` (özsermaye olayına göre düzeltilmiş önceki kapanış) tavan/taban
    kilidini doğru hesaplamak içindir. Katsayı yoksa (``adjusted`` False) ham fiyat kullanılır
    ve özsermaye olayı bayrağı taşıyan günler ``flagged`` ile işaretlenir.
    """

    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    base: np.ndarray
    adj: np.ndarray
    flagged: np.ndarray
    adjusted: bool


def quotes(panel: MarketPanel, sym: str, factor: pd.DataFrame | None = None) -> Quotes:
    cl = panel.close[sym].to_numpy(dtype=float)
    pc = panel.prev_close[sym].to_numpy(dtype=float)
    flagged = (panel.corp_action[sym] != "").to_numpy()
    f = None
    if factor is not None and sym in factor.columns:
        f = factor[sym].reindex(panel.dates).to_numpy(dtype=float)
        if not np.isfinite(f).any():
            f = None
    if f is None:
        adj, base = pd.Series(cl).ffill().to_numpy(), pc
    else:
        f = pd.Series(f).ffill().bfill().to_numpy()
        adj = pd.Series(cl * f).ffill().to_numpy()
        f_prev = np.concatenate([[f[0]], f[:-1]])
        base = pc * f_prev / f
    return Quotes(
        open=panel.open[sym].to_numpy(dtype=float), high=panel.high[sym].to_numpy(dtype=float),
        low=panel.low[sym].to_numpy(dtype=float), close=cl, base=base, adj=adj,
        flagged=flagged, adjusted=f is not None,
    )


def sync_history(isy, panel: MarketPanel, symbols: list[str], today: dt.date, max_age_days: float = 10.0) -> dict:
    """Düzeltme katsayıları için İş Yatırım fiyat geçmişini gerektiği kadar yeniler.

    Yeniden indirilir: dosya yok ya da boş; dosyanın son gününden sonra bültende özsermaye
    olayı bayrağı var (geriye dönük katsayılar değişir); dosya ``max_age_days`` günden eski.
    """
    import time

    now, need = time.time(), []
    for sym in symbols:
        path = isy.path("history", sym)
        hist = isy.load("history", sym) if path.exists() else None
        if hist is None or hist.empty or (now - path.stat().st_mtime) / 86400.0 > max_age_days:
            need.append(sym)
        elif (panel.corp_action[sym][panel.dates > hist["date"].max()] != "").any():
            need.append(sym)
    return isy.sync("history", need, today, force=True, workers=2, progress_every=0)


def load_factors(panel: MarketPanel, isy, symbols: list[str]) -> pd.DataFrame:
    """İş Yatırım geçmişinden düzeltme katsayıları (tarih × sembol); verisi olmayan sütun boş."""
    from .data.dataset import _symbol_factor

    return pd.DataFrame({s: _symbol_factor(panel, s, isy.load("history", s))[0] for s in symbols})


def event_row(panel: MarketPanel, sym: str, pos: int, factor: pd.DataFrame | None = None) -> dict:
    """Bir halka arzın tavan serisi (S), açılma günü (T) ve F sinyali günü."""
    dates = panel.dates
    q = quotes(panel, sym, factor)
    lo, hi, cl = q.low, q.high, q.close
    n = len(dates)
    t = pos
    while t < n:
        if np.isfinite(q.base[t]):
            locked = _locked_up(lo[t], q.base[t], price_limit(dates[t]))
        else:  # baz fiyat yok (ilk gün): tek fiyattan geçen gün kilitli sayılır
            locked = np.isfinite(lo[t]) and lo[t] == hi[t]
        if np.isfinite(lo[t]) and not locked:
            break
        t += 1
    if t >= n:
        return {"T": None}
    up = bool(np.isfinite(q.base[t]) and cl[t] >= q.base[t])
    # F: T'den sonraki DIP_WINDOW seans içinde (düzeltilmiş) zirve kapanışın %30 altına ilk iniş
    peak, dip = np.nanmax(q.adj[pos:t + 1]), None
    for k in range(t + 1, min(n, t + 1 + DIP_WINDOW)):
        if not np.isfinite(cl[k]):
            continue
        if q.adj[k] <= (1.0 - DIP_DRAWDOWN) * peak:
            dip = k
            break
        peak = max(peak, q.adj[k])
    # Katsayı yoksa zirve, özsermaye olayı sonrası ham fiyatla karşılaştırılamaz.
    if dip is not None and not q.adjusted and q.flagged[pos:dip + 1].any():
        dip = None
    return {"T": t, "S": t - pos, "t_up": up, "dip": dip}


def events(panel: MarketPanel, listings: pd.DataFrame, factor: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    for r in listings.itertuples():
        e = event_row(panel, r.symbol, r.pos, factor)
        if e["T"] is None:
            continue
        rows.append({"symbol": r.symbol, "name": r.name, "first_day": r.first_day, "pos": r.pos,
                     "base": r.base, **e})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------
# İşlem ve istatistik
# ---------------------------------------------------------------------------------------------
def trade(panel: MarketPanel, mkt: Market, rf: pd.Series, sym: str, signal: int, horizon: int,
          cost: CostConfig, factor: pd.DataFrame | None = None) -> dict | None:
    """Sinyal gününü izleyen seansın açılışında al, ``horizon`` seans sonra kapanışta sat.

    Dönen sözlük: brüt, piyasa, anormal, net ve nakit getirisi. İşlem yapılamadıysa (giriş günü
    tavanda kilitli / işlem yok), pencere veri sonunu aşıyorsa ya da düzeltme katsayısı olmayan
    bir payda pencereye özsermaye olayı giriyorsa ``None``.
    """
    dates = panel.dates
    n = len(dates)
    e = signal + 1
    if e >= n:
        return None
    q = quotes(panel, sym, factor)
    if not np.isfinite(q.open[e]) or not np.isfinite(q.close[e]):
        return None
    if _locked_up(q.low[e], q.base[e], price_limit(dates[e])):
        return None
    x = e + horizon - 1
    while x < n and (not np.isfinite(q.close[x]) or _locked_down(q.high[x], q.base[x], price_limit(dates[x]))):
        x += 1
    if x >= n:
        return None
    if not q.adjusted and q.flagged[e + 1:x + 1].any():
        return None
    gross = q.close[e] / q.open[e] * q.adj[x] / q.adj[e]
    market = 1.0 + mkt.open_to_close.iat[e]
    for k in range(e + 1, x + 1):
        market *= 1.0 + mkt.close_to_close.iat[k]
    days = (dates[x] - dates[e]).days + 1
    rate = rf.asof(dates[e]) if len(rf) else np.nan
    side = cost.per_side
    return {
        "symbol": sym, "entry": dates[e], "exit": dates[x], "gross": gross - 1.0,
        "market": market - 1.0, "abn": gross - market,
        "net": gross * (1.0 - side) / (1.0 + side) - 1.0,
        "cash": rate * days / 365.0 if np.isfinite(rate) else np.nan,
    }


def signal_days(ev: pd.DataFrame, signal: str) -> pd.DataFrame:
    """Ön kayıtlı sinyale giren olaylar ve sinyal günü (panel konumu)."""
    if signal == "A":
        sub = ev
    elif signal == "B":
        sub = ev[(ev["S"] >= 1) & ev["t_up"]]
    elif signal == "C":
        sub = ev[(ev["S"] >= 1) & ~ev["t_up"]]
    elif signal == "D":
        sub = ev[ev["S"] == 0]
    elif signal == "E":
        sub = ev[ev["S"] >= 4]
    elif signal == "F":
        sub = ev[ev["dip"].notna()]
        return sub.assign(sig=sub["dip"].astype(int))
    else:
        raise ValueError(signal)
    return sub.assign(sig=sub["T"].astype(int))


def clustered_t(x: np.ndarray, groups: np.ndarray) -> float:
    """Ortalamanın küme-sağlam t-istatistiği (kümeler: giriş ayı)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 2:
        return float("nan")
    m = x.mean()
    sums = pd.Series(x - m).groupby(pd.Series(groups).to_numpy()).sum().to_numpy()
    g = len(sums)
    if g < 2:
        return float("nan")
    var = (sums ** 2).sum() / n ** 2 * g / (g - 1)
    return float(m / np.sqrt(var)) if var > 0 else float("nan")


def summarize(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"n": 0}
    month = trades["entry"].dt.to_period("M").astype(str).to_numpy()
    abn = trades["abn"].to_numpy()
    excess = (trades["net"] - trades["cash"]).to_numpy()
    return {
        "n": int(len(trades)), "months": int(len(set(month))),
        "abn_mean": float(abn.mean()), "abn_median": float(np.median(abn)),
        "abn_t": clustered_t(abn, month), "win": float((abn > 0).mean()),
        "gross_mean": float(trades["gross"].mean()), "net_mean": float(trades["net"].mean()),
        "cash_mean": float(trades["cash"].mean()),
        "net_vs_cash": float(np.nanmean(excess)), "net_vs_cash_t": clustered_t(excess[np.isfinite(excess)],
                                                                             month[np.isfinite(excess)]),
    }


def run_family(panel: MarketPanel, mkt: Market, rf: pd.Series, ev: pd.DataFrame,
               cost: CostConfig | None = None, factor: pd.DataFrame | None = None,
               ) -> tuple[pd.DataFrame, dict[tuple[str, int], pd.DataFrame]]:
    """Verilen olaylar için 18 denemenin özet tablosu ve işlem listeleri."""
    cost = cost or CostConfig()
    rows, book = [], {}
    for sig in SIGNALS:
        sub = signal_days(ev, sig)
        for h in HORIZONS:
            tr = [trade(panel, mkt, rf, r.symbol, r.sig, h, cost, factor) for r in sub.itertuples()]
            tr = pd.DataFrame([t for t in tr if t is not None])
            book[(sig, h)] = tr
            rows.append({"signal": sig, "horizon": h, "events": int(len(sub)), **summarize(tr)})
    return pd.DataFrame(rows), book


def split(ev: pd.DataFrame, holdout_start: str = HOLDOUT_START) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = pd.Timestamp(holdout_start)
    return ev[ev["first_day"] < cut], ev[ev["first_day"] >= cut]


# ---------------------------------------------------------------------------------------------
# Ön kayıtlı yöntemin uygulanması
# ---------------------------------------------------------------------------------------------
def _records(tab: pd.DataFrame) -> list[dict]:
    out = []
    for row in tab.to_dict("records"):
        out.append({k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in row.items()})
    return out


def study(panel: MarketPanel, rf: pd.Series, cost: CostConfig | None = None,
          first: str = FIRST_EVENT_DATE, seasoned_benchmark: int = 0,
          factor: pd.DataFrame | None = None) -> dict:
    """Ön kayıttaki dört adımı uygular ve sonucu döndürür.

    ``verdict``: ``"kesif-yok"`` (keşif örnekleminde aday çıkmadı), ``"gecti"`` ya da
    ``"gecemedi"`` (aday doğrulama örnekleminde sınandı).
    """
    cost = cost or CostConfig()
    ev = events(panel, find_listings(panel, first), factor)
    disc, hold = split(ev)
    mkt = market_returns(panel, seasoned_benchmark)
    tab_d, _ = run_family(panel, mkt, rf, disc, cost, factor)
    tab_h, _ = run_family(panel, mkt, rf, hold, cost, factor)
    tab_a, book_a = run_family(panel, mkt, rf, ev, cost, factor)

    ok = (tab_d["n"] >= MIN_TRADES) & (tab_d["abn_t"] >= DISCOVERY_T) & (tab_d["net_mean"] > 0)
    cands = tab_d[ok].sort_values("abn_t", ascending=False)
    result = {
        "as_of": str(panel.dates[-1].date()), "events": int(len(ev)),
        "discovery_events": int(len(disc)), "holdout_events": int(len(hold)),
        "by_year": {int(y): int(c) for y, c in ev["first_day"].dt.year.value_counts().sort_index().items()},
        "discovery": _records(tab_d), "holdout": _records(tab_h), "all": _records(tab_a),
        "candidate": None, "verdict": "kesif-yok",
    }
    if len(cands):
        best = cands.iloc[0]
        h = tab_h[(tab_h["signal"] == best["signal"]) & (tab_h["horizon"] == best["horizon"])].iloc[0]
        passed = bool(
            h["n"] > 0 and h["abn_mean"] > 0 and h["abn_t"] >= HOLDOUT_T
            and h["net_vs_cash"] > 0 and h["abn_median"] > 0
        )
        result["candidate"] = {"signal": best["signal"], "horizon": int(best["horizon"])}
        result["verdict"] = "gecti" if passed else "gecemedi"
    # Ortalamanın birkaç büyük kazanana ne kadar dayandığını gösteren özet (A sinyali).
    spread = {}
    for h in HORIZONS:
        t = book_a[("A", h)]
        if t.empty:
            continue
        top = t["abn"].sort_values().tail(10)
        spread[h] = {
            "n": int(len(t)), "lost_money": float((t["net"] < 0).mean()),
            "below_cash": float((t["net"] < t["cash"]).mean()), "net_median": float(t["net"].median()),
            "net_mean": float(t["net"].mean()), "abn_mean": float(t["abn"].mean()),
            "abn_mean_without_top10": float((t["abn"].sum() - top.sum()) / max(len(t) - len(top), 1)),
        }
    result["lottery"] = spread
    return result


def format_study(res: dict) -> str:
    """Sonucun okunur özeti (Türkçe)."""
    def pct(v, d=1):
        if v is None:
            return "–"
        text = f"%{abs(v) * 100:.{d}f}".replace(".", ",")
        return ("−" if v < 0 and text.strip("%0,") else "") + text

    def table(rows):
        lines = ["  Sinyal  Süre   İşlem   Ort. anormal   Ortanca    t     Piyasayı geçen   Net − faiz"]
        for r in rows:
            if not r.get("n"):
                lines.append(f"  {r['signal']:<7} {r['horizon']:>3}       0")
                continue
            t = "–" if r["abn_t"] is None else f"{r['abn_t']:.2f}"
            lines.append(
                f"  {r['signal']:<7} {r['horizon']:>3}   {r['n']:>5}   {pct(r['abn_mean']):>12}   {pct(r['abn_median']):>7}  "
                f"{t:>5}   {pct(r['win'], 0):>14}   {pct(r['net_vs_cash']):>10}"
            )
        return "\n".join(lines)

    out = [
        f"Halka arz keşfi — veri sonu {res['as_of']}",
        f"Halka arz sayısı: {res['events']} (keşif {res['discovery_events']}, doğrulama {res['holdout_events']})",
        "", f"KEŞİF ÖRNEKLEMİ (2024 öncesi) — aday eşiği: en az {MIN_TRADES} işlem, t ≥ {DISCOVERY_T}",
        table(res["discovery"]), "",
    ]
    if res["verdict"] == "kesif-yok":
        out.append("SONUÇ: keşif yok. 18 kuralın hiçbiri önceden konan eşiği geçemedi.")
    else:
        c = res["candidate"]
        word = "GEÇTİ" if res["verdict"] == "gecti" else "GEÇEMEDİ"
        out.append(f"SONUÇ: aday {c['signal']}/{c['horizon']} doğrulama örnekleminde {word}.")
    out += ["", "DOĞRULAMA ÖRNEKLEMİ (2024 ve sonrası)" +
            (" — yalnızca bilgi için" if res["verdict"] == "kesif-yok" else ""), table(res["holdout"]), ""]
    out.append("Açılma gününün ertesi sabahı alan biri (A sinyali, tüm dönem):")
    for h, s in res["lottery"].items():
        out.append(
            f"  {h} seans ({s['n']} işlem): zarar eden {pct(s['lost_money'], 0)}, faizin altında kalan "
            f"{pct(s['below_cash'], 0)}; ortanca net getiri {pct(s['net_median'])}, ortalama {pct(s['net_mean'])}. "
            f"Ortalama anormal getiri {pct(s['abn_mean'])}; en iyi 10 işlem çıkarılınca {pct(s['abn_mean_without_top10'])}."
        )
    return "\n".join(out)
