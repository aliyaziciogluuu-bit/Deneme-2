"""Günlük çalıştırıcı: veriyi eşitler, kâğıt portföyü günceller, sonraki seansın emirlerini üretir.

Akış (her işlem günü kapanıştan sonra):

1. Resmî günlük bültenleri, TLREF'i, BIST 100 endeksini ve gereken İş Yatırım verilerini eşitle.
2. Verinin bütünlüğünü sına (eksik bülten, kayıtlı kararların günleri, eldeki hisselerin verisi).
3. Kâğıt portföyü başlangıçtan bugüne, dondurulmuş kararlarla ve backtest motorunun aynısıyla
   (tam lot kipinde) yeniden oynat.
4. Yeniden dengeleme zamanı geldiyse, veri sağlıklıysa ve kullanıcının emirleri girebileceği
   bir zamandaysak kararı ver ve dondur.
5. Panel (JSON) ve bildirim metnini üret.

Gerçek emir GÖNDERİLMEZ: bot emir listesini hazırlar, emri aracı kurumunuzda siz verirsiniz.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

from .. import rules
from ..backtest.engine import BacktestResult, run_backtest
from ..backtest.metrics import cagr, drawdown
from ..config import Config, CostConfig
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
#: Bu saatten (İstanbul) sonra, o günün bülteni gelmeden karar verilmez: emirler açılış seansı
#: (09:40-09:55) içindir ve kullanıcının girmesi için zaman kalmalıdır.
PRE_OPEN_CUTOFF = dt.time(9, 30)
#: İlk kararda sabitlenen ve sonradan ``ayar.toml`` değişse de korunan portföy ayarları.
FROZEN_PORTFOLIO_KEYS = ("rebalance_band", "max_participation", "buy_headroom")


class DataNotReady(RuntimeError):
    """Güvenle çalışmak için gereken veri yok ya da eksik."""


@dataclass
class DailyResult:
    as_of: pd.Timestamp
    payload: dict | None
    decided: bool
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    state: BotState | None = None


# ------------------------------------------------------------------------------ yardımcılar
def frozen_settings(cfg: Config) -> dict:
    c = cfg.cost
    return {
        "cost": {"commission": c.commission, "bsmv": c.bsmv, "slippage": c.slippage,
                 "cash_yield_share": c.cash_yield_share},
        "portfolio": {k: getattr(cfg.portfolio, k) for k in FROZEN_PORTFOLIO_KEYS},
    }


def apply_settings(cfg: Config, state: BotState) -> Config:
    """Güncel ayarları, başlangıçta sabitlenen sermaye ve işlem ayarlarıyla birleştirir.

    Masraflar ve emir kuralları geçmişi yeniden yazmasın diye sabittir; sinyal ve seçim
    ayarları (ör. temkinli mod) güncel dosyadan gelir ve yalnızca sonraki kararları etkiler.
    """
    out = replace(cfg, capital=float(state.capital if state.capital else cfg.capital))
    saved = state.settings or {}
    if saved.get("cost"):
        out = replace(out, cost=CostConfig(**saved["cost"]))
    keep = {k: v for k, v in (saved.get("portfolio") or {}).items() if k in FROZEN_PORTFOLIO_KEYS}
    if keep:
        out = replace(out, portfolio=replace(out.portfolio, **keep))
    return out


def next_weekday(day: dt.date) -> dt.date:
    nxt = day + dt.timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += dt.timedelta(days=1)
    return nxt


def can_issue_orders(last: dt.date, now: dt.datetime, bulletin_pending: bool) -> tuple[bool, str]:
    """Şu an verilecek bir karar, sonraki seansın açılışından ÖNCE kullanıcıya ulaşır mı?

    Emirler "son bültenden sonraki ilk seansın açılışı" içindir. O seans başlamış ya da
    bitmişse (bülteni henüz gelmemiş olsa bile) karar verilmez; o günün kapanış verisi beklenir.
    """
    today = now.date()
    if last >= today:
        return True, ""
    if bulletin_pending:
        return False, "bugünkü seansın bülteni henüz yayımlanmadı"
    if today.weekday() >= 5 or now.time() < PRE_OPEN_CUTOFF:
        return True, ""
    return False, "seans başladı; karar bugünün kapanış verisiyle verilecek"


def expected_session(last: dt.date, now: dt.datetime) -> dt.date:
    """Emirlerin girileceği en erken seans günü (resmî tatiller hesaba katılmaz)."""
    today = now.date()
    if last < today and today.weekday() < 5 and now.time() < PRE_OPEN_CUTOFF:
        return today
    return next_weekday(max(last, today))


def _map_symbols(weights: dict[str, float], renames: dict[str, str]) -> pd.Series:
    """Kayıtlı karardaki eski kodları güncel kodlara çevirir (sıra korunur)."""
    mapped: dict[str, float] = {}
    for sym, w in weights.items():
        cur = renames.get(sym, sym)
        mapped[cur] = mapped.get(cur, 0.0) + float(w)
    return pd.Series(mapped, dtype=float)


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
        problems.append("BIST 100 endeks verisi güncel değil")
    return problems


def _held_data_problems(ds: Dataset, symbols: set[str], day: pd.Timestamp) -> list[str]:
    """Portföydeki (ve son kararda hedeflenen) her hissenin fiyatı ve düzeltme katsayısı var mı?

    Yalnızca yeniden oynatılan pozisyonlara bakmak yetmez: verisi bozulan bir hisse yeniden
    oynatmada hiç alınmamış görünür ve portföyden sessizce kaybolur. Bu yüzden son dondurulmuş
    kararın hedefleri de sınanır.
    """
    bad = []
    for sym in sorted(symbols):
        if sym not in ds.factor.columns or not ds.panel.listed.at[day, sym]:
            continue
        if not np.isfinite(ds.factor.at[day, sym]) or not np.isfinite(ds.panel.close[sym].ffill().at[day]):
            bad.append(sym)
    return [f"eldeki hisselerin verisi eksik: {', '.join(sorted(bad))}"] if bad else []


def _factor_at(ds: Dataset, day: pd.Timestamp, sym: str) -> float:
    f = ds.factor[sym].ffill().get(day, np.nan) if sym in ds.factor.columns else np.nan
    return float(f) if np.isfinite(f) and f > 0 else 1.0


def _ledger(ds: Dataset, res: BacktestResult) -> list[dict]:
    names = ds.panel.names
    rows = []
    for t in res.trades.itertuples(index=False):
        f = _factor_at(ds, t.date, t.symbol)
        rows.append(
            {"date": str(t.date.date()), "symbol": t.symbol, "name": names.get(t.symbol, t.symbol), "side": t.side,
             "lots": int(round(t.shares * f)), "price": round(t.price / f, 4), "value": round(t.value, 2),
             "cost": round(t.cost, 2), "reason": t.reason}
        )
    return rows


def _compact(rows: list[dict]) -> list[list]:
    return [[r["date"], r["symbol"], r["side"], r["lots"], r["price"]] for r in rows]


def _audit(reported: list[list], ledger: list[dict]) -> list[str]:
    """Daha önce bildirilen işlemler, yeniden hesaplamada aynı mı? Değişenleri döndürür."""
    if not reported:
        return []
    last_reported = max(r[0] for r in reported)
    now = {tuple(r) for r in _compact(ledger) if r[0] <= last_reported}
    before = {tuple(r) for r in reported}
    changed = sorted(before ^ now)
    return [f"{r[0]} {r[1]} {'SAT' if r[2] == 'sell' else 'AL'} {r[3]} lot" for r in changed]


def notification_digest(payload: dict) -> str:
    """Kullanıcının bilmesi gerekenlerin özeti: içerik değişirse bildirim yeniden gönderilir."""
    key = {
        "as_of": payload["as_of"],
        "orders": [[o["symbol"], o["side"], o["lots"], o["limit_price"]] for o in payload["orders"]],
        "warnings": payload["warnings"],
        "fills": len(payload["fills_today"]),
        "events": [[e["symbol"], e["kind"]] for e in payload.get("events", [])],
    }
    return hashlib.sha256(json.dumps(key, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


# ------------------------------------------------------------------------------- ana akış
def run_daily(
    stores: Stores,
    state_path: Path,
    cfg: Config,
    now: dt.datetime,
    sync: bool = True,
    save: bool = True,
) -> DailyResult:
    """``now``: İstanbul saatiyle şimdiki zaman (karar vermenin anlamlı olup olmadığını belirler)."""
    state = BotState.load(state_path)
    today = now.date()
    start_date = dt.date.fromisoformat(state.start) if state.start else today
    data_start = start_date - dt.timedelta(days=WARMUP_DAYS)

    if sync:
        log.info("bültenler: %s", stores.bulletins.sync(data_start, today, today=today))
        stores.macro.sync_rf(data_start - dt.timedelta(days=40), today)
        stores.macro.sync_index("XU100", data_start - dt.timedelta(days=40), today)
    panel = load_panel(stores, data_start, today)
    if len(panel.dates) < MIN_SESSIONS:
        raise DataNotReady(f"yalnızca {len(panel.dates)} seans veri var; en az {MIN_SESSIONS} gerekli")

    # Seans takvimini ikinci bir kaynakla (endeks serisi) sına: endekste olup bültende olmayan
    # bir gün, indirilememiş bir bültendir; eksik günle portföy yeniden oynatılamaz.
    index = stores.macro.load_index("XU100")

    def holes(p) -> list[pd.Timestamp]:
        return [d for d in index.index if p.dates[0] <= d <= p.dates[-1] and d not in p.dates]

    missing = holes(panel)
    if missing:
        stores.bulletins.forget_nosession([d.date() for d in missing])
        if sync:
            for d in missing:
                try:
                    stores.bulletins.fetch_day(d.date())
                except Exception as exc:
                    log.warning("eksik bülten yeniden alınamadı %s: %s", d.date(), exc)
            panel = load_panel(stores, data_start, today)
            missing = holes(panel)
        if missing:
            raise DataNotReady("bülten eksik: " + ", ".join(str(d.date()) for d in missing[:5]))
    last = panel.dates[-1]
    bulletin_pending = bool(len(index)) and index.index.max() > last

    # Kayıtlı durum esastır: başlangıç ve karar günlerinin tamamı veride olmalı.
    for key in ([state.start] if state.start else []) + list(state.decisions):
        if pd.Timestamp(key) not in panel.dates:
            raise DataNotReady(f"kayıtlı {key} gününün bülteni veride yok")

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

    actionable, why_not = can_issue_orders(last.date(), now, bulletin_pending)
    if state.start is None:
        if not actionable:
            text = (
                "BIST Bot kuruldu. İlk emir listesi bugünün kapanış verisi yayımlandıktan sonra "
                f"(akşam) gelecek ({why_not})."
            )
            return DailyResult(as_of=last, payload=None, decided=False, message=text, warnings=[why_not], state=state)
        state.start = str(last.date())
        state.capital = float(cfg.capital)
    if state.settings is None:
        state.settings = frozen_settings(cfg)
    run_cfg = apply_settings(cfg, state)
    start_ts = pd.Timestamp(state.start)

    fixed = {pd.Timestamp(d): _map_symbols(w, panel.renames) for d, w in state.decisions.items()}
    scheduled = [d for d in rebalance_dates(panel.dates, run_cfg.portfolio) if start_ts <= d <= last]
    last_frozen = max(fixed) if fixed else None
    due = last_frozen is None or any(d > last_frozen for d in scheduled)

    def replay(decision_dates: list[pd.Timestamp]) -> BacktestResult:
        return run_backtest(
            ds, run_cfg, feats, universe, start=start_ts, fixed_targets=fixed,
            decision_dates=decision_dates, keep_scores=True, lot_mode=True,
        )

    res = replay(sorted(fixed))
    warnings: list[str] = []
    needs = ds.quality.get("needs_refresh")
    if needs is not None and needs.fillna(False).any():
        stale = sorted(needs[needs.fillna(False).astype(bool)].index)
        warnings.append("Düzeltme katsayısı güncellenemedi: " + ", ".join(stale[:8]) + ".")
    targeted = set(fixed[last_frozen].index) if last_frozen is not None else set()
    problems = _held_data_problems(ds, set(res.positions) | targeted, last)
    changed = _audit(state.reported, _ledger(ds, res))
    if changed:
        warnings.append(
            "Daha önce bildirilen kâğıt işlemler veri düzeltmesi nedeniyle yeniden hesaplandı: "
            + "; ".join(changed[:6]) + ". Hesabınızdaki lotları panelle karşılaştırın."
        )
        # Geçmiş değiştiyse o çalıştırmada yeni karar verilmez; sonraki çalıştırma yeni kaydı esas alır.
        problems.append("geçmiş kâğıt işlemler değişti")

    decided = False
    if due and last not in fixed:
        if not actionable:
            warnings.append(f"Yeniden dengeleme kararı bekliyor: {why_not}.")
        else:
            problems += _health(ds, feats, universe, last)
            if problems:
                warnings.append("Yeni karar ertelendi: " + "; ".join(problems) + ".")
            else:
                res = replay(sorted(fixed) + [last])
                state.decisions[str(last.date())] = {s: round(float(w), 6) for s, w in res.weights[last].items()}
                decided = True
    elif problems:
        warnings.append("Veri uyarısı: " + "; ".join(problems) + ".")

    payload = build_payload(ds, feats, universe, res, run_cfg, state, last, now, warnings)
    state.reported = _compact(payload.pop("ledger_all"))
    if save:
        state.save(state_path)
    return DailyResult(as_of=last, payload=payload, decided=decided, warnings=warnings, state=state)


# ------------------------------------------------------------------------------- çıktı
def _cost_basis(ledger: list[dict], events: list[dict]) -> dict[str, dict]:
    """Ortalama maliyet (lot bazında) ve ilk alış günü. Bedelsizde lot değişir, maliyet aynı kalır."""
    timeline = [(r["date"], 1, r) for r in ledger] + [(str(e["date"].date()), 0, e) for e in events]
    book: dict[str, dict] = {}
    for _, kind, item in sorted(timeline, key=lambda x: (x[0], x[1])):
        sym = item["symbol"]
        if kind == 0:
            if sym in book:
                book[sym]["lots"] = item["lots_after"]
            continue
        b = book.setdefault(sym, {"lots": 0.0, "cost": 0.0, "since": None})
        if item["side"] == "buy":
            if b["lots"] <= 1e-9:
                b["since"] = item["date"]
            b["lots"] += item["lots"]
            b["cost"] += item["value"] + item["cost"]
        else:
            if b["lots"] > 1e-9:
                frac = min(item["lots"] / b["lots"], 1.0)
                b["cost"] *= 1.0 - frac
                b["lots"] -= item["lots"]
            if b["lots"] <= 1e-9:
                book.pop(sym, None)
    return book


def build_payload(
    ds: Dataset, feats, universe: pd.DataFrame, res: BacktestResult, cfg: Config,
    state: BotState, last: pd.Timestamp, now: dt.datetime, warnings: list[str],
) -> dict:
    p = ds.panel
    close = p.close.ffill()
    eq = res.equity
    equity = float(eq.iloc[-1])
    names = p.names
    headroom = cfg.portfolio.buy_headroom
    session = expected_session(last.date(), now)

    table = score_date(ds, feats, universe.loc[last], last, cfg.signal)
    rank = table["rank"].to_dict() if not table.empty else {}
    ledger = _ledger(ds, res)
    basis = _cost_basis(ledger, res.events)

    positions = []
    lots_held: dict[str, int] = {}
    for sym, shares in sorted(res.positions.items()):
        px = float(close.at[last, sym])
        f = _factor_at(ds, last, sym)
        lots = int(round(shares * f))
        lots_held[sym] = lots
        value = shares * f * px
        b = basis.get(sym, {})
        cost = b.get("cost", float("nan"))
        positions.append(
            {"symbol": sym, "name": names.get(sym, sym), "lots": lots, "price": px, "value": round(value, 2),
             "weight": round(value / equity, 4) if equity > 0 else 0.0,
             "pnl_pct": round(value / cost - 1.0, 4) if cost and np.isfinite(cost) and cost > 0 else None,
             "since": b.get("since"), "rank": int(rank[sym]) if sym in rank else None}
        )
    positions.sort(key=lambda r: -r["value"])

    orders = []
    for o in res.pending:
        px = float(close.at[last, o.symbol])
        if not np.isfinite(px) or px <= 0:
            continue
        f = _factor_at(ds, last, o.symbol)
        if o.side == "sell" and o.exit:
            lots = lots_held.get(o.symbol, 0)
        else:
            lots = math.floor(o.shares * f + 1e-9)
            if o.side == "sell":
                lots = min(lots, lots_held.get(o.symbol, 0))
        if lots <= 0:
            continue
        floor_px, ceil_px = rules.limit_prices(px, pd.Timestamp(session))
        if o.side == "buy":
            limit = rules.round_to_tick(min(px * (1 + headroom), ceil_px), "down")
        else:
            limit = rules.round_to_tick(max(px * (1 - headroom), floor_px), "up")
        orders.append(
            {"symbol": o.symbol, "name": names.get(o.symbol, o.symbol), "side": o.side, "lots": int(lots),
             "ref_price": px, "limit_price": limit, "value": round(lots * px, 2), "reason": o.reason,
             "carried": bool(res.pending_due is not None and res.pending_due != last)}
        )
    # Sıra korunur: önce satışlar, sonra alımlar öncelik sırasıyla (en iyi sıradaki hisse önce).
    # Bir satış gerçekleşmez de para yetmezse kâğıt portföy listenin SONUNDAKİ alımı kısar.

    today_iso = str(last.date())
    events = [
        {"symbol": e["symbol"], "name": names.get(e["symbol"], e["symbol"]), "kind": e["kind"],
         "cash": round(e["cash"], 2), "lots_before": int(round(e["lots_before"])),
         "lots_after": int(round(e["lots_after"]))}
        for e in res.events if e["date"] == last
    ]

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

    held_now = set(res.positions)
    top = [
        {"rank": int(row["rank"]), "symbol": sym, "name": names.get(sym, sym), "score": round(float(row["score"]), 3),
         **{k: (round(float(row[k]), 2) if np.isfinite(row[k]) else None) for k in ("value", "quality", "lowrisk", "momentum")},
         "held": sym in held_now}
        for sym, row in table.head(40).iterrows()
    ]

    frozen = list(state.decisions)
    xu_last, rf_last = ds.xu100.loc[last], ds.rf.loc[last]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "as_of": today_iso,
        "next_session": str(session),
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
        "xu100": round(float(xu_last), 2) if np.isfinite(xu_last) else None,
        "rf_annual": round(float(rf_last), 5) if np.isfinite(rf_last) else None,
        "universe_size": int(universe.loc[last].sum()),
        "decided_today": today_iso in state.decisions,
        "last_decision": max(frozen) if frozen else None,
        "positions": positions,
        "orders": orders,
        "fills_today": [r for r in ledger if r["date"] == today_iso],
        "events": events,
        "ledger": ledger[-200:],
        "ledger_all": ledger,
        "top": top,
        "curve": curve,
        "warnings": list(warnings),
        "costs_paid": round(res.total_costs(), 2),
        "settings": {
            "n_holdings": cfg.portfolio.n_holdings, "hold_rank": cfg.portfolio.hold_rank,
            "frequency": cfg.portfolio.frequency, "regime": cfg.portfolio.regime,
            "commission": cfg.cost.commission, "slippage": cfg.cost.slippage,
        },
    }
