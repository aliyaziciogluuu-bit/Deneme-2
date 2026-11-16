"""İş Yatırım'ın herkese açık (anahtarsız, resmî olmayan) veri uçları.

Bu projede İş Yatırım iki amaçla kullanılır:

1. ``HisseTekil``: aynı gün için ham kapanış (``HG_KAPANIS``) ve temettü + bedelli +
   bedelsiz düzeltilmiş kapanış (``HGDG_KAPANIS``). İkisinin oranı o günün geriye dönük
   düzeltme katsayısıdır. Kottan çıkmış paylar da sorgulanabilir; kodu değişen paylar
   yalnızca yeni kodlarıyla bulunur.
2. ``GetSermayeArttirimlari``: sermaye artırımı ve temettü olayları (tarih, oranlar,
   brüt/net nakit temettü, fiyat ayar oranı).

Ayrıca her satırda BIST 100 kapanışı (``END_DEGER``) ve USD/TRY (``DD_DEGER``) gelir.
"""
from __future__ import annotations

import datetime as dt
import json
import logging

import pandas as pd

from .http import HttpClient, HttpError

log = logging.getLogger(__name__)

BASE = "https://www.isyatirim.com.tr"
HISSE_TEKIL_URL = BASE + "/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil"
SERMAYE_URL = BASE + "/_layouts/15/IsYatirim.Website/StockInfo/CompanyInfoAjax.aspx/GetSermayeArttirimlari"

HISTORY_COLUMNS = [
    "date", "raw_close", "adj_close", "raw_vwap", "raw_low", "raw_high", "value",
    "xu100", "usdtry", "mcap", "ff_mcap",
]
_FIELD_MAP = {
    "HG_KAPANIS": "raw_close",
    "HGDG_KAPANIS": "adj_close",
    "HG_AOF": "raw_vwap",
    "HG_MIN": "raw_low",
    "HG_MAX": "raw_high",
    "HG_HACIM": "value",
    "END_DEGER": "xu100",
    "DD_DEGER": "usdtry",
    "PD": "mcap",
    "HAO_PD": "ff_mcap",
}

ACTION_COLUMNS = [
    "date", "type_code", "type_name", "rights_pct", "bonus_pct", "div_gross_pct",
    "div_net_pct", "price_factor",
]


def _loads(content: bytes) -> dict:
    return json.loads(content.decode("utf-8-sig"))


def fetch_history(client: HttpClient, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Bir payın günlük ham ve düzeltilmiş kapanışlarını getirir (boşsa boş tablo)."""
    params = {
        "hisse": symbol,
        "startdate": start.strftime("%d-%m-%Y"),
        "enddate": end.strftime("%d-%m-%Y"),
    }
    resp = client.get(HISSE_TEKIL_URL, params=params)
    if resp is None:
        raise HttpError(f"HisseTekil 404: {symbol}")
    payload = _loads(resp.content)
    if not payload.get("ok", False):
        raise HttpError(f"HisseTekil hata: {symbol}: {payload.get('errorCode')} {payload.get('errorDescription')}")
    rows = payload.get("value") or []
    if not rows:
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    df = pd.DataFrame(rows)
    out = pd.DataFrame({"date": pd.to_datetime(df["HGDG_TARIH"], format="%d-%m-%Y")})
    for src, dst in _FIELD_MAP.items():
        out[dst] = pd.to_numeric(df[src], errors="coerce") if src in df.columns else float("nan")
    out = out.dropna(subset=["date"]).drop_duplicates("date", keep="last").sort_values("date")
    return out[HISTORY_COLUMNS].reset_index(drop=True)


def fetch_corporate_actions(client: HttpClient, symbol: str) -> pd.DataFrame:
    """Bir payın sermaye artırımı / temettü olaylarını getirir."""
    body = {
        "hisseKodu": symbol, "hisseTanimKodu": "", "yil": 0, "zaman": "HEPSI",
        "endeksKodu": "09", "sektorKodu": "",
    }
    resp = client.post_json(SERMAYE_URL, body)
    payload = _loads(resp.content)
    rows = json.loads(payload.get("d") or "[]")
    if not rows:
        return pd.DataFrame(columns=ACTION_COLUMNS)
    df = pd.DataFrame(rows)

    def num(col: str) -> pd.Series:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return pd.Series(0.0, index=df.index)

    # Zaman damgaları İstanbul gece yarısıdır (UTC+3); tarihe çevirirken kaydır.
    ts = pd.to_datetime(pd.to_numeric(df["SHHE_TARIH"], errors="coerce"), unit="ms", utc=True)
    out = pd.DataFrame(
        {
            "date": ts.dt.tz_convert("Europe/Istanbul").dt.tz_localize(None).dt.normalize(),
            "type_code": df.get("SHT_KODU", pd.Series("", index=df.index)).astype(str),
            "type_name": df.get("SHT_TANIMI", pd.Series("", index=df.index)).astype(str),
            "rights_pct": num("SHHE_BDLI_ORAN"),
            "bonus_pct": num("SHHE_BDSZ_IK_ORAN") + num("SHHE_BDSZ_TM_ORAN"),
            "div_gross_pct": num("SHHE_NAKIT_TM_ORAN"),
            "div_net_pct": num("SHHE_NAKIT_TM_ORAN_NET"),
            "price_factor": pd.to_numeric(df.get("SHHE_FIYAT_AYAR_OR"), errors="coerce"),
        }
    )
    return out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)[ACTION_COLUMNS]


# --------------------------------------------------------------------------- mali tablolar
FINANCIALS_URL = BASE + "/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"

#: Mali tablo grubu -> {iç ad: kalem kodu}. XI_29: sanayi/ticaret/holding/GYO (TFRS);
#: UFRS_K ve UFRS: banka, sigorta vb. (konsolide ve konsolide olmayan).
FINANCIAL_ITEMS = {
    "XI_29": {"equity": "2O", "net_income": "3Z", "total_assets": "1BL", "sales": "3C", "gross_profit": "3D"},
    "UFRS_K": {"equity": "2O", "net_income": "3Z", "total_assets": "1Z"},
    "UFRS": {"equity": "2O", "net_income": "3Z", "total_assets": "1Z"},
}
FINANCIAL_COLUMNS = ["year", "period", "group", "equity", "net_income", "total_assets", "sales", "gross_profit"]


def fetch_financials(
    client: HttpClient, symbol: str, group: str, periods: list[tuple[int, int]]
) -> pd.DataFrame:
    """En fazla 4 dönem (yıl, ay∈{3,6,9,12}) için seçilmiş bilanço/gelir kalemlerini getirir.

    Gelir tablosu kalemleri yıl içi kümülatiftir (3, 6, 9, 12 aylık). Veri olmayan dönem
    satır olarak dönmez.
    """
    if not 1 <= len(periods) <= 4:
        raise ValueError("bir istekte 1-4 dönem istenebilir")
    padded = list(periods) + [periods[-1]] * (4 - len(periods))
    params = {"companyCode": symbol, "exchange": "TRY", "financialGroup": group}
    for i, (year, month) in enumerate(padded, start=1):
        params[f"year{i}"] = year
        params[f"period{i}"] = month
    resp = client.get(FINANCIALS_URL, params=params)
    if resp is None:
        raise HttpError(f"MaliTablo 404: {symbol}")
    payload = _loads(resp.content)
    rows = payload.get("value") or []
    if not rows:
        return pd.DataFrame(columns=FINANCIAL_COLUMNS)
    by_code = {r.get("itemCode"): r for r in rows}
    items = FINANCIAL_ITEMS[group]
    out = []
    for i, (year, month) in enumerate(periods, start=1):
        rec = {"year": year, "period": month, "group": group}
        found = False
        for name in ("equity", "net_income", "total_assets", "sales", "gross_profit"):
            code = items.get(name)
            raw = by_code.get(code, {}).get(f"value{i}") if code else None
            val = pd.to_numeric(raw, errors="coerce") if raw is not None else float("nan")
            rec[name] = float(val) if val == val else float("nan")
            found = found or (val == val)
        if found and rec["equity"] == rec["equity"]:
            out.append(rec)
    return pd.DataFrame(out, columns=FINANCIAL_COLUMNS)
