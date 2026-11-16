"""Günlük çalıştırıcının uçtan uca testi: sentetik önbellek, ağ erişimi yok."""
import copy
import datetime as dt
import json
import shutil

import pandas as pd
import pytest

from bistbot import cli
from bistbot.config import Config
from bistbot.data.bulletin import DAY_COLUMNS
from bistbot.live import notify, runner
from bistbot.live.runner import _map_symbols, can_issue_orders, expected_session, notification_digest, run_daily
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
        ni = float(ds.ni_annual[sym].iloc[0])
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


def evening(day) -> dt.datetime:
    """O günün kapanışından sonra (bülten yayımlanmış) çalışma anı."""
    return dt.datetime.combine(pd.Timestamp(day).date(), dt.time(19, 17))


def test_first_run_starts_portfolio_and_issues_fundable_whole_lot_orders(live):
    stores, state_path, ds = live
    day = ds.dates[320]
    res = run_daily(stores, state_path, Config(), evening(day), sync=False)
    p = res.payload
    assert res.decided and p["as_of"] == str(day.date()) and p["equity"] == 100_000
    assert len(p["orders"]) == 20 and all(o["side"] == "buy" and o["lots"] >= 1 for o in p["orders"])
    for o in p["orders"]:
        assert o["ref_price"] < o["limit_price"] <= o["ref_price"] * 1.03 + 0.01
    # Emirlerin tamamı, limit fiyattan ve masraflarıyla eldeki paraya sığar.
    assert sum(o["lots"] * o["limit_price"] for o in p["orders"]) * 1.0031 <= 100_000
    state = BotState.load(state_path)
    assert state.start == str(day.date()) and state.capital == 100_000 and state.settings["cost"]["commission"] == 0.002
    assert list(state.decisions) == [str(day.date())] and len(state.decisions[str(day.date())]) == 20
    text = notify.format_message(p)
    assert "SONRAKİ SEANS AÇILIŞI İÇİN EMİRLER" in text and str(day.day) in text


def test_rerun_is_idempotent_and_paper_fills_equal_the_ticket(live):
    stores, state_path, ds = live
    d0, d1 = ds.dates[320], ds.dates[321]
    first = run_daily(stores, state_path, Config(), evening(d0), sync=False)
    again = run_daily(stores, state_path, Config(), evening(d0), sync=False)
    assert _strip(first.payload) == _strip(again.payload) and not again.decided
    assert notification_digest(first.payload) == notification_digest(again.payload)
    nxt = run_daily(stores, state_path, Config(), evening(d1), sync=False)
    p = nxt.payload
    assert not nxt.decided and p["orders"] == [] and len(p["positions"]) == 20
    ticket = {o["symbol"]: o["lots"] for o in first.payload["orders"]}
    fills = {f["symbol"]: f["lots"] for f in p["fills_today"]}
    assert fills == ticket  # kâğıt portföy tam olarak fişteki lotları aldı
    assert {x["symbol"]: x["lots"] for x in p["positions"]} == ticket
    for f in p["fills_today"]:
        assert f["price"] == pytest.approx(ds.panel.open.at[d1, f["symbol"]], abs=1e-3)
    assert p["equity"] == pytest.approx(sum(x["value"] for x in p["positions"]) + p["cash"], rel=1e-6)
    assert p["cash"] >= 0 and p["costs_paid"] > 0
    assert notification_digest(p) != notification_digest(first.payload)
    assert len(BotState.load(state_path).reported) == 20


def test_exit_tickets_never_exceed_the_lots_the_user_holds(live):
    stores, state_path, ds = live
    cfg = Config()
    holdings: dict[str, int] = {}
    pending: list[dict] = []
    for i in range(300, N_DAYS):
        res = run_daily(stores, state_path, cfg, evening(ds.dates[i]), sync=False)
        p = res.payload
        # Kullanıcı, önceki akşamın fişini bu sabah aynen uyguladı.
        filled = {(f["symbol"], f["side"]): f["lots"] for f in p["fills_today"]}
        for o in pending:
            lots = filled.get((o["symbol"], o["side"]), 0)
            if o["side"] == "sell":
                assert o["lots"] <= holdings.get(o["symbol"], 0)  # elde olandan fazlası istenmez
                holdings[o["symbol"]] = holdings.get(o["symbol"], 0) - lots
            else:
                assert lots == o["lots"]  # sentetik veride tüm alımlar gerçekleşir
                holdings[o["symbol"]] = holdings.get(o["symbol"], 0) + lots
        holdings = {s: n for s, n in holdings.items() if n}
        assert holdings == {x["symbol"]: x["lots"] for x in p["positions"]}
        pending = p["orders"]
    assert len(BotState.load(state_path).decisions) >= 2


def test_no_decision_while_the_next_session_is_already_open(live):
    stores, state_path, ds = live
    next_day = ds.dates[321]
    # Bültenler yalnızca "last" gününe kadar var; ertesi gün öğleden sonra elle çalıştırma.
    for d in ds.dates[321:]:
        stores.bulletins.day_path(d.date()).unlink()
    midday = dt.datetime.combine(next_day.date(), dt.time(14, 0))
    res = run_daily(stores, state_path, Config(), midday, sync=False)
    assert res.payload is None and not res.decided and "kuruldu" in res.message
    assert not state_path.exists()  # hiçbir şey başlatılmadı
    # Aynı gün açılıştan önce çalışsaydı karar verilebilirdi ve emirler o günün açılışı içindir.
    early = dt.datetime.combine(next_day.date(), dt.time(8, 43))
    res = run_daily(stores, state_path, Config(), early, sync=False)
    assert res.decided and res.payload["next_session"] == str(next_day.date())


def test_timing_rules():
    fri, sat, mon = dt.date(2026, 11, 13), dt.date(2026, 11, 14), dt.date(2026, 11, 16)
    at = lambda d, h, m=0: dt.datetime.combine(d, dt.time(h, m))  # noqa: E731
    assert can_issue_orders(fri, at(fri, 19, 17), False)[0]
    assert can_issue_orders(fri, at(sat, 12), False)[0]
    assert can_issue_orders(fri, at(mon, 8, 43), False)[0]
    assert not can_issue_orders(fri, at(mon, 9, 45), False)[0]
    assert not can_issue_orders(fri, at(mon, 18, 15), True)[0]  # endeks geldi, bülten gelmedi
    assert expected_session(fri, at(fri, 19, 17)) == mon
    assert expected_session(fri, at(mon, 8, 43)) == mon
    assert expected_session(fri, at(sat, 12)) == mon


def test_missed_rebalance_day_is_decided_late(live):
    stores, state_path, ds = live
    cfg = Config()
    start = ds.dates[300]
    run_daily(stores, state_path, cfg, evening(start), sync=False)
    month_starts = [d for d in ds.dates[301:] if d.month != ds.dates[ds.dates.get_loc(d) - 1].month]
    scheduled = month_starts[0]
    late = ds.dates[ds.dates.get_loc(scheduled) + 2]  # bot ay başında çalışmadı, iki gün sonra çalıştı
    res = run_daily(stores, state_path, cfg, evening(late), sync=False)
    assert res.decided and res.payload["last_decision"] == str(late.date())
    assert str(scheduled.date()) not in BotState.load(state_path).decisions
    after = run_daily(stores, state_path, cfg, evening(ds.dates[ds.dates.get_loc(late) + 1]), sync=False)
    assert not after.decided


def test_unhealthy_data_postpones_then_heals_and_notification_changes(live):
    stores, state_path, ds = live
    backup = stores.root / "fin-backup"
    shutil.copytree(stores.isy.root / "financials", backup)
    for sym in ds.symbols:  # bilançolar yok: değer/kârlılık hesaplanamaz
        stores.isy.path("financials", sym).unlink()
    day = ds.dates[320]
    bad = run_daily(stores, state_path, Config(), evening(day), sync=False)
    assert not bad.decided and bad.payload["orders"] == []
    assert any("ertelendi" in w for w in bad.warnings) and BotState.load(state_path).decisions == {}
    # Aynı akşamın yedek çalışmasında veri tamam: karar verilir ve bildirim özeti değişir
    # (yani emir listesi kullanıcıya mutlaka gönderilir).
    shutil.rmtree(stores.isy.root / "financials")
    shutil.copytree(backup, stores.isy.root / "financials")
    good = run_daily(stores, state_path, Config(), evening(day), sync=False)
    assert good.decided and len(good.payload["orders"]) == 20
    assert notification_digest(good.payload) != notification_digest(bad.payload)


def test_missing_bulletin_of_a_decision_day_stops_the_run(live):
    stores, state_path, ds = live
    d0 = ds.dates[320]
    run_daily(stores, state_path, Config(), evening(d0), sync=False)
    stores.bulletins.day_path(d0.date()).unlink()
    with pytest.raises(runner.DataNotReady):
        run_daily(stores, state_path, Config(), evening(ds.dates[325]), sync=False)
    assert list(BotState.load(state_path).decisions) == [str(d0.date())]  # durum bozulmadı


def test_session_missing_from_bulletins_but_present_in_index_is_detected(live):
    stores, state_path, ds = live
    ds.xu100.rename("value").rename_axis("date").to_csv(stores.macro.index_path("XU100"))
    stores.bulletins.day_path(ds.dates[310].date()).unlink()
    with pytest.raises(runner.DataNotReady, match="bülten eksik"):
        run_daily(stores, state_path, Config(), evening(ds.dates[320]), sync=False)


def test_missing_data_for_a_held_stock_blocks_new_decisions(live):
    stores, state_path, ds = live
    cfg = Config()
    first = run_daily(stores, state_path, cfg, evening(ds.dates[300]), sync=False)
    held = first.payload["orders"][0]["symbol"]
    month_start = next(d for d in ds.dates[302:] if d.month != ds.dates[ds.dates.get_loc(d) - 1].month)
    # Eldeki hissenin geçmiş dosyası bozuldu (son günleri yok ve arada özsermaye bayrağı var gibi).
    hist = pd.read_csv(stores.isy.path("history", held))
    hist.iloc[: 290].to_csv(stores.isy.path("history", held), index=False)
    flag_day = ds.dates[295]
    path = stores.bulletins.day_path(flag_day.date())
    rows = pd.read_csv(path, dtype={"corp_action": str}, keep_default_na=False)
    rows.loc[rows["symbol"] == held, "corp_action"] = "06"
    rows.to_csv(path, index=False, compression="gzip")
    res = run_daily(stores, state_path, cfg, evening(month_start), sync=False)
    assert not res.decided and any("ertelendi" in w for w in res.warnings)
    assert any("katsayısı güncellenemedi" in w for w in res.warnings)


def test_settings_are_frozen_at_start_but_capital_and_costs_edits_do_not_rewrite_history(live):
    stores, state_path, ds = live
    run_daily(stores, state_path, Config(), evening(ds.dates[300]), sync=False)
    base = run_daily(stores, state_path, Config(), evening(ds.dates[310]), sync=False).payload
    edited = Config().with_overrides(cost={"commission": 0.0005}, capital=250_000, portfolio={"rebalance_band": 0.01})
    after = run_daily(stores, state_path, edited, evening(ds.dates[310]), sync=False)
    assert _strip(after.payload) == _strip(base)
    assert not any("yeniden hesaplandı" in w for w in after.warnings)


def test_replay_change_of_reported_trades_is_flagged(live):
    stores, state_path, ds = live
    run_daily(stores, state_path, Config(), evening(ds.dates[300]), sync=False)
    run_daily(stores, state_path, Config(), evening(ds.dates[305]), sync=False)
    state = BotState.load(state_path)
    state.reported[0][3] += 7  # kullanıcıya daha önce farklı bir lot bildirilmiş olsun
    state.save(state_path)
    res = run_daily(stores, state_path, Config(), evening(ds.dates[306]), sync=False)
    assert any("yeniden hesaplandı" in w for w in res.warnings)
    # Uyarı bir kez verilir; yeni kayıt esas alınır.
    again = run_daily(stores, state_path, Config(), evening(ds.dates[307]), sync=False)
    assert not any("yeniden hesaplandı" in w for w in again.warnings)


def test_not_enough_history_raises(tmp_path):
    ds = make_dataset(n_days=120, n_symbols=20, start="2024-01-01")
    stores = write_cache(tmp_path / "cache", ds)
    with pytest.raises(runner.DataNotReady):
        run_daily(stores, tmp_path / "bot.json", Config(), evening(ds.dates[-1]), sync=False)


def test_old_codes_in_saved_decisions_follow_renames():
    w = _map_symbols({"KOZAL": 0.05, "THYAO": 0.05}, {"KOZAL": "TRALT"})
    assert w.to_dict() == {"TRALT": 0.05, "THYAO": 0.05} and list(w.index) == ["TRALT", "THYAO"]


def test_state_roundtrip_keeps_decision_order_and_guards_version(tmp_path):
    path = tmp_path / "bot.json"
    assert BotState.load(path) == BotState()
    BotState(start="2026-01-02", capital=5e4, decisions={"2026-01-02": {"ZZZ": 0.05, "AAA": 0.05}}).save(path)
    loaded = BotState.load(path)
    assert list(loaded.decisions["2026-01-02"]) == ["ZZZ", "AAA"] and loaded.reported == []
    path.write_text(json.dumps({"version": 1, "start": "2026-01-02", "decisions": {}}), encoding="utf-8")
    assert BotState.load(path).start == "2026-01-02"  # eski sürüm dosyası okunur
    path.write_text(json.dumps({"version": 99}), encoding="utf-8")
    with pytest.raises(ValueError):
        BotState.load(path)


def test_empty_vendor_answer_never_overwrites_good_cache(tmp_path):
    from bistbot.data.isystore import IsyStore

    class EmptyClient:
        def get(self, url, params=None, **kw):
            class R:
                content = b'{"ok": true, "value": []}'
            return R()

    store = IsyStore(tmp_path / "isy", EmptyClient())
    good = pd.DataFrame({"date": ["2026-01-02"], "raw_close": [10.0], "adj_close": [10.0], "raw_vwap": [10.0],
                         "raw_low": [10.0], "raw_high": [10.0], "value": [1.0], "xu100": [1.0], "usdtry": [1.0],
                         "mcap": [1.0], "ff_mcap": [1.0]})
    good.to_csv(store.path("history", "GARAN"), index=False)
    stats = store.sync("history", ["GARAN"], dt.date(2026, 1, 5), force=True, progress_every=0)
    assert stats == {"fetched": 0, "empty": 0, "failed": 1}
    assert len(store.load("history", "GARAN")) == 1  # eski veri duruyor
    # Hiç dosyası olmayan sembolde boş yanıt "boş" olarak kaydedilir.
    assert store.sync("history", ["YENI"], dt.date(2026, 1, 5), force=True, progress_every=0)["empty"] == 1


def test_cli_daily_writes_dashboard_json_and_notifies_on_new_content(live, tmp_path, capsys, monkeypatch):
    stores, state_path, ds = live
    sent = []
    monkeypatch.setattr(notify, "send_telegram", lambda text, timeout=30.0: sent.append(text) or True)
    shutil.copytree(stores.isy.root, stores.root / "isy-live")  # günlük çalışma ayrı klasör kullanır
    web = tmp_path / "web"
    cfg_file = tmp_path / "ayar.toml"
    cfg_file.write_text("capital = 250000\n", encoding="utf-8")
    day = str(ds.dates[320].date())
    argv = ["--onbellek", str(stores.root), "--ayar", str(cfg_file), "gunluk", "--durum", str(state_path),
            "--web", str(web), "--bugun", day, "--esitleme-yok"]
    assert cli.main(argv) == 0
    data = json.loads((web / "latest.json").read_text(encoding="utf-8"))
    assert data["capital"] == 250000 and len(data["orders"]) == 20 and len(data["top"]) == 40
    assert "ledger_all" not in data and "BIST Bot" in capsys.readouterr().out and len(sent) == 1
    # Aynı gün yeniden çalıştırmak dosyayı değiştirmez ve ikinci bildirim göndermez.
    before = (web / "latest.json").read_bytes()
    assert cli.main(argv) == 0
    assert (web / "latest.json").read_bytes() == before and len(sent) == 1
    # --deneme hiçbir şey yazmaz.
    other = tmp_path / "other.json"
    cli.main(["--onbellek", str(stores.root), "gunluk", "--durum", str(other), "--web", str(tmp_path / "w2"),
              "--bugun", day, "--esitleme-yok", "--deneme"])
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


def test_stale_index_series_blocks_new_decision(live):
    """Endeks verisi günlerdir güncellenmemişse bayat endeksle karar verilmez."""
    stores, state_path, ds = live
    stale = ds.xu100.iloc[:300]  # son 45 seans eksik
    stale.rename("value").rename_axis("date").to_csv(stores.macro.index_path("XU100"))
    res = run_daily(stores, state_path, Config(), evening(ds.dates[330]), sync=False)
    assert not res.decided and any("endeks" in w for w in res.warnings)
    ds.xu100.rename("value").rename_axis("date").to_csv(stores.macro.index_path("XU100"))
    assert run_daily(stores, state_path, Config(), evening(ds.dates[330]), sync=False).decided


def test_enabling_hybrid_later_keeps_past_decisions_and_changes_only_future_ones(live):
    """Hibrit mod sonradan açılırsa dondurulmuş kararlar ve geçmiş kâğıt işlemler değişmez."""
    stores, state_path, ds = live
    first = ds.dates[320]
    base = run_daily(stores, state_path, Config(), evening(first), sync=False)
    assert base.decided
    frozen = dict(BotState.load(state_path).decisions)
    hybrid = Config().with_overrides(signal={"w_technical": 1.0}, portfolio={"trend_gate": "entry_exit"})
    later = ds.dates[330]
    plain_run = run_daily(stores, state_path, Config(), evening(later), sync=False, save=False)
    hybrid_run = run_daily(stores, state_path, hybrid, evening(later), sync=False, save=False)
    assert BotState.load(state_path).decisions == frozen
    # Aynı dondurulmuş kararlarla aynı kâğıt portföy: değer, pozisyonlar ve işlemler birebir aynı.
    a, b = plain_run.payload, hybrid_run.payload
    assert a["equity"] == b["equity"] and a["ledger"] == b["ledger"]
    assert [(p["symbol"], p["lots"]) for p in a["positions"]] == [(p["symbol"], p["lots"]) for p in b["positions"]]
    assert b["settings"]["w_technical"] == 1.0 and b["settings"]["trend_gate"] == "entry_exit"
    # Panel verisi teknik görünümü taşır.
    top = b["top"][0]
    assert {"fundamental", "tech", "technical", "uptrend", "rsi", "trend", "macd_up"} <= set(top)
    assert all("uptrend" in p for p in b["positions"])


def test_live_payload_is_a_valid_order_ticket(live):
    """Bulut tarafının ürettiği fiş, emir katmanının sıkı doğrulamasından geçer."""
    from bistbot.exec.guard import check_ticket
    from bistbot.exec.runner import IST
    from bistbot.exec.settings import Limits
    from bistbot.exec.ticket import parse_ticket

    stores, state_path, ds = live
    day = ds.dates[320]
    payload = run_daily(stores, state_path, Config(), evening(day), sync=False).payload
    ticket = parse_ticket(payload)
    assert len(ticket.orders) == 20 and ticket.session > ticket.as_of
    made = dt.datetime.fromisoformat(payload["generated_at"])
    now = dt.datetime.combine(ticket.session, dt.time(9, 20), IST)
    # Üretim zamanı gerçek saatten geldiği için yalnızca tutar/fiyat sınırları sınanır.
    problems = [p for p in check_ticket(ticket, now, Limits(azami_fis_yasi_saat=1e9)) if "gelecekte" not in p]
    assert problems == [], problems
    assert made.tzinfo is not None
