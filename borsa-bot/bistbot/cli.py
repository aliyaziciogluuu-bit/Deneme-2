"""Komut satırı: ``python -m bistbot <komut>``.

* ``gunluk``   — günlük çalıştırma: veri eşitle, kâğıt portföyü güncelle, emir listesi üret, bildir.
* ``backtest`` — ön kayıtlı stratejinin geçmiş testi ve sağlamlık raporu.
* ``veri``     — uzun dönem veriyi indir (backtest için).
* ``doktor``   — veri kaynaklarına erişimi sına.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config
from .pipeline import default_cache_dir, load_panel, open_stores, prepare_dataset, sync_isy

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "ayar.toml"
DEFAULT_STATE = ROOT / "state" / "bot.json"
DEFAULT_WEB_DATA = ROOT / "web" / "data"
BACKTEST_START = dt.date(2015, 11, 30)

log = logging.getLogger("bistbot")


def _istanbul_now() -> dt.datetime:
    """İstanbul saati (UTC+3, yaz saati uygulaması yok)."""
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3)).replace(tzinfo=None)


def _istanbul_today() -> dt.date:
    return _istanbul_now().date()


def _json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if not np.isfinite(obj) else float(obj)
    if isinstance(obj, (pd.Timestamp, dt.date, dt.datetime)):
        return str(obj)[:10]
    raise TypeError(f"JSON'a çevrilemeyen tür: {type(obj)}")


def _clean(obj):
    """NaN/inf değerlerini JSON için ``None`` yapar."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, float) and not np.isfinite(obj):
        return None
    return obj


def same_content(path: Path, data: dict, ignore: tuple[str, ...] = ("generated_at",)) -> bool:
    """Dosyadaki JSON, ``ignore`` alanları dışında ``data`` ile aynı mı?"""
    if not path.exists():
        return False
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    new = json.loads(json.dumps(_clean(data), ensure_ascii=False, default=_json_default))
    for key in ignore:
        old.pop(key, None)
        new.pop(key, None)
    return old == new


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_clean(data), ensure_ascii=False, default=_json_default, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------- komutlar
def cmd_gunluk(args) -> int:
    from .live.notify import format_message, send_telegram
    from .live.runner import DataNotReady, notification_digest, run_daily

    cfg = load_config(args.ayar)
    stores = open_stores(args.onbellek, live=True)
    if args.bugun:
        hour, minute = (int(x) for x in args.saat.split(":"))
        now = dt.datetime.combine(dt.date.fromisoformat(args.bugun), dt.time(hour, minute))
    else:
        now = _istanbul_now()
    try:
        result = run_daily(stores, args.durum, cfg, now, sync=not args.esitleme_yok, save=not args.deneme)
    except DataNotReady as exc:
        log.error("veri hazır değil: %s", exc)
        if not args.bildirim_yok and not args.deneme:
            send_telegram(f"⚠️ BIST Bot çalışamadı: {exc}. Bir sonraki çalıştırmada yeniden denenecek.")
        return 2
    payload = result.payload
    if payload is None:  # henüz başlamadı: ilk karar için uygun zaman bekleniyor
        print(result.message)
        return 0
    message = format_message(payload)
    print(message)
    if args.deneme:
        return 0
    # Yeni seans yoksa içerik değişmez: dosyayı yeniden yazma (gereksiz depo kaydı oluşmasın).
    if not same_content(args.web / "latest.json", payload):
        write_json(args.web / "latest.json", payload)
    state = result.state
    digest = notification_digest(payload)
    if not args.bildirim_yok and (digest != state.notified or args.yeniden_bildir):
        if send_telegram(message):
            state.notified = digest
            state.save(args.durum)
    return 0


def cmd_veri(args) -> int:
    stores = open_stores(args.onbellek)
    today = _istanbul_today()
    start = dt.date.fromisoformat(args.baslangic) if args.baslangic else BACKTEST_START
    stats = stores.bulletins.sync(start, today, today=today, workers=args.is_parcacigi, progress=True)
    log.info("bültenler: %s", stats)
    stores.macro.sync_rf(start - dt.timedelta(days=40), today)
    stores.macro.sync_index("XU100", start - dt.timedelta(days=40), today)
    panel = load_panel(stores, start, today)
    ever = sorted(panel.bist100.columns[panel.bist100.any().to_numpy()])
    log.info("%d seans, %d pay; BIST 100'e girmiş %d pay için İş Yatırım verisi eşitleniyor", len(panel.dates),
             len(panel.symbols), len(ever))
    log.info("İş Yatırım: %s", sync_isy(stores, panel, ever, today, financials_start=dt.date(start.year - 1, 1, 1)))
    return 0


def cmd_backtest(args) -> int:
    from .research import full_report

    cfg = load_config(args.ayar)
    stores = open_stores(args.onbellek)
    today = _istanbul_today()
    panel = load_panel(stores, BACKTEST_START, today)
    ever = sorted(panel.bist100.columns[panel.bist100.any().to_numpy()])
    ds = prepare_dataset(stores, panel, ever)
    report = full_report(ds, cfg, args.baslangic, n_random=args.rastgele, n_boot=args.bootstrap)
    series = report.pop("_series")
    report.pop("_primary")
    weekly = pd.DataFrame(series).resample("W-FRI").last().dropna(how="all")
    report["curve"] = [
        {"d": str(d.date()), **{k: (round(float(v), 5) if np.isfinite(v) else None) for k, v in row.items()}}
        for d, row in weekly.iterrows()
    ]
    report["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    write_json(args.cikti, report)
    p = report["primary"]["vs_ew"]
    print(f"Dönem {report['start']} → {report['end']}")
    print(f"Strateji: yıllık %{p['cagr'] * 100:.1f}, Sharpe {p['sharpe']:.2f}, en büyük düşüş %{p['max_drawdown'] * 100:.1f}")
    for key, label in (("ew", "Eşit ağırlıklı BIST 100"), ("xu100", "BIST 100 endeksi"), ("cash", "Gecelik faiz")):
        b = report["benchmarks"][key]
        print(f"{label}: yıllık %{b['cagr'] * 100:.1f}, en büyük düşüş %{b['max_drawdown'] * 100:.1f}")
    print(f"Rapor: {args.cikti}")
    return 0


def cmd_doktor(args) -> int:
    from .data import isyatirim as isy
    from .data.bulletin import bulletin_url
    from .data.http import HttpClient
    from .data.macro import fetch_tlref_latest

    client = HttpClient(retries=1, timeout=30)
    today = _istanbul_today()
    ok = True

    def check(name, fn):
        nonlocal ok
        try:
            print(f"[tamam] {name}: {fn()}")
        except Exception as exc:
            ok = False
            print(f"[HATA ] {name}: {type(exc).__name__}: {exc}")

    def bulletin():
        day = today
        for _ in range(10):
            day -= dt.timedelta(days=1)
            if day.weekday() < 5 and client.get(bulletin_url(day)) is not None:
                return f"{day} bülteni erişilebilir"
        raise RuntimeError("son 10 günde bülten bulunamadı")

    check("Borsa İstanbul günlük bülten", bulletin)
    check("Borsa İstanbul TLREF", lambda: f"{fetch_tlref_latest(client).iloc[-1] * 100:.2f}%")
    check("İş Yatırım fiyat", lambda: f"{len(isy.fetch_history(client, 'GARAN', today - dt.timedelta(days=20), today))} satır")
    check("İş Yatırım özsermaye olayları", lambda: f"{len(isy.fetch_corporate_actions(client, 'GARAN'))} olay")
    check("İş Yatırım mali tablo", lambda: f"{len(isy.fetch_financials(client, 'GARAN', 'UFRS_K', [(today.year - 1, 12)]))} dönem")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bistbot", description="Borsa İstanbul için kurallı al-sat botu (kâğıt portföy + emir listesi).")
    parser.add_argument("--onbellek", type=Path, default=default_cache_dir(), help="veri önbelleği klasörü")
    parser.add_argument("--ayar", type=Path, default=DEFAULT_CONFIG, help="ayar dosyası (TOML)")
    parser.add_argument("-v", "--ayrintili", action="store_true")
    sub = parser.add_subparsers(dest="komut", required=True)

    g = sub.add_parser("gunluk", help="günlük çalıştırma")
    g.add_argument("--durum", type=Path, default=DEFAULT_STATE)
    g.add_argument("--web", type=Path, default=DEFAULT_WEB_DATA)
    g.add_argument("--bugun", help="tarihi elle ver (YYYY-AA-GG); sınama içindir")
    g.add_argument("--saat", default="20:00", help="--bugun ile birlikte İstanbul saati (SS:DD)")
    g.add_argument("--esitleme-yok", action="store_true", help="veri indirme; yalnızca önbelleği kullan")
    g.add_argument("--bildirim-yok", action="store_true")
    g.add_argument("--yeniden-bildir", action="store_true", help="içerik değişmese de bildirimi yeniden gönder")
    g.add_argument("--deneme", action="store_true", help="hiçbir şey kaydetme, yalnızca ekrana yaz")
    g.set_defaults(func=cmd_gunluk)

    d = sub.add_parser("veri", help="uzun dönem veriyi indir")
    d.add_argument("--baslangic", help="YYYY-AA-GG (varsayılan 2015-11-30)")
    d.add_argument("--is-parcacigi", type=int, default=4)
    d.set_defaults(func=cmd_veri)

    b = sub.add_parser("backtest", help="geçmiş testi ve sağlamlık raporu")
    b.add_argument("--baslangic", default="2017-01-02")
    b.add_argument("--rastgele", type=int, default=200, help="rastgele portföy sayısı")
    b.add_argument("--bootstrap", type=int, default=2000)
    b.add_argument("--cikti", type=Path, default=DEFAULT_WEB_DATA / "backtest.json")
    b.set_defaults(func=cmd_backtest)

    k = sub.add_parser("doktor", help="veri kaynaklarına erişimi sına")
    k.set_defaults(func=cmd_doktor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.ayrintili else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S",
    )
    # HTTP kitaplığının ayrıntı günlüğü istek adresini yazar; Telegram adresi anahtarı içerdiği
    # için ayrıntılı kipte bile kapalı tutulur.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
