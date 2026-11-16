"""Strateji ve işletim ayarları.

Buradaki varsayılanlar, BIST verisiyle hiçbir backtest çalıştırılmadan ÖNCE, yalnızca
yayımlanmış akademik bulgulara ve piyasa kurallarına dayanılarak sabitlenmiştir (ön kayıt).
Sonradan yapılan her değişiklik bir "deneme" sayılır ve istatistiksel raporda hesaba katılır.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields, replace
from pathlib import Path


@dataclass(frozen=True)
class UniverseConfig:
    #: Yalnızca o günkü resmî BIST 100 üyeleri.
    require_bist100: bool = True
    #: Sinyaller için gereken asgari işlem geçmişi (seans). Yeni halka arzları dışarıda tutar.
    min_history: int = 250
    #: Son 60 seansın en az bu kadarında işlem görmüş olmalı.
    min_traded_days_60: int = 55


@dataclass(frozen=True)
class SignalConfig:
    #: Sütun ağırlıkları (eşit ağırlık: uydurma katsayı yok). 0 ağırlık sütunu kapatır.
    w_value: float = 1.0
    w_quality: float = 1.0
    w_lowrisk: float = 1.0
    w_momentum: float = 1.0
    #: Bileşik puan için en az kaç sütunun verisi bulunmalı.
    min_pillars: int = 3
    vol_window: int = 252
    beta_window: int = 252
    max_window: int = 21
    max_top_n: int = 5
    #: Momentum: [t - lookback, t - skip] aralığındaki getiri (12-1 ay).
    mom_lookback: int = 252
    mom_skip: int = 21
    #: Değer ve kârlılık sıralaması finans / finans dışı grup içinde yapılır
    #: (enflasyon muhasebesi bankalarda uygulanmadığı için defter değerleri karşılaştırılamaz).
    group_neutral: bool = True
    min_group_size: int = 8


@dataclass(frozen=True)
class PortfolioConfig:
    #: Portföydeki hedef hisse sayısı.
    n_holdings: int = 20
    #: Elde tutma bandı: sıra bu değerin altına düşmedikçe satılmaz (devir hızını azaltır).
    hold_rank: int = 40
    #: Hedef ağırlıktan bu oranda (göreli) sapmadıkça ağırlık düzeltmesi yapılmaz.
    rebalance_band: float = 0.25
    #: Yeniden dengeleme sıklığı: "monthly" (ayın son seansı) veya "weekly".
    frequency: str = "monthly"
    #: Aylık dengelemede ay sonundan kaç seans önce karar verileceği (0 = son seans).
    offset: int = 0
    #: Tek emrin, hissenin 20 günlük medyan işlem hacmine oranı için üst sınır.
    max_participation: float = 0.05
    #: Piyasa rejimi filtresi: "none" | "trend" (bkz. risk.py).
    regime: str = "none"
    #: Rejim olumsuzken hisse ağırlığı (0-1).
    regime_off_exposure: float = 0.0
    #: Rejim filtresinin geriye bakış süresi (seans; 252 ≈ 12 ay).
    regime_lookback: int = 252


@dataclass(frozen=True)
class CostConfig:
    #: Komisyon (tek yön), BSMV hariç. Banka aracı kurumlarının liste oranı civarı.
    commission: float = 0.0020
    #: Komisyon üzerinden BSMV.
    bsmv: float = 0.05
    #: Kayma + alım-satım farkı varsayımı (tek yön).
    slippage: float = 0.0010
    #: Boştaki nakdin gecelik faizden aldığı pay (stopaj ve kesintiler sonrası).
    cash_yield_share: float = 0.80

    @property
    def per_side(self) -> float:
        return self.commission * (1.0 + self.bsmv) + self.slippage


@dataclass(frozen=True)
class Config:
    universe: UniverseConfig = field(default_factory=UniverseConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    cost: CostConfig = field(default_factory=CostConfig)
    #: Kâğıt portföyün başlangıç sermayesi (TL).
    capital: float = 100_000.0

    def with_overrides(self, **sections: dict) -> "Config":
        """``cfg.with_overrides(portfolio={"n_holdings": 15})`` gibi kısmi değişiklik."""
        out = self
        for name, changes in sections.items():
            if name == "capital":
                out = replace(out, capital=float(changes))
            else:
                out = replace(out, **{name: replace(getattr(out, name), **changes)})
        return out


def load_config(path: Path | None = None) -> Config:
    """TOML dosyasından ayarları okur; dosyada olmayan alanlar varsayılanda kalır."""
    cfg = Config()
    if path is None or not Path(path).exists():
        return cfg
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    sections = {}
    for name in ("universe", "signal", "portfolio", "cost"):
        if name in data:
            valid = {f.name for f in fields(getattr(cfg, name))}
            unknown = set(data[name]) - valid
            if unknown:
                raise ValueError(f"[{name}] bölümünde bilinmeyen ayar: {sorted(unknown)}")
            sections[name] = data[name]
    if "capital" in data:
        sections["capital"] = data["capital"]
    return cfg.with_overrides(**sections)
