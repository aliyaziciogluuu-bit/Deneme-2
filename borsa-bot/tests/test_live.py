"""Günlük çalıştırıcının uçtan uca testi: sentetik önbellek, ağ erişimi yok."""
import copy
import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

from bistbot import cli
from bistbot.config import Config
from bistbot.data.bulletin import DAY_COLUMNS
from bistbot.live import notify, runner
from bistbot.live.runner import _map_symbols, run_daily
from bistbot.live.state import BotState
from bistbot.pipeline import open_stores
from conftest import make_dataset

N_SYMBOLS = 70
N_DAYS = 345


def write_cache(root, ds):
    """Sentetik veri setini gerçek önbellek biçiminde diske yazar."""
    stores = open_stores(root)
    p = ds.panel
    for day in ds.dates:
        rows = pd.DataFrame(
            {
                "date": day, "symbol": list(ds.symbols), "name": [f"{s} A.S." for s in ds.symbols],
                "market": p.market.loc[day].to_numpy(), "method": p.method.loc[day].to_numpy(),
                "bist100": p.bist100.loc[day].astype(int).to_numpy(), "bist30": 0, "gross": 0, "suspended": 0,
                "short_ok": 1, "corp_action": "",
                **{k: getattr(p, k).loc[day].to_numpy() for k in ("prev_close", "open", "high", "low", "close", "vwap", "value")},
                "volume": 1e6, "trades": 100,
            }
        )[DAY_COLUMNS]
        path = stores.bulletins.day_path(day.date())
        path.parent.mkdir(parents=True, exist_ok=True)
        rows.to_csv(path, index=False, compression="gzip")
    for sym in ds.symbols:
        close = p.close[sym]
        pd.DataFrame(
            {"date": ds.dates.strftime("%Y-%m-%d"), "raw_close": close.to_numpy(), "adj_close": close.to_numpy(),
             "raw_vwap": close.to_numpy(), "raw_low": close.to_numpy(), "raw_high": close.to_numpy(), "value": 1e8,
             "xu100": ds.xu100.to_numpy(), "usdtry": ds.usdtry.to_numpy(),
             "mcap": (close * 1e8).to_numpy(), "ff_mcap": (close * 5e7).to_numpy()}
        ).to_csv(stores.isy.path("history", sym), index=False)
        pd.DataFrame(columns=["date", "type_code", "type_name", "rights_pct", "bonus_pct", "div_gross_pct",
                              "div_net_pct", "price_factor"]).to_csv(stores.isy.path("actions", sym), index=False)
        eq = float(ds.equity[sym].iloc[0])
        ni = float(ds.ni_ttm[sym].iloc[0])
        years = sorted({d.year for d in ds.dates} | {ds.dates[0].year - 1})
        fin = [{"year": y, "period": m, "group": "UFRS_K" if ds.is_financial[sym] else "XI_29", "equity": eq,
                "net_income": ni * m / 12, "total_assets": eq * 3, "sales": eq, "gross_profit": eq * 0.2}
               for y in years for m in (3, 6, 9, 12)]
        pd.DataFrame(fin).to_csv(stores.isy.path("financials", sym), index=False)
    ds.rf.rename("rf").rename_axis("date").to_csv(stores.macro.rf_path)
    return stores


@pytest.fixture()
def live(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "MIN_BULLETIN_ROWS", 50)
    monkeypatch.setattr(runner, "MIN_UNIVERSE", 40)
    ds = make_dataset(n_days=N_DAYS, n_symbols=N_SYMBOLS, start="2024-01-01")
    stores = write_cache(tmp_path / "cache", ds)
    return stores, tmp_path / "state" / "bot.json", ds


def _strip(payload):
    out = copy.deepcopy(payload)
    out.pop("generated_at")
    return out


def test_first_run_starts_portfolio_and_issues_buy_orders(live):
    stores, state_path, ds = live
    day = ds.dates[320]
    res = run_daily(stores, state_path, Config(), day.date(), sync=False)
    p = res.payload
    assert res.decided and p["as_of"] == str(day.date()) and p["equity"] == 100_000
    assert len(p["orders"]) == 20 and all(o["side"] == "buy" and o["lots"] > 0 for o in p["orders"])
    for o in p["orders"]:
        assert o["limit_price"] <= o["ref_price"] * 1.03 + 0.01 and o["limit_price"] > o["ref_price"]
        assert o["value"] <= 5_000 + 1e-6  # eşit ağırlık: sermayenin %5'i, lot aşağı yuvarlanır
    state = BotState.load(state_path)
    assert state.start == str(day.date()) and state.capital == 100_000
    assert list(state.decisions) == [str(day.date())] and len(state.decisions[str(day.date())]) == 20
    assert "AÇILIŞI İÇİN EMİRLER" in notify.format_message(p)


def test_rerun_is_idempotent_and_next_day_fills_at_open(live):
    stores, state_path, ds = live
    d0, d1 = ds.dates[320], ds.dates[321]
    first = run_daily(stores, state_path, Config(), d0.date(), sync=False)
    again = run_daily(stores, state_path, Config(), d0.date(), sync=False)
    assert _strip(first.payload) == _strip(again.payload) and not again.decided
    nxt = run_daily(stores, state_path, Config(), d1.date(), sync=False)
    p = nxt.payload
    assert not nxt.decided and p["orders"] == [] and len(p["positions"]) == 20 and len(p["fills_today"]) == 20
    for f in p["fills_today"]:
        assert f["price"] == pytest.approx(ds.panel.open.at[d1, f["symbol"]], abs=1e-3)
    assert p["equity"] == pytest.approx(sum(x["value"] for x in p["positions"]) + p["cash"], rel=1e-6)
    assert p["costs_paid"] > 0 and abs(p["total_return"]) < 0.05
    assert BotState.load(state_path).decisions.keys() == BotState.load(state_path).decisions.keys()


def test_missed_rebalance_day_is_decided_late(live):
    stores, state_path, ds = live
    cfg = Config()
    start = ds.dates[300]
    run_daily(stores, state_path, cfg, start.date(), sync=False)
    month_starts = [d for d in ds.dates[301:] if d.month != ds.dates[ds.dates.get_loc(d) - 1].month]
    scheduled = month_starts[0]
    late = ds.dates[ds.dates.get_loc(scheduled) + 2]  # bot ay başında çalışmadı, iki gün sonra çalıştı
    res = run_daily(stores, state_path, cfg, late.date(), sync=False)
    assert res.decided and res.payload["last_decision"] == str(late.date())
    assert str(scheduled.date()) not in BotState.load(state_path).decisions
    # Bir sonraki gün yeni karar yok.
    after = run_daily(stores, state_path, cfg, ds.dates[ds.dates.get_loc(late) + 1].date(), sync=False)
    assert not after.decided


def test_unhealthy_data_postpones_decision_without_touching_state(live):
    stores, state_path, ds = live
    for sym in ds.symbols:  # bilançolar yok: değer/kârlılık hesaplanamaz
        stores.isy.path("financials", sym).unlink()
    res = run_daily(stores, state_path, Config(), ds.dates[320].date(), sync=False)
    assert not res.decided and res.payload["orders"] == []
    assert any("ertelendi" in w for w in res.warnings)
    assert BotState.load(state_path).decisions == {}


def test_not_enough_history_raises(tmp_path):
    ds = make_dataset(n_days=120, n_symbols=20, start="2024-01-01")
    stores = write_cache(tmp_path / "cache", ds)
    with pytest.raises(runner.DataNotReady):
        run_daily(stores, tmp_path / "bot.json", Config(), ds.dates[-1].date(), sync=False)


def test_old_codes_in_saved_decisions_follow_renames():
    w = _map_symbols({"KOZAL": 0.05, "THYAO": 0.05}, {"KOZAL": "TRALT"})
    assert w.to_dict() == {"TRALT": 0.05, "THYAO": 0.05}


def test_state_roundtrip_and_version_guard(tmp_path):
    path = tmp_path / "bot.json"
    assert BotState.load(path) == BotState()
    BotState(start="2026-01-02", capital=5e4, decisions={"2026-01-02": {"A": 0.05}}, notified="2026-01-02").save(path)
    assert BotState.load(path).decisions == {"2026-01-02": {"A": 0.05}}
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")
    with pytest.raises(ValueError):
        BotState.load(path)


def test_cli_daily_writes_dashboard_json(live, tmp_path, capsys, monkeypatch):
    stores, state_path, ds = live
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    web = tmp_path / "web"
    cfg_file = tmp_path / "ayar.toml"
    cfg_file.write_text("capital = 250000\n", encoding="utf-8")
    code = cli.main(["--onbellek", str(stores.root), "--ayar", str(cfg_file), "gunluk", "--durum", str(state_path),
                     "--web", str(web), "--bugun", str(ds.dates[320].date()), "--esitleme-yok"])
    assert code == 0
    data = json.loads((web / "latest.json").read_text(encoding="utf-8"))
    assert data["capital"] == 250000 and len(data["orders"]) == 20 and len(data["top"]) == 40
    assert "BIST Bot" in capsys.readouterr().out
    # Aynı gün yeniden çalıştırmak dosyayı değiştirmez (yalnızca üretim zamanı farklı olurdu).
    before = (web / "latest.json").read_bytes()
    cli.main(["--onbellek", str(stores.root), "--ayar", str(cfg_file), "gunluk", "--durum", str(state_path),
              "--web", str(web), "--bugun", str(ds.dates[320].date()), "--esitleme-yok"])
    assert (web / "latest.json").read_bytes() == before
    # --deneme hiçbir şey yazmaz
    other = tmp_path / "other.json"
    cli.main(["--onbellek", str(stores.root), "gunluk", "--durum", str(other), "--web", str(tmp_path / "w2"),
              "--bugun", str(ds.dates[320].date()), "--esitleme-yok", "--deneme"])
    assert not other.exists() and not (tmp_path / "w2").exists()


def test_notification_text_formatting_and_splitting(monkeypatch):
    assert notify.tl(1234567.891) == "1.234.568" and notify.tl(12.5, 2) == "12,50"
    assert notify.pct(0.0123) == "+1,2%" and notify.pct(-0.5) == "-50,0%" and notify.pct(None) == "–"
    assert notify.tr_date("2026-11-13") == "13.11.2026"
    parts = notify.split_message("\n".join(["x" * 90] * 100), limit=1000)
    assert all(len(p) <= 1000 for p in parts) and "".join(parts).count("x") == 9000
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert notify.send_telegram("merhaba") is False and not notify.telegram_configured()
