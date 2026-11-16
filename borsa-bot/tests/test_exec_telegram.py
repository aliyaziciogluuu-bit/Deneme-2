"""Telegram onayı: yalnızca yetkili kişinin, o isteğe özel koduyla verilen onay geçerlidir."""
import pytest
import requests

from bistbot.exec.telegram import Telegram, TelegramError, command, new_code, normalize, request_approval
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


@pytest.mark.parametrize("text", ["ONAY 4821", "onay4821", " 4821 ", "Evet 4821", "/4821", "4821.", "ONAY 4821.",
                                  "48 21", "kod 4821", "4821@BistBot"])
def test_accepted_spellings(text):
    clock = FakeClock()
    tg, _ = fake_telegram(clock, lambda code: [text])
    assert ask(tg, clock).approved


@pytest.mark.parametrize("text", ["RED", "red", "Hayır", "iptal", "İPTAL", "dur", "vazgeç", "hayır dur", "iptal et",
                                  "DUR DUR DUR", "dur lütfen", "vazgeçtim", "red ediyorum", "🛑 DUR", "gönderme",
                                  "@BistBot dur", "/dur@BistBot", "4821 hayır gönderme"])
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


def conversation(http, replies):
    """Botun her yanıtından sonra sıradaki mesajı kuyruğa ekler (karşılıklı yazışma)."""
    orig, pending = http.post, list(replies)

    def post(url, data=None, timeout=None):
        resp = orig(url, data=data, timeout=timeout)
        if url.endswith("sendMessage") and pending:
            http.add_message(pending.pop(0))
        return resp

    http.post = post


def test_wrong_codes_then_lockout():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    conversation(http, ["1111", "2222", "3333", "4444", "5555", "4821"])
    d = ask(tg, clock)
    assert d.status == "rejected" and "yanlış" in d.detail and not d.by_user
    assert any("GÖNDERİLMEDİ" in t for t in http.sent)


def test_wrong_code_then_right_code_and_replies_never_repeat_the_code():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    conversation(http, ["0000", "merhaba", "4821"])
    assert ask(tg, clock).approved
    replies = http.sent[1:]
    assert any("Kod hatalı" in t for t in replies) and any("Anlaşılmadı" in t for t in replies)
    assert all("4821" not in t for t in replies)  # geçerli kod hata yanıtlarında yinelenmez


@pytest.mark.parametrize("after", ["RED", "DUR", "İptal", "/dur", "vazgeç.", "hayır dur gönderme", "iptal et"])
def test_last_word_wins_when_code_and_revocation_arrive_together(after):
    """Kod yazıldıktan sonra vazgeçildiyse (aynı yığında ya da hemen ardından) emir gönderilmez."""
    clock = FakeClock()
    tg, _ = fake_telegram(clock, lambda code: [code, after])
    d = ask(tg, clock)
    assert d.status == "rejected" and d.by_user
    clock = FakeClock()
    tg, _ = fake_telegram(clock, lambda code: [after, code])
    assert ask(tg, clock).status == "rejected"
    # Vazgeçme, kodun okunduğu çağrıdan hemen sonra geldiyse de yakalanır.
    clock = FakeClock()
    tg, http = fake_telegram(clock, "approve")
    orig, state = http.post, {"n": 0}

    def post(url, data=None, timeout=None):
        resp = orig(url, data=data, timeout=timeout)
        if url.endswith("getUpdates") and resp.json()["result"] and state["n"] == 0:
            state["n"] = 1
            http.add_message(after)
        return resp

    http.post = post
    assert ask(tg, clock).status == "rejected"


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
    assert tg.stop_requested(0) is False


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


def test_stop_words_after_approval_and_helpers():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    assert not tg.stop_requested(0)
    http.add_message("dur", user_id=999)
    assert not tg.stop_requested(0)
    # Onaydan sonra yalnız DUR değil, bütün vazgeçme sözcükleri ve yazım biçimleri durdurur.
    for text in ("DUR", "red", "İptal", "Hayır", "vazgeç", "Dur.", "/dur", "/dur@BistBot", "durdur", "STOP!",
                 "hayır dur", "@BistBot dur", "lütfen durdurun", "iptal edin"):
        http.add_message(text)
        assert tg.stop_requested(0), text
    for text in ("ne oldu?", "durum nedir", "durma devam et"):  # durdurma değil
        http.add_message(text)
        assert not tg.stop_requested(0), text
    assert "Anlaşılmadı" in http.sent[-1] and "DUR" in http.sent[-1]  # kullanıcı durdurduğunu sanmasın
    assert normalize(" İptal ") == "IPTAL" and normalize("vazgeç") == "VAZGEC" and normalize("Hayır") == "HAYIR"
    assert command("/dur@BistBot") == "DUR" and command("Dur.") == "DUR" and command("1234.") == "1234"
    codes = {new_code() for _ in range(200)}
    assert all(len(c) == 4 and c.isdigit() for c in codes) and len(codes) > 100


def test_stop_check_reads_the_whole_backlog():
    """Yabancıların yığdığı yüzlerce mesaj, yetkili kişinin DUR'unu geciktiremez."""
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    for _ in range(250):
        http.add_message("spam", user_id=999, chat_id=999)
    http.add_message("DUR")
    orig = http.post

    def paged(url, data=None, timeout=None):  # gerçek getUpdates gibi: çağrı başına en çok 100 güncelleme
        if url.endswith("getUpdates"):
            offset = int(data.get("offset") or 0)
            http.calls.append(("getUpdates", dict(data)))
            keep = [u for u in http.queue if u["update_id"] >= offset]
            http.queue = keep
            return type("R", (), {"status_code": 200, "json": lambda self: {"ok": True, "result": keep[:100]}})()
        return orig(url, data=data, timeout=timeout)

    http.post = paged
    assert tg.stop_requested(0)


def test_stop_check_backs_off_while_telegram_is_unreachable():
    ticks = iter(range(0, 1000, 1))
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    tg._monotonic = lambda: next(ticks)
    http.status = 500
    assert not tg.stop_requested(0)
    calls = len(http.calls)
    for _ in range(5):
        assert not tg.stop_requested(0)  # 10 sn dolmadan yeniden denenmez
    assert len(http.calls) == calls


def test_permanent_errors_stop_the_wait_immediately():
    for status in (409, 401, 403):
        clock = FakeClock()
        tg, http = fake_telegram(clock, "none")
        http.status = status
        start = clock.now()
        d = ask(tg, clock, minutes=480)
        assert d.status == "timeout" and (clock.now() - start).total_seconds() < 60  # 8 saat beklemez


def test_important_messages_are_retried_and_group_privacy_is_detected():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    orig, state = http.post, {"n": 0}

    def flaky(url, data=None, timeout=None):
        state["n"] += 1
        if state["n"] <= 2:
            raise requests.ConnectionError("ağ yok")
        return orig(url, data=data, timeout=timeout)

    http.post = flaky
    assert tg.deliver("rapor", clock=lambda: clock.now().timestamp(), sleep=clock.sleep) and http.sent == ["rapor"]
    http.post = lambda url, data=None, timeout=None: (_ for _ in ()).throw(requests.ConnectionError("yok"))
    assert tg.deliver("rapor", patience=60, clock=lambda: clock.now().timestamp(), sleep=clock.sleep) is False
    http.post = orig
    assert tg.can_read_group_messages() is False
    http.reads_groups = True
    assert tg.can_read_group_messages() is True
    assert not tg.is_group and Telegram(TOKEN, "-100123", "42", http=http).is_group


def test_unclear_text_next_to_the_code_is_not_an_approval():
    """Kodla birlikte anlaşılmayan bir şey yazıldıysa onay sayılmaz; kullanıcıya sorulur."""
    clock2 = FakeClock()
    tg2, http2 = fake_telegram(clock2, lambda code: [code, "bekle biraz"])
    orig = http2.post

    def post(url, data=None, timeout=None):
        resp = orig(url, data=data, timeout=timeout)
        if url.endswith("sendMessage") and "birlikte yazdığınızı anlamadım" in data["text"]:
            http2.add_message("4821")  # kullanıcı netleştirir: yalnızca kod
        return resp

    http2.post = post
    d = ask(tg2, clock2)
    assert d.approved and any("birlikte yazdığınızı anlamadım" in t for t in http2.sent)
    # Netleştirmezse süre dolar ve emir gitmez.
    clock3 = FakeClock()
    tg3, _ = fake_telegram(clock3, lambda code: [code, "sonra bakarız"])
    assert ask(tg3, clock3, minutes=5).status == "timeout"


def test_owner_text_from_an_earlier_page_survives_a_failed_later_page():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    http.add_message("DUR")
    for _ in range(150):
        http.add_message("spam", user_id=999, chat_id=999)
    orig, state = http.post, {"n": 0}

    def paged(url, data=None, timeout=None):
        if url.endswith("getUpdates"):
            state["n"] += 1
            if state["n"] == 2:
                raise requests.ConnectionError("ikinci sayfa okunamadı")
            offset = int(data.get("offset") or 0)
            keep = [u for u in http.queue if u["update_id"] >= offset]
            http.queue = keep
            return type("R", (), {"status_code": 200, "json": lambda self: {"ok": True, "result": keep[:100]}})()
        return orig(url, data=data, timeout=timeout)

    http.post = paged
    assert tg.stop_requested(0)  # ilk sayfadaki DUR, ikinci sayfa hatasına rağmen görülür


def test_a_single_stray_conflict_does_not_end_the_wait():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "approve")
    orig, state = http.post, {"n": 0}

    def post(url, data=None, timeout=None):
        if url.endswith("getUpdates"):
            state["n"] += 1
            if state["n"] == 2:  # başka bir yerden bir kez getUpdates çağrıldı
                return type("R", (), {"status_code": 409, "json": lambda self: {"ok": False}})()
        return orig(url, data=data, timeout=timeout)

    http.post = post
    assert ask(tg, clock).approved


def test_long_reports_resend_only_the_missing_parts():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    text = "\n".join(f"satır {i} " + "x" * 60 for i in range(120))  # iki parçaya bölünür
    orig, state = http.post, {"n": 0}

    def post(url, data=None, timeout=None):
        if url.endswith("sendMessage"):
            state["n"] += 1
            if state["n"] in (2, 3):  # ikinci parça iki kez başarısız
                raise requests.ConnectionError("yok")
        return orig(url, data=data, timeout=timeout)

    http.post = post
    from bistbot.live.notify import split_message

    parts = split_message(text)
    assert len(parts) >= 2
    assert tg.deliver(text, clock=lambda: clock.now().timestamp(), sleep=clock.sleep)
    assert http.sent == parts  # her parça tam bir kez: gönderilmiş ilk parça yinelenmedi


def test_stop_poll_backoff_is_measured_after_the_failure():
    clock = FakeClock()
    tg, http = fake_telegram(clock, "none")
    now = {"t": 0.0}
    tg._monotonic = lambda: now["t"]
    orig = http.post

    def slow_failure(url, data=None, timeout=None):
        now["t"] += 12.0  # hata 12 saniye sürdü
        raise requests.ConnectionError("yavaş ağ")

    http.post = slow_failure
    assert not tg.stop_requested(0)
    before = now["t"]
    for _ in range(5):
        assert not tg.stop_requested(0)  # hemen yeniden denenmez (her emirde 12 sn beklenmez)
    assert now["t"] == before
    now["t"] += 11.0
    http.post = orig
    http.add_message("DUR")
    assert tg.stop_requested(0)  # süre dolunca yoklama sürer
    # Anında dönen tek bir hata sonraki yoklamayı geciktirmez.
    http.status = 502
    assert not tg.stop_requested(0)
    http.status = 200
    http.add_message("dur")
    assert tg.stop_requested(0)
