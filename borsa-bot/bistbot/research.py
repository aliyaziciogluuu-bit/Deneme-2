"""Araştırma ve doğrulama: ön kayıtlı stratejinin backtest'i ve sağlamlık testleri.

Ön kayıt ilkesi: dağıtılan strateji ``Config()`` varsayılanıdır ve veriye bakılmadan önce
sabitlenmiştir. Aşağıdaki "deneme" listesi de önceden beyan edilmiştir; amaç en iyisini
seçmek değil, sonucun tek bir parametre seçimine bağlı olup olmadığını görmektir. Yine de
her deneme, şans payını ölçen istatistiklerde (DSR, PBO) sayılır.

Hibrit (teknik + temel) ön kaydı — 16 Kasım 2026, hiçbir hibrit backtest koşulmadan önce
----------------------------------------------------------------------------------------
Dört hibrit deneme beyan edilmiştir (``hibrit_*``). Aday olan ``hibrit_kapi_cikis``'tır:
hisseyi bileşik puan seçer, teknik analiz alımı onaylar ve eğilim bozulunca çıkarır
("temel analizle seç, teknik analizle zamanla"). Eğilim, enflasyon yanılgısına düşmemek için
nakde (gecelik faize) göre fiyatın 200 günlük ortalamasıyla ölçülür; pencere uzunlukları
(200/50/252) yaygın kullanılan değerlerdir ve denenerek seçilmemiştir.

Karar kuralı (sonuç görülmeden yazıldı): hibrit aday ancak şu üç koşulun **hepsini**
sağlarsa varsayılan strateji olur; aksi hâlde varsayılan değişmez ve hibrit, ``ayar.toml``
ile açılabilen bir seçenek olarak kalır:

1. Tam dönemde hem Sharpe oranı hem yıllık getirisi birincil stratejiden yüksek,
2. Üç alt dönemin (2017-19, 2020-22, 2023-26) en az ikisinde yıllık getirisi birincilden yüksek,
3. İşlem masrafı iki katına çıkarıldığında da Sharpe oranı birincilden yüksek.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .backtest import benchmarks as bm
from .backtest import stats
from .backtest.engine import BacktestResult, run_backtest
from .backtest.metrics import TRADING_DAYS, cagr, daily_rf, deflate, summarize, yearly_returns
from .config import Config
from .data.dataset import Dataset
from .portfolio import rebalance_dates
from .signals import Features, compute_features, score_date, universe_mask

log = logging.getLogger(__name__)

PERIODS = {
    "2017-2019": ("2017-01-01", "2019-12-31"),
    "2020-2022": ("2020-01-01", "2022-12-31"),
    "2023-2026": ("2023-01-01", "2026-12-31"),
}


#: Ön kayıtlı hibrit aday (bkz. modül başı).
HYBRID_CANDIDATE = "hibrit_kapi_cikis"


def declared_trials(base: Config) -> dict[str, Config]:
    """Önceden beyan edilmiş deneme seti (birincil yapılandırma + tek tek komşuları)."""
    o = base.with_overrides
    only = lambda **w: {"w_value": 0.0, "w_quality": 0.0, "w_lowrisk": 0.0, "w_momentum": 0.0, **w}  # noqa: E731
    n = base.portfolio.n_holdings
    return {
        "birincil": base,
        "hisse_10": o(portfolio={"n_holdings": 10, "hold_rank": 20}),
        "hisse_15": o(portfolio={"n_holdings": 15, "hold_rank": 30}),
        "hisse_30": o(portfolio={"n_holdings": 30, "hold_rank": 60}),
        "bant_yok": o(portfolio={"hold_rank": n}),
        "bant_3x": o(portfolio={"hold_rank": 3 * n}),
        "haftalik": o(portfolio={"frequency": "weekly"}),
        "ay_gun_5": o(portfolio={"offset": 5}),
        "ay_gun_10": o(portfolio={"offset": 10}),
        "ay_gun_15": o(portfolio={"offset": 15}),
        "yalniz_deger": o(signal=only(w_value=1.0)),
        "yalniz_karlilik": o(signal=only(w_quality=1.0)),
        "yalniz_dusuk_risk": o(signal=only(w_lowrisk=1.0)),
        "yalniz_momentum": o(signal=only(w_momentum=1.0)),
        "degersiz": o(signal={"w_value": 0.0}),
        "karliliksiz": o(signal={"w_quality": 0.0}),
        "dusuk_risksiz": o(signal={"w_lowrisk": 0.0}),
        "momentumsuz": o(signal={"w_momentum": 0.0}),
        "momentum_6_1": o(signal={"mom_lookback": 126}),
        "momentum_12_0": o(signal={"mom_skip": 0}),
        "oynaklik_126": o(signal={"vol_window": 126, "beta_window": 126}),
        "grup_notr_degil": o(signal={"group_neutral": False}),
        "gecmis_126": o(universe={"min_history": 126}),
        "rejim_nakit": o(portfolio={"regime": "trend", "regime_off_exposure": 0.0}),
        "rejim_yari": o(portfolio={"regime": "trend", "regime_off_exposure": 0.5}),
        "rejim_yari_6ay": o(portfolio={"regime": "trend", "regime_off_exposure": 0.5, "regime_lookback": 126}),
        "rejim_yari_9ay": o(portfolio={"regime": "trend", "regime_off_exposure": 0.5, "regime_lookback": 189}),
        # Hibrit (teknik + temel) denemeleri: bkz. modül başındaki ön kayıt.
        "hibrit_sutun": o(signal={"w_technical": 1.0}),
        "hibrit_kapi": o(portfolio={"trend_gate": "entry"}),
        HYBRID_CANDIDATE: o(portfolio={"trend_gate": "entry_exit"}),
        "hibrit_tam": o(signal={"w_technical": 1.0}, portfolio={"trend_gate": "entry_exit"}),
    }


@dataclass
class Prepared:
    """Bir sinyal ayarı için önceden hesaplanmış özellikler, evren ve puan tabloları."""

    feats: Features
    universe: pd.DataFrame
    tables: dict


class Lab:
    """Aynı veri seti üzerinde çok sayıda backtest koşmak için önbellekli yardımcı."""

    def __init__(self, ds: Dataset, start: str, end: str | None = None, symbols: list[str] | None = None):
        self.ds = ds
        self.start = pd.Timestamp(start)
        self.end = pd.Timestamp(end) if end else ds.dates[-1]
        self.symbols = symbols or sorted(ds.panel.bist100.columns[ds.panel.bist100.any().to_numpy()])
        self._prepared: dict = {}
        self.rf_daily = daily_rf(ds.rf, ds.dates)

    def prepare(self, cfg: Config) -> Prepared:
        key = (cfg.signal, cfg.universe)
        if key not in self._prepared:
            fkey = ("f", cfg.signal.vol_window, cfg.signal.beta_window, cfg.signal.max_window,
                    cfg.signal.max_top_n, cfg.signal.mom_lookback, cfg.signal.mom_skip,
                    cfg.signal.trend_window, cfg.signal.trend_short_window)
            if fkey not in self._prepared:
                self._prepared[fkey] = compute_features(self.ds, cfg.signal, self.symbols)
            feats = self._prepared[fkey]
            self._prepared[key] = Prepared(feats, universe_mask(self.ds, feats, cfg.universe), {})
        return self._prepared[key]

    def decision_days(self, cfg: Config) -> list[pd.Timestamp]:
        days = set(rebalance_dates(self.ds.dates, cfg.portfolio)) | {self.start}
        return sorted(d for d in days if self.start <= d <= self.end)

    def tables(self, cfg: Config) -> dict:
        """Karar günlerinin puan tabloları (bir kez hesaplanır, koşular arasında paylaşılır)."""
        prep = self.prepare(cfg)
        for day in self.decision_days(cfg):
            if day not in prep.tables:
                prep.tables[day] = score_date(self.ds, prep.feats, prep.universe.loc[day], day, cfg.signal)
        return prep.tables

    def run(self, cfg: Config, scorer=None, **kw) -> BacktestResult:
        prep = self.prepare(cfg)
        self.tables(cfg)
        start = kw.pop("start", self.start)
        end = kw.pop("end", self.end)
        return run_backtest(
            self.ds, cfg, prep.feats, prep.universe, start=start, end=end,
            scorer=scorer, score_tables=prep.tables, **kw,
        )

    # -- kıyaslar -------------------------------------------------------------------
    def benchmarks(self, cfg: Config) -> dict[str, pd.Series]:
        prep = self.prepare(cfg)
        window = slice(self.start, self.end)

        def norm(s: pd.Series) -> pd.Series:
            s = s.loc[window].dropna()
            return s / s.iloc[0]

        tables = self.tables(cfg)
        # Sepet, stratejinin o gün seçim yaptığı havuzun (puanlanan hisselerin) tamamıdır.
        baskets = {d: list(tables[d].index) for d in self.decision_days(cfg) if not tables[d].empty}
        return {
            "ew": norm(bm.periodic_equal_weight(self.ds, baskets)),
            "ew_daily": norm(bm.equal_weight_universe(self.ds, prep.universe)),
            "xu100": norm(self.ds.xu100),
            "cash": norm(bm.cash(self.ds)),
        }


def _row(name: str, res: BacktestResult, lab: Lab, bench: dict[str, pd.Series]) -> dict:
    s = summarize(res.equity, lab.ds.rf, bench["ew"])
    return {
        "deneme": name,
        "cagr": s["cagr"], "sharpe": s["sharpe"], "max_dd": s["max_drawdown"], "vol": s["volatility"],
        "ew_ustu_cagr": s["excess_cagr"], "bilgi_orani": s["information_ratio"],
        "alfa_yillik": s["alpha_annual"], "alfa_t": s["alpha_tstat"], "beta": s["beta"],
        "devir_hizi": res.turnover(), "ort_hisse": float(res.n_positions.mean()),
        "ort_yatirim": float(res.invested.mean()),
    }


HYBRID_TRIALS = ("hibrit_sutun", "hibrit_kapi", HYBRID_CANDIDATE, "hibrit_tam")


def _double_cost(cfg: Config) -> Config:
    return cfg.with_overrides(cost={"commission": cfg.cost.commission * 2, "slippage": cfg.cost.slippage * 2})


def hybrid_report(lab: Lab, base: Config, results: dict[str, BacktestResult], sr_trials: np.ndarray) -> dict:
    """Hibrit denemelerin birincil stratejiyle karşılaştırması ve ön kayıtlı karar kuralı.

    ``results``: ``{deneme adı: backtest sonucu}`` (birincil ve dört hibrit deneme).
    Ölçütler modül başındaki ön kayıttaki üç koşuldur; her hibrit için ayrı ayrı sınanır,
    ama bağlayıcı olan yalnızca ön kayıtlı adayın (``HYBRID_CANDIDATE``) sonucudur.
    """
    trials = declared_trials(base)
    rows: dict[str, dict] = {}
    for name in ("birincil", *HYBRID_TRIALS):
        cfg, res = trials[name], results[name]
        s = summarize(res.equity, lab.ds.rf, lab.benchmarks(cfg)["ew"])
        costly = summarize(lab.run(_double_cost(cfg)).equity, lab.ds.rf)
        no_yield = summarize(lab.run(cfg.with_overrides(cost={"cash_yield_share": 0.0})).equity, lab.ds.rf)
        x = (res.equity.pct_change().fillna(0.0) - lab.rf_daily.reindex(res.equity.index)).to_numpy()
        rows[name] = {
            "cagr": s["cagr"], "sharpe": s["sharpe"], "max_dd": s["max_drawdown"], "alfa_t": s["alpha_tstat"],
            "ew_ustu_cagr": s["excess_cagr"], "devir_hizi": res.turnover(), "ort_yatirim": float(res.invested.mean()),
            "sharpe_2x": costly["sharpe"], "cagr_2x": costly["cagr"],
            "cagr_faizsiz": no_yield["cagr"], "sharpe_faizsiz": no_yield["sharpe"],
            "dsr_vs_cash": stats.deflated_sharpe(x, sr_trials),
            "donem": {p: cagr(res.equity.loc[a:b]) for p, (a, b) in PERIODS.items() if len(res.equity.loc[a:b]) > 60},
        }
    ref = rows["birincil"]
    for name in HYBRID_TRIALS:
        r = rows[name]
        better = [p for p in r["donem"] if r["donem"][p] > ref["donem"][p]]
        rule = {
            "tam_donem": bool(r["sharpe"] > ref["sharpe"] and r["cagr"] > ref["cagr"]),
            "iyi_donem_sayisi": len(better), "donem_sayisi": len(r["donem"]),
            "alt_donem": bool(len(better) >= 2),
            "maliyet_2x": bool(r["sharpe_2x"] > ref["sharpe_2x"]),
        }
        rule["gecti"] = bool(rule["tam_donem"] and rule["alt_donem"] and rule["maliyet_2x"])
        # Nakit faiz kazanmasa da birincilden iyi mi (ön kayıtlı ölçüt değil, ek bilgi).
        rule["faizsiz_de_iyi"] = bool(r["cagr_faizsiz"] > ref["cagr_faizsiz"])
        r["kural"] = rule
    gate = {"trend_gate": "entry_exit"}
    windows = {}
    for w in (150, 250):  # duyarlılık (seçim denemesi değil): eğilim penceresi
        cfg = base.with_overrides(portfolio=gate, signal={"trend_window": w})
        res = lab.run(cfg)
        s = summarize(res.equity, lab.ds.rf)
        windows[str(w)] = {"cagr": s["cagr"], "sharpe": s["sharpe"], "max_dd": s["max_drawdown"]}
    return {
        "aday": HYBRID_CANDIDATE,
        "aday_gecti": rows[HYBRID_CANDIDATE]["kural"]["gecti"],
        "denemeler": rows,
        "aday_pencere": windows,
    }


def full_report(ds: Dataset, base: Config, start: str, end: str | None = None,
                n_random: int = 200, n_boot: int = 2000, seed: int = 20261116, live: Config | None = None) -> dict:
    """Birincil backtest + tüm sağlamlık testleri. Dönen sözlük JSON'a yazılabilir.

    ``base`` ön kayıtlı (birincil) stratejidir. ``live`` verilirse, kullanıcının ``ayar.toml``
    ile çalıştırdığı ayarın (ör. hibrit mod) sonuçları ``live`` başlığı altında ayrıca raporlanır.
    """
    lab = Lab(ds, start, end)
    bench = lab.benchmarks(base)
    primary = lab.run(base, keep_scores=True)
    eq = primary.equity
    rfd = lab.rf_daily.reindex(eq.index)
    ret = eq.pct_change().fillna(0.0)

    report: dict = {"start": str(eq.index[0].date()), "end": str(eq.index[-1].date()), "capital": base.capital}
    report["primary"] = {
        "vs_ew": summarize(eq, ds.rf, bench["ew"]),
        "vs_xu100": summarize(eq, ds.rf, bench["xu100"]),
        "turnover": primary.turnover(),
        "cost_total": primary.total_costs(),
        "cost_drag_annual": primary.total_costs() / eq.mean() / max(report_years(eq), 1e-9),
        "trades": int(len(primary.trades)),
        "unfilled": primary.unfilled["reason"].value_counts().to_dict(),
        "avg_positions": float(primary.n_positions.mean()),
        "avg_invested": float(primary.invested.mean()),
    }
    report["benchmarks"] = {k: summarize(v, ds.rf) for k, v in bench.items()}

    usd = ds.usdtry
    series = {
        "strateji": eq / eq.iloc[0], "esit_agirlik": bench["ew"], "esit_agirlik_gunluk": bench["ew_daily"],
        "bist100": bench["xu100"], "nakit": bench["cash"],
        "strateji_usd": deflate(eq, usd), "bist100_usd": deflate(bench["xu100"], usd),
        "strateji_nakde_gore": deflate(eq, bench["cash"]),
    }
    report["yearly"] = yearly_returns(series).round(4).to_dict(orient="index")
    report["periods"] = {}
    for name, (a, b) in PERIODS.items():
        sub = eq.loc[a:b]
        if len(sub) > 60:
            report["periods"][name] = {
                "strateji": summarize(sub, ds.rf, bench["ew"].loc[a:b]),
                "esit_agirlik_cagr": cagr(bench["ew"].loc[a:b]),
                "bist100_cagr": cagr(bench["xu100"].loc[a:b]),
                "nakit_cagr": cagr(bench["cash"].loc[a:b]),
            }

    # Duyarlılık (seçim denemesi değil): maliyet ve gecikme.
    sens = {}
    zero = base.with_overrides(cost={"commission": 0.0, "slippage": 0.0})
    double = base.with_overrides(cost={"commission": base.cost.commission * 2, "slippage": base.cost.slippage * 2})
    for name, res in (
        ("maliyetsiz", lab.run(zero)), ("maliyet_2x", lab.run(double)), ("bir_gun_gec", lab.run(base, execution_delay=2)),
        ("nakit_faizsiz", lab.run(base.with_overrides(cost={"cash_yield_share": 0.0}))),
        ("rejim_yari_nakit_faizsiz", lab.run(base.with_overrides(
            portfolio={"regime": "trend", "regime_off_exposure": 0.5}, cost={"cash_yield_share": 0.0}))),
    ):
        sens[name] = _row(name, res, lab, bench)
    report["sensitivity"] = sens

    # Beyan edilmiş denemeler.
    trials = declared_trials(base)
    rows, excess_cash, active, hybrid_results = [], {}, {}, {}
    ew_ret = bench["ew"].pct_change().fillna(0.0)
    for name, cfg in trials.items():
        res = primary if name == "birincil" else lab.run(cfg)
        if name == "birincil" or name in HYBRID_TRIALS:
            hybrid_results[name] = res
        b = lab.benchmarks(cfg)
        rows.append(_row(name, res, lab, b))
        r = res.equity.pct_change().fillna(0.0)
        excess_cash[name] = r - rfd
        active[name] = r - b["ew"].pct_change().fillna(0.0).reindex(r.index).fillna(0.0)
    table = pd.DataFrame(rows).set_index("deneme")
    report["trials"] = table.round(4).to_dict(orient="index")

    x = (ret - rfd).to_numpy()
    a = (ret - ew_ret.reindex(ret.index).fillna(0.0)).to_numpy()
    ex_df, ac_df = pd.DataFrame(excess_cash), pd.DataFrame(active)
    sr_trials = (ex_df.mean() / ex_df.std()).to_numpy()
    ir_trials = (ac_df.mean() / ac_df.std()).to_numpy()
    report["selection_bias"] = {
        "n_trials": len(trials),
        "sharpe_annual": float(x.mean() / x.std(ddof=1) * np.sqrt(TRADING_DAYS)),
        "psr_vs_cash": stats.probabilistic_sharpe(x, 0.0),
        "dsr_vs_cash": stats.deflated_sharpe(x, sr_trials),
        "expected_max_sharpe_annual": stats.expected_max_sharpe(float(np.var(sr_trials, ddof=1)), len(trials))
        * np.sqrt(TRADING_DAYS),
        "psr_active": stats.probabilistic_sharpe(a, 0.0),
        "dsr_active": stats.deflated_sharpe(a, ir_trials),
        "pbo_vs_cash": stats.cscv_pbo(ex_df, 10),
        "pbo_active": stats.cscv_pbo(ac_df, 10),
        "primary_rank_by_sharpe": int((table["sharpe"] > table.at["birincil", "sharpe"]).sum() + 1),
    }

    report["hybrid"] = hybrid_report(lab, base, hybrid_results, sr_trials)

    if live is not None:
        live_res = lab.run(live)
        live_bench = lab.benchmarks(live)
        lx = (live_res.equity.pct_change().fillna(0.0) - rfd).to_numpy()
        report["live"] = {
            "vs_ew": summarize(live_res.equity, ds.rf, live_bench["ew"]),
            "turnover": live_res.turnover(),
            "avg_invested": float(live_res.invested.mean()),
            "dsr_vs_cash": stats.deflated_sharpe(lx, sr_trials),
            "periods": {p: cagr(live_res.equity.loc[a:b]) for p, (a, b) in PERIODS.items()
                        if len(live_res.equity.loc[a:b]) > 60},
            "settings": {
                "w_technical": live.signal.w_technical, "trend_gate": live.portfolio.trend_gate,
                "regime": live.portfolio.regime, "regime_off_exposure": live.portfolio.regime_off_exposure,
            },
        }
        series["canli"] = live_res.equity / live_res.equity.iloc[0]
        series["canli_usd"] = deflate(live_res.equity, usd)
        report["yearly"] = yearly_returns(series).round(4).to_dict(orient="index")

    frame = pd.DataFrame({"s": ret.to_numpy(), "rf": rfd.to_numpy(), "b": ew_ret.reindex(ret.index).fillna(0.0).to_numpy()})
    ann = TRADING_DAYS
    report["bootstrap"] = {
        "sharpe": stats.bootstrap_ci(
            frame, lambda f: (f["s"] - f["rf"]).mean() / (f["s"] - f["rf"]).std() * np.sqrt(ann), n_boot, seed=seed),
        "cash_ustu_yillik": stats.bootstrap_ci(frame, lambda f: (f["s"] - f["rf"]).mean() * ann, n_boot, seed=seed + 1),
        "ew_ustu_yillik": stats.bootstrap_ci(frame, lambda f: (f["s"] - f["b"]).mean() * ann, n_boot, seed=seed + 2),
        "max_dd": stats.bootstrap_ci(
            frame, lambda f: float(((1 + f["s"]).cumprod() / (1 + f["s"]).cumprod().cummax() - 1).min()),
            max(n_boot // 4, 200), seed=seed + 3),
    }

    # Rastgele portföy testi: aynı evren, aynı kurallar, karıştırılmış sıralar.
    # Her rastgele portföyde hisselere bir kez rastgele puan verilir ve koşu boyunca sabit
    # tutulur: sıralar gerçek puanlar gibi kalıcıdır, devir hızı (dolayısıyla masraf)
    # stratejiden yüksek olmaz. Her ay yeniden karıştırmak rastgele portföylere yılda ~%4
    # fazladan masraf yükler ve testi stratejinin lehine çarpıtırdı.
    rng = np.random.default_rng(seed)
    rand_cagr, rand_sharpe, rand_turnover = [], [], []

    def fixed_random_scorer():
        score = pd.Series(rng.random(len(lab.symbols)), index=lab.symbols)

        def scorer(_day, tbl):
            out = tbl.copy()
            out["score"] = score.reindex(out.index).to_numpy()
            out = out.assign(_s=out.index).sort_values(["score", "_s"], ascending=[False, True]).drop(columns="_s")
            out["rank"] = np.arange(1, len(out) + 1)
            return out

        return scorer

    for _ in range(n_random):
        r = lab.run(base, scorer=fixed_random_scorer())
        rand_turnover.append(r.turnover())
        s = summarize(r.equity, ds.rf)
        rand_cagr.append(s["cagr"])
        rand_sharpe.append(s["sharpe"])
    p = report["primary"]["vs_ew"]
    report["random_portfolios"] = {
        "n": n_random,
        "cagr_median": float(np.median(rand_cagr)) if rand_cagr else float("nan"),
        "cagr_p05": float(np.quantile(rand_cagr, 0.05)) if rand_cagr else float("nan"),
        "cagr_p95": float(np.quantile(rand_cagr, 0.95)) if rand_cagr else float("nan"),
        "strategy_cagr_percentile": stats.percentile_of(p["cagr"], np.array(rand_cagr)),
        "strategy_sharpe_percentile": stats.percentile_of(p["sharpe"], np.array(rand_sharpe)),
        "turnover_median": float(np.median(rand_turnover)) if rand_turnover else float("nan"),
    }
    report["_series"] = {k: v for k, v in series.items()}
    report["_primary"] = primary
    return report


def report_years(equity: pd.Series) -> float:
    return (equity.index[-1] - equity.index[0]).days / 365.25
