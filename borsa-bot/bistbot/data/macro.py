"""Risksiz TL faizi (gecelik) ve endeks serileri.

Risksiz oran, Borsa İstanbul'un gecelik referans faizi TLREF'tir (yıllık basit oran, 365
gün esası). Resmî TLREF 28.12.2018'de başlar; öncesi için İş Yatırım'ın aynı kod altında
verdiği bankalararası gecelik repo oranı kullanılır (BIST repo bültenleriyle ortalama farkı
yüzde puanın yüzde biri düzeyindedir ve harmanlanmış repo ortalamasından biraz yüksektir;
yani Sharpe hesabı için temkinli taraftadır).

``t`` günü belirlenen oran, ``t``'den bir sonraki iş gününe kadar işler.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import logging
import zipfile
from pathlib import Path

import pandas as pd

from .http import HttpClient, HttpError

log = logging.getLogger(__name__)

TLREF_HISTORY_URL = "https://www.borsaistanbul.com/datum/TLREFORANI_D.zip"
TLREF_LATEST_URL = "https://www.borsaistanbul.com/datum/tlreforani.csv"
ISY_INDEX_URL = (
    "https://www.isyatirim.com.tr/_Layouts/15/IsYatirim.Website/Common/ChartData.aspx/IndexHistoricalAll"
)
TLREF_START = dt.date(2018, 12, 28)
_MIN_RATE, _MAX_RATE = 0.0, 3.0  # ondalık; %0 - %300 dışı değer veri hatasıdır


def _validate(series: pd.Series, what: str) -> pd.Series:
    s = series.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if s.empty:
        raise HttpError(f"{what}: boş seri")
    if ((s <= _MIN_RATE) | (s >= _MAX_RATE)).any():
        raise HttpError(f"{what}: akla yatmayan oran")
    return s


def fetch_tlref_history(client: HttpClient) -> pd.Series:
    """Resmî TLREF geçmişi (28.12.2018 →): tarih dizinli, ondalık yıllık oran."""
    resp = client.get(TLREF_HISTORY_URL)
    if resp is None:
        raise HttpError("TLREF geçmiş dosyası bulunamadı")
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        text = zf.read(zf.namelist()[0]).decode("utf-16")
    rows = {}
    for line in text.splitlines()[1:]:
        f = line.split(";")
        # Veri satırları GG/AA/YYYY ile başlar; dosya sonundaki açıklama satırları atlanır.
        if len(f) > 5 and len(f[0]) == 10 and f[0][2] == "/" and f[0][5] == "/":
            try:
                rows[pd.Timestamp(dt.datetime.strptime(f[0], "%d/%m/%Y"))] = float(f[5]) / 100.0
            except ValueError:
                continue
    s = _validate(pd.Series(rows, dtype=float), "TLREF geçmişi")
    if len(s) < 1900 or s.index[0].date() != TLREF_START:
        raise HttpError("TLREF geçmiş dosyası beklenen biçimde değil")
    return s


def fetch_tlref_latest(client: HttpClient) -> pd.Series:
    """Yalnızca son TLREF değeri (gün içinde geçmiş dosyasından önce güncellenir)."""
    resp = client.get(TLREF_LATEST_URL)
    if resp is None:
        raise HttpError("günlük TLREF dosyası bulunamadı")
    lines = resp.content.decode("latin-1").splitlines()
    f = lines[2].split(";") if len(lines) > 2 else []
    if len(f) < 6 or f[3] != "TLREF":
        raise HttpError("günlük TLREF dosyası beklenen biçimde değil")
    day = pd.Timestamp(dt.datetime.strptime(f[0], "%d/%m/%Y"))
    return _validate(pd.Series({day: float(f[5]) / 100.0}), "günlük TLREF")


def fetch_isy_index(client: HttpClient, code: str, start: dt.date, end: dt.date) -> pd.Series:
    """İş Yatırım endeks/oran geçmişi (ör. ``XU100``, ``TLREF``): tarih dizinli seri."""
    params = {
        "period": 1440,
        "from": start.strftime("%Y%m%d000000"),
        "to": end.strftime("%Y%m%d235959"),
        "endeks": code,
    }
    resp = client.get(ISY_INDEX_URL, params=params)
    if resp is None or not resp.content:
        raise HttpError(f"İş Yatırım endeks verisi boş: {code}")
    data = json.loads(resp.content.decode("utf-8-sig")).get("data") or []
    if not data:
        raise HttpError(f"İş Yatırım endeks verisi boş: {code}")
    # Zaman damgası İstanbul gece yarısıdır (UTC+3): tarihe çevirmeden önce 3 saat eklenir.
    idx = [(pd.Timestamp(ms, unit="ms") + pd.Timedelta(hours=3)).normalize() for ms, _ in data]
    s = pd.Series([float(v) for _, v in data], index=pd.DatetimeIndex(idx)).sort_index()
    return s[~s.index.duplicated(keep="last")]


def build_risk_free(client: HttpClient, start: dt.date, end: dt.date) -> pd.Series:
    """Gecelik risksiz oran serisi (ondalık). Resmî dosya alınamazsa İş Yatırım yansısı kullanılır."""
    mirror = None
    try:
        mirror = _validate(fetch_isy_index(client, "TLREF", start, end) / 100.0, "İş Yatırım TLREF")
    except Exception as exc:  # yansı yalnızca 2018 öncesi ve yedek için gerekir
        log.warning("İş Yatırım TLREF alınamadı: %s", exc)
    try:
        official = fetch_tlref_history(client)
        try:
            latest = fetch_tlref_latest(client)
            if latest.index[0] > official.index[-1]:
                official = pd.concat([official, latest])
        except Exception as exc:
            log.info("günlük TLREF dosyası kullanılamadı (geçmiş dosyası yeterli): %s", exc)
    except Exception as exc:
        if mirror is None:
            raise
        log.warning("resmî TLREF alınamadı, İş Yatırım yansısı kullanılıyor: %s", exc)
        official = mirror[mirror.index >= pd.Timestamp(TLREF_START)]
    parts = [official]
    if mirror is not None:
        parts.insert(0, mirror[mirror.index < official.index[0]])
    rf = pd.concat(parts).sort_index()
    rf = rf[(rf.index >= pd.Timestamp(start)) & (rf.index <= pd.Timestamp(end))]
    return _validate(rf, "risksiz oran").rename("rf")


class MacroStore:
    """``<root>/rf.csv``: risksiz oran önbelleği."""

    def __init__(self, root: Path, client: HttpClient | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.client = client or HttpClient(min_interval=0.4)
        self.rf_path = self.root / "rf.csv"

    def load_rf(self) -> pd.Series:
        if not self.rf_path.exists():
            return pd.Series(dtype=float, name="rf")
        df = pd.read_csv(self.rf_path, parse_dates=["date"])
        return df.set_index("date")["rf"]

    def sync_rf(self, start: dt.date, end: dt.date) -> pd.Series:
        """Seriyi yeniler. İndirme başarısız olursa ve eldeki seri varsa onu korur."""
        old = self.load_rf()
        try:
            rf = build_risk_free(self.client, start, end)
        except Exception as exc:
            if old.empty:
                raise
            log.warning("risksiz oran yenilenemedi, önbellek kullanılıyor: %s", exc)
            return old
        if not old.empty:
            # Yeni indirmenin kapsamadığı eski günleri koru (ör. kaynak geçmişi kısalttıysa).
            rf = pd.concat([old[old.index < rf.index[0]], rf])
        rf.rename("rf").rename_axis("date").to_csv(self.rf_path)
        return rf

    # -- endeksler ------------------------------------------------------------------
    def index_path(self, code: str) -> Path:
        return self.root / f"{code.lower()}.csv"

    def load_index(self, code: str = "XU100") -> pd.Series:
        path = self.index_path(code)
        if not path.exists():
            return pd.Series(dtype=float, name=code)
        df = pd.read_csv(path, parse_dates=["date"])
        return df.set_index("date")["value"].rename(code)

    def sync_index(self, code: str, start: dt.date, end: dt.date) -> pd.Series:
        """Endeks kapanışlarını yeniler (ör. ``XU100``). Başarısızlıkta önbelleği korur."""
        old = self.load_index(code)
        try:
            new = fetch_isy_index(self.client, code, start, end)
            new = new[new > 0]
            if new.empty:
                raise HttpError(f"{code}: boş seri")
        except Exception as exc:
            if old.empty:
                raise
            log.warning("%s endeksi yenilenemedi, önbellek kullanılıyor: %s", code, exc)
            return old
        merged = pd.concat([old[~old.index.isin(new.index)], new]).sort_index() if not old.empty else new
        merged.rename("value").rename_axis("date").to_csv(self.index_path(code))
        return merged.rename(code)
