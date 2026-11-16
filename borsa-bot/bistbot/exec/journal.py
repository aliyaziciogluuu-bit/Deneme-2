"""Emir günlüğü: gönderilen her emrin kalıcı, yalnızca eklenen kaydı.

Günlük iki işe yarar: (1) aynı emrin iki kez gönderilmesini önler (program yarıda kesilip
yeniden başlasa bile), (2) ne zaman, ne gönderildiğinin denetlenebilir izini tutar.

Kural: bir emir için ``sending`` kaydı düşülüp sonucu yazılmadıysa o emrin akıbeti belirsizdir
ve program onu kendiliğinden YENİDEN GÖNDERMEZ; önce aracı kurumdaki emir/pozisyon durumu
kontrol edilmelidir. İki istisna vardır, ikisinde de emrin aracı kurumda çalışmadığı kesindir:
bağlantı daha gönderimden önce yoksa yazılan ``not_sent`` ve aracı kurumun reddi (``rejected``).

Bir emrin kimliği kararın dayandığı gündür (``karar günü|sembol|yön``); aynı karar başka bir
seans için yeniden yayımlansa da ikinci kez gönderilmez. Satış parası beklenerek ikinci turda
gönderilen alışlar aynı kimliğin ``|2`` ekli hâlini kullanır ve aynı emir sayılır.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

#: Bu olaylardan biri kayıtlıysa emir gönderilmiş (ya da gönderilmiş olabilir) sayılır.
SENT_EVENTS = frozenset({"sending", "accepted", "partial", "filled", "unknown", "cancelled"})
#: İkinci tur (yeniden deneme) anahtarının eki.
RETRY = "|2"


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, key: str = "", **data) -> dict:
        entry = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "event": event, "key": key, **data}
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        # Her kayıt diske hemen yazılır: emir gönderilmeden ÖNCE "sending" kaydı güvende olmalı.
        # Dosya yarım bir satırla bitiyorsa (elektrik kesintisi) yeni kayıt ona yapışmasın.
        torn = False
        try:
            with open(self.path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                if fh.tell() > 0:
                    fh.seek(-1, os.SEEK_END)
                    torn = fh.read(1) != b"\n"
        except FileNotFoundError:
            pass
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(("\n" if torn else "") + line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return entry

    def entries(self) -> list[dict]:
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            return []
        out = []
        for raw in data.split(b"\n"):
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                # Yarım ya da bozuk satır (ör. elektrik kesintisi): yok sayılır ama o emrin
                # "sending" kaydı bir önceki satırda durur.
                continue
            if isinstance(entry, dict):
                out.append(entry)
        return out

    def last_events(self) -> dict[str, dict]:
        """Her emir anahtarı için son kayıt."""
        last: dict[str, dict] = {}
        for e in self.entries():
            if e.get("key"):
                last[e["key"]] = e
        return last

    def was_sent(self, key: str) -> bool:
        """Tam bu anahtarla bir emir gönderildi mi (ya da gönderilmiş olabilir mi)?

        ``sending`` kaydının hemen ardından gelen ``not_sent`` ("kesinlikle gitmedi") ve hiç
        gerçekleşmeden gelen ``rejected`` (aracı kurum reddetti) o denemeyi geri alır; başka
        hiçbir kayıt gönderilmiş bir emri gönderilmemiş yapmaz. Kısmen de olsa gerçekleşmiş bir emir
        sonradan "reddedildi" görünse bile gönderilmiş sayılır.
        """
        sent, last, filled = False, None, False
        for e in self.entries():
            if e.get("key") != key:
                continue
            event = e.get("event")
            # Bir kez gerçekleşme görülmüşse (kısmi de olsa) sonradan gelen hiçbir kayıt emri yok saydıramaz.
            filled = filled or bool(e.get("filled")) or event in ("partial", "filled")
            if event in SENT_EVENTS:
                sent, last = True, event
            elif event == "not_sent" and last == "sending":
                sent, last = False, None
            elif event == "rejected" and not filled:
                sent, last = False, None
        return sent

    def working_buys(self, session: str) -> float:
        """Bu seansta gönderilmiş, henüz bitmemiş (bekleyen ya da akıbeti belirsiz) alışların gerçekleşmemiş
        kısmının limit fiyattan tutarı. Bakiye hesabında bu tutar "harcanmış" sayılır."""
        orders: dict[str, dict] = {}
        for e in self.entries():
            key = e.get("key") or ""
            if e.get("event") == "sending" and e.get("session") == session and e.get("side") == "buy":
                orders[key] = {"lots": float(e.get("lots") or 0), "limit": float(e.get("limit") or 0),
                               "filled": 0.0, "event": "sending"}
            elif key in orders and e.get("event") in SENT_EVENTS | {"rejected", "not_sent"}:
                orders[key]["event"] = e["event"]
                orders[key]["filled"] = max(orders[key]["filled"], float(e.get("filled") or 0))
        total = 0.0
        for o in orders.values():
            if o["event"] in ("sending", "accepted", "partial", "unknown"):
                total += max(o["lots"] - o["filled"], 0.0) * o["limit"]
        return total

    def order_sent(self, key: str) -> bool:
        """Emir, ilk denemede ya da ikinci turda gönderildi mi? (``key`` ek taşımayan temel anahtardır.)"""
        return self.was_sent(key) or self.was_sent(key + RETRY)

    def batch_done(self, digest: str) -> bool:
        return any(e.get("event") == "batch_done" and e.get("digest") == digest for e in self.entries())
