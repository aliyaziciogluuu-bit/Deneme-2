"""Bildirim: günlük özet ve emir listesinin metni, Telegram'a gönderimi.

Telegram bilgileri ortam değişkenlerinden okunur (``TELEGRAM_BOT_TOKEN``, ``TELEGRAM_CHAT_ID``)
ve hiçbir zaman günlüğe ya da dosyaya yazılmaz.
"""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4000  # Telegram sınırı 4096 karakter; pay bırakılır


def tl(value: float, digits: int = 0) -> str:
    """12345.6 -> '12.346' (Türkçe binlik ayırıcı)."""
    text = f"{value:,.{digits}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "–"
    return f"{value * 100:+.{digits}f}".replace(".", ",") + "%"


def tr_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def format_message(payload: dict) -> str:
    """Panel verisinden okunaklı Türkçe özet üretir."""
    lines = [
        f"📊 BIST Bot — {tr_date(payload['as_of'])} kapanışı",
        f"Kâğıt portföy: {tl(payload['equity'])} TL  (gün {pct(payload['day_return'])}, toplam {pct(payload['total_return'])})",
        f"Aynı dönemde BIST 100 {pct(payload['xu100_return'])}, gecelik faiz {pct(payload['cash_return'])}",
        f"Hisse ağırlığı %{payload['invested_pct'] * 100:.0f}, {len(payload['positions'])} hisse, nakit {tl(payload['cash'])} TL",
    ]
    orders = payload.get("orders") or []
    if orders:
        lines += ["", f"🔔 SONRAKİ SEANS AÇILIŞI İÇİN EMİRLER (en erken {tr_date(payload['next_session'])})"]
        for o in orders:
            side = "SAT" if o["side"] == "sell" else "AL "
            bound = "en az" if o["side"] == "sell" else "en çok"
            note = "  (önceki günden kalan)" if o.get("carried") else ""
            lines.append(
                f"{side} {o['symbol']:<6} {o['lots']} lot  ≈{tl(o['value'])} TL  "
                f"limit {bound} {tl(o['limit_price'], 2)}{note}"
            )
        lines.append("Önce satışları, sonra alışları girin. Emirler açılış seansı (09:40-09:55) için limitlidir.")
    else:
        lines += ["", "Yeni emir yok."]
    fills = payload.get("fills_today") or []
    if fills:
        lines += ["", "✅ Bugün gerçekleşen (kâğıt portföy, açılış fiyatından)"]
        for f in fills:
            side = "SAT" if f["side"] == "sell" else "AL "
            lines.append(f"{side} {f['symbol']:<6} {f['lots']} lot @ {tl(f['price'], 2)}")
    for e in payload.get("events") or []:
        if e["kind"] == "temettü":
            lines += ["", f"💰 {e['symbol']} temettü ödedi: nakde +{tl(e['cash'])} TL (stopaj sonrası)."]
        elif e["kind"] == "bedelsiz":
            lines += ["", f"ℹ️ {e['symbol']} bedelsiz/bölünme: lot adediniz {e['lots_before']} → {e['lots_after']}."]
        else:
            lines += ["", (f"⚠️ {e['symbol']} bedelli sermaye artırımı: rüçhan haklarınızı satmanız ya da kullanmanız "
                           f"gerekir. Kâğıt portföy hakların satıldığını varsaydı (+{tl(e['cash'])} TL).")]
    for w in payload.get("warnings") or []:
        lines += ["", f"⚠️ {w}"]
    lines += ["", "Bu bir yatırım tavsiyesi değildir; emirleri kendiniz verirsiniz."]
    return "\n".join(lines)


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Uzun metni satır sınırlarından böler."""
    parts, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # tek satır sınırı aşıyorsa zorla böl
            parts.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def telegram_configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def send_telegram(text: str, timeout: float = 30.0) -> bool:
    """Metni Telegram'a gönderir. Ayar yoksa veya gönderim başarısızsa ``False`` döner."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.info("Telegram ayarlı değil; bildirim gönderilmedi")
        return False
    ok = True
    for part in split_message(text):
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": part, "disable_web_page_preview": "true"},
                timeout=timeout,
            )
            if resp.status_code != 200:
                # Yanıt gövdesi anahtarı içermez; yine de yalnızca durum kodu yazılır.
                log.warning("Telegram gönderimi başarısız: HTTP %s", resp.status_code)
                ok = False
        except requests.RequestException as exc:
            # İstisna metni URL'yi (ve içindeki anahtarı) barındırabilir: yazdırma.
            log.warning("Telegram gönderimi başarısız: %s", type(exc).__name__)
            ok = False
    return ok
