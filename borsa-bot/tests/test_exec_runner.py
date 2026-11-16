"""Emir çalıştırıcısı: onay, zamanlama, tekrar göndermeme, durdurma, ikinci tur."""
import datetime as dt
import json

import pytest
import requests

from bistbot.exec import app
from bistbot.exec.dryrun import DryRunBroker
from bistbot.exec.journal import Journal
from bistbot.exec.runner import (IST, AlreadyRunning, RunLock, journal_path, load_state, run_batch, save_state,
                                 send_window)
from bistbot.exec.settings import ExecSettings, Limits, MatriksSettings, Schedule, SettingsError, TelegramSettings
from exec_helpers import SESSION, TOKEN, FakeClock, ScriptedBroker, fake_telegram, payload, settings, ticket
from matriks_mock import MockMatriks

HELD = {"GARAN": 40, "AKBNK": 70}


def run(tmp_path, broker=None, reply="approve", clock=None, mod="gercek", tk=None, **kw):
    clock = clock or FakeClock()
    s = settings(tmp_path, mod=mod, **kw)
    tg, http = fake_telegram(clock, reply)
    broker = broker or ScriptedBroker(HELD)
    journal = Journal(journal_path(s))
    result = run_batch(s, tk or ticket(), broker, tg, journal, clock)
    return result, broker, http, journal, clock


def events(journal, key=None):
    return [e["event"] for e in journal.entries() if key is None or e.get("key") == key]


def test_happy_path_sends_after_approval_in_opening_window(tmp_path):
    result, broker, http, journal, clock = run(tmp_path)
    assert result.status == "done"
    assert [(o.symbol, o.side, o.lots) for o in broker.placed] == [("GARAN", "sell", 40), ("THYAO", "buy", 15), ("ASELS", "buy", 50)]
    # 09:20'de onaylandı ama emirler açılış seansı penceresi (09:40:15) beklenerek gönderildi.
    first_sent = next(e for e in journal.entries() if e["event"] == "sending")
    assert events(journal).index("approved") < events(journal).index("sending")
    assert clock.now().time() >= dt.time(9, 40, 15)
    assert "GERÇEK EMİR ONAYI" in http.sent[0] and "SAT GARAN" in http.sent[0] and "…456" in http.sent[0]
    assert "Emir raporu" in http.sent[-1] and "gerçekleşti 40/40" in http.sent[-1]
    assert journal.batch_done(ticket().digest) and first_sent["digest"] == ticket().digest
    assert broker.closed


def test_nothing_is_sent_without_approval(tmp_path):
    for reply, status in (("reject", "rejected"), ("none", "timeout"), ("wrong_user", "timeout")):
        result, broker, http, journal, _ = run(tmp_path / reply, reply=reply)
        assert result.status == status and broker.placed == []
        assert "sending" not in events(journal) and "GÖNDERİLMEDİ" in http.sent[-1]


def test_intent_is_journaled_before_the_order_leaves(tmp_path):
    seen = {}

    class Spy(ScriptedBroker):
        def place(self, order):
            seen[order.key] = [e["event"] for e in Journal(spy_path).entries() if e.get("key") == order.key]
            return super().place(order)

    spy_path = journal_path(settings(tmp_path, mod="gercek"))
    run(tmp_path, broker=Spy(HELD))
    assert all(v == ["sending"] for v in seen.values()) and len(seen) == 3


def test_second_run_does_not_resend(tmp_path):
    _, first, _, _, _ = run(tmp_path)
    assert len(first.placed) == 3
    result, second, http, _, _ = run(tmp_path)
    assert result.status == "already_done" and second.placed == [] and http.sent == []


def test_unknown_outcome_halts_and_is_never_resent(tmp_path):
    broker = ScriptedBroker(HELD, behaviour={"THYAO": "unknown"})
    result, _, http, journal, _ = run(tmp_path, broker=broker)
    assert result.status == "halted"
    assert [o.symbol for o in broker.placed] == ["GARAN", "THYAO"]  # ASELS gönderilmedi
    assert "DURDU" in http.sent[-1] and "BELİRSİZ" in http.sent[-1] and "ASELS" in http.sent[-1]
    assert not journal.batch_done(ticket().digest)
    # Yeniden çalıştırma: GARAN ve belirsiz THYAO yeniden gönderilmez, yalnızca ASELS gider.
    again = ScriptedBroker(HELD)
    result2, _, http2, _, _ = run(tmp_path, broker=again)
    assert [o.symbol for o in again.placed] == ["ASELS"] and result2.status == "done"
    assert "akıbeti BELİRSİZ" in http2.sent[0] and "daha önce gönderildi" in http2.sent[0]


def test_broker_error_during_send_halts(tmp_path):
    broker = ScriptedBroker(HELD, behaviour={"GARAN": "error"})
    result, _, http, journal, _ = run(tmp_path, broker=broker)
    assert result.status == "halted" and len(broker.placed) == 1
    assert events(journal, "2026-11-30|GARAN|sell") == ["sending", "unknown"]


def test_connection_failure_sends_nothing(tmp_path):
    class Down(ScriptedBroker):
        def connect(self):
            from bistbot.exec.base import BrokerError
            raise BrokerError("Matriks IQ'ya bağlanılamadı")

    result, broker, http, _, _ = run(tmp_path, broker=Down(HELD))
    assert result.status == "error" and broker.placed == [] and "GÖNDERİLMEDİ" in http.sent[-1]
    assert not any("Onaylamak" in t for t in http.sent)  # bağlantı yokken onay bile istenmez


def test_limit_violation_blocks_everything_and_alerts_once(tmp_path):
    tight = Limits(azami_emir_tl=1000.0)
    result, broker, http, _, _ = run(tmp_path, sinirlar=tight)
    assert result.status == "blocked" and broker.placed == [] and broker.connected is False
    assert len(http.sent) == 1 and "güvenlik kontrolü" in http.sent[0]
    result2, _, http2, _, _ = run(tmp_path, sinirlar=tight)
    assert result2.status == "blocked" and http2.sent == []  # aynı uyarı yinelenmez


def test_wrong_day_is_quiet(tmp_path):
    for tk in (ticket(session=dt.date(2026, 12, 2)), ticket(session=dt.date(2026, 11, 30), as_of=dt.date(2026, 11, 27))):
        result, broker, http, journal, _ = run(tmp_path, tk=tk)
        assert result.status == "not_today" and broker.placed == [] and http.sent == [] and journal.entries() == []
    result, broker, http, _, _ = run(tmp_path, tk=ticket(orders=[]))
    assert result.status == "no_orders" and http.sent == []


def test_too_late_in_the_day_is_blocked(tmp_path):
    result, broker, http, _, _ = run(tmp_path, clock=FakeClock(17, 45))
    assert result.status == "blocked" and broker.placed == [] and "süresi geçti" in http.sent[0]


def test_approval_expires_at_deadline(tmp_path):
    result, broker, _, _, clock = run(tmp_path, reply="none", clock=FakeClock(17, 0))
    assert result.status == "timeout" and broker.placed == []
    assert dt.time(17, 30) <= clock.now().time() <= dt.time(17, 32)


def test_late_approval_goes_to_continuous_session(tmp_path):
    result, broker, _, journal, clock = run(tmp_path, clock=FakeClock(9, 56))  # 09:55-10:00 emir girilemez
    assert result.status == "done" and len(broker.placed) == 3
    first = next(e for e in journal.entries() if e["event"] == "sending")
    assert dt.datetime.fromisoformat(first["ts"]) is not None and clock.now().time() >= dt.time(10, 0, 30)


def test_send_window_boundaries():
    z = Schedule()
    at = lambda h, m, s=0: dt.datetime.combine(SESSION, dt.time(h, m, s), IST)  # noqa: E731
    assert send_window(at(9, 0), z) == (at(9, 40, 15), "acilis")
    assert send_window(at(9, 45), z) == (at(9, 45), "acilis")
    assert send_window(at(9, 57), z) == (at(10, 0, 30), "surekli")
    assert send_window(at(14, 0), z) == (at(14, 0), "surekli")
    assert send_window(at(17, 56), z) == (None, "kapali")


def test_stop_file_halts(tmp_path):
    s = settings(tmp_path, mod="gercek")
    s.klasor.mkdir(parents=True)
    (s.klasor / "DUR").write_text("")
    result, broker, http, _, _ = run(tmp_path)
    assert result.status == "stopped" and broker.placed == [] and http.sent == []


def test_telegram_stop_between_orders(tmp_path):
    clock = FakeClock()
    s = settings(tmp_path, mod="gercek")
    tg, http = fake_telegram(clock, "approve")

    class StopAfterFirst(ScriptedBroker):
        def place(self, order):
            state = super().place(order)
            if len(self.placed) == 1:
                http.add_message("DUR")
            return state

    broker = StopAfterFirst(HELD)
    result = run_batch(s, ticket(), broker, tg, Journal(journal_path(s)), clock)
    assert result.status == "halted" and len(broker.placed) == 1 and "durdurma istendi" in result.message


def test_sells_capped_to_real_holdings_and_missing_position_skipped(tmp_path):
    broker = ScriptedBroker({"GARAN": 12})
    result, _, http, _, _ = run(tmp_path, broker=broker)
    assert broker.placed[0].lots == 12 and "12 lot satılacak" in http.sent[0]
    broker2 = ScriptedBroker({})
    _, _, http2, _, _ = run(tmp_path / "b", broker=broker2)
    assert [o.side for o in broker2.placed] == ["buy", "buy"] and "satılabilir lot yok" in http2.sent[0]


def test_buys_beyond_cash_wait_for_sells_then_go_in_second_round(tmp_path):
    # Bakiye yalnızca THYAO'ya (15×309≈4.649 TL) yeter; ASELS (50×82,4=4.120) satış parasını bekler.
    broker = ScriptedBroker(HELD, cash=5_000.0)
    result, _, http, journal, clock = run(tmp_path, broker=broker)
    assert [(o.symbol, o.key.endswith("|2")) for o in broker.placed] == [("GARAN", False), ("THYAO", False), ("ASELS", True)]
    assert "deferred" in events(journal, "2026-11-30|ASELS|buy")
    assert result.status == "done" and clock.now().time() >= dt.time(10, 0, 30)  # ikinci tur sürekli işlemde


def test_second_round_skipped_when_sells_did_not_fill(tmp_path):
    broker = ScriptedBroker(HELD, cash=5_000.0, behaviour={"GARAN": "rest"})
    result, _, http, _, _ = run(tmp_path, broker=broker)
    assert [o.symbol for o in broker.placed] == ["GARAN", "THYAO"]
    assert "Satışlar gerçekleşmediği için" in http.sent[-1] and "ASELS" in http.sent[-1]
    assert "bekliyor" in http.sent[-1] and "bistbot emir --iptal" in http.sent[-1]


def test_rejected_buy_is_retried_once_after_sells_fill(tmp_path):
    broker = ScriptedBroker(HELD, behaviour={"ASELS": "reject_once"})
    result, _, http, journal, _ = run(tmp_path, broker=broker)
    keys = [o.key for o in broker.placed]
    assert keys == ["2026-11-30|GARAN|sell", "2026-11-30|THYAO|buy", "2026-11-30|ASELS|buy", "2026-11-30|ASELS|buy|2"]
    always = ScriptedBroker(HELD, behaviour={"ASELS": "reject"})
    result2, _, http2, _, _ = run(tmp_path / "b", broker=always)
    assert [o.symbol for o in always.placed].count("ASELS") == 2  # bir kez daha denenir, sonra bırakılır
    assert "REDDEDİLDİ" in http2.sent[-1]


def test_second_round_can_be_disabled(tmp_path):
    broker = ScriptedBroker(HELD, cash=5_000.0)
    _, _, http, _, _ = run(tmp_path, broker=broker, zaman=Schedule(ikinci_tur=False))
    assert [o.symbol for o in broker.placed] == ["GARAN", "THYAO"] and "ikinci tur kapalı" in http.sent[-1]


def test_resting_orders_are_watched_until_after_the_opening_print(tmp_path):
    broker = ScriptedBroker(HELD, default="rest")
    result, _, http, _, clock = run(tmp_path, broker=broker)
    assert clock.now().time() >= dt.time(10, 2) and "bekliyor (limit" in http.sent[-1]
    broker2 = ScriptedBroker(HELD, default="rest")
    broker2.fill_on_refresh = {"GARAN", "THYAO", "ASELS"}
    result2, _, http2, _, clock2 = run(tmp_path / "b", broker=broker2)
    assert "gerçekleşti 40/40" in http2.sent[-1] and clock2.now().time() < dt.time(9, 45)  # hepsi bitince beklemez


def test_dry_run_is_labelled_and_kept_in_a_separate_journal(tmp_path):
    result, broker, http, _, _ = run(tmp_path, broker=DryRunBroker({"GARAN": 40}), mod="deneme")
    assert result.status == "done" and "DENEME" in http.sent[0] and "Deneme raporu" in http.sent[-1]
    assert "GERÇEK EMİR ONAYI" not in http.sent[0]
    # Deneme kaydı gerçek kipin göndermesini engellemez.
    live, live_broker, _, _, _ = run(tmp_path, mod="gercek")
    assert live.status == "done" and len(live_broker.placed) == 3
    assert journal_path(settings(tmp_path, mod="deneme")) != journal_path(settings(tmp_path, mod="gercek"))


def test_dry_run_without_telegram_needs_no_approval_but_live_does(tmp_path):
    clock = FakeClock()
    s = settings(tmp_path, mod="deneme", telegram=TelegramSettings())
    broker = DryRunBroker({"GARAN": 40})
    assert run_batch(s, ticket(), broker, None, Journal(journal_path(s)), clock).status == "done"
    live = settings(tmp_path, mod="gercek")
    real = ScriptedBroker(HELD)
    result = run_batch(live, ticket(), real, None, Journal(journal_path(live)), FakeClock())
    assert result.status == "error" and real.placed == []


def test_run_lock_is_exclusive_and_recovers_from_stale_lock(tmp_path):
    with RunLock(tmp_path):
        with pytest.raises(AlreadyRunning):
            with RunLock(tmp_path):
                pass
    with RunLock(tmp_path):  # serbest bırakıldıktan sonra yeniden alınır
        pass
    (tmp_path / "kilit").write_text("eski")
    import os
    old = dt.datetime.now().timestamp() - 13 * 3600
    os.utime(tmp_path / "kilit", (old, old))
    with RunLock(tmp_path):
        pass


def test_token_never_reaches_journal_or_messages(tmp_path):
    _, _, http, journal, _ = run(tmp_path)
    assert TOKEN not in journal.path.read_text(encoding="utf-8")
    assert all(TOKEN not in text for text in http.sent)


# ------------------------------------------------------------------- uçtan uca (sahte Matriks)
def live_settings(tmp_path, port, **kw):
    return ExecSettings(mod="gercek", klasor=tmp_path / ".emir", fis=str(tmp_path / "latest.json"),
                        telegram=TelegramSettings(token=TOKEN, chat_id="555"),
                        matriks=MatriksSettings(port=port, zaman_asimi=3.0, **kw))


def test_live_mode_is_locked_until_side_test_passes(tmp_path):
    with MockMatriks(default="rest") as server:
        s = live_settings(tmp_path, server.port)
        with pytest.raises(SettingsError, match="yön testi"):
            app.make_broker(s, ticket())
        said = []
        # Kullanıcı "hayır" derse kilit açılmaz, test emri yine de iptal edilir.
        answers = iter(["evet", "hayır"])
        assert app.cmd_side_test(s, "kchol", 200.0, ask=lambda _: next(answers), out=said.append) == 1
        assert len(server.cancels) == 1 and app.calibration(s) is None
        # Test emri: 1 lot ALIŞ, piyasanın %5 altında, fiyat adımına uygun.
        test_order = server.new_orders[0]
        assert (test_order["Symbol"], test_order["OrderSide"], test_order["Quantity"], test_order["Price"]) == ("KCHOL", 1, 1, 190.0)
        answers = iter(["evet", "evet"])
        assert app.cmd_side_test(s, "KCHOL", 200.0, ask=lambda _: next(answers), out=said.append) == 0
        record = app.calibration(s)
        # Belgedeki gibi: istekte alış 1, yanıtta alış 0 görünür; öğrenilen değer 0'dır.
        assert record["yanit_alis"] == 0 and record["alis_kodu"] == 1 and len(server.cancels) == 2
        assert "0~123456" not in json.dumps(load_state(s.klasor))  # hesap numarası açık yazılmaz
        live_broker = app.make_broker(s, ticket())
        assert live_broker.echo_buy == 0 and record["kimlik_yankisi"] is True and live_broker._ids_echoed
        # Kodlar sonradan değiştirilirse doğrulama geçersiz olur.
        changed = live_settings(tmp_path, server.port, alis_kodu=0, satis_kodu=1)
        with pytest.raises(SettingsError):
            app.make_broker(changed, ticket())


def test_side_test_refuses_held_symbol_and_rejected_order(tmp_path):
    with MockMatriks(positions={"KCHOL": 10.0}, behaviour={"SISE": "reject"}) as server:
        s = live_settings(tmp_path, server.port)
        said = []
        assert app.cmd_side_test(s, "KCHOL", 200.0, ask=lambda _: "evet", out=said.append) == 1
        assert server.new_orders == [] and any("ELİNİZDE OLMAYAN" in t for t in said)
        assert app.cmd_side_test(s, "SISE", 40.0, ask=lambda _: "evet", out=said.append) == 1
        assert app.calibration(s) is None


def test_end_to_end_with_mock_matriks(tmp_path):
    with MockMatriks(positions={"GARAN": 40.0, "AKBNK": 70.0}) as server:
        s = live_settings(tmp_path, server.port)
        (tmp_path / "latest.json").write_text(json.dumps(payload()), encoding="utf-8")
        save_state(s.klasor, {app.CALIBRATION_KEY: {
            "dogrulandi": True, "alis_kodu": 1, "satis_kodu": 2, "yanit_alis": 0,
            "hesap": app.account_fingerprint("7", "0~123456")}})
        clock = FakeClock()
        tg, http = fake_telegram(clock, "approve")
        tk = ticket()
        broker = app.make_broker(s, tk)
        result = run_batch(s, tk, broker, tg, Journal(journal_path(s)), clock)
        assert result.status == "done", result.message
        sent = [(m["Symbol"], m["OrderSide"], m["Quantity"], m["Price"]) for m in server.new_orders]
        assert sent == [("GARAN", 2, 40, 97.0), ("THYAO", 1, 15, 309.0), ("ASELS", 1, 50, 82.4)]
        assert "Test Yatırım" in http.sent[0] and "0~123456" not in "".join(http.sent)
        assert all(st.status == "filled" for st in result.states.values())


def test_end_to_end_side_mismatch_stops_after_first_order(tmp_path):
    # Sunucu satışı alış gibi (0) bildiriyor: ilk emir (GARAN satış) iptal edilir ve gönderim durur.
    with MockMatriks(positions={"GARAN": 40.0}, default="rest", side_echo="always_zero") as server:
        s = live_settings(tmp_path, server.port)
        save_state(s.klasor, {app.CALIBRATION_KEY: {
            "dogrulandi": True, "alis_kodu": 1, "satis_kodu": 2, "yanit_alis": 0,
            "hesap": app.account_fingerprint("7", "0~123456")}})
        clock = FakeClock()
        tg, http = fake_telegram(clock, "approve")
        tk = ticket()
        result = run_batch(s, tk, app.make_broker(s, tk), tg, Journal(journal_path(s)), clock)
        assert result.status == "halted" and len(server.new_orders) == 1 and len(server.cancels) == 1
        assert "Matriks IQ farklı bildirdi" in http.sent[-1]


def test_wrong_account_after_calibration_is_refused(tmp_path):
    with MockMatriks(positions={"GARAN": 40.0}) as server:
        s = live_settings(tmp_path, server.port)
        save_state(s.klasor, {app.CALIBRATION_KEY: {
            "dogrulandi": True, "alis_kodu": 1, "satis_kodu": 2, "yanit_alis": 1,
            "hesap": app.account_fingerprint("7", "BASKA-HESAP")}})
        clock = FakeClock()
        tg, http = fake_telegram(clock, "approve")
        tk = ticket()
        result = run_batch(s, tk, app.make_broker(s, tk), tg, Journal(journal_path(s)), clock)
        assert result.status == "error" and server.new_orders == [] and "yön testinin yapıldığı hesap değil" in http.sent[-1]


def test_cmd_run_reads_ticket_file_and_handles_missing_ticket(tmp_path):
    s = settings(tmp_path, mod="deneme", telegram=TelegramSettings(), fis="latest.json")
    assert app.cmd_run(s, tmp_path, FakeClock()).status == "error"  # fiş yok
    (tmp_path / "latest.json").write_text(json.dumps(payload()), encoding="utf-8")
    result = app.cmd_run(s, tmp_path, FakeClock())
    assert result.status == "done" and "Deneme raporu" in result.message
    assert app.cmd_run(s, tmp_path, FakeClock()).status == "already_done"
    lines = []
    assert app.cmd_status(s, out=lines.append, today=SESSION) == 0
    assert any("GARAN" in line and "filled" in line for line in lines)


def test_side_echo_check_can_be_disabled_when_field_is_unreliable(tmp_path):
    """Matriks IQ yanıtta yönü hep 0 gönderiyorsa denetim kapatılır ve satışlar gönderilebilir."""
    with MockMatriks(positions={"GARAN": 40.0, "AKBNK": 70.0}, side_echo="always_zero") as server:
        s = live_settings(tmp_path, server.port, yon_yanit_denetimi=False)
        save_state(s.klasor, {app.CALIBRATION_KEY: {
            "dogrulandi": True, "alis_kodu": 1, "satis_kodu": 2, "yanit_alis": 0,
            "hesap": app.account_fingerprint("7", "0~123456")}})
        clock = FakeClock()
        tg, http = fake_telegram(clock, "approve")
        tk = ticket()
        result = run_batch(s, tk, app.make_broker(s, tk), tg, Journal(journal_path(s)), clock)
        assert result.status == "done" and [m["OrderSide"] for m in server.new_orders] == [2, 1, 1]


def test_cancel_command_cancels_only_the_bots_working_orders(tmp_path):
    with MockMatriks(positions={"GARAN": 40.0, "AKBNK": 70.0}, default="rest") as server:
        s = live_settings(tmp_path, server.port)
        save_state(s.klasor, {app.CALIBRATION_KEY: {
            "dogrulandi": True, "alis_kodu": 1, "satis_kodu": 2, "yanit_alis": 0,
            "hesap": app.account_fingerprint("7", "0~123456")}})
        clock = FakeClock()
        tg, _ = fake_telegram(clock, "approve")
        tk = ticket()
        run_batch(s, tk, app.make_broker(s, tk), tg, Journal(journal_path(s)), clock)
        assert len(server.new_orders) == 3
        # Kullanıcının elle girdiği, bota ait olmayan bir emir de bekliyor olsun.
        server.orders["9999"] = {**server.orders["1001"], "OrderID": "9999", "Symbol": "SISE"}
        said = []
        assert app.cmd_cancel(s, out=said.append, today=SESSION) == 0
        cancelled = sorted(str(c["OrderID"]) for c in server.cancels)
        assert cancelled == ["1001", "1002", "1003"]
        # İptal isteğinde yön, yeni emirdeki kodlamayla gider (belgedeki örnek): satış 2, alış 1.
        assert {c["Symbol"]: c["OrderSide"] for c in server.cancels} == {"GARAN": 2, "THYAO": 1, "ASELS": 1}
        assert all(c["ApiCommands"] == 4 and c["Quantity"] == c["LeavesQty"] > 0 for c in server.cancels)


# ------------------------------------------------------------------ bağımsız incelemenin senaryoları
FOUR = [
    {"symbol": "GARAN", "side": "sell", "lots": 40, "ref_price": 100.0, "limit_price": 97.0},
    {"symbol": "THYAO", "side": "buy", "lots": 15, "ref_price": 300.0, "limit_price": 309.0},
    {"symbol": "ASELS", "side": "buy", "lots": 50, "ref_price": 80.0, "limit_price": 82.4},
    {"symbol": "KCHOL", "side": "buy", "lots": 20, "ref_price": 200.0, "limit_price": 206.0},
]


def test_second_round_orders_are_not_duplicated_on_rerun(tmp_path):
    """Kritik: ikinci turda (|2) gönderilen ya da belirsiz kalan alış, yeniden çalıştırmada bir daha gönderilmez."""
    big_sell = [{**FOUR[0], "lots": 100}] + FOUR[1:]  # satış 9.700 TL: ikinci turda iki alışa da yeter
    tk = ticket(orders=big_sell)
    first = ScriptedBroker({"GARAN": 100}, cash=5_000.0, behaviour={"KCHOL": "unknown"})
    result, _, http, journal, _ = run(tmp_path, broker=first, tk=tk)
    keys = [o.key for o in first.placed]
    assert keys == ["2026-11-30|GARAN|sell", "2026-11-30|THYAO|buy", "2026-11-30|ASELS|buy|2", "2026-11-30|KCHOL|buy|2"]
    assert result.status == "halted" and "BELİRSİZ" in http.sent[-1]
    again = ScriptedBroker({"THYAO": 15, "ASELS": 50}, cash=20_000.0)
    result2, _, http2, _, _ = run(tmp_path, broker=again, tk=tk)
    assert again.placed == [] and result2.status == "done"
    assert "KCHOL alış: önceki çalıştırmada akıbeti BELİRSİZ" in http2.sent[0]
    assert "ASELS alış: daha önce gönderildi" in http2.sent[0]


def test_same_decision_reissued_for_next_session_is_not_bought_twice(tmp_path):
    """Bülten gecikince aynı karar ertesi seans için yeniden yayımlanır; emirler ikinci kez gitmez."""
    run(tmp_path)  # 1 Aralık seansı: üç emir gönderildi
    reissued = ticket(session=dt.date(2026, 12, 2), generated="2026-12-01T16:25:00+00:00")  # karar günü yine 30 Kasım
    broker = ScriptedBroker({"AKBNK": 70, "THYAO": 15, "ASELS": 50})
    result, _, http, _, _ = run(tmp_path, broker=broker, tk=reissued, clock=FakeClock(day=dt.date(2026, 12, 2)))
    assert broker.placed == [] and result.status == "done"
    assert "daha önce gönderildi" in http.sent[0]


def test_stale_decision_and_already_held_buys_are_flagged_in_the_approval(tmp_path):
    late = ticket(session=dt.date(2026, 12, 2), generated="2026-12-01T16:25:00+00:00")
    broker = ScriptedBroker({"GARAN": 40, "AKBNK": 70, "THYAO": 15})
    _, _, http, _, _ = run(tmp_path, broker=broker, tk=late, clock=FakeClock(day=dt.date(2026, 12, 2)), reply="reject")
    text = http.sent[0]
    assert "arada işlem günü var (01.12)" in text and "ZATEN var" in text and "THYAO" in text
    assert broker.placed == []
    # Aradaki gün tatil listesindeyse uyarı çıkmaz.
    _, _, http2, _, _ = run(tmp_path / "b", broker=ScriptedBroker(HELD), tk=late, reply="reject",
                            clock=FakeClock(day=dt.date(2026, 12, 2)), tatiller=("2026-12-01",))
    assert "arada işlem günü" not in http2.sent[0]


def test_changing_your_mind_after_approval_stops_the_orders(tmp_path):
    for word in ("RED", "İptal", "vazgeç", "/dur"):
        clock = FakeClock()
        s = settings(tmp_path / word.strip("/"), mod="gercek")
        tg, http = fake_telegram(clock, lambda code, w=word: [code])
        orig = http.post

        def post(url, data=None, timeout=None, w=word):
            resp = orig(url, data=data, timeout=timeout)
            if url.endswith("sendMessage") and "Onay alındı" in data["text"]:
                http.add_message(w)  # 09:20'de onayladı, emirler 09:40'ta gidecekti
            return resp

        http.post = post
        broker = ScriptedBroker(HELD)
        result = run_batch(s, ticket(), broker, tg, Journal(journal_path(s)), clock)
        assert result.status == "halted" and broker.placed == [], word
        assert "DURDU" in http.sent[-1]


def test_second_round_never_spends_more_than_the_cash_that_is_really_there(tmp_path):
    # (a) Yalnız alış var, bakiye birine yetiyor: ertelenenler bakiye yetmediği için gönderilmez.
    only_buys = ticket(orders=FOUR[1:])
    broker = ScriptedBroker(HELD, cash=5_000.0)
    _, _, http, _, _ = run(tmp_path / "a", broker=broker, tk=only_buys)
    assert [o.symbol for o in broker.placed] == ["THYAO"]
    assert "Bakiye yetmediği için şu alışlar gönderilmedi: ASELS, KCHOL" in http.sent[-1]
    # (b) Satış parası yalnızca birine yetiyor: sığan gönderilir, sığmayan bildirilir.
    broker = ScriptedBroker(HELD, cash=5_000.0)
    _, _, http, _, _ = run(tmp_path / "b", broker=broker, tk=ticket(orders=FOUR))
    assert [o.symbol for o in broker.placed] == ["GARAN", "THYAO", "ASELS"]  # 351 + 3.880 = 4.231 TL: yalnız ASELS sığar
    assert "Bakiye yetmediği için şu alışlar gönderilmedi: KCHOL" in http.sent[-1]

    # (c) Bakiye ikinci turda okunamıyorsa ertelenen alışlar gönderilmez.
    class CashGoesAway(ScriptedBroker):
        def cash(self):
            self.reads = getattr(self, "reads", 0) + 1
            return 5_000.0 if self.reads <= 2 else None

    broker = CashGoesAway(HELD)
    _, _, http, _, _ = run(tmp_path / "c", broker=broker, tk=ticket(orders=FOUR))
    assert [o.symbol for o in broker.placed] == ["GARAN", "THYAO"] and "Bakiye yeniden okunamadığı için" in http.sent[-1]


def test_positions_are_reread_right_before_sending(tmp_path):
    """Onay ile gönderim arasında hisse elle satıldıysa bot olmayan lotu satmaya çalışmaz."""
    class SoldByHand(ScriptedBroker):
        def positions(self):
            self.reads = getattr(self, "reads", 0) + 1
            return {"GARAN": 40, "AKBNK": 70} if self.reads == 1 else {"GARAN": 10, "AKBNK": 70}

    broker = SoldByHand()
    result, _, http, _, _ = run(tmp_path, broker=broker)
    assert broker.placed[0].symbol == "GARAN" and broker.placed[0].lots == 10
    assert "10 lot kaldığı için 40 yerine 10 lot satılıyor" in http.sent[-1]

    class Gone(ScriptedBroker):
        def positions(self):
            self.reads = getattr(self, "reads", 0) + 1
            return {"GARAN": 40} if self.reads == 1 else {}

    gone = Gone()
    run(tmp_path / "b", broker=gone)
    assert [o.side for o in gone.placed] == ["buy", "buy"]  # satış hiç gönderilmedi (açığa satış yok)


def test_definitely_unsent_order_can_be_sent_on_the_next_run(tmp_path):
    broker = ScriptedBroker(HELD, behaviour={"THYAO": "not_sent"})
    result, _, http, journal, _ = run(tmp_path, broker=broker)
    assert result.status == "halted" and "hiçbir şey gitmedi" in http.sent[-1] and "BELİRSİZ" not in http.sent[-1]
    assert events(journal, "2026-11-30|THYAO|buy") == ["sending", "not_sent"]
    again = ScriptedBroker({"AKBNK": 70})
    run(tmp_path, broker=again)
    assert [o.symbol for o in again.placed] == ["THYAO", "ASELS"]  # GARAN yeniden gönderilmez


def test_unexpected_exception_still_produces_a_report(tmp_path):
    broker = ScriptedBroker(HELD, behaviour={"THYAO": "crash"})
    result, _, http, journal, _ = run(tmp_path, broker=broker)
    assert result.status == "halted" and [o.symbol for o in broker.placed] == ["GARAN", "THYAO"]
    report = http.sent[-1]
    assert "DURDU" in report and "beklenmeyen hata" in report and "BELİRSİZ" in report and "ASELS" in report
    assert events(journal, "2026-11-30|THYAO|buy") == ["sending", "unknown"]

    class BrokenReader(ScriptedBroker):
        def positions(self):
            self.reads = getattr(self, "reads", 0) + 1
            if self.reads > 1:
                raise RuntimeError("çözülemeyen yanıt")
            return dict(HELD)

    broken = BrokenReader()
    result2, _, http2, _, _ = run(tmp_path / "b", broker=broken)
    assert result2.status == "halted" and broken.placed == [] and "DURDU" in http2.sent[-1]


def test_journal_failure_after_sending_does_not_hide_the_report(tmp_path):
    clock = FakeClock()
    s = settings(tmp_path, mod="gercek")
    tg, http = fake_telegram(clock, "approve")
    journal = Journal(journal_path(s))
    orig = journal.record

    def record(event, key="", **data):
        if event == "filled":
            raise OSError("disk dolu")
        return orig(event, key, **data)

    journal.record = record
    broker = ScriptedBroker(HELD)
    run_batch(s, ticket(), broker, tg, journal, clock)
    assert len(broker.placed) == 3 and "Emir günlüğüne yazılamadı" in http.sent[-1] and "gerçekleşti" in http.sent[-1]
    # Sonuç yazılamadıysa emir "gönderilmiş olabilir" olarak kalır ve yeniden gönderilmez.
    again = ScriptedBroker(HELD)
    run_batch(s, ticket(), again, fake_telegram(FakeClock(), "approve")[0], Journal(journal_path(s)), FakeClock())
    assert again.placed == []


def test_ticket_is_not_marked_done_when_sells_could_not_be_planned(tmp_path):
    exits = ticket(orders=[FOUR[0]])
    result, broker, http, journal, _ = run(tmp_path, broker=ScriptedBroker({}), tk=exits)  # pozisyonlar boş okundu
    assert result.status == "nothing_sendable" and not journal.batch_done(exits.digest)
    assert "satılabilir lot yok" in http.sent[0]
    later = ScriptedBroker({"GARAN": 40})
    result2, _, _, _, _ = run(tmp_path, broker=later, tk=exits)
    assert result2.status == "done" and [o.symbol for o in later.placed] == ["GARAN"]


def test_rejected_orders_are_offered_again_with_an_honest_label(tmp_path):
    broker = ScriptedBroker(HELD, behaviour={"THYAO": "reject", "GARAN": "rest"})
    run(tmp_path, broker=broker)  # THYAO reddedildi; satış gerçekleşmediği için ikinci tur yok
    again = ScriptedBroker(HELD)
    _, _, http, _, _ = run(tmp_path, broker=again)
    assert [o.symbol for o in again.placed] == ["THYAO"]  # red kesin: yeni onayla yeniden denenebilir
    assert "GARAN satış: daha önce gönderildi" in http.sent[0] and "THYAO alış: daha önce" not in http.sent[0]


def test_non_user_rejections_are_not_reported_as_your_decision(tmp_path):
    clock = FakeClock()
    s = settings(tmp_path, mod="gercek")
    tg, http = fake_telegram(clock, "approve")
    http.now = lambda: int(clock.now().timestamp()) + 3600
    result = run_batch(s, ticket(), ScriptedBroker(HELD), tg, Journal(journal_path(s)), clock)
    assert result.status == "rejected" and "onay verilmedi" in result.message and "vazgeçtiniz" not in result.message
    result2, _, http2, _, _ = run(tmp_path / "b", reply="reject")
    assert "vazgeçtiniz" in result2.message


def test_final_report_is_retried_and_kept_if_telegram_stays_down(tmp_path):
    clock = FakeClock()
    s = settings(tmp_path, mod="gercek")
    tg, http = fake_telegram(clock, "approve")
    orig = http.post

    def post(url, data=None, timeout=None):
        if url.endswith("sendMessage") and "Emir raporu" in data["text"]:
            raise requests.ConnectionError("ağ yok")
        return orig(url, data=data, timeout=timeout)

    http.post = post
    result = run_batch(s, ticket(), ScriptedBroker(HELD), tg, Journal(journal_path(s)), clock)
    assert result.status == "done" and not any("Emir raporu" in t for t in http.sent)
    kept = (s.klasor / "iletilemeyen.jsonl").read_text(encoding="utf-8")
    assert "Emir raporu" in kept
    # Sonraki çalıştırmanın başında (o gün emir olmasa da) iletilir.
    tg2, http2 = fake_telegram(FakeClock(day=dt.date(2026, 12, 2)), "approve")
    run_batch(s, ticket(orders=[]), ScriptedBroker(HELD), tg2, Journal(journal_path(s)), FakeClock(day=dt.date(2026, 12, 2)))
    assert "Daha önce iletilemeyen bildirim" in http2.sent[0] and "Emir raporu" in http2.sent[0]
    assert not (s.klasor / "iletilemeyen.jsonl").exists()


def test_daily_totals_count_what_was_already_sent_today(tmp_path):
    tight = Limits(azami_alis_tl=10_000.0)
    first = ticket(orders=[FOUR[1]])                                            # THYAO 4.635 TL
    assert run(tmp_path, tk=first, sinirlar=tight, broker=ScriptedBroker(HELD))[0].status == "done"
    second = ticket(orders=[FOUR[1], {"symbol": "KCHOL", "side": "buy", "lots": 30, "ref_price": 200.0, "limit_price": 206.0}])
    result, broker, http, _, _ = run(tmp_path, tk=second, sinirlar=tight, broker=ScriptedBroker(HELD))  # +6.180 TL
    assert result.status == "blocked" and broker.placed == [] and "bugün daha önce gönderilenlerle birlikte" in http.sent[0]
    # Aynı fişin yeniden çalıştırılması kendi emirlerini iki kez saymaz.
    ok = ticket(orders=[FOUR[1], {"symbol": "KCHOL", "side": "buy", "lots": 20, "ref_price": 200.0, "limit_price": 206.0}])
    result2, broker2, _, _, _ = run(tmp_path, tk=ok, sinirlar=tight, broker=ScriptedBroker(HELD))  # 4.635 + 4.120
    assert result2.status == "done" and [o.symbol for o in broker2.placed] == ["KCHOL"]


def test_group_chat_privacy_mode_is_explained(tmp_path):
    clock = FakeClock()
    s = settings(tmp_path, mod="gercek", telegram=TelegramSettings(token=TOKEN, chat_id="-100555", onaylayan_id="555"))
    from exec_helpers import FakeTelegramHttp
    from bistbot.exec.telegram import Telegram
    http = FakeTelegramHttp(clock, "approve", user_id=555, chat_id=-100555)
    tg = Telegram(TOKEN, "-100555", "555", http=http)
    run_batch(s, ticket(), ScriptedBroker(HELD), tg, Journal(journal_path(s)), clock)
    assert "gizlilik kipi" in http.sent[0] and "/setprivacy" in http.sent[0]


def test_run_lock_releases_only_its_own_lock(tmp_path):
    lock = RunLock(tmp_path)
    with lock:
        (tmp_path / "kilit").write_text("baska-jeton 1 x\n")  # kilidi başka bir çalıştırma devralmış
    assert (tmp_path / "kilit").exists()  # başkasının kilidi silinmez
    with pytest.raises(AlreadyRunning):
        with RunLock(tmp_path):
            pass


def test_side_test_rechecks_the_order_after_the_user_answers(tmp_path):
    """Kullanıcı yanıt verirken emir reddedilir ya da gerçekleşirse yön doğrulanmış sayılmaz."""
    import time

    for event in ("reject", "fill"):
        with MockMatriks(default="rest") as server:
            s = live_settings(tmp_path / event, server.port)
            said = []

            def ask(prompt, server=server, event=event):
                if "ALIŞ olarak" in prompt:
                    getattr(server, event)("KCHOL")
                    time.sleep(0.3)
                return "evet"

            assert app.cmd_side_test(s, "KCHOL", 200.0, ask=ask, out=said.append) == 1
            assert app.calibration(s) is None
            assert any("REDDEDİLDİ" in t or "GERÇEKLEŞTİ" in t for t in said)


def test_cancel_command_finds_orders_whose_number_was_never_journaled(tmp_path):
    with MockMatriks(positions={"GARAN": 40.0, "AKBNK": 70.0}, default="rest") as server:
        s = live_settings(tmp_path, server.port)
        journal = Journal(journal_path(s))
        # Günlükte emir numarası olmayan (ilk yanıtta gelmemiş) bekleyen bir alış.
        journal.record("sending", "2026-11-30|THYAO|buy", symbol="THYAO", side="buy", lots=15, limit=309.0,
                       session=str(SESSION), as_of="2026-11-30")
        journal.record("accepted", "2026-11-30|THYAO|buy", broker_id=None, filled=0)
        server.orders["4242"] = {"Symbol": "THYAO", "OrderID": "4242", "OrderID2": "4242*309", "OrderQty": 15.0,
                                 "OrdStatus": "0", "LeavesQty": 15.0, "FilledQty": 0.0, "Price": 309.0, "Quantity": 0.0,
                                 "OrderSide": 0, "AccountId": "0~123456", "BrokageId": "7", "TimeInForce": "0"}
        server.orders["4243"] = {**server.orders["4242"], "OrderID": "4243", "Symbol": "SISE"}  # bota ait değil
        said = []
        assert app.cmd_cancel(s, out=said.append, today=SESSION) == 0
        assert [c["OrderID"] for c in server.cancels] == ["4242"] and server.cancels[0]["OrderSide"] == 1


def test_command_line_mode_can_only_be_made_safer(tmp_path, capsys):
    from bistbot import cli

    config = tmp_path / "emir-ayar.toml"
    config.write_text('mod = "deneme"\nfis = "yok.json"\n', encoding="utf-8")
    assert cli.main(["emir", "--emir-ayar", str(config), "--mod", "salt-okunur"]) == 2
    assert "daha güvenli bir kipe" in capsys.readouterr().out
    assert cli.main(["emir", "--emir-ayar", str(config), "--mod", "deneme"]) == 1  # fiş yok: hata, ama kip kabul edildi
    assert "Emir fişi okunamadı" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["emir", "--emir-ayar", str(config), "--mod", "gercek"])  # komut satırında gerçek kip seçeneği yok
