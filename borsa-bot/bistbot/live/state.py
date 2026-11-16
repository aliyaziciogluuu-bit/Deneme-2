"""Botun kalıcı durumu: başlangıç günü, sermaye ve dondurulmuş kararlar.

Kâğıt portföyün kendisi saklanmaz; her çalıştırmada başlangıç gününden itibaren, kayıtlı
kararlar ve resmî fiyatlarla yeniden hesaplanır. Bu sayede aynı gün iki kez çalıştırmak
ya da kaçırılan günleri sonradan tamamlamak aynı sonucu verir.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATE_VERSION = 1


@dataclass
class BotState:
    #: Kâğıt portföyün başladığı seans (ISO tarih). İlk çalıştırmada atanır.
    start: str | None = None
    #: Başlangıç sermayesi (TL). İlk çalıştırmada ayar dosyasından alınır, sonra değişmez.
    capital: float | None = None
    #: Dondurulmuş kararlar: ``{karar günü: {sembol: hedef ağırlık}}``.
    decisions: dict[str, dict[str, float]] = field(default_factory=dict)
    #: Son bildirim gönderilen seans (yinelenen bildirimi önlemek için).
    notified: str | None = None
    version: int = STATE_VERSION

    @classmethod
    def load(cls, path: Path) -> "BotState":
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version", STATE_VERSION) > STATE_VERSION:
            raise ValueError(f"durum dosyası daha yeni bir sürümle yazılmış: {path}")
        known = {k: data[k] for k in ("start", "capital", "decisions", "notified", "version") if k in data}
        return cls(**known)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)
