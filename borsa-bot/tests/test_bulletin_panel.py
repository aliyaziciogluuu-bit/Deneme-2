import datetime as dt
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from bistbot.data.bulletin import BulletinFormatError, parse_bulletin_csv, parse_bulletin_zip
from bistbot.data.panel import build_panel, detect_renames, resolve_chain

HEADER_TR = (
    "TARIH;ISLEM  KODU;BULTEN ADI;PAZAR;ENSTRUMAN GRUBU;ISLEM YONTEMI;BIST 100 ENDEKS;BIST 30 ENDEKS;"
    "BRUT TAKAS;OZSERMAYE HALI;GECICI DURDURMA;ONCEKI KAPANIS FIYATI;ACILIS FIYATI;EN DUSUK FIYAT;"
    "EN YUKSEK FIYAT;KAPANIS FIYATI;A.O.F;TOPLAM ISLEM HACMI;TOPLAM ISLEM ADEDI;TOPLAM SOZLESME SAYISI;ACIGA SATIS"
)
HEADER_EN = HEADER_TR.replace("TARIH", "TRADE DATE")
ROWS = [
    "2026-11-13;THYAO.E;TURK HAVA YOLLARI;Z;EQT;SI;1;1;0;;0;319;315.75;315;323.5;320.25;320.986;9504155459.75;29607838;57568;1",
    "2026-11-13;MGROS.E;MIGROS TICARET;Z;EQT;SI;1;1;0;06;0;491;491;474.5;491.25;476.5;479.919;992156251;2067339;21229;1",
    "2026-11-13;UMPAS.E;UMPAS HOLDING;S;EQT;TF;0;0;1;;1;9.3;0;0;0;0;0;0;0;0;0",
    "2026-11-13;THYAO.V;THYAO VARANT;K;ECW;PY;0;0;0;;0;1;1;1;1;1;1;100;100;1;0",
    "2026-11-13;GLDTR.F;ALTIN FONU;K;ETF;SI;0;0;0;;0;100;100;100;100;100;100;100;1;1;0",
]


def _csv(rows=ROWS) -> bytes:
    return "\n".join([HEADER_TR, HEADER_EN, *rows]).encode("cp1254")


def test_parse_keeps_only_equities_and_normalises_fields():
    df = parse_bulletin_csv(_csv(), dt.date(2026, 11, 13))
    assert list(df["symbol"]) == ["MGROS", "THYAO", "UMPAS"]
    thy = df.set_index("symbol").loc["THYAO"]
    assert thy["close"] == 320.25 and thy["open"] == 315.75 and thy["bist100"] == 1
    assert thy["value"] == pytest.approx(9504155459.75)
    assert df.set_index("symbol").loc["MGROS", "corp_action"] == "06"


def test_untraded_stock_has_nan_prices_but_keeps_previous_close():
    row = parse_bulletin_csv(_csv(), dt.date(2026, 11, 13)).set_index("symbol").loc["UMPAS"]
    assert np.isnan(row["close"]) and np.isnan(row["open"])
    assert row["prev_close"] == 9.3 and row["suspended"] == 1 and row["gross"] == 1 and row["value"] == 0


def test_zip_wrapper_and_format_errors():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("thb202611131.csv", _csv())
    assert len(parse_bulletin_zip(buf.getvalue(), dt.date(2026, 11, 13))) == 3
    with pytest.raises(BulletinFormatError):
        parse_bulletin_csv("A;B\nC;D\n1;2".encode("cp1254"), dt.date(2026, 11, 13))
    with pytest.raises(BulletinFormatError):
        parse_bulletin_csv(_csv(ROWS[3:]), dt.date(2026, 11, 13))  # hiç pay satırı yok


def _long(spec):
    """spec: {symbol: (name, first_day_index, last_day_index, close)}"""
    days = pd.bdate_range("2025-11-17", periods=10)
    rows = []
    for sym, (name, first, last, close) in spec.items():
        for i in range(first, last + 1):
            rows.append(
                {"date": days[i], "symbol": sym, "name": name, "market": "Z", "method": "SI",
                 "bist100": 1, "bist30": 0, "gross": 0, "suspended": 0, "short_ok": 1, "corp_action": "",
                 "prev_close": np.nan if i == first else close, "open": close, "high": close, "low": close,
                 "close": close, "vwap": close, "value": 1e6, "volume": 1e5, "trades": 10}
            )
    return pd.DataFrame(rows)


def test_rename_detected_by_same_name():
    long = _long({"KOZAL": ("TURK ALTIN", 0, 4, 40.0), "TRALT": ("TURK ALTIN", 5, 9, 40.04), "AAA": ("A", 0, 9, 5.0)})
    assert detect_renames(long) == {"KOZAL": "TRALT"}


def test_rename_detected_by_price_continuity_when_name_changes():
    long = _long({"GUSGR": ("GUNES SIGORTA", 0, 4, 6.14), "TURSG": ("TURKIYE SIGORTA", 5, 9, 6.16),
                  "AAA": ("A", 0, 9, 5.0)})
    assert detect_renames(long) == {"GUSGR": "TURSG"}


def test_merger_and_unrelated_ipo_are_not_renames():
    # TRKCM kottan çıkıyor; aynı gün bambaşka fiyatla bir halka arz başlıyor.
    long = _long({"TRKCM": ("TRAKYA CAM", 0, 4, 4.79), "ESEN": ("ESENBOGA", 5, 9, 9.35), "AAA": ("A", 0, 9, 5.0)})
    assert detect_renames(long) == {}


def test_ambiguous_price_match_is_rejected():
    long = _long({"OLD1": ("X", 0, 4, 10.0), "OLD2": ("Y", 0, 4, 10.2), "NEW": ("Z", 5, 9, 10.1),
                  "AAA": ("A", 0, 9, 5.0)})
    assert detect_renames(long) == {}


def test_chain_and_panel_merge_history_under_latest_code():
    long = _long({"A1": ("FIRMA", 0, 2, 10.0), "A2": ("FIRMA", 3, 6, 10.0), "A3": ("FIRMA", 7, 9, 10.0),
                  "BBB": ("B", 0, 9, 5.0)})
    renames = detect_renames(long)
    assert resolve_chain(renames) == {"A1": "A3", "A2": "A3"}
    panel = build_panel(long, renames)
    assert list(panel.symbols) == ["A3", "BBB"]
    assert panel.close["A3"].notna().all() and panel.listed["A3"].all()
    assert sorted(panel.old_codes("A3")) == ["A1", "A2"]
