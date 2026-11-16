import datetime as dt

import pytest

from bistbot import rules
from bistbot.exec import guard
from bistbot.exec.guard import build_plan, check_ticket, on_tick, round_down_to_tick, session_problems
from bistbot.exec.runner import IST
from bistbot.exec.settings import Limits, SettingsError, load_settings
from bistbot.exec.ticket import TicketError, parse_ticket
from exec_helpers import SESSION, payload, ticket

NOW = dt.datetime.combine(SESSION, dt.time(9, 20), IST)


def test_tick_table_matches_exchange_rules():
    assert guard.TICKS == rules.TICK_TABLE
    for price in (0.57, 12.34, 19.99, 20.02, 49.98, 50.05, 99.95, 100.1, 249.9, 250.25, 999.5, 1000.0, 2502.5):
        assert on_tick(price), price
        assert rules.round_to_tick(price, "nearest") == price
    assert not on_tick(20.01) and not on_tick(100.05) and not on_tick(1000.5)
    assert round_down_to_tick(123.456) == 123.4 and round_down_to_tick(19.999) == 19.99


def test_valid_ticket_passes():
    assert check_ticket(ticket(), NOW, Limits()) == []
    assert session_problems(ticket(), NOW) == []


def test_calendar_problems_are_separate_and_quiet():
    assert "erken" in session_problems(ticket(session=dt.date(2026, 12, 2)), NOW)[0]
    assert "eski" in session_problems(ticket(session=dt.date(2026, 11, 30), as_of=dt.date(2026, 11, 27)), NOW)[0]
    saturday = dt.datetime(2026, 12, 5, 9, 20, tzinfo=IST)
    assert any("hafta sonu" in p for p in session_problems(ticket(session=dt.date(2026, 12, 5)), saturday))
    republic_day = dt.datetime(2026, 10, 29, 9, 20, tzinfo=IST)
    t = ticket(session=dt.date(2026, 10, 29), as_of=dt.date(2026, 10, 28))
    assert any("tatil" in p for p in session_problems(t, republic_day))
    assert any("tatil" in p for p in session_problems(ticket(), NOW, holidays=("2026-12-01",)))


@pytest.mark.parametrize("change, expected", [
    ({"generated": "2026-11-20T10:00:00+00:00"}, "saat önce"),
    ({"generated": "bozuk"}, "okunamadı"),
    ({"generated": "2026-12-02T10:00:00+00:00"}, "gelecekte"),
    ({"as_of": dt.date(2026, 11, 10)}, "10 günden eski"),
])
def test_stale_or_odd_tickets_are_blocked(change, expected):
    assert any(expected in p for p in check_ticket(ticket(**change), NOW, Limits()))


def one(side="buy", lots=10, ref=100.0, limit=103.0, symbol="THYAO"):
    return [{"symbol": symbol, "side": side, "lots": lots, "ref_price": ref, "limit_price": limit}]


@pytest.mark.parametrize("orders, limits, expected", [
    (one(lots=300), Limits(), "tek emir sınırı"),                       # 30.900 TL > 25.000
    (one(lots=200), Limits(), "portföyün"),                             # %20,6 > %15
    (one(limit=106.0), Limits(), "uzakta"),                             # %6 sapma
    (one(limit=98.0), Limits(), "yönüyle uyumsuz"),                     # alış limiti kapanışın altında
    (one(side="sell", limit=102.0), Limits(), "yönüyle uyumsuz"),
    (one(limit=103.03), Limits(), "fiyat adımına"),                     # 100 TL üstünde adım 0,10
    (one(), Limits(azami_alis_tl=500.0), "alışların toplamı"),
    (one(side="sell", limit=97.0), Limits(azami_satis_tl=500.0), "satışların toplamı"),
])
def test_limit_violations_block_the_whole_ticket(orders, limits, expected):
    problems = check_ticket(ticket(orders=orders), NOW, limits)
    assert any(expected in p for p in problems), problems


def test_too_many_orders_and_buys_exceeding_equity():
    many = [{"symbol": f"AB{i:02d}", "side": "buy", "lots": 1, "ref_price": 10.0, "limit_price": 10.3} for i in range(50)]
    assert any("50 emir" in p for p in check_ticket(ticket(orders=many), NOW, Limits()))
    big = [{"symbol": f"AB{i:02d}", "side": "buy", "lots": 100, "ref_price": 100.0, "limit_price": 103.0} for i in range(11)]
    assert any("kâğıt portföy değerini aşıyor" in p for p in check_ticket(ticket(orders=big), NOW, Limits()))


def test_plan_puts_sells_first_and_caps_them_at_real_holdings():
    t = ticket()
    plan = build_plan(t, {"GARAN": 25, "AKBNK": 70}, cash=None)
    assert [(o.symbol, o.side, o.lots) for o in plan.orders] == [("GARAN", "sell", 25), ("THYAO", "buy", 15), ("ASELS", "buy", 50)]
    assert any("25 lot satılacak" in n for n in plan.notes)
    assert any("GARAN kâğıtta 40, hesapta 25" in n for n in plan.notes)
    assert plan.sell_total == pytest.approx(25 * 97.0) and plan.buy_total == pytest.approx(15 * 309.0 + 50 * 82.4)

    none = build_plan(t, {}, cash=None)
    assert [o.symbol for o in none.orders] == ["THYAO", "ASELS"]  # elde olmayan hisse satılmaz (açığa satış yok)
    assert any("GARAN satış" in s for s in none.skipped)

    done = build_plan(t, {"GARAN": 40}, cash=None, done={t.order_key(t.orders[1])})
    assert [o.symbol for o in done.orders] == ["GARAN", "ASELS"] and any("daha önce" in s for s in done.skipped)


def test_plan_warns_when_cash_is_short():
    t = ticket()
    assert not any("aşıyor" in n for n in build_plan(t, {"GARAN": 40, "AKBNK": 70}, cash=50_000.0).notes)
    assert any("aşıyor" in n for n in build_plan(t, {"GARAN": 40, "AKBNK": 70}, cash=1_000.0).notes)


@pytest.mark.parametrize("bad", [
    {"orders": [{"symbol": "garan", "side": "buy", "lots": 1, "ref_price": 1.0, "limit_price": 1.0}]},
    {"orders": [{"symbol": "GARAN", "side": "al", "lots": 1, "ref_price": 1.0, "limit_price": 1.0}]},
    {"orders": [{"symbol": "GARAN", "side": "buy", "lots": 1.5, "ref_price": 1.0, "limit_price": 1.0}]},
    {"orders": [{"symbol": "GARAN", "side": "buy", "lots": True, "ref_price": 1.0, "limit_price": 1.0}]},
    {"orders": [{"symbol": "GARAN", "side": "buy", "lots": -3, "ref_price": 1.0, "limit_price": 1.0}]},
    {"orders": [{"symbol": "GARAN", "side": "buy", "lots": 1, "ref_price": 1.0, "limit_price": "1.0"}]},
    {"orders": [{"symbol": "GARAN", "side": "buy", "lots": 1, "ref_price": 1.0, "limit_price": float("nan")}]},
    {"orders": one(symbol="GARAN") + one(symbol="GARAN")},
    {"orders": one(symbol="GARAN") + one(symbol="GARAN", side="sell", limit=97.0)},
    {"session": dt.date(2026, 11, 30)},
])
def test_malformed_tickets_are_rejected(bad):
    with pytest.raises(TicketError):
        parse_ticket(payload(**bad))


def test_settings_defaults_are_safe_and_validated(tmp_path):
    s = load_settings(None, env={})
    assert s.mod == "deneme" and not s.live and s.matriks.host == "127.0.0.1" and s.matriks.port == 18890
    assert (s.matriks.alis_kodu, s.matriks.satis_kodu) == (1, 2)

    def write(text):
        path = tmp_path / "emir-ayar.toml"
        path.write_text(text, encoding="utf-8")
        return path

    with pytest.raises(SettingsError, match="Telegram"):
        load_settings(write('mod = "gercek"\n'), env={})
    with pytest.raises(SettingsError, match="onaylayan"):
        load_settings(write('mod = "gercek"\n'), env={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "-100123"})
    live = load_settings(write('mod = "gercek"\n[telegram]\nonaylayan_id = "42"\n'),
                         env={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "-100123"})
    assert live.live and live.telegram.approver == "42" and live.klasor == tmp_path / ".emir"
    with pytest.raises(SettingsError, match="host"):
        load_settings(write('[matriks]\nhost = "10.0.0.5"\n'), env={})
    with pytest.raises(SettingsError, match="bilinmeyen"):
        load_settings(write('[sinirlar]\nazami_emir = 5\n'), env={})
    with pytest.raises(SettingsError, match="mod"):
        load_settings(write('mod = "canli"\n'), env={})
    with pytest.raises(SettingsError, match="aynı"):
        load_settings(write('[matriks]\nalis_kodu = 2\n'), env={})
    with pytest.raises(SettingsError, match="tatiller"):
        load_settings(write('tatiller = ["10.03.2027"]\n'), env={})
    custom = load_settings(write('tatiller = ["2027-03-10"]\n[zaman]\nonay_son = "16:00"\n[sinirlar]\nazami_emir_tl = 9000\n'
                                 '[matriks]\nlot_alanlari = ["QtyAvailable", "QtyT2"]\n'), env={})
    assert custom.zaman.onay_son == dt.time(16, 0) and custom.sinirlar.azami_emir_tl == 9000.0
    assert custom.matriks.lot_alanlari == ("QtyAvailable", "QtyT2") and custom.tatiller == ("2027-03-10",)


def test_ticket_equity_must_be_positive_and_finite():
    for bad in (0, -5, float("nan"), float("inf"), "100000", None):
        with pytest.raises(TicketError):
            parse_ticket(payload(equity=bad))


def test_order_identity_is_the_decision_not_the_session():
    a, b = ticket(), ticket(session=dt.date(2026, 12, 2))
    assert a.order_key(a.orders[0]) == b.order_key(b.orders[0]) == "2026-11-30|GARAN|sell"
    assert a.digest != b.digest
    from bistbot.exec.guard import trading_days_between
    assert trading_days_between(a) == [] and trading_days_between(b) == [dt.date(2026, 12, 1)]
    friday = ticket(as_of=dt.date(2026, 11, 27), session=dt.date(2026, 11, 30))
    assert trading_days_between(friday) == []  # hafta sonu işlem günü değildir
    assert trading_days_between(b, holidays=("2026-12-01",)) == []


def test_journal_semantics_and_torn_files(tmp_path):
    from bistbot.exec.journal import Journal

    j = Journal(tmp_path / "g.jsonl")
    j.record("sending", "k1")
    assert j.was_sent("k1")                       # akıbeti belirsiz: gönderilmiş say
    j.record("not_sent", "k1")
    assert not j.was_sent("k1")                   # kesinlikle gitmedi
    j.record("sending", "k1"); j.record("rejected", "k1", filled=0)
    assert not j.was_sent("k1")                   # aracı kurum reddetti
    j.record("sending", "k2"); j.record("accepted", "k2"); j.record("not_sent", "k2")
    assert j.was_sent("k2")                       # kabul edilmiş emri hiçbir kayıt geri almaz
    j.record("sending", "k3|2"); j.record("unknown", "k3|2")
    assert j.order_sent("k3") and not j.was_sent("k3")
    j.record("deferred", "k4")
    assert not j.order_sent("k4")
    # Yarım yazılmış, bozuk UTF-8 ile biten dosya: okuma çökmez, sonraki kayıt yeni satırda başlar.
    with open(j.path, "ab") as fh:
        fh.write('{"event": "sending", "key": "k5", "message": "\u015f'.encode("utf-8")[:-1] + b"\xc5")
    assert j.was_sent("k1") is False and j.was_sent("k2")
    j.record("sending", "k6")
    assert j.was_sent("k6") and not j.was_sent("k5")
    assert all(isinstance(e, dict) for e in j.entries())
