"""Emir katmanı testleri için sahte saat, sahte Telegram ve betikli aracı kurum."""
from __future__ import annotations

import datetime as dt
import re

from bistbot.exec.base import BrokerError, NotSent, OrderRequest, OrderState
from bistbot.exec.runner import IST
from bistbot.exec.settings import ExecSettings, Limits, TelegramSettings
from bistbot.exec.telegram import Telegram
from bistbot.exec.ticket import parse_ticket

SESSION = dt.date(2026, 12, 1)  # salı
TOKEN = "123456:GIZLI-ANAHTAR"


class FakeClock:
    """``sleep`` gerçek beklemeden saati ilerletir."""

    def __init__(self, hour=9, minute=20, second=0, day=SESSION):
        self.t = dt.datetime.combine(day, dt.time(hour, minute, second), IST)
        self.sleeps: list[float] = []

    def now(self) -> dt.datetime:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += dt.timedelta(seconds=max(seconds, 0.001))


def payload(orders=None, positions=None, session=SESSION, as_of=dt.date(2026, 11, 30), equity=100_000.0,
            generated="2026-11-30T16:25:00+00:00"):
    if orders is None:
        orders = [
            {"symbol": "GARAN", "side": "sell", "lots": 40, "ref_price": 100.0, "limit_price": 97.0},
            {"symbol": "THYAO", "side": "buy", "lots": 15, "ref_price": 300.0, "limit_price": 309.0},
            {"symbol": "ASELS", "side": "buy", "lots": 50, "ref_price": 80.0, "limit_price": 82.4},
        ]
    if positions is None:
        positions = [{"symbol": "GARAN", "lots": 40}, {"symbol": "AKBNK", "lots": 70}]
    return {"as_of": str(as_of), "next_session": str(session), "generated_at": generated, "equity": equity,
            "orders": orders, "positions": positions}


def ticket(**kw):
    return parse_ticket(payload(**kw))


def settings(tmp_path, mod="deneme", **kw) -> ExecSettings:
    tg = kw.pop("telegram", TelegramSettings(token=TOKEN, chat_id="555", onaylayan_id=""))
    return ExecSettings(mod=mod, klasor=tmp_path / ".emir", telegram=tg, sinirlar=kw.pop("sinirlar", Limits()), **kw)


class _Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body if body is not None else {"ok": True, "result": {}}

    def json(self):
        return self._body


class FakeTelegramHttp:
    """``requests`` yerine geçer. ``reply``: onay isteği görülünce kuyruğa eklenecek yanıt(lar)."""

    def __init__(self, clock=None, reply="approve", user_id=555, chat_id=555):
        self.clock, self.reply, self.user_id, self.chat_id = clock, reply, user_id, chat_id
        self.sent: list[str] = []
        self.queue: list[dict] = []
        self.calls: list[tuple[str, dict]] = []
        self._update_id = 100
        self.status = 200
        self.reads_groups = False

    def now(self) -> int:
        return int(self.clock.now().timestamp()) if self.clock else 1_800_000_000

    def add_message(self, text, user_id=None, chat_id=None, date=None, is_bot=False):
        self._update_id += 1
        self.queue.append({"update_id": self._update_id, "message": {
            "text": text, "date": self.now() if date is None else date,
            "chat": {"id": self.chat_id if chat_id is None else chat_id},
            "from": {"id": self.user_id if user_id is None else user_id, "is_bot": is_bot}}})

    def post(self, url, data=None, timeout=None):
        assert url.startswith("https://api.telegram.org/bot" + TOKEN + "/")
        method = url.rsplit("/", 1)[1]
        self.calls.append((method, dict(data or {})))
        if self.status != 200:
            return _Resp(self.status, {"ok": False})
        if method == "sendMessage":
            text = data["text"]
            self.sent.append(text)
            code = re.search(r"Onaylamak için (\d{4}) yazın", text)
            if code:
                answers = self.reply(code.group(1)) if callable(self.reply) else {
                    "approve": [code.group(1)], "reject": ["RED"], "none": [],
                    "wrong_user": [(code.group(1), 999)],
                }[self.reply]
                for a in answers:
                    if isinstance(a, tuple):
                        self.add_message(a[0], user_id=a[1])
                    else:
                        self.add_message(a)
            return _Resp(body={"ok": True, "result": {"date": self.now()}})
        if method == "getMe":
            return _Resp(body={"ok": True, "result": {"id": 1, "is_bot": True, "can_read_all_group_messages": self.reads_groups}})
        if method == "getUpdates":
            offset = int(data.get("offset") or 0)
            items = [u for u in self.queue if u["update_id"] >= offset]
            self.queue = []
            if not items and self.clock is not None and int(data.get("timeout") or 0) > 0:
                self.clock.sleep(float(data["timeout"]))  # uzun yoklama: süre geçer
            return _Resp(body={"ok": True, "result": items})
        raise AssertionError(method)


def fake_telegram(clock=None, reply="approve", approver="555", **kw) -> tuple[Telegram, FakeTelegramHttp]:
    http = FakeTelegramHttp(clock, reply, **kw)
    return Telegram(TOKEN, "555", approver, http=http), http


class ScriptedBroker:
    """Bellek içi aracı kurum: sembole göre davranış (fill | rest | reject | unknown | error | reject_once)."""

    name = "Betik"

    def __init__(self, positions=None, cash=None, behaviour=None, default="fill"):
        self._positions = dict(positions or {})
        self._cash = cash
        self.behaviour = dict(behaviour or {})
        self.default = default
        self.placed: list[OrderRequest] = []
        self.connected = self.closed = False
        self.fill_on_refresh: set[str] = set()
        self._seen: set[str] = set()

    def connect(self):
        self.connected = True

    def close(self):
        self.closed = True

    def describe(self):
        return "Betik aracı kurum · hesap …456"

    def positions(self):
        return dict(self._positions)

    def cash(self):
        return self._cash

    def _settle(self, order: OrderRequest) -> None:
        """Gerçekleşen emir bakiyeyi ve pozisyonu değiştirir (bakiye biliniyorsa)."""
        sign = 1 if order.side == "sell" else -1
        if self._cash is not None:
            self._cash += sign * order.value
        self._positions[order.symbol] = self._positions.get(order.symbol, 0) - sign * order.lots

    def place(self, order: OrderRequest) -> OrderState:
        self.placed.append(order)
        mode = self.behaviour.get(order.symbol, self.default)
        if mode == "reject_once":
            mode = "fill" if order.symbol in self._seen else "reject"
            self._seen.add(order.symbol)
        if mode == "error":
            raise BrokerError("bağlantı koptu")
        if mode == "not_sent":
            raise NotSent("bağlantı kapalı")
        if mode == "crash":
            raise ValueError("beklenmeyen yanıt biçimi")
        if mode == "unknown":
            return OrderState(order.key, "unknown", message="yanıt yok")
        if mode == "reject":
            return OrderState(order.key, "rejected", broker_id="r1", message="reddedildi — Yetersiz bakiye")
        if mode == "rest":
            return OrderState(order.key, "accepted", broker_id=f"b{len(self.placed)}", message="bekliyor")
        self._settle(order)
        return OrderState(order.key, "filled", broker_id=f"b{len(self.placed)}", filled_lots=order.lots,
                          avg_price=order.limit_price, message="gerçekleşti")

    def refresh(self, state: OrderState) -> OrderState:
        symbol = state.key.split("|")[1]
        if state.status == "accepted" and symbol in self.fill_on_refresh:
            order = next(o for o in self.placed if o.key == state.key)
            self._settle(order)
            return OrderState(state.key, "filled", broker_id=state.broker_id, filled_lots=order.lots,
                              avg_price=order.limit_price, message="gerçekleşti")
        return state

    def cancel(self, state):
        return OrderState(state.key, "cancelled", broker_id=state.broker_id)
