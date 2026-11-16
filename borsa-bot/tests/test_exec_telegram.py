"""Telegram onayı: yalnızca yetkili kişinin, o isteğe özel koduyla verilen onay geçerlidir."""
import pytest
import requests

from bistbot.exec.telegram import Telegram, TelegramError, new_code, normalize, request_approval
from exec_helpers import TOKEN, FakeClock, fake_telegram


def ask(tg, clock, code="4821", minutes=30):
    deadline = clock.now().timestamp() + minutes * 60
    text = f"emirler...\nOnaylamak için {code} yazın. Vazgeçmek için RED yazın."
    return request_approval(tg, text, code, deadline, clock=lambda: clock.now().timestamp(), sleep=clock.sleep)


def test_correct_code_from_owner_approves():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "approve")
    assert ask(tg, clock).approved
    assert http.sent[0].startswith("emirler")


@pytest.mark.parametrize("text", ["ONAY 4821", "onay4821", " 4821 ", "Evet 4821"])
def test_accepted_spellings(text):
    clock = FakeClock()
    tg, _ = fake_telegram(clock, lambda code: [text])
    assert ask(tg, clock).approved


@pytest.mark.parametrize("text", ["RED", "red", "Hayır", "iptal", "İPTAL", "dur", "vazgeç"])
def test_reject_words(text):
    clock = FakeClock()
    tg, _ = fake_telegram(clock, lambda code: [text])
    assert ask(tg, clock).status == "rejected"


def test_code_from_someone_else_is_ignored():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "wrong_user")
    d = ask(tg, clock, minutes=5)
    assert d.status == "timeout"
    assert len(http.sent) == 1  # yabancıya yanıt bile verilmez


def test_code_from_another_chat_or_a_bot_is_ignored():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    orig = http.post

    def post(url, data=None, timeout=None):
        resp = orig(url, data=data, timeout=timeout)
        if url.endswith("sendMessage") and "Onaylamak" in data["text"]:
            http.add_message("4821", chat_id=777)            # başka sohbet
            http.add_message("4821", is_bot=True)            # bot hesabı
        return resp

    http.post = post
    assert ask(tg, clock, minutes=3).status == "timeout"


def test_messages_written_before_the_request_do_not_count():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    http.add_message("4821")                      # istek gönderilmeden önce kuyrukta
    http.add_message("ONAY 4821")
    assert ask(tg, clock, minutes=3).status == "timeout"

    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    orig = http.post

    def post(url, data=None, timeout=None):
        resp = orig(url, data=data, timeout=timeout)
        if url.endswith("sendMessage") and "Onaylamak" in data["text"]:
            http.add_message("4821", date=http.now() - 3600)  # eski tarihli mesaj
        return resp

    http.post = post
    assert ask(tg, clock, minutes=3).status == "timeout"


def test_wrong_codes_then_lockout():
    clock = FakeClock()
    tg, http = fake_telegram(clock, lambda code: ["1111", "2222", "3333", "4444", "5555", "4821"])
    d = ask(tg, clock)
    assert d.status == "rejected" and "yanlış" in d.detail
    assert any("GÖNDERİLMEDİ" in t for t in http.sent)


def test_wrong_code_then_right_code():
    clock = FakeClock()
    tg, http = fake_telegram(clock, lambda code: ["0000", "merhaba", code])
    assert ask(tg, clock).approved
    assert any("Kod hatalı" in t for t in http.sent) and any("Anlaşılmadı" in t for t in http.sent)


def test_timeout_when_nobody_answers():
    clock = FakeClock()
    tg, _ = fake_telegram(clock, "none")
    start = clock.now()
    d = ask(tg, clock, minutes=10)
    assert d.status == "timeout"
    assert 9.5 * 60 <= (clock.now() - start).total_seconds() <= 11 * 60


def test_network_errors_never_leak_the_token():
    class Boom:
        def post(self, url, data=None, timeout=None):
            raise requests.ConnectionError(f"HTTPSConnectionPool: {url}")

    tg = Telegram(TOKEN, "555", http=Boom())
    with pytest.raises(TelegramError) as err:
        tg.send("x")
    assert TOKEN not in str(err.value) and "GIZLI" not in repr(err.value)
    assert err.value.__cause__ is None and err.value.__suppress_context__
    assert tg.try_send("x") is False and tg.stop_requested(0) is False


def test_conflict_and_bad_token_are_explained():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    http.status = 409
    with pytest.raises(TelegramError, match="dinleniyor"):
        tg.updates()
    http.status = 401
    with pytest.raises(TelegramError, match="anahtarı"):
        tg.send("x")
    # Onay akışı Telegram okunamıyorsa onaysız sayılır.
    http.status = 409
    assert ask(tg, clock, minutes=1).status == "timeout"


def test_request_is_retried_while_the_network_is_down():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "approve")
    orig, calls = http.post, {"n": 0}

    def flaky(url, data=None, timeout=None):
        calls["n"] += 1
        if calls["n"] <= 3:
            raise requests.ConnectionError("ağ yok")
        return orig(url, data=data, timeout=timeout)

    http.post = flaky
    assert ask(tg, clock).approved and calls["n"] > 3


def test_wrong_computer_clock_blocks_sending():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "approve")
    http.now = lambda: int(clock.now().timestamp()) + 3600  # Telegram saati bir saat ileride
    d = ask(tg, clock)
    assert d.status == "rejected" and "saat" in d.detail
    assert any("saati" in t for t in http.sent)


def test_stop_word_detection_and_helpers():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    assert not tg.stop_requested(0)
    http.add_message("dur", user_id=999)
    assert not tg.stop_requested(0)
    http.add_message("DUR")
    assert tg.stop_requested(0)
    assert normalize(" İptal ") == "IPTAL" and normalize("vazgeç") == "VAZGEC" and normalize("Hayır") == "HAYIR"
    codes = {new_code() for _ in range(200)}
    assert all(len(c) == 4 and c.isdigit() for c in codes) and len(codes) > 100
