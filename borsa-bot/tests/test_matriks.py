"""Matriks IQ istemcisi, sahte sunucuya karşı (gerçek programla denenmemiştir)."""
import time

import pytest

from bistbot.exec.base import BrokerError, NotSent, OrderRequest
from bistbot.exec.matriks import MatriksBroker, SideMismatch, client_order_id, mask
from bistbot.exec.settings import MatriksSettings
from matriks_mock import MockMatriks


def broker_for(server, **kw):
    settings = MatriksSettings(port=server.port, zaman_asimi=kw.pop("timeout", 3.0), **kw)
    return MatriksBroker(settings, echo_buy=kw.pop("echo_buy", None))


def wait_done(b, st, seconds=3.0):
    deadline = time.time() + seconds
    while not b.refresh(st).done and time.time() < deadline:
        time.sleep(0.02)
    return b.refresh(st)


def order(symbol="GARAN", side="buy", lots=10, price=98.5, key=None):
    return OrderRequest(key or f"2026-12-01|{symbol}|{side}", symbol, side, lots, price)


def test_connect_selects_bist_account_and_reads_positions_and_cash():
    with MockMatriks(positions={"GARAN": 120.0, "THYAO": 30.0}, cash_rows=True) as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=3.0, nakit_anahtari="kullanılabilir bakiye"))
        b.connect()
        try:
            assert (b.brokage_id, b.account_id, b.brokage_name) == ("7", "0~123456", "Test Yatırım")
            assert server.raw_prefix == b"SetMessageType0"  # JSON kipi, sonlandırıcısız
            assert b.positions() == {"GARAN": 120, "THYAO": 30}  # nakit satırı (IsSymbol=false) hisse sayılmaz
            assert b.cash() == pytest.approx(12345.67)  # "12.345,67" Türkçe yazım
            sent = [m for m in server.received if m["ApiCommands"] == 1][0]
            assert sent == {"BrokageId": "7", "AccountId": "0~123456", "ExchangeId": 4, "ApiCommands": 1}
            assert "123456" not in b.describe() and b.describe().endswith("…456")
        finally:
            b.close()


def test_new_order_payload_matches_vendor_sample_and_fill_is_reported():
    with MockMatriks() as server:
        b = broker_for(server)
        b.connect()
        try:
            st = b.place(order("GARAN", "buy", 10, 98.5))
            assert (st.status, st.filled_lots, st.avg_price) == ("filled", 10, 98.5)
            assert st.broker_id == "1001"
            m = server.new_orders[0]
            # Matriks örnek uygulaması: alış 1, limit '2', günlük '0', normal '1'.
            assert (m["ApiCommands"], m["OrderSide"], m["OrderType"], m["TimeInForce"], m["TransactionType"]) == (3, 1, "2", "0", "1")
            assert (m["Symbol"], m["Price"], m["Quantity"], m["OrderQty"], m["LeavesQty"]) == ("GARAN", 98.5, 10, 10, 10)
            assert (m["AccountId"], m["BrokageId"], m["OrdStatus"]) == ("0~123456", "7", "0")
            assert len(m["ClientOrderId"]) == 20 and m["ClientOrderId"].isdigit()
            # Örnek istemcinin serileştirdiği tüm alanlar bulunur.
            for name in ("OrderId", "OrderId2", "FilledQty", "AvgPx", "TradeDate", "TransactTime", "StopPx",
                         "Explanation", "ExpireDate", "IncludeAfterSession"):
                assert name in m
            st2 = b.place(order("THYAO", "sell", 3, 312.5))
            assert server.new_orders[1]["OrderSide"] == 2 and st2.status == "filled"
        finally:
            b.close()


def test_fragmented_and_coalesced_frames_are_reassembled():
    with MockMatriks(positions={"GARAN": 5.0}, chunk=7) as server:
        b = broker_for(server)
        b.connect()
        try:
            assert b.positions() == {"GARAN": 5}
            st = b.place(order())  # iki ileti 7 baytlık parçalarla gelir: önce kabul, sonra gerçekleşme
            assert st.status in ("accepted", "filled")
            assert wait_done(b, st).status == "filled"
        finally:
            b.close()


def test_reject_rest_partial_and_later_fill():
    with MockMatriks(behaviour={"AAA": "reject", "BBB": "rest", "CCC": "partial"}) as server:
        b = broker_for(server)
        b.connect()
        try:
            rejected = b.place(order("AAA"))
            assert rejected.status == "rejected" and "Yetersiz bakiye" in rejected.message and rejected.done
            resting = b.place(order("BBB"))
            assert resting.status == "accepted" and not resting.done
            partial = b.place(order("CCC", lots=10))
            deadline = time.time() + 3
            while b.refresh(partial).status != "partial" and time.time() < deadline:
                time.sleep(0.05)
            assert (b.refresh(partial).status, b.refresh(partial).filled_lots) == ("partial", 5)
            server.fill("BBB", 97.0)
            deadline = time.time() + 3
            while not b.refresh(resting).done and time.time() < deadline:
                time.sleep(0.05)
            done = b.refresh(resting)
            assert (done.status, done.filled_lots, done.avg_price) == ("filled", 10, 97.0)
        finally:
            b.close()


def test_silent_server_gives_unknown_not_resend():
    with MockMatriks(default="silent") as server:
        b = broker_for(server, timeout=0.6)
        b.connect()
        try:
            st = b.place(order())
            assert st.status == "unknown" and not st.done
            assert len(server.new_orders) == 1  # istemci kendiliğinden yeniden göndermez
        finally:
            b.close()


def test_connection_drop_is_reported():
    with MockMatriks(default="drop") as server:
        b = broker_for(server, timeout=1.5)
        b.connect()
        try:
            st = b.place(order())
            assert st.status == "unknown"
            with pytest.raises(BrokerError):
                b.place(order("THYAO"))
        finally:
            b.close()


def test_matching_without_client_order_id_echo():
    with MockMatriks(echo_client_id=False, default="rest") as server:
        b = broker_for(server)
        b.connect()
        try:
            a = b.place(order("GARAN", lots=10, price=98.5))
            c = b.place(order("GARAN", lots=7, price=98.5, key="2026-12-01|GARAN|buy|2"))
            assert a.status == c.status == "accepted" and a.broker_id != c.broker_id
            server.fill("GARAN")
            deadline = time.time() + 3
            while not (b.refresh(a).done and b.refresh(c).done) and time.time() < deadline:
                time.sleep(0.05)
            assert (b.refresh(a).filled_lots, b.refresh(c).filled_lots) == (10, 7)
        finally:
            b.close()


def test_side_mismatch_cancels_and_raises():
    """Yön testinde alış yanıtı 1 görüldüyse, alış emrine 2 dönen sunucu yön karışıklığıdır."""
    with MockMatriks(default="rest", side_echo="swapped") as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0), echo_buy=1)
        b.connect()
        try:
            with pytest.raises(SideMismatch):
                b.place(order())
            assert len(server.cancels) == 1 and server.cancels[0]["ApiCommands"] == 4
            assert server.cancels[0]["OrderId"] == "1001"
        finally:
            b.close()


def test_side_echo_convention_is_respected():
    """Eski yanıt biçimi (0 alış, 1 satış) yön testinde öğrenildiyse sorun sayılmaz."""
    with MockMatriks(side_echo="zero") as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0), echo_buy=0)
        b.connect()
        try:
            assert b.place(order("GARAN", "buy")).status == "filled"
            assert b.place(order("THYAO", "sell")).status == "filled"
        finally:
            b.close()


def test_cancel_resting_order():
    with MockMatriks(default="rest") as server:
        b = broker_for(server)
        b.connect()
        try:
            st = b.place(order())
            final = b.cancel(st)
            assert final.status == "cancelled" and final.done
            sent = server.cancels[0]
            assert (sent["OrderId"], sent["Symbol"], sent["OrderType"], sent["TransactionType"]) == ("1001", "GARAN", "2", "1")
            assert b.open_orders() == []
        finally:
            b.close()


def test_account_selection_errors():
    two = [{"BrokageId": "7", "BrokageName": "A", "AccountIdList": [{"AccountId": "1", "ExchangeId": 4}]},
           {"BrokageId": "9", "BrokageName": "B", "AccountIdList": [{"AccountId": "2", "ExchangeId": 4}]}]
    with MockMatriks(accounts=two) as server:
        b = broker_for(server)
        with pytest.raises(BrokerError, match="Birden çok"):
            b.connect()
        b.close()
        chosen = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0, araci_kurum_id="9", hesap_id="2"))
        chosen.connect()
        assert chosen.account_id == "2"
        chosen.close()
    with MockMatriks(accounts=[]) as server:
        b = broker_for(server)
        with pytest.raises(BrokerError, match="bulunamadı"):
            b.connect()
        b.close()


def test_not_running_gives_clear_error():
    b = MatriksBroker(MatriksSettings(port=1, zaman_asimi=1.0))
    with pytest.raises(BrokerError, match="bağlanılamadı"):
        b.connect()


def test_missing_lot_field_means_nothing_sellable():
    with MockMatriks(positions={"GARAN": 50.0}) as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0, lot_alanlari=("YokBoyleAlan",)))
        b.connect()
        try:
            assert b.positions() == {}
        finally:
            b.close()


def test_helpers():
    a, b = client_order_id(1_800_000_000.0), client_order_id(1_800_000_001.0)
    assert len(a) == 20 and a.isdigit() and a < b
    assert mask("0~123456") == "…456" and mask("12") == "…"


def test_official_document_message_shapes_are_understood():
    """Belgedeki örnek iletiler: ``OrderID`` yazımı, boş ilk durum, ``Quantity`` = 0, ``ExchangeID``."""
    with MockMatriks(positions={"GARAN": 120.0}, default="rest", echo_client_id=False) as server:
        b = broker_for(server)
        b.connect()
        try:
            assert b.positions() == {"GARAN": 120}  # satırlarda "ExchangeID" (büyük ID)
            st = b.place(order("THYAO", "buy", 9, 9.47))
            assert st.broker_id == "1001" and st.status == "accepted"  # "OrderID" okunur
            assert "bekleniyor" in st.message or "bekliyor" in st.message
            deadline = time.time() + 2
            while "Bekliyor" not in b.refresh(st).message and time.time() < deadline:
                time.sleep(0.02)
            assert "Bekliyor" in b.refresh(st).message  # ikinci bildirim emir numarasıyla eşleşti
            server.fill("THYAO", 9.40)  # bildirimde Quantity 0, OrderQty 9
            done = wait_done(b, st)
            assert (done.status, done.filled_lots, done.avg_price) == ("filled", 9, 9.40)
            assert b.open_orders() == [] and len(b.filled_orders()) == 1
        finally:
            b.close()


def test_late_statusless_message_does_not_reopen_a_finished_order():
    with MockMatriks(default="fill") as server:
        b = broker_for(server)
        b.connect()
        try:
            st = wait_done(b, b.place(order("GARAN", "buy", 10, 98.5)))
            assert st.status == "filled"
            stale = {**server.orders["1001"], "OrdStatus": "\u0000", "FilledQty": 0.0, "ApiCommands": 3}
            server.push(stale)
            time.sleep(0.2)
            assert b.refresh(st).status == "filled" and b.refresh(st).filled_lots == 10
        finally:
            b.close()


def test_case_insensitive_messages_and_number_formats():
    from bistbot.exec.matriks import Msg, _number, _order_qty

    m = Msg({"OrderID": "7", "ExchangeID": 4, "Quantity": 0.0, "OrderQty": 0.0, "LeavesQty": 8.0, "FilledQty": 1.0})
    assert m.get("OrderId") == "7" and m["orderid"] == "7" and "exchangeid" in m and m.get("yok") is None
    m["_rx"] = 1.5
    assert m["_rx"] == 1.5 and _order_qty(m) == 9.0
    assert _number("9574528.62") == 9574528.62 and _number("12.345,67") == 12345.67
    assert _number("-1,570.50") == -1570.5 and _number("1234,5") == 1234.5 and _number("") == 0.0
    assert _number(True) == 0.0 and _number(None) == 0.0 and _number("abc", default=-1.0) == -1.0


# ------------------------------------------------------------------ bağımsız incelemenin senaryoları
def test_order_id_arriving_in_a_later_event_is_adopted():
    """İlk bildirim emir numarasız gelse de sonraki bildirimler aynı emre yazılır."""
    with MockMatriks(default="pending", echo_client_id=False) as server:
        b = broker_for(server)
        b.connect()
        try:
            st = b.place(order("GARAN", "buy", 10, 98.5))
            deadline = time.time() + 2
            while b.refresh(st).broker_id is None and time.time() < deadline:
                time.sleep(0.02)
            assert b.refresh(st).broker_id == "1001"
            server.fill("GARAN", 98.0)
            assert wait_done(b, st).filled_lots == 10
        finally:
            b.close()


def test_foreign_orders_are_never_attributed_to_ours():
    with MockMatriks(default="silent") as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=0.8), echo_buy=0)
        b.connect()
        try:
            foreign = {"Symbol": "GARAN", "OrderID": "777", "OrderQty": 10.0, "Quantity": 0.0, "Price": 98.5,
                       "OrdStatus": "2", "FilledQty": 10.0, "OrderSide": 0, "AccountId": "0~123456", "ApiCommands": 3}
            import threading
            # Bizim alışımız yanıt beklerken aynı içerikte ama başkasına ait iletiler gelir:
            # (1) başka bir istemci kimliği taşıyan, (2) başka hesaba ait, (3) adedi farklı olan.
            threading.Timer(0.2, lambda: server.push(
                {**foreign, "ClientOrderId": "baska-kimlik"},
                {**foreign, "AccountId": "0~999999"},
                {**foreign, "OrderQty": 11.0, "FilledQty": 11.0},
            )).start()
            st = b.place(order("GARAN", "buy", 10, 98.5))
            assert st.status == "unknown" and st.broker_id is None  # hiçbiri bizim emrimize yazılmadı
        finally:
            b.close()


def test_reversed_order_is_caught_even_when_the_server_does_not_echo_client_ids():
    """Kimlik geri gelmiyorsa da: içeriği aynı, yönü ters ileti emrimize yazılır, emir iptal edilir, gönderim durur."""
    with MockMatriks(default="rest", side_echo="swapped", echo_client_id=False) as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0), echo_buy=1)
        b.connect()
        try:
            with pytest.raises(SideMismatch) as err:
                b.place(order("GARAN", "buy", 10, 98.5))
            assert len(server.cancels) == 1 and server.cancels[0]["OrderID"] == "1001"
            assert err.value.state.status == "cancelled"
        finally:
            b.close()


def test_content_matching_stops_once_server_is_seen_to_echo_client_ids():
    with MockMatriks(behaviour={"THYAO": "silent"}) as server:
        b = broker_for(server, timeout=0.8)
        b.connect()
        try:
            assert wait_done(b, b.place(order("GARAN", "buy", 10, 98.5))).status == "filled"  # kimlik geri geldi
            import threading
            threading.Timer(0.2, lambda: server.push(
                {"Symbol": "THYAO", "OrderID": "555", "OrderQty": 3.0, "Price": 312.5, "OrdStatus": "0",
                 "OrderSide": 0, "AccountId": "0~123456", "ApiCommands": 3})).start()
            st = b.place(order("THYAO", "buy", 3, 312.5))
            assert st.status == "unknown"  # kimliksiz ileti elle girilmiş başka bir emirdir
        finally:
            b.close()


def test_refresh_reports_lost_monitoring_instead_of_stale_state():
    with MockMatriks(default="rest") as server:
        b = broker_for(server)
        b.connect()
        try:
            st = b.place(order())
            assert b.refresh(st).status == "accepted"
            server.session(logged_in=False)
            time.sleep(0.2)
            with pytest.raises(BrokerError, match="izlenemiyor"):
                b.refresh(st)
            server.session(logged_in=True)
            time.sleep(0.2)
            assert b.refresh(st).status == "accepted"
            server.drop_clients()
            time.sleep(1.3)
            with pytest.raises(BrokerError, match="izlenemiyor"):
                b.refresh(st)
        finally:
            b.close()


def test_orders_blocked_before_sending_are_definitely_not_sent_and_reconnect_works():
    with MockMatriks() as server:
        b = broker_for(server)
        b.connect()
        try:
            server.session(logged_in=False)
            time.sleep(0.2)
            with pytest.raises(NotSent):
                b.place(order())
            server.drop_clients()
            time.sleep(1.3)
            with pytest.raises(NotSent):
                b.place(order())
            assert server.new_orders == []
            b.ensure_ready()  # yeniden bağlanır ve hesabı yeniden seçer
            assert b.place(order()).status in ("accepted", "filled") and len(server.new_orders) == 1
            # Eski bağlantının iş parçacıkları yeni bağlantıyı kapatmamalı.
            time.sleep(1.3)
            assert b.wire.connected and b.positions() == {}
        finally:
            b.close()


def test_sync_recovers_fills_missed_while_disconnected():
    with MockMatriks(default="rest") as server:
        b = broker_for(server)
        b.connect()
        try:
            st = b.place(order("GARAN", "buy", 10, 98.5))
            deadline = time.time() + 2
            while b.refresh(st).broker_id is None and time.time() < deadline:
                time.sleep(0.02)
            server.drop_clients()
            time.sleep(1.3)
            server.fill("GARAN", 98.1)  # bildirim kimseye ulaşmaz
            b.ensure_ready()
            assert b.refresh(st).status == "accepted"  # henüz bilinmiyor
            b.sync()
            done = b.refresh(st)
            assert (done.status, done.filled_lots, done.avg_price) == ("filled", 10, 98.1)
        finally:
            b.close()


def test_side_mismatch_reports_the_real_outcome():
    # (a) Emir iptal edilebildi.
    with MockMatriks(default="rest", side_echo="swapped") as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0), echo_buy=1)
        b.connect()
        try:
            with pytest.raises(SideMismatch) as err:
                b.place(order())
            assert "emir iptal edildi" in str(err.value) and err.value.state.status == "cancelled"
        finally:
            b.close()
    # (b) Emir hemen gerçekleşti: iptal gönderilmez ve mesaj bunu söyler.
    with MockMatriks(default="fill", side_echo="swapped") as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0), echo_buy=1)
        b.connect()
        try:
            with pytest.raises(SideMismatch) as err:
                b.place(order())
            text = str(err.value)
            assert ("GERÇEKLEŞTİ" in text or "iptal edildi" in text) and "iptal istendi" not in text
            if "GERÇEKLEŞTİ" in text:
                assert server.cancels == [] and err.value.state.filled_lots == 10
        finally:
            b.close()
    # (c) Emir numarası ilk bildirimde yok: numara beklenir, sonra iptal gönderilir.
    with MockMatriks(default="pending", side_echo="swapped") as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0), echo_buy=1)
        b.connect()
        try:
            with pytest.raises(SideMismatch) as err:
                b.place(order())
            assert len(server.cancels) == 1 and server.cancels[0]["OrderID"] == "1001"
            assert err.value.state.status == "cancelled"
        finally:
            b.close()


def test_sync_tolerates_queries_that_stay_unanswered_when_empty():
    with MockMatriks(default="rest") as server:
        server.silent_when_empty = True
        b = broker_for(server, timeout=1.0)
        b.connect()
        try:
            st = b.place(order("GARAN", "buy", 10, 98.5))
            started = time.time()
            b.sync()  # gerçekleşen ve iptal listeleri boş: yanıt gelmez, hata sayılmaz
            first = time.time() - started
            assert b.refresh(st).status == "accepted"
            started = time.time()
            b.sync()
            assert time.time() - started < first  # ikinci turda yanıtsız sorgular için uzun beklenmez
            server.fill("GARAN")
            b.sync()
            assert wait_done(b, st).status == "filled"
        finally:
            b.close()


def test_side_mismatch_cancels_the_remainder_of_a_partially_filled_order():
    with MockMatriks(default="partial", side_echo="swapped") as server:
        b = MatriksBroker(MatriksSettings(port=server.port, zaman_asimi=2.0), echo_buy=1)
        b.connect()
        try:
            with pytest.raises(SideMismatch) as err:
                b.place(order("GARAN", "buy", 10, 98.5))
            text = str(err.value)
            assert len(server.cancels) == 1 and err.value.state.done  # çalışan kalan için iptal gönderildi
            if err.value.state.filled_lots:  # kısmi gerçekleşme iptalden önce görüldüyse mesajda yer alır
                assert "5 lot GERÇEKLEŞTİ" in text and "kalan iptal edildi" in text
            else:
                assert "emir iptal edildi" in text
        finally:
            b.close()
