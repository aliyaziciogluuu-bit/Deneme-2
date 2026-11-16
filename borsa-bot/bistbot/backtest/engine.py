"""Günlük çubuklu, olay güdümlü backtest motoru.

Zaman çizelgesi (ileriye bakmayı önleyen tek kural):

* ``t`` günü kapanışından sonra: puanlar ``t`` ve öncesi verilerle hesaplanır, emirler yazılır.
* ``t+1`` günü açılış seansında: emirler açılış fiyatından, maliyetlerle gerçekleşir.

Gerçekçilik:

* açılışı tavandan olan hisse alınamaz, tabandan olan satılamaz (satış ertesi güne taşınır);
* işlem görmeyen / durdurulan hissede emir gerçekleşmez;
* tek emir, hissenin 20 günlük medyan hacminin belirli bir payını aşamaz;
* komisyon + BSMV + kayma her işlemde düşülür;
* nakit temettüdeki stopaj hak kullanım gününde düşülür (fiyat serisi brüt temettüyle düzeltilmiştir);
* boştaki nakit gecelik faizin bir payını kazanır;
* kottan çıkan hisse son kapanışından nakde döner.

Hesaplar düzeltilmiş fiyat uzayında yapılır; TL değerleri gerçektir. İki kip vardır:

* araştırma kipi (varsayılan): kesirli pay, temettüler (stopaj düşülerek) aynı hisseye yeniden
  yatırılmış sayılır;
* lot kipi (``lot_mode=True``, canlı kâğıt portföy): yalnızca tam lot alınıp satılır, nakit
  temettü ve rüçhan hakkı değeri nakde eklenir, bedelsiz/bölünmede lot adedi değişir. Böylece
  kâğıt portföy, emir listesini uygulayan birinin hesabıyla aynı lotları taşır.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import Config
from ..data.dataset import Dataset
from ..portfolio import rebalance_dates, regime_exposure, select_holdings, target_weights
from ..rules import price_limit_series
from ..signals import Features, compute_features, score_date, universe_mask

#: Tavan/taban kilidi karşılaştırmasında fiyat adımı yuvarlaması için pay.
LIMIT_TOLERANCE = 0.006


@dataclass
class Order:
    symbol: str
    side: str  # "buy" | "sell"
    shares: float  # düzeltilmiş pay adedi (karar günü kapanışıyla hesaplanır)
    exit: bool = False  # pozisyonun tamamını sat
    reason: str = ""


@dataclass
class BacktestResult:
    equity: pd.Series
    cash: pd.Series
    invested: pd.Series  # hisse ağırlığı (0-1)
    n_positions: pd.Series
    trades: pd.DataFrame
    unfilled: pd.DataFrame
    weights: dict[pd.Timestamp, pd.Series] = field(default_factory=dict)  # karar günü hedefleri
    scores: dict[pd.Timestamp, pd.DataFrame] = field(default_factory=dict)
    positions: dict[str, float] = field(default_factory=dict)  # son gün: sembol -> düzeltilmiş pay
    pending: list[Order] = field(default_factory=list)  # son günden sonra gerçekleşecek emirler
    pending_due: pd.Timestamp | None = None  # bekleyen emirlerin karar günü
    events: list[dict] = field(default_factory=list)  # lot kipinde eldeki hisselerin özsermaye olayları

    @property
    def returns(self) -> pd.Series:
        return self.equity.pct_change().fillna(0.0)

    def turnover(self) -> float:
        """Yıllık tek yönlü devir hızı: min(alış, satış) / ortalama portföy değeri."""
        if self.trades.empty:
            return 0.0
        years = max((self.equity.index[-1] - self.equity.index[0]).days / 365.25, 1e-9)
        buys = self.trades.loc[self.trades["side"] == "buy", "value"].sum()
        sells = self.trades.loc[self.trades["side"] == "sell", "value"].sum()
        return float(min(buys, sells) / self.equity.mean() / years)

    def total_costs(self) -> float:
        return float(self.trades["cost"].sum()) if not self.trades.empty else 0.0


def is_share_event(code: str) -> bool:
    """Bültenin özsermaye hali kodu lot adedini değiştiren bir olay mı (bedelsiz, sermaye azaltımı)?

    Kodlar: 01 bedelli, 03 bedelsiz, 04 sermaye azaltımı, 06 nakit temettü; birleşik olaylar
    ``01&03`` gibi yazılır. Bedelsiz ya da azaltım içeren her olay lot adedini değiştirir;
    yalnızca temettü / yalnızca bedelli olaylarda lot aynı kalır, değer farkı nakittir.
    """
    parts = {p.strip().lstrip("0") for p in re.split(r"[&\-]", str(code)) if p.strip()}
    return bool(parts & {"3", "4"})


def plan_orders(
    position_values: dict[str, float],
    position_shares: dict[str, float],
    prices: dict[str, float],
    equity: float,
    targets: pd.Series,
    band: float,
    cash: float | None = None,
    cost_rate: float = 0.0,
    headroom: float = 0.0,
) -> list[Order]:
    """Mevcut pozisyonlardan hedef ağırlıklara geçiş emirleri (önce satışlar).

    Hedefte olmayan pozisyon tümüyle satılır. Hedefte olan pozisyonun ağırlığı hedefinden
    göreli olarak ``band``'dan fazla sapmışsa farkı kadar alınır/satılır.

    ``cash`` verilirse alımlar eldeki paraya sığdırılır: mevcut nakit + satışlardan beklenen
    gelir (masraf düşülmüş). Alımların maliyeti, fiyatın ``headroom`` kadar yukarıda
    gerçekleşebileceği varsayımıyla hesaplanır (limit fiyat payı). Para yetmiyorsa bütün
    alımlar aynı oranda küçültülür (sıradaki son hisse aç bırakılmaz).
    """
    sells: list[Order] = []
    buys: list[Order] = []
    for sym, shares in position_shares.items():
        if sym not in targets.index and shares > 0:
            sells.append(Order(sym, "sell", shares, exit=True, reason="çıkış"))
    for sym, weight in targets.items():
        price = prices.get(sym)
        if price is None or not np.isfinite(price) or price <= 0:
            continue
        target_value = float(weight) * equity
        current = position_values.get(sym, 0.0)
        if current <= 0:
            if target_value > 0:
                buys.append(Order(sym, "buy", target_value / price, reason="giriş"))
            continue
        diff = target_value - current
        if target_value <= 0:
            sells.append(Order(sym, "sell", position_shares[sym], exit=True, reason="çıkış"))
        elif abs(diff) > band * target_value:
            if diff > 0:
                buys.append(Order(sym, "buy", diff / price, reason="ağırlık"))
            else:
                sells.append(Order(sym, "sell", min(-diff / price, position_shares[sym]), reason="ağırlık"))
    if cash is not None and buys:
        proceeds = sum(o.shares * prices.get(o.symbol, 0.0) for o in sells if np.isfinite(prices.get(o.symbol, np.nan)))
        available = max(cash + proceeds * (1.0 - cost_rate), 0.0)
        need = sum(o.shares * prices[o.symbol] for o in buys) * (1.0 + cost_rate + headroom)
        if need > available:
            scale = available / need if need > 0 else 0.0
            for o in buys:
                o.shares *= scale
            buys = [o for o in buys if o.shares > 0]
    return sells + buys


def run_backtest(
    ds: Dataset,
    cfg: Config,
    feats: Features | None = None,
    universe: pd.DataFrame | None = None,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    execution_delay: int = 1,
    keep_scores: bool = False,
    scorer=None,
    score_tables: dict | None = None,
    fixed_targets: dict | None = None,
    decision_dates: list | None = None,
    lot_mode: bool = False,
) -> BacktestResult:
    """Stratejiyi geçmiş veride çalıştırır.

    ``execution_delay``: kararla işlem arasındaki seans sayısı (varsayılan 1). 2 verilirse
    "bir gün geç işlem" duyarlılık testi yapılır.

    ``scorer``: ``scorer(gün, puan_tablosu) -> puan_tablosu`` biçiminde isteğe bağlı kanca;
    gerçek puan tablosunu değiştirerek (ör. sıraları karıştırarak) rastgele portföy testi
    yapmaya yarar. ``score_tables``: önceden hesaplanmış ``{gün: puan_tablosu}`` (aynı
    sinyal ayarıyla çok sayıda koşuyu hızlandırmak için). ``fixed_targets``: geçmişte verilmiş
    ve dondurulmuş kararlar ``{gün: hedef ağırlık serisi}``; bu günlerde puan hesaplanmaz,
    kayıtlı hedefler aynen uygulanır (canlı kâğıt portföyün yeniden oynatılması için).
    ``decision_dates``: verilirse takvim yerine yalnızca bu günlerde karar verilir (canlıda
    botun gerçekten çalışıp karar verdiği günler). ``lot_mode``: tam lot ve nakit temettü
    kipi (modül açıklamasına bakın).
    """
    if execution_delay < 1:
        raise ValueError("execution_delay en az 1 olmalı (aynı gün kapanışından işlem yapılamaz)")
    feats = feats if feats is not None else compute_features(ds, cfg.signal)
    universe = universe if universe is not None else universe_mask(ds, feats, cfg.universe)
    cols = list(feats.vol.columns)
    col_pos = {s: j for j, s in enumerate(cols)}
    dates = ds.dates
    start = pd.Timestamp(start) if start is not None else dates[0]
    end = pd.Timestamp(end) if end is not None else dates[-1]
    i0 = int(dates.searchsorted(start))
    i1 = int(dates.searchsorted(end, side="right")) - 1
    if i1 < i0 or i0 >= len(dates):
        raise ValueError("backtest aralığı boş")

    adj_open = ds.adjusted("open")[cols].to_numpy(dtype=float)
    adj_close_raw = ds.adjusted("close")[cols]
    adj_close = adj_close_raw.ffill().to_numpy(dtype=float)
    traded_value = ds.panel.value[cols].to_numpy(dtype=float)
    suspended = ds.panel.suspended[cols].to_numpy(dtype=bool)
    listed = ds.panel.listed[cols].to_numpy(dtype=bool)
    div_tax = ds.div_tax[cols].to_numpy(dtype=float)
    factor = ds.factor[cols].ffill().to_numpy(dtype=float)
    corp = ds.panel.corp_action[cols].to_numpy(dtype=object)
    adv = feats.adv_20.to_numpy(dtype=float)
    limit = price_limit_series(dates).to_numpy()
    rf = ds.rf.to_numpy(dtype=float)
    day_gap = np.concatenate([[0.0], np.diff(dates.values).astype("timedelta64[D]").astype(float)])
    exposure = regime_exposure(ds.xu100, ds.rf, cfg.portfolio).to_numpy()

    if decision_dates is not None:
        decision_set = {pd.Timestamp(d) for d in decision_dates}
    else:
        decision_set = set(rebalance_dates(dates, cfg.portfolio))
        decision_set.add(dates[i0])  # ilk gün nakitte beklememek için

    cost = cfg.cost
    commission = cost.commission * (1.0 + cost.bsmv)
    slip = cost.slippage

    cash = float(cfg.capital)
    shares: dict[str, float] = {}
    pending: list[tuple[int, Order]] = []  # (gerçekleşeceği gün dizini, emir)
    pending_day: pd.Timestamp | None = None
    trades: list[dict] = []
    unfilled: list[dict] = []
    events: list[dict] = []
    eq_hist, cash_hist, inv_hist, npos_hist = [], [], [], []
    weights_hist: dict[pd.Timestamp, pd.Series] = {}
    scores_hist: dict[pd.Timestamp, pd.DataFrame] = {}

    for i in range(i0, i1 + 1):
        day = dates[i]
        # 1) Nakit faizi: önceki seanstan bugüne geçen takvim günleri için.
        if i > i0 and np.isfinite(rf[i - 1]) and cash > 0:
            cash *= 1.0 + rf[i - 1] * cost.cash_yield_share * day_gap[i] / 365.0

        # 2) Temettü stopajı ve kottan çıkış.
        for sym in list(shares):
            j = col_pos[sym]
            if lot_mode and i > 0:
                f_now, f_prev = factor[i, j], factor[i - 1, j]
                if np.isfinite(f_now) and np.isfinite(f_prev) and f_now > 0 and abs(f_prev / f_now - 1.0) > 1e-9:
                    step = f_prev / f_now  # < 1: hak kullanım gününde fiyat bu oranda düşer
                    prev_px = adj_close[i - 1, j]
                    lots_before = shares[sym] * f_prev
                    code = str(corp[i, j] or "")
                    if is_share_event(code) or step > 1.0:
                        # Bedelsiz / bölünme: düzeltilmiş pay aynı kalır, lot 1/step katına çıkar;
                        # küsurat lot nakde çevrilir.
                        lots = shares[sym] * f_now
                        whole = math.floor(lots + 1e-9)
                        credit = (lots - whole) / f_now * prev_px if np.isfinite(prev_px) else 0.0
                        shares[sym] = whole / f_now
                        kind = "bedelsiz"
                    else:
                        # Nakit temettü / rüçhan hakkı: lot aynı kalır, değer farkı nakde eklenir
                        # (temettüde stopaj düşülür; rüçhan hakkı kuramsal değerinden satılmış sayılır).
                        value_prev = shares[sym] * prev_px if np.isfinite(prev_px) else 0.0
                        credit = max(value_prev * ((1.0 - step) - div_tax[i, j]), 0.0)
                        shares[sym] *= step
                        kind = "bedelli" if "1" in {p.lstrip("0") for p in re.split(r"[&\-]", code)} else "temettü"
                    cash += credit
                    events.append(
                        {"date": day, "symbol": sym, "kind": kind, "code": code, "step": step, "cash": credit,
                         "lots_before": lots_before, "lots_after": shares.get(sym, 0.0) * f_now}
                    )
                    if shares[sym] <= 1e-12:
                        del shares[sym]
                        continue
            elif div_tax[i, j] > 0:
                shares[sym] *= 1.0 - div_tax[i, j]
            if not listed[i, j]:
                last_px = adj_close[i, j]
                if np.isfinite(last_px):
                    value = shares[sym] * last_px
                    cash += value
                    trades.append(
                        {"date": day, "symbol": sym, "side": "sell", "shares": shares[sym], "price": last_px,
                         "value": value, "cost": 0.0, "reason": "kottan çıkış"}
                    )
                del shares[sym]

        # 3) Bekleyen emirlerin açılışta gerçekleşmesi (önce satışlar).
        due = [o for when, o in pending if when <= i]
        later = [(when, o) for when, o in pending if when > i]
        carry: list[tuple[int, Order]] = []
        for order in sorted(due, key=lambda o: o.side != "sell"):
            j = col_pos[order.symbol]
            px = adj_open[i, j]
            prev = adj_close[i - 1, j] if i > 0 else np.nan
            ok = np.isfinite(px) and px > 0 and traded_value[i, j] > 0 and not suspended[i, j]
            reason = "" if ok else "işlem yok"
            if ok and np.isfinite(prev) and prev > 0:
                gap = px / prev - 1.0
                if order.side == "buy" and gap >= limit[i] - LIMIT_TOLERANCE:
                    ok, reason = False, "tavan"
                elif order.side == "sell" and gap <= -limit[i] + LIMIT_TOLERANCE:
                    ok, reason = False, "taban"
            if not ok:
                unfilled.append({"date": day, "symbol": order.symbol, "side": order.side, "reason": reason})
                if order.side == "sell" and order.symbol in shares:
                    carry.append((i + 1, order))  # satış ertesi gün yeniden denenir
                continue

            qty = order.shares
            f_exec = factor[i, j] if lot_mode and np.isfinite(factor[i, j]) and factor[i, j] > 0 else 1.0

            def whole_lots(q: float) -> float:
                """Lot kipinde miktarı tam lota aşağı yuvarlar (düzeltilmiş pay cinsinden döner)."""
                return math.floor(q * f_exec + 1e-9) / f_exec if lot_mode else q

            if order.side == "sell":
                held = shares.get(order.symbol, 0.0)
                qty = held if order.exit else min(whole_lots(qty), held)
                if qty <= 0:
                    continue
            else:
                qty = whole_lots(qty)
            cap_value = cfg.portfolio.max_participation * adv[i - 1, j] if i > 0 else np.inf
            if np.isfinite(cap_value) and qty * px > cap_value:
                unfilled.append({"date": day, "symbol": order.symbol, "side": order.side, "reason": "hacim sınırı"})
                qty = whole_lots(cap_value / px)
                if qty <= 0:
                    continue
            if order.side == "sell":
                gross = qty * px
                fee = gross * (commission + slip)
                cash += gross - fee
                shares[order.symbol] = shares.get(order.symbol, 0.0) - qty
                if shares[order.symbol] <= 1e-12:
                    del shares[order.symbol]
            else:
                unit = px * (1.0 + commission + slip)
                if qty * unit > cash:
                    qty = whole_lots(max(cash, 0.0) / unit)
                if qty <= 0:
                    unfilled.append({"date": day, "symbol": order.symbol, "side": "buy", "reason": "nakit yok"})
                    continue
                gross = qty * px
                fee = gross * (commission + slip)
                cash -= gross + fee
                shares[order.symbol] = shares.get(order.symbol, 0.0) + qty
            trades.append(
                {"date": day, "symbol": order.symbol, "side": order.side, "shares": qty, "price": px,
                 "value": gross, "cost": fee, "reason": order.reason}
            )
        pending = later + carry

        # 4) Gün sonu değerleme.
        values = {s: q * adj_close[i, col_pos[s]] for s, q in shares.items()}
        invested = float(sum(v for v in values.values() if np.isfinite(v)))
        equity = cash + invested
        eq_hist.append(equity)
        cash_hist.append(cash)
        inv_hist.append(invested / equity if equity > 0 else 0.0)
        npos_hist.append(len(shares))

        # 5) Karar günü: puanla, seç, emirleri yaz (bir sonraki seansta gerçekleşir).
        if day in decision_set:
            table = None
            if fixed_targets is not None and day in fixed_targets:
                targets = fixed_targets[day]
            else:
                if score_tables is not None and day in score_tables:
                    table = score_tables[day]
                else:
                    table = score_date(ds, feats, universe.loc[day], day, cfg.signal)
                if table.empty:
                    # Hiçbir hisse puanlanamadı: piyasa kapalı ya da veri yok. Portföye
                    # dokunma; karar bir sonraki seansa kalır.
                    if decision_dates is None and i + 1 <= i1:
                        decision_set.add(dates[i + 1])
                    continue
                if scorer is not None:
                    table = scorer(day, table)
                holdings = select_holdings(table, list(shares), cfg.portfolio)
                targets = target_weights(holdings, float(exposure[i]), cfg.portfolio)
            targets = targets[[s for s in targets.index if s in col_pos]]
            prices = {s: adj_close[i, col_pos[s]] for s in set(shares) | set(targets.index)}
            orders = plan_orders(
                values, shares, prices, equity, targets, cfg.portfolio.rebalance_band,
                cash=cash, cost_rate=commission + slip, headroom=cfg.portfolio.buy_headroom,
            )
            pending = [(i + execution_delay, o) for o in orders]  # yeni plan eskisinin yerini alır
            pending_day = day
            weights_hist[day] = targets
            if keep_scores and table is not None:
                scores_hist[day] = table

    idx = dates[i0 : i1 + 1]
    trade_cols = ["date", "symbol", "side", "shares", "price", "value", "cost", "reason"]
    return BacktestResult(
        equity=pd.Series(eq_hist, index=idx, name="equity"),
        cash=pd.Series(cash_hist, index=idx, name="cash"),
        invested=pd.Series(inv_hist, index=idx, name="invested"),
        n_positions=pd.Series(npos_hist, index=idx, name="n_positions"),
        trades=pd.DataFrame(trades, columns=trade_cols),
        unfilled=pd.DataFrame(unfilled, columns=["date", "symbol", "side", "reason"]),
        weights=weights_hist,
        scores=scores_hist,
        positions=dict(shares),
        pending=[o for _, o in pending],
        pending_due=pending_day if pending else None,
        events=events,
    )
