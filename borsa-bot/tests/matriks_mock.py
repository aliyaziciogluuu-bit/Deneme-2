"""Sahte Matriks IQ sunucusu (testler için).

Matriks'in resmî API belgesindeki (sürüm 1.6) örnek iletileri ve yayımladığı örnek istemcileri
taklit eder: JSON iletiler ``0x0B`` ile biter, bağlantının başında sonlandırıcısız
``SetMessageType0`` metni gelir, yanıtlar ``ApiCommands`` alanında yanıt türünü taşır. Belgedeki
örneklere uyularak yanıtlarda emir numarası ``OrderID`` / ``OrderID2``, pozisyon satırlarında
borsa ``ExchangeID`` adıyla yazılır; yeni emrin ilk yanıtında ``OrdStatus`` boştur (``\u0000``),
sonraki bildirimlerde ``Quantity`` 0 gelir ve yön ``OrderSide`` 0 (alış) / 1 (satış) olarak döner.
Gerçek programın davranışı bundan farklı olabilir; bu sunucu istemcinin belgeyle tutarlı
çalıştığını sınar.
"""
from __future__ import annotations

import json
import socket
import threading
import time

VT = b"\x0b"


class MockMatriks:
    def __init__(self, positions=None, behaviour=None, default="fill", echo_client_id=True, side_echo="zero",
                 chunk=None, accounts=None, info=None, cash_rows=False):
        self.positions = dict(positions or {})
        #: sembol -> davranış: fill | rest | reject | partial | silent | drop | reject_once
        self.behaviour = dict(behaviour or {})
        self.default = default
        self.echo_client_id = echo_client_id
        self.side_echo = side_echo  # zero (0 alış, 1 satış) | same | swapped | always_zero (alan doldurulmuyor)
        self.chunk = chunk
        self.accounts = accounts if accounts is not None else [{
            "BrokageId": "7", "BrokageName": "Test Yatırım",
            "AccountIdList": [{"AccountId": "0~123456", "ExchangeId": 4}, {"AccountId": "0~123456", "ExchangeId": 9}],
        }]
        self.info = info if info is not None else [
            {"Code": "T2", "Key": "Kullanılabilir Bakiye", "Value": "12.345,67", "DataType": 1},
            {"Code": "LMT", "Key": "İşlem Limiti", "Value": "50000", "DataType": 1},
        ]
        self.cash_rows = cash_rows
        self.received: list[dict] = []
        self.new_orders: list[dict] = []
        self.cancels: list[dict] = []
        self.orders: dict[str, dict] = {}
        self.raw_prefix = b""
        self._seen_reject: set[str] = set()
        self._next_id = 1000
        self._lock = threading.Lock()
        self._conns: list[socket.socket] = []
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(4)
        self.port = self._server.getsockname()[1]
        self._stop = threading.Event()
        threading.Thread(target=self._accept, daemon=True).start()

    # -- yaşam döngüsü ---------------------------------------------------------------
    def close(self) -> None:
        self._stop.set()
        for s in [self._server, *self._conns]:
            try:
                s.close()
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _accept(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            self._conns.append(conn)
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        buf = bytearray()
        while not self._stop.is_set():
            try:
                data = conn.recv(65536)
            except OSError:
                return
            if not data:
                return
            buf.extend(data)
            if buf.startswith(b"SetMessageType"):
                # sonlandırıcısız kip iletisi: "SetMessageType" + tek hane
                if len(buf) < len(b"SetMessageType0"):
                    continue
                self.raw_prefix = bytes(buf[:15])
                del buf[:15]
            while VT in buf:
                cut = buf.index(VT)
                raw, buf = bytes(buf[:cut]), buf[cut + 1:]
                try:
                    msg = json.loads(raw.decode("utf-8"))
                except ValueError:
                    continue
                self.received.append(msg)
                try:
                    self._dispatch(conn, msg)
                except OSError:
                    return

    # -- gönderme --------------------------------------------------------------------
    def _send(self, conn: socket.socket, *messages: dict) -> None:
        data = b"".join(json.dumps(m, ensure_ascii=False).encode("utf-8") + VT for m in messages)
        if self.chunk:
            for i in range(0, len(data), self.chunk):
                conn.sendall(data[i:i + self.chunk])
                time.sleep(0.002)
        else:
            conn.sendall(data)

    def push(self, *messages: dict) -> None:
        """Bağlı tüm istemcilere ileti yollar (sonradan gerçekleşme vb.)."""
        for conn in list(self._conns):
            try:
                self._send(conn, *messages)
            except OSError:
                pass

    # -- protokol --------------------------------------------------------------------
    def _echo_side(self, code):
        if self.side_echo == "zero":
            return code - 1
        if self.side_echo == "always_zero":
            return 0
        if self.side_echo == "swapped":
            return {1: 2, 2: 1}.get(code, code)
        return code

    @staticmethod
    def _pushed(order: dict) -> dict:
        """Belgedeki bildirim örneği: ``Quantity`` 0, emir ve işlem tipi boş."""
        return {**order, "Quantity": 0.0, "OrderType": "\u0000", "TransactionType": "\u0000", "ApiCommands": 0}

    def _order_message(self, order: dict) -> dict:
        return {**self._pushed(order), "ApiCommands": 3}

    def _dispatch(self, conn: socket.socket, m: dict) -> None:
        cmd = m.get("ApiCommands")
        ident = {"BrokageId": m.get("BrokageId"), "AccountId": m.get("AccountId"), "ExchangeId": m.get("ExchangeId")}
        if cmd == 0:
            self._send(conn, {"Accounts": self.accounts, "ApiCommands": 0})
        elif cmd == 1:
            rows = [{"Symbol": s, "QtyT": 0.0, "QtyT2": q, "QtyAvailable": q, "IsSymbol": True, "ExchangeID": 4,
                     "LastPx": 10.0, "Side": 0, "AccountId": m.get("AccountId"), "BrokageId": m.get("BrokageId"),
                     "ApiCommands": 0}
                    for s, q in self.positions.items()]
            if self.cash_rows:
                rows.append({"Symbol": "TRY", "QtyT2": 50000.0, "QtyAvailable": 50000.0, "IsSymbol": False, "ExchangeID": 4})
            self._send(conn, {**ident, "PositionResponseList": rows, "ApiCommands": 1})
        elif cmd == 2:
            working = [self._pushed(o) for o in self.orders.values() if o["OrdStatus"] in ("0", "1", "A")]
            self._send(conn, {**ident, "OrderApiModels": working, "ApiCommands": 2})
        elif cmd == 3:
            self._new_order(conn, m)
        elif cmd == 4:
            self.cancels.append(m)
            order = self.orders.get(str(m.get("OrderID") or m.get("OrderId")))
            if order is not None and order["OrdStatus"] in ("0", "1", "A"):
                order.update(OrdStatus="4", LeavesQty=0.0, Explanation="İptal edildi")
                self._send(conn, self._order_message(order))
        elif cmd == 6:
            self._send(conn, {"KeepAliveDate": m.get("KeepAliveDate"), "ApiCommands": 7})
        elif cmd == 7:
            self._send(conn, {"Informations": self.info, "Request": m, "ApiCommands": 8})
        elif cmd == 8:
            done = [self._pushed(o) for o in self.orders.values() if o["OrdStatus"] == "2"]
            self._send(conn, {**ident, "FilledOrderApiModels": done, "ApiCommands": 9})

    def _new_order(self, conn: socket.socket, m: dict) -> None:
        self.new_orders.append(m)
        symbol = m["Symbol"]
        mode = self.behaviour.get(symbol, self.default)
        if mode == "reject_once":
            mode = "fill" if symbol in self._seen_reject else "reject"
            self._seen_reject.add(symbol)
        if mode == "silent":
            return
        if mode == "drop":
            conn.close()
            return
        with self._lock:
            self._next_id += 1
            oid = str(self._next_id)
        qty = float(m["OrderQty"])
        order = {
            "Symbol": symbol, "OrderID": oid, "OrderID2": f"{oid}*{m['Price']}".replace(".", ","), "OrderQty": qty,
            "OrdStatus": "0", "LeavesQty": qty, "FilledQty": 0.0, "AvgPx": 0.0, "TradeDate": "2026-12-01T09:41:00",
            "TransactTime": "09:41:00", "StopPx": 0.0, "Explanation": "Bekliyor", "ExpireDate": "0001-01-01T00:00:00",
            "Price": m["Price"], "Quantity": qty, "OrderSide": self._echo_side(m["OrderSide"]),
            "IncludeAfterSession": False, "TimeInForce": m.get("TimeInForce"), "OrderType": m.get("OrderType"),
            "TransactionType": m.get("TransactionType"), "AccountId": m["AccountId"], "BrokageId": m["BrokageId"],
        }
        if self.echo_client_id:
            order["ClientOrderId"] = m.get("ClientOrderId")
        self.orders[oid] = order
        # Belgedeki "Yeni Emir İsteği" örnek çıktısı: durum henüz boş, açıklama yok.
        first = {**order, "OrdStatus": "\u0000", "Explanation": None, "TradeDate": "0001-01-01T00:00:00",
                 "TransactTime": "00:00:00", "ApiCommands": 3}
        if mode == "reject":
            order.update(OrdStatus="8", LeavesQty=0.0, Explanation="Yetersiz bakiye")
            self._send(conn, first, self._order_message(order))
            return
        accepted = self._order_message(dict(order))
        if mode == "rest":
            self._send(conn, first, accepted)
        elif mode == "partial":
            half = float(max(int(qty) // 2, 1))
            order.update(OrdStatus="1", LeavesQty=qty - half, FilledQty=half, AvgPx=m["Price"],
                         Explanation="Kısmen gerçekleşti")
            self._send(conn, first, accepted, self._order_message(order))
        else:  # fill
            order.update(OrdStatus="2", LeavesQty=0.0, FilledQty=qty, AvgPx=m["Price"], Explanation="Gerçekleşti")
            self._send(conn, first, accepted, self._order_message(order))

    def fill(self, symbol: str, price: float | None = None) -> None:
        """Bekleyen emri sonradan gerçekleştirir."""
        for order in self.orders.values():
            if order["Symbol"] == symbol and order["OrdStatus"] in ("0", "1", "A"):
                order.update(OrdStatus="2", LeavesQty=0.0, FilledQty=float(order["OrderQty"]), AvgPx=price or order["Price"],
                             Explanation="Gerçekleşti")
                self.push(self._order_message(order))
