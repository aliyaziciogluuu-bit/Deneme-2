"""Günlük çalıştırıcı: veriyi eşitler, kâğıt portföyü günceller, yarının emirlerini üretir.

Akış (her işlem günü kapanıştan sonra):

1. Resmî günlük bültenleri, TLREF'i ve gereken İş Yatırım verilerini eşitle.
2. Sinyalleri hesapla. Yeniden dengeleme günüyse (ve veri sağlıklıysa) kararı ver, dondur.
3. Kâğıt portföyü başlangıçtan bugüne, dondurulmuş kararlarla ve backtest motorunun aynısıyla
   yeniden oynat: pozisyonlar, gerçekleşen işlemler, değer eğrisi ve ertesi seansın emirleri.
4. Panel (JSON) ve bildirim metnini üret.

Gerçek emir GÖNDERİLMEZ: bot emir listesini hazırlar, emri aracı kurumunuzda siz verirsiniz.
"""
from __future__ import annotations

import datetime as dt
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .. import rules
from ..backtest.engine import BacktestResult, run_backtest
from ..backtest.metrics import cagr, drawdown
from ..config import Config
from ..data.dataset import Dataset
from ..pipeline import Stores, candidate_symbols, load_panel, prepare_dataset, sync_isy
from ..portfolio import cash_index, rebalance_dates
from ..signals import compute_features, score_date, universe_mask
from .state import BotState

log = logging.getLogger(__name__)

#: Sinyaller ~273 seans geçmiş ister; başlangıçtan önce bu kadar takvim günü veri indirilir.
WARMUP_DAYS = 500
MIN_SESSIONS = 290
#: Sağlık eşikleri: bunların altında yeni karar verilmez (veri kesintisinde yanlış satış olmasın).
MIN_UNIVERSE = 60
MIN_FUNDAMENTAL_COVERAGE = 0.70
MIN_BULLETIN_ROWS = 300
#: Emir fişindeki limit fiyat payı (açılış seansı için, son kapanışa göre).
LIMIT_COLLAR = 0.03


class DataNotReady(RuntimeError):
    """Çalışmak için yeterli veri yok."""


@dataclass
class DailyResult:
    as_of: pd.Timestamp
    payload: dict
    decided: bool
    warnings: list[str] = field(default_factory=list)
    state: BotState | None = None


def _health(ds: Dataset, feats, universe: pd.DataFrame, day: pd.Timestamp) -> list[str]:
    """Yeni karar vermeye engel veri sorunları (boş liste = sağlıklı)."""
    problems = []
    listed_today = int(ds.panel.listed.loc[day].sum())
    if listed_today < MIN_BULLETIN_ROWS:
        problems.append(f"bültende yalnızca {listed_today} pay var")
    members = universe.loc[day]
    n = int(members.sum())
    if n < MIN_UNIVERSE:
        problems.append(f"alınabilir evren çok küçük ({n} hisse); veri eksik olabilir")
    if n:
        cols = members.index[members.to_numpy(dtype=bool)]
        coverage = float(feats.book_to_market.loc[day, cols].notna().mean())
        if coverage < MIN_FUNDAMENTAL_COVERAGE:
            problems.append(f"bilanço verisi evrenin yalnızca %{coverage * 100:.0f}'inde var")
    if not np.isfinite(ds.rf.loc[day]):
        problems.append("risksiz faiz verisi yok")
    if not np.isfinite(ds.xu100.loc[day]):
        problems.append("BIST 100 endeks verisi yok")
    return problems


def _map_symbols(weights: dict[str, float], renames: dict[str, str]) -> pd.Series:
    """Kayıtlı karardaki eski kodları güncel kodlara çevirir."""
    mapped: dict[str, float] = {}
    for sym, w in weights.items():
        cur = renames.get(sym, sym)
        mapped[cur] = mapped.get(cur, 0.0) + float(w)
    return pd.Series(mapped, dtype=float)


def _next_weekday(day: pd.Timestamp) -> pd.Timestamp:
    nxt = day + pd.Timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += pd.Timedelta(days=1)
    return nxt


def run_daily(
    stores: Stores,
    state_path: Path,
    cfg: Config,
    today: dt.date,
    sync: bool = True,
    save: bool = True,
) -> DailyResult:
    state = BotState.load(state_path)
    start_date = dt.date.fromisoformat(state.start) if state.start else today
    data_start = start_date - dt.timedelta(days=WARMUP_DAYS)

    if sync:
        stats = stores.bulletins.sync(data_start, today, today=today)
        log.info("bültenler: %s", stats)
        stores.macro.sync_rf(data_start - dt.timedelta(days=40), today)
    panel = load_panel(stores, data_start, today)
    if len(panel.dates) < MIN_SESSIONS:
        raise DataNotReady(f"yalnızca {len(panel.dates)} seans veri var; en az {MIN_SESSIONS} gerekli")
    last = panel.dates[-1]

    held = {panel.renames.get(s, s) for w in state.decisions.values() for s in w}
    symbols = candidate_symbols(panel, lookback=len(panel.dates), extra=sorted(held))
    if sync:
        isy_stats = sync_isy(
            stores, panel, symbols, today, max_financial_refresh=60,
            history_start=data_start - dt.timedelta(days=30),
        )
        log.info("İş Yatırım: %s", isy_stats)
    ds = prepare_dataset(stores, panel, symbols)
    feats = compute_features(ds, cfg.signal, symbols)
    universe = universe_mask(ds, feats, cfg.universe)

    if state.start is None:
        state.start = str(last.date())
        state.capital = float(cfg.capital)
    start_ts = pd.Timestamp(state.start)
    if start_ts not in panel.dates:
        later = panel.dates[panel.dates >= start_ts]
        if len(later) == 0:
            raise DataNotReady("başlangıç gününden sonra seans yok")
        start_ts = later[0]
    run_cfg = cfg.with_overrides(capital=state.capital if state.capital else cfg.capital)

    fixed = {pd.Timestamp(d): _map_symbols(w, panel.renames) for d, w in state.decisions.items()}
    fixed = {d: w for d, w in fixed.items() if d in panel.dates and d >= start_ts}
    scheduled = [d for d in rebalance_dates(panel.dates, run_cfg.portfolio) if start_ts <= d <= last]
    last_frozen = max(fixed) if fixed else None
    due = last_frozen is None or any(d > last_frozen for d in scheduled)

    warnings: list[str] = []
    needs = ds.quality.get("needs_refresh")
    if needs is not None and needs.fillna(False).any():
        stale = sorted(needs[needs.fillna(False).astype(bool)].index)
        warnings.append("düzeltme katsayısı güncellenemedi: " + ", ".join(stale[:8]))
    decided = False
    decision_dates = sorted(fixed)
    if due and last not in fixed:
        problems = _health(ds, feats, universe, last)
        if problems:
            warnings.append("Yeni karar ertelendi: " + "; ".join(problems))
        else:
            decision_dates.append(last)
            decided = True

    res = run_backtest(
        ds, run_cfg, feats, universe, start=start_ts,
        fixed_targets=fixed, decision_dates=decision_dates, keep_scores=True,
    )
    if decided:
        state.decisions[str(last.date())] = {s: round(float(w), 6) for s, w in res.weights[last].items()}

    payload = build_payload(ds, feats, universe, res, run_cfg, state, last, decided, warnings)
    if save:
        state.save(state_path)
    return DailyResult(as_of=last, payload=payload, decided=decided, warnings=warnings, state=state)


# ------------------------------------------------------------------------------- çıktı
def _lots(shares_adj: float, factor: float) -> float:
    """Düzeltilmiş pay adedini gerçek lota çevirir (lot = düzeltilmiş pay × katsayı)."""
    f = factor if np.isfinite(factor) and factor > 0 else 1.0
    return shares_adj * f


def _cost_basis(trades: pd.DataFrame) -> dict[str, dict]:
    """Ortalama maliyet yöntemiyle eldeki pozisyonların maliyeti ve ilk alış günü."""
    book: dict[str, dict] = {}
    for t in trades.itertuples(index=False):
        b = book.setdefault(t.symbol, {"shares": 0.0, "cost": 0.0, "since": None})
        if t.side == "buy":
            if b["shares"] <= 1e-12:
                b["since"] = t.date
            b["shares"] += t.shares
            b["cost"] += t.value + t.cost
        else:
            if b["shares"] > 1e-12:
                frac = min(t.shares / b["shares"], 1.0)
                b["cost"] *= 1.0 - frac
                b["shares"] -= t.shares
            if b["shares"] <= 1e-12:
                book.pop(t.symbol, None)
    return book


def build_payload(
    ds: Dataset, feats, universe: pd.DataFrame, res: BacktestResult, cfg: Config,
    state: BotState, last: pd.Timestamp, decided: bool, warnings: list[str],
) -> dict:
    p = ds.panel
    close = p.close.ffill()
    factor = ds.factor
    eq = res.equity
    equity = float(eq.iloc[-1])
    names = p.names

    table = score_date(ds, feats, universe.loc[last], last, cfg.signal)
    rank = table["rank"].to_dict() if not table.empty else {}

    basis = _cost_basis(res.trades)
    positions = []
    for sym, shares in sorted(res.positions.items()):
        px = float(close.at[last, sym])
        f = float(factor.at[last, sym]) if sym in factor.columns else float("nan")
        value = shares * px * (f if np.isfinite(f) else 1.0)
        b = basis.get(sym, {})
        cost = b.get("cost", float("nan"))
        positions.append(
            {
                "symbol": sym, "name": names.get(sym, sym), "lots": round(_lots(shares, f)),
                "price": px, "value": round(value, 2), "weight": round(value / equity, 4) if equity > 0 else 0.0,
                "pnl_pct": round(value / cost - 1.0, 4) if cost and np.isfinite(cost) and cost > 0 else None,
                "since": str(b["since"].date()) if b.get("since") is not None else None,
                "rank": int(rank[sym]) if sym in rank else None,
            }
        )
    positions.sort(key=lambda r: -r["value"])

    next_session = _next_weekday(last)
    orders = []
    if res.pending and res.pending_due is not None:
        for o in res.pending:
            px = float(close.at[last, o.symbol])
            f = float(factor.at[last, o.symbol])
            raw = _lots(o.shares, f)
            if o.side == "buy":
                lots = math.floor(raw + 1e-9)
            elif o.exit:
                lots = round(_lots(res.positions.get(o.symbol, o.shares), f))
            else:
                lots = math.floor(raw + 1e-9)
            if lots <= 0 or not np.isfinite(px):
                continue
            floor_px, ceil_px = rules.limit_prices(px, next_session)
            if o.side == "buy":
                limit = rules.round_to_tick(min(px * (1 + LIMIT_COLLAR), ceil_px), "down")
            else:
                limit = rules.round_to_tick(max(px * (1 - LIMIT_COLLAR), floor_px), "up")
            orders.append(
                {
                    "symbol": o.symbol, "name": names.get(o.symbol, o.symbol), "side": o.side, "lots": int(lots),
                    "ref_price": px, "limit_price": limit, "value": round(lots * px, 2), "reason": o.reason,
                    "carried": bool(res.pending_due != last),
                }
            )
        orders.sort(key=lambda r: (r["side"] != "sell", r["symbol"]))

    def trade_row(t) -> dict:
        f = float(factor.at[t.date, t.symbol]) if t.symbol in factor.columns else float("nan")
        f = f if np.isfinite(f) and f > 0 else 1.0
        return {
            "date": str(t.date.date()), "symbol": t.symbol, "name": names.get(t.symbol, t.symbol), "side": t.side,
            "lots": round(t.shares * f), "price": round(t.price / f, 4), "value": round(t.value, 2),
            "cost": round(t.cost, 2), "reason": t.reason,
        }

    ledger = [trade_row(t) for t in res.trades.itertuples(index=False)]
    fills_today = [r for r in ledger if r["date"] == str(last.date())]

    xu = ds.xu100.reindex(eq.index).ffill()
    cash_idx = cash_index(ds.rf).reindex(eq.index).ffill()
    start_eq = float(cfg.capital)
    curve = [
        {"d": str(d.date()), "e": round(float(v) / start_eq, 5), "x": round(float(xu.loc[d] / xu.iloc[0]), 5),
         "c": round(float(cash_idx.loc[d] / cash_idx.iloc[0]), 5)}
        for d, v in eq.items()
    ]
    day_ret = float(eq.iloc[-1] / eq.iloc[-2] - 1.0) if len(eq) > 1 else 0.0
    years = (eq.index[-1] - eq.index[0]).days / 365.25

    top = []
    held_now = set(res.positions)
    for sym, row in table.head(40).iterrows():
        top.append(
            {"rank": int(row["rank"]), "symbol": sym, "name": names.get(sym, sym), "score": round(float(row["score"]), 3),
             **{k: (round(float(row[k]), 2) if np.isfinite(row[k]) else None) for k in ("value", "quality", "lowrisk", "momentum")},
             "held": sym in held_now}
        )

    frozen = sorted(state.decisions)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "as_of": str(last.date()),
        "next_session": str(next_session.date()),
        "start": str(eq.index[0].date()),
        "capital": start_eq,
        "equity": round(equity, 2),
        "cash": round(float(res.cash.iloc[-1]), 2),
        "invested_pct": round(float(res.invested.iloc[-1]), 4),
        "day_return": round(day_ret, 5),
        "total_return": round(equity / start_eq - 1.0, 5),
        "xu100_return": round(float(xu.iloc[-1] / xu.iloc[0] - 1.0), 5),
        "cash_return": round(float(cash_idx.iloc[-1] / cash_idx.iloc[0] - 1.0), 5),
        "cagr": round(cagr(eq), 5) if years >= 1.0 else None,
        "max_drawdown": round(float(drawdown(eq).min()), 5),
        "xu100": round(float(ds.xu100.loc[last]), 2),
        "rf_annual": round(float(ds.rf.loc[last]), 5),
        "universe_size": int(universe.loc[last].sum()),
        "decided_today": str(last.date()) in state.decisions,
        "last_decision": frozen[-1] if frozen else None,
        "positions": positions,
        "orders": orders,
        "fills_today": fills_today,
        "ledger": ledger[-200:],
        "top": top,
        "curve": curve,
        "warnings": warnings,
        "costs_paid": round(res.total_costs(), 2),
        "settings": {
            "n_holdings": cfg.portfolio.n_holdings, "hold_rank": cfg.portfolio.hold_rank,
            "frequency": cfg.portfolio.frequency, "commission": cfg.cost.commission, "slippage": cfg.cost.slippage,
        },
    }
