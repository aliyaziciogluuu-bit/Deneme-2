"""Emir katmanının ayarları (``emir-ayar.toml``): kip, sınırlar, saatler, Matriks IQ bağlantısı.

Bu dosya kullanıcının bilgisayarında durur ve depoya GÖNDERİLMEZ (hesap numarası ve Telegram
anahtarı içerebilir). Yazılmayan her ayar aşağıdaki temkinli varsayılanda kalır.
"""
from __future__ import annotations

import datetime as dt
import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

#: ``deneme``: hiçbir yere bağlanmaz, emirler yalnızca ekrana/Telegram'a yazılır.
#: ``salt-okunur``: Matriks IQ'dan hesap ve pozisyon okunur, emir GÖNDERİLMEZ.
#: ``gercek``: emirler Matriks IQ üzerinden aracı kuruma gönderilir.
MODES = ("deneme", "salt-okunur", "gercek")


class SettingsError(ValueError):
    """Ayar dosyası hatalı."""


def _clock(text: str) -> dt.time:
    try:
        return dt.time.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise SettingsError(f"saat SS:DD[:SN] biçiminde olmalı: {text!r}") from exc


@dataclass(frozen=True)
class Limits:
    """Emir fişi bu sınırlardan birini aşarsa HİÇBİR emir gönderilmez."""

    #: Tek emrin tutarı için üst sınır (TL).
    azami_emir_tl: float = 25_000.0
    #: Bir gündeki alışların / satışların toplam tutarı için üst sınır (TL).
    azami_alis_tl: float = 120_000.0
    azami_satis_tl: float = 120_000.0
    #: Tek emrin, fişteki kâğıt portföy değerine oranı için üst sınır.
    azami_emir_orani: float = 0.15
    #: Bir fişteki emir sayısı için üst sınır.
    azami_emir_sayisi: int = 45
    #: Limit fiyatın son kapanıştan en çok ne kadar uzak olabileceği (0.035 = %3,5).
    azami_fiyat_sapmasi: float = 0.035
    #: Fiş en çok kaç saat önce üretilmiş olabilir (hafta sonu ve bayram tatillerini kapsar;
    #: fişin doğru seans için olduğu ayrıca tarihinden denetlenir).
    azami_fis_yasi_saat: float = 100.0


@dataclass(frozen=True)
class Schedule:
    """İstanbul saatiyle gönderim pencereleri (Pay Piyasası seans saatleri)."""

    #: Açılış seansı emir toplama: 09:40-09:55.
    acilis_baslangic: dt.time = dt.time(9, 40, 15)
    acilis_bitis: dt.time = dt.time(9, 54, 30)
    #: Sürekli işlem: 10:00-18:00.
    surekli_baslangic: dt.time = dt.time(10, 0, 30)
    surekli_bitis: dt.time = dt.time(17, 55, 0)
    #: Onay en geç bu saate kadar gelmeli.
    onay_son: dt.time = dt.time(17, 30, 0)
    #: Emirler gönderildikten sonra gerçekleşmeleri izleme süresi (dakika).
    izleme_dakika: float = 12.0
    #: Satışlar gerçekleşince reddedilen/ertelenen alışlar bir kez daha denensin mi.
    ikinci_tur: bool = True


@dataclass(frozen=True)
class MatriksSettings:
    host: str = "127.0.0.1"
    port: int = 18890
    #: Boş bırakılırsa Matriks IQ'da giriş yapılmış tek BIST hesabı kullanılır.
    araci_kurum_id: str = ""
    hesap_id: str = ""
    #: Borsa İstanbul Pay Piyasası.
    borsa_id: int = 4
    #: Yeni emirde yön kodları (Matriks API belgesi, Tablo 4.6: alış 1, satış 2).
    alis_kodu: int = 1
    satis_kodu: int = 2
    #: Her emrin yanıtındaki yön, yön testinde görülen değerle karşılaştırılsın mı. Matriks IQ
    #: yanıtlarda bu alanı doldurmuyorsa (hep aynı değer geliyorsa) kapatılır.
    yon_yanit_denetimi: bool = True
    #: Satılabilir lotun okunacağı alan(lar); ilk bulunan kullanılır.
    lot_alanlari: tuple[str, ...] = ("QtyAvailable",)
    #: Hesap bilgisinde kullanılabilir TL bakiyenin anahtarı (boşsa nakit okunmaz).
    nakit_anahtari: str = ""
    zaman_asimi: float = 15.0
    #: Bağlanınca "SetMessageType0" (JSON kipi) gönderilsin mi.
    json_kipi_gonder: bool = True


@dataclass(frozen=True)
class TelegramSettings:
    token: str = ""
    chat_id: str = ""
    #: Onay verebilecek Telegram kullanıcı numarası. Boşsa ``chat_id`` (özel sohbet) kullanılır.
    onaylayan_id: str = ""

    @property
    def approver(self) -> str:
        return self.onaylayan_id or self.chat_id

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)


@dataclass(frozen=True)
class ExecSettings:
    mod: str = "deneme"
    #: Emir fişinin adresi (``https://...latest.json``) ya da yerel dosya yolu.
    fis: str = "web/data/latest.json"
    #: Yerel dosyadan okunuyorsa önce ``git pull`` yapılsın mı.
    git_guncelle: bool = False
    #: Günlük, durum ve kilit dosyalarının klasörü.
    klasor: Path = Path(".emir")
    #: Borsanın kapalı olduğu, tarihi yıla göre değişen günler (``"2027-03-10"`` biçiminde).
    tatiller: tuple[str, ...] = ()
    sinirlar: Limits = field(default_factory=Limits)
    zaman: Schedule = field(default_factory=Schedule)
    matriks: MatriksSettings = field(default_factory=MatriksSettings)
    telegram: TelegramSettings = field(default_factory=TelegramSettings)

    @property
    def live(self) -> bool:
        return self.mod == "gercek"


def _section(cls, data: dict, name: str):
    valid = {f.name: f for f in fields(cls)}
    unknown = set(data) - set(valid)
    if unknown:
        raise SettingsError(f"[{name}] bölümünde bilinmeyen ayar: {sorted(unknown)}")
    out = {}
    for key, value in data.items():
        kind = valid[key].type
        if kind == "dt.time":
            value = _clock(value)
        elif kind == "tuple[str, ...]":
            if isinstance(value, str):
                value = (value,)
            if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) and v for v in value):
                raise SettingsError(f"[{name}] {key} metin listesi olmalı")
            value = tuple(value)
        elif kind == "bool":
            if not isinstance(value, bool):
                raise SettingsError(f"[{name}] {key} true/false olmalı")
        elif kind in ("float", "int"):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SettingsError(f"[{name}] {key} sayı olmalı")
            value = int(value) if kind == "int" else float(value)
        elif kind == "str":
            value = str(value)
        out[key] = value
    return cls(**out)


def load_settings(path: Path | None, env: dict | None = None) -> ExecSettings:
    """Ayarları okur. Telegram bilgileri ortam değişkenlerinden de alınabilir (öncelik onlarda)."""
    env = os.environ if env is None else env
    data: dict = {}
    if path is not None and Path(path).exists():
        try:
            data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise SettingsError(f"{path} okunamadı: {exc}") from exc
    top = {k: v for k, v in data.items() if not isinstance(v, dict)}
    holidays = top.get("tatiller", [])
    if not isinstance(holidays, list):
        raise SettingsError("tatiller bir tarih listesi olmalı")
    for day in holidays:
        try:
            dt.date.fromisoformat(str(day))
        except ValueError as exc:
            raise SettingsError(f"tatiller: tarih YYYY-AA-GG biçiminde olmalı ({day!r})") from exc
    unknown = set(top) - {"mod", "fis", "git_guncelle", "klasor", "tatiller"}
    unknown |= {k for k, v in data.items() if isinstance(v, dict)} - {"sinirlar", "zaman", "matriks", "telegram"}
    if unknown:
        raise SettingsError(f"bilinmeyen ayar: {sorted(unknown)}")
    mod = str(top.get("mod", "deneme"))
    if mod not in MODES:
        raise SettingsError(f"mod şunlardan biri olmalı: {', '.join(MODES)}")
    tg = dict(data.get("telegram", {}))
    for key, var in (("token", "TELEGRAM_BOT_TOKEN"), ("chat_id", "TELEGRAM_CHAT_ID"), ("onaylayan_id", "TELEGRAM_APPROVER_ID")):
        if env.get(var):
            tg[key] = env[var]
    tg = {k: str(v).strip() for k, v in tg.items()}
    base = Path(path).parent if path is not None else Path(".")
    folder = Path(str(top.get("klasor", ".emir")))
    settings = ExecSettings(
        mod=mod,
        fis=str(top.get("fis", ExecSettings.fis)),
        git_guncelle=bool(top.get("git_guncelle", False)),
        klasor=folder if folder.is_absolute() else base / folder,
        tatiller=tuple(str(d) for d in holidays),
        sinirlar=_section(Limits, data.get("sinirlar", {}), "sinirlar"),
        zaman=_section(Schedule, data.get("zaman", {}), "zaman"),
        matriks=_section(MatriksSettings, data.get("matriks", {}), "matriks"),
        telegram=_section(TelegramSettings, tg, "telegram"),
    )
    validate(settings)
    return settings


def validate(s: ExecSettings) -> None:
    lim, z, m = s.sinirlar, s.zaman, s.matriks
    for name in ("azami_emir_tl", "azami_alis_tl", "azami_satis_tl", "azami_emir_orani", "azami_fiyat_sapmasi",
                 "azami_fis_yasi_saat"):
        if not getattr(lim, name) > 0:
            raise SettingsError(f"[sinirlar] {name} pozitif olmalı")
    if lim.azami_emir_sayisi < 1:
        raise SettingsError("[sinirlar] azami_emir_sayisi en az 1 olmalı")
    if lim.azami_fiyat_sapmasi > 0.10:
        raise SettingsError("[sinirlar] azami_fiyat_sapmasi günlük fiyat marjını (%10) aşamaz")
    if not (z.acilis_baslangic < z.acilis_bitis < z.surekli_baslangic < z.surekli_bitis):
        raise SettingsError("[zaman] pencereler sıralı olmalı: açılış başlangıç < bitiş < sürekli başlangıç < bitiş")
    if not (0 < z.izleme_dakika <= 120):
        raise SettingsError("[zaman] izleme_dakika 0-120 arasında olmalı")
    if m.alis_kodu == m.satis_kodu:
        raise SettingsError("[matriks] alış ve satış kodları aynı olamaz")
    if m.host not in ("127.0.0.1", "localhost", "::1"):
        # Matriks IQ'nun emir kapısı şifresizdir; yalnızca aynı bilgisayardan bağlanılır.
        raise SettingsError("[matriks] host yalnızca bu bilgisayar olabilir (127.0.0.1)")
    if s.live:
        if not s.telegram.configured:
            raise SettingsError("gerçek emir kipi Telegram onayı olmadan çalışmaz: token ve chat_id gerekli")
        approver = s.telegram.approver
        if not approver.lstrip("-").isdigit() or int(approver) <= 0:
            raise SettingsError(
                "gerçek emir kipinde onaylayan kişi belli olmalı: chat_id bir grup ise [telegram] onaylayan_id yazın"
            )
