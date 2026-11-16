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
    #: Teknik sütunun ağırlığı (0 = kapalı). Teknik sütun üç eğilim ölçüsünün ortalamasıdır:
    #: nakde göre fiyatın 200 günlük ortalamaya uzaklığı, 50/200 günlük ortalama oranı ve
    #: 52 haftalık zirveye yakınlık (bkz. technical.py).
    w_technical: float = 0.0
    #: Eğilim ölçülerinin uzun ve kısa hareketli ortalama pencereleri (seans).
    trend_window: int = 200
    trend_short_window: int = 50
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
    #: Yeniden dengeleme sıklığı: "monthly" (ayın ilk seansı) veya "weekly" (haftanın ilk seansı).
    frequency: str = "monthly"
    #: Karar gününün dönem başından kaç seans sonra olacağı (0 = dönemin ilk seansı).
    offset: int = 0
    #: Tek emrin, hissenin 20 günlük medyan işlem hacmine oranı için üst sınır.
    max_participation: float = 0.05
    #: Alımlar planlanırken fiyat için bırakılan pay. Alış emirleri son kapanışın bu kadar
    #: üstüne kadar limitli verilir; aracı kurum alım gücünü limit fiyattan ayırdığı için
    #: emirlerin toplamı bu fiyattan da eldeki paraya sığmalıdır.
    buy_headroom: float = 0.03
    #: Teknik onay kapısı (hibrit mod): "none" | "entry" | "entry_exit".
    #: ``entry``: bir hisse ancak yükseliş eğilimindeyse (nakde göre fiyatı 200 günlük
    #: ortalamasının üstündeyse) ve sırası elde tutma bandının içindeyse alınır.
    #: ``entry_exit``: ayrıca eldeki hisse eğilimini yitirdiyse karar gününde satılır.
    #: Kapıdan geçen hisse yetmezse boş kalan paylar nakitte bekler.
    trend_gate: str = "none"
    #: Piyasa rejimi filtresi: "none" | "trend" (bkz. portfolio.py).
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
    for name, values in sections.items():
        if name != "capital":
            _check_types(name, values, getattr(cfg, name))
    if isinstance(data.get("capital"), bool) or not isinstance(data.get("capital", 0), (int, float)):
        raise ValueError(f"capital sayı olmalı ({data.get('capital')!r}); tırnak ya da nokta kullanmadan yazın (ör. 100000)")
    portfolio = data.get("portfolio", {})
    if portfolio.get("regime") == "trend" and "regime_off_exposure" not in portfolio:
        # Yazılmazsa 0 olur, yani rejim olumsuzken portföyün TAMAMI nakde geçer.
        raise ValueError("[portfolio] regime açıldığında regime_off_exposure da yazılmalı "
                         "(0.5 = portföyün yarısı nakitte; 0 = tamamı nakitte)")
    cfg = cfg.with_overrides(**sections)
    validate_config(cfg)
    return cfg


def _check_types(section: str, values: dict, current) -> None:
    """Dosyadaki değerin türü alanın türüyle aynı olmalı (tırnak içine alınmış sayı, ondalıklı hisse
    sayısı gibi hatalar yükleme anında, ayarın adıyla bildirilir)."""
    for key, value in values.items():
        default = getattr(current, key)
        if isinstance(default, bool):
            ok = isinstance(value, bool)
        elif isinstance(default, int):
            ok = isinstance(value, int) and not isinstance(value, bool)
        elif isinstance(default, float):
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            ok = isinstance(value, str)
        if not ok:
            kind = {bool: "true/false", int: "tam sayı", float: "sayı"}.get(type(default), "metin")
            raise ValueError(f"[{section}] {key} {kind} olmalı ({value!r})")


def validate_config(cfg: Config) -> None:
    """Ayar değerlerini yükleme anında sınar: yanlış yazılmış bir seçenek ancak karar gününde ortaya
    çıkıp o günün kararını kaçırtmasın."""
    def check(ok: bool, text: str) -> None:
        if not ok:
            raise ValueError(text)

    p, s, c = cfg.portfolio, cfg.signal, cfg.cost
    check(p.trend_gate in ("none", "entry", "entry_exit"),
          f'[portfolio] trend_gate "none", "entry" ya da "entry_exit" olmalı ({p.trend_gate!r})')
    check(p.regime in ("none", "trend"), f'[portfolio] regime "none" ya da "trend" olmalı ({p.regime!r})')
    check(p.frequency in ("monthly", "weekly"), f'[portfolio] frequency "monthly" ya da "weekly" olmalı ({p.frequency!r})')
    check(0.0 <= p.regime_off_exposure <= 1.0, "[portfolio] regime_off_exposure 0 ile 1 arasında olmalı")
    check(1 <= p.n_holdings <= p.hold_rank, "[portfolio] n_holdings en az 1 ve hold_rank'ten büyük olmamalı")
    check(p.offset >= 0 and p.regime_lookback >= 20, "[portfolio] offset ve regime_lookback geçersiz")
    weights = (s.w_value, s.w_quality, s.w_lowrisk, s.w_momentum, s.w_technical)
    check(all(w >= 0 for w in weights) and any(w > 0 for w in weights),
          "[signal] sütun ağırlıkları eksi olamaz ve en az biri pozitif olmalı")
    check(1 <= s.trend_short_window < s.trend_window, "[signal] trend_short_window, trend_window'dan küçük olmalı")
    check(c.commission >= 0 and c.slippage >= 0 and 0 <= c.cash_yield_share <= 1.5, "[cost] masraf ayarları geçersiz")
    check(cfg.capital >= 1000,
          f"capital en az 1.000 TL olmalı ({cfg.capital:g}); binlik ayırıcı kullanmadan yazın (ör. 100000)")
