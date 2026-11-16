"""Botun kalıcı durumu: başlangıç günü, sermaye, sabitlenen ayarlar ve dondurulmuş kararlar.

Kâğıt portföyün kendisi saklanmaz; her çalıştırmada başlangıç gününden itibaren, kayıtlı
kararlar ve resmî fiyatlarla yeniden hesaplanır. Bu sayede aynı gün iki kez çalıştırmak
ya da kaçırılan günleri sonradan tamamlamak aynı sonucu verir. Kullanıcıya bildirilen
işlemler ayrıca ``reported`` listesinde tutulur; yeniden hesaplama bunları değiştirirse
uyarı verilir.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATE_VERSION = 2


@dataclass
class BotState:
    #: Kâğıt portföyün başladığı seans (ISO tarih). İlk kararla birlikte atanır.
    start: str | None = None
    #: Başlangıç sermayesi (TL). İlk kararda ayar dosyasından alınır, sonra değişmez.
    capital: float | None = None
    #: İlk kararda sabitlenen işlem ayarları (masraflar, bant vb.). Sonradan ``ayar.toml``
    #: değişse de geçmiş yeniden yazılmasın diye bunlar kullanılır.
    settings: dict | None = None
    #: Dondurulmuş kararlar: ``{karar günü: {sembol: hedef ağırlık}}`` (sıra korunur).
    decisions: dict[str, dict[str, float]] = field(default_factory=dict)
    #: Kullanıcıya bildirilmiş kâğıt işlemler: ``[tarih, sembol, yön, lot, fiyat]``.
    reported: list[list] = field(default_factory=list)
    #: Son gönderilen bildirimin özeti (aynı içerik iki kez gönderilmesin diye).
    notified: str | None = None
    version: int = STATE_VERSION

    @classmethod
    def load(cls, path: Path) -> "BotState":
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version", 1) > STATE_VERSION:
            raise ValueError(f"durum dosyası daha yeni bir sürümle yazılmış: {path}")
        fields = ("start", "capital", "settings", "decisions", "reported", "notified")
        state = cls(**{k: data[k] for k in fields if k in data and data[k] is not None})
        return state

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        # Kararların içindeki sıra anlamlıdır (alım önceliği); anahtarlar sıralanmaz.
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        tmp.replace(path)
