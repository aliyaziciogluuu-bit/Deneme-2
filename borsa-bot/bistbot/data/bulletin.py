"""Borsa İstanbul resmî Pay Piyasası günlük bülteni (thb) — indirme ve ayrıştırma.

Kaynak: https://www.borsaistanbul.com/data/thb/YYYY/MM/thbYYYYMMDD1.zip
BISTECH biçimi 30.11.2015'ten itibaren mevcuttur. Her dosya o gün işlem gören TÜM
enstrümanları içerir; dolayısıyla bu veri

* hayatta kalma yanlılığı içermez (sonradan kottan çıkan paylar da o günkü dosyada vardır),
* o günkü BIST 100 / BIST 30 üyeliğini, brüt takas ve geçici durdurma bayraklarını,
  pazar ve işlem yöntemini "o gün bilindiği hâliyle" verir,
* ham (düzeltilmemiş) açılış / en yüksek / en düşük / kapanış / AOF ve hacmi verir.

Fiyatlar hamdır; temettü, bedelli ve bedelsiz düzeltmeleri ``adjust`` modülünde yapılır.
"""
from __future__ import annotations

import datetime as dt
import io
import logging
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from .http import HttpClient

log = logging.getLogger(__name__)

FIRST_BULLETIN_DATE = dt.date(2015, 11, 30)
URL_TEMPLATE = "https://www.borsaistanbul.com/data/thb/{y:04d}/{m:02d}/thb{y:04d}{m:02d}{d:02d}1.zip"

# Bülten sütunu (boşlukları tekilleştirilmiş) -> iç ad
_COLUMNS = {
    "ISLEM KODU": "code",
    "BULTEN ADI": "name",
    "PAZAR": "market",
    "ENSTRUMAN GRUBU": "group",
    "ISLEM YONTEMI": "method",
    "BIST 100 ENDEKS": "bist100",
    "BIST 30 ENDEKS": "bist30",
    "BRUT TAKAS": "gross",
    "OZSERMAYE HALI": "corp_action",
    "GECICI DURDURMA": "suspended",
    "ACIGA SATIS": "short_ok",
    "ONCEKI KAPANIS FIYATI": "prev_close",
    "ACILIS FIYATI": "open",
    "EN YUKSEK FIYAT": "high",
    "EN DUSUK FIYAT": "low",
    "KAPANIS FIYATI": "close",
    "A.O.F": "vwap",
    "TOPLAM ISLEM HACMI": "value",
    "TOPLAM ISLEM ADEDI": "volume",
    "TOPLAM SOZLESME SAYISI": "trades",
}
_REQUIRED = ("code", "group", "prev_close", "open", "high", "low", "close", "vwap", "value")
_PRICE_COLS = ("prev_close", "open", "high", "low", "close", "vwap")
_NUM_COLS = _PRICE_COLS + ("value", "volume", "trades")
_FLAG_COLS = ("bist100", "bist30", "gross", "suspended", "short_ok")

DAY_COLUMNS = [
    "date", "symbol", "name", "market", "method",
    "bist100", "bist30", "gross", "suspended", "short_ok", "corp_action",
    "prev_close", "open", "high", "low", "close", "vwap", "value", "volume", "trades",
]


class BulletinFormatError(ValueError):
    """Bülten dosyası beklenen biçimde değil."""


def bulletin_url(day: dt.date) -> str:
    return URL_TEMPLATE.format(y=day.year, m=day.month, d=day.day)


def parse_bulletin_csv(raw: bytes, day: dt.date) -> pd.DataFrame:
    """Ham bülten CSV içeriğini pay (EQT, ``.E``) satırlarına indirger."""
    text = raw.decode("cp1254", errors="replace")
    # 1. satır Türkçe başlık, 2. satır İngilizce başlık.
    df = pd.read_csv(io.StringIO(text), sep=";", skiprows=[1], dtype=str, keep_default_na=False)
    df.columns = [" ".join(str(c).split()) for c in df.columns]
    df = df.rename(columns=_COLUMNS)
    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        raise BulletinFormatError(f"{day}: eksik sütunlar {missing}")

    df = df[(df["group"] == "EQT") & df["code"].str.endswith(".E")].copy()
    if df.empty:
        raise BulletinFormatError(f"{day}: pay satırı bulunamadı")
    df["symbol"] = df["code"].str[:-2].str.strip()
    df["date"] = pd.Timestamp(day)

    for col in _NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = float("nan")
    for col in _FLAG_COLS:
        if col in df.columns:
            df[col] = (df[col].str.strip() == "1").astype("int8")
        else:
            df[col] = pd.array([pd.NA] * len(df), dtype="Int8")
    for col in ("name", "market", "method", "corp_action"):
        if col in df.columns:
            df[col] = df[col].str.strip()
        else:
            df[col] = ""

    # İşlem görmeyen payda bülten fiyatları 0 yazar: bunlar "veri yok" demektir.
    for col in ("open", "high", "low", "close", "vwap"):
        df.loc[df[col] <= 0, col] = float("nan")
    df.loc[df["prev_close"] <= 0, "prev_close"] = float("nan")
    df["value"] = df["value"].fillna(0.0)
    df["volume"] = df["volume"].fillna(0.0)

    dup = df["symbol"].duplicated()
    if dup.any():
        raise BulletinFormatError(f"{day}: yinelenen semboller {df.loc[dup, 'symbol'].tolist()[:5]}")
    return df[DAY_COLUMNS].sort_values("symbol").reset_index(drop=True)


def parse_bulletin_zip(content: bytes, day: dt.date) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise BulletinFormatError(f"{day}: zip içinde csv yok ({zf.namelist()})")
        return parse_bulletin_csv(zf.read(names[0]), day)


class BulletinStore:
    """Ayrıştırılmış günlük bültenlerin disk önbelleği.

    ``<root>/YYYY/YYYYMMDD.csv.gz``: yalnızca pay satırları (günde ~30 KB).
    ``<root>/nosession.txt``: seans olmadığı kesinleşmiş günler (tatiller).
    """

    #: Bu kadar günden eski bir tarihte dosya yoksa "tatil" olarak kalıcı işaretlenir.
    #: Daha yeni tarihlerde dosya henüz yayımlanmamış olabilir.
    SETTLE_DAYS = 7

    def __init__(self, root: Path, client: HttpClient | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.client = client or HttpClient()
        self._nosession_path = self.root / "nosession.txt"
        self._nosession: set[dt.date] = set()
        if self._nosession_path.exists():
            for line in self._nosession_path.read_text().split():
                self._nosession.add(dt.date.fromisoformat(line))

    # -- yollar -----------------------------------------------------------------
    def day_path(self, day: dt.date) -> Path:
        return self.root / f"{day.year:04d}" / f"{day:%Y%m%d}.csv.gz"

    def has_day(self, day: dt.date) -> bool:
        return self.day_path(day).exists()

    def cached_days(self) -> list[dt.date]:
        days = []
        for p in self.root.glob("[0-9][0-9][0-9][0-9]/*.csv.gz"):
            try:
                days.append(dt.datetime.strptime(p.name[:8], "%Y%m%d").date())
            except ValueError:
                continue
        return sorted(days)

    # -- indirme ----------------------------------------------------------------
    def fetch_day(self, day: dt.date) -> pd.DataFrame | None:
        """Tek günü indirir, ayrıştırır, önbelleğe yazar. Seans yoksa ``None``."""
        resp = self.client.get(bulletin_url(day))
        if resp is None:
            return None
        df = parse_bulletin_zip(resp.content, day)
        path = self.day_path(day)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        df.to_csv(tmp, index=False, compression="gzip")
        tmp.replace(path)
        return df

    def sync(
        self,
        start: dt.date,
        end: dt.date,
        today: dt.date | None = None,
        workers: int = 4,
        progress: bool = False,
    ) -> dict[str, int]:
        """``[start, end]`` aralığındaki eksik günleri indirir.

        Dönen sözlük: indirilen, seans olmayan ve hata veren gün sayıları.
        """
        today = today or dt.date.today()
        start = max(start, FIRST_BULLETIN_DATE)
        wanted = []
        day = start
        while day <= end:
            if day.weekday() < 5 and not self.has_day(day) and day not in self._nosession:
                wanted.append(day)
            day += dt.timedelta(days=1)

        stats = {"downloaded": 0, "nosession": 0, "failed": 0}
        if not wanted:
            return stats
        new_nosession: list[dt.date] = []

        def job(d: dt.date) -> tuple[dt.date, str]:
            try:
                return d, ("ok" if self.fetch_day(d) is not None else "none")
            except Exception as exc:  # tek günün hatası tüm eşitlemeyi durdurmasın
                log.warning("bülten alınamadı %s: %s", d, exc)
                return d, "fail"

        done = 0
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [pool.submit(job, d) for d in wanted]
            for fut in as_completed(futures):
                d, status = fut.result()
                done += 1
                if status == "ok":
                    stats["downloaded"] += 1
                elif status == "none":
                    stats["nosession"] += 1
                    if (today - d).days > self.SETTLE_DAYS:
                        new_nosession.append(d)
                else:
                    stats["failed"] += 1
                if progress and done % 100 == 0:
                    log.info("bülten eşitleme: %d/%d", done, len(wanted))

        if new_nosession:
            self._nosession.update(new_nosession)
            self._nosession_path.write_text("\n".join(d.isoformat() for d in sorted(self._nosession)) + "\n")
        return stats

    def forget_nosession(self, days: list[dt.date]) -> None:
        """"Seans yok" işaretlerini kaldırır (başka bir kaynak o gün seans olduğunu gösterdiyse)."""
        before = len(self._nosession)
        self._nosession.difference_update(days)
        if len(self._nosession) != before:
            self._nosession_path.write_text("".join(d.isoformat() + "\n" for d in sorted(self._nosession)))

    # -- okuma ------------------------------------------------------------------
    def load_day(self, day: dt.date) -> pd.DataFrame:
        df = pd.read_csv(
            self.day_path(day),
            dtype={"symbol": str, "name": str, "market": str, "method": str, "corp_action": str},
            keep_default_na=False,
            na_values={c: [""] for c in _NUM_COLS + _FLAG_COLS},
            parse_dates=["date"],
        )
        return df

    def load_range(self, start: dt.date, end: dt.date) -> pd.DataFrame:
        """Önbellekteki günleri uzun (long) biçimde birleştirir."""
        days = [d for d in self.cached_days() if start <= d <= end]
        if not days:
            return pd.DataFrame(columns=DAY_COLUMNS)
        frames = [self.load_day(d) for d in days]
        return pd.concat(frames, ignore_index=True)
