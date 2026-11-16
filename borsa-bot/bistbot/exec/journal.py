"""Emir günlüğü: gönderilen her emrin kalıcı, yalnızca eklenen kaydı.

Günlük iki işe yarar: (1) aynı emrin iki kez gönderilmesini önler (program yarıda kesilip
yeniden başlasa bile), (2) ne zaman, ne gönderildiğinin denetlenebilir izini tutar.

Kural: bir emir için ``sending`` kaydı düşülüp sonucu yazılmadıysa o emrin akıbeti belirsizdir
ve program onu kendiliğinden YENİDEN GÖNDERMEZ; önce aracı kurumdaki emir/pozisyon durumu
kontrol edilmelidir.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

#: Bu olaylardan biri kayıtlıysa emir gönderilmiş (ya da gönderilmiş olabilir) sayılır.
SENT_EVENTS = frozenset({"sending", "accepted", "partial", "filled", "unknown", "cancelled"})


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, key: str = "", **data) -> dict:
        entry = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "event": event, "key": key, **data}
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        # Her kayıt diske hemen yazılır: emir gönderilmeden ÖNCE "sending" kaydı güvende olmalı.
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return entry

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                # Yarım yazılmış son satır (ör. elektrik kesintisi): yok sayılır ama
                # o emrin "sending" kaydı bir önceki satırda durur.
                continue
        return out

    def last_events(self) -> dict[str, dict]:
        """Her emir anahtarı için son kayıt."""
        last: dict[str, dict] = {}
        for e in self.entries():
            if e.get("key"):
                last[e["key"]] = e
        return last

    def was_sent(self, key: str) -> bool:
        """Bu emir daha önce gönderildi mi (ya da gönderilmiş olabilir mi)?"""
        return any(e.get("key") == key and e.get("event") in SENT_EVENTS for e in self.entries())

    def batch_done(self, digest: str) -> bool:
        return any(e.get("event") == "batch_done" and e.get("digest") == digest for e in self.entries())
