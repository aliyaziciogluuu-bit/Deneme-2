"""Halka Arz Karnesi: halka arz çalışmasının (``ipo.py``) verisinden durağan bir site üretir.

Sayfalar: ana sayfa (bütün halka arzların tablosu), her halka arz için bir karne sayfası,
analiz yazısı ve yöntem sayfası. Her şey resmî günlük bültenlerden hesaplanır; yorum ya da
öneri üretilmez.

Geçmişteki bir halka arzın karnesi (tavan serisi, sonraki 20/60 seans) zamanla değişmez.
Günlük değişen rakamlar (son fiyat, bugüne kadarki getiri) ``data/ozet.json`` dosyasında
tutulur ve karne sayfalarına tarayıcıda yerleştirilir; böylece günlük güncelleme yalnızca
birkaç dosyayı değiştirir.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import ipo
from .config import CostConfig
from .data.panel import MarketPanel
from .rules import LIMIT_AFTER, LIMIT_CHANGE_DATE

SITE_NAME = "Halka Arz Karnesi"
MARKET_NAMES = {"Z": "Yıldız Pazar", "N": "Ana Pazar", "K": "Kolektif Yatırım Ürünleri Pazarı",
                "G": "Gelişen İşletmeler Pazarı"}
MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim",
          "Kasım", "Aralık")
#: Karne grafiğinde gösterilen seans sayısı.
CHART_SESSIONS = 60
#: Halka arz fiyatı bültende yoktur. İlk iki gün tavanda kilitliyse ilk kapanış halka arz
#: fiyatının bir tavan (%10) üstüdür; fiyat ancak o durumda hesaplanır.
MIN_STREAK_FOR_PRICE = 2


# ---------------------------------------------------------------------------------------------
# Biçimlendirme
# ---------------------------------------------------------------------------------------------
def num(v: float, d: int = 2) -> str:
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float | None, d: int = 1, sign: bool = True) -> str:
    """``0.123`` → ``+%12,3``; eksi için gerçek eksi işareti; değer yoksa uzun çizgi."""
    if v is None or not np.isfinite(v):
        return "—"
    body = "%" + num(abs(v) * 100, d)
    if float(num(abs(v) * 100, d).replace(".", "").replace(",", ".")) == 0:
        return body
    return ("−" if v < 0 else "+" if sign else "") + body


def tone(v: float | None) -> str:
    if v is None or not np.isfinite(v) or abs(v) < 0.0005:
        return ""
    return "pos" if v > 0 else "neg"


def day(d) -> str:
    d = pd.Timestamp(d)
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def long_day(d) -> str:
    d = pd.Timestamp(d)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


# ---------------------------------------------------------------------------------------------
# Veri
# ---------------------------------------------------------------------------------------------
def _clean(v):
    if v is None:
        return None
    if isinstance(v, (np.floating, float)):
        return float(v) if np.isfinite(v) else None
    if isinstance(v, (np.integer,)):
        return int(v)
    return v


def build_records(panel: MarketPanel, rf: pd.Series, factor: pd.DataFrame | None = None,
                  cost: CostConfig | None = None) -> list[dict]:
    """Her halka arz için karne kaydı (en yeni önce)."""
    cost = cost or CostConfig()
    dates = panel.dates
    mkt = ipo.market_returns(panel)
    listings = ipo.find_listings(panel)
    ev = ipo.events(panel, listings, factor)
    markets = dict(zip(listings["symbol"], listings["market"]))
    out = []
    for r in ev.itertuples():
        q = ipo.quotes(panel, r.symbol, factor)
        pos, t = int(r.pos), int(r.T)
        first_close = float(q.close[pos]) if np.isfinite(q.close[pos]) else float(q.adj[pos])
        traded = np.flatnonzero(np.isfinite(q.close))
        last = int(traded[-1])
        # Katsayısı olmayan payda özsermaye olayı sonrası getiri hesaplanamaz.
        reliable = q.adjusted or not q.flagged[pos + 1:].any()
        index = q.adj / q.adj[pos]                      # ilk gün kapanışı = 1
        priced = int(r.S) >= MIN_STREAK_FOR_PRICE and dates[pos] >= LIMIT_CHANGE_DATE
        up = 1.0 + LIMIT_AFTER
        rec = {
            "symbol": r.symbol, "name": r.name, "first_day": dates[pos], "market": markets.get(r.symbol, ""),
            "streak": int(r.S), "open_day": dates[t], "sessions": int(last - pos + 1),
            "first_close": first_close, "ipo_price": round(first_close / up, 2) if priced else None,
            "last_close": float(q.close[last]), "last_day": dates[last],
            "active": bool(panel.listed[r.symbol].iloc[-1]) and last >= len(dates) - 5,
            "since_first": float(index[last] - 1.0) if reliable else None,
            "since_ipo": float(index[last] * up - 1.0) if reliable and priced else None,
            "streak_gain": float(q.adj[t - 1] / q.adj[pos] * up - 1.0) if priced else None,
        }
        for h in (20, 60):
            tr = ipo.trade(panel, mkt, rf, r.symbol, t, h, cost, factor)
            rec[f"r{h}"] = None if tr is None else float(tr["gross"])
            rec[f"m{h}"] = None if tr is None else float(tr["market"])
            rec[f"n{h}"] = None if tr is None else float(tr["net"])
        end = min(len(dates), pos + CHART_SESSIONS + 1)
        base = up if priced else 1.0
        rec["chart"] = [round(float(v * base - 1.0), 4) for v in index[pos:end]] if reliable else []
        rec["chart_open"] = t - pos
        out.append({k: _clean(v) for k, v in rec.items()})
    out.sort(key=lambda x: (x["first_day"], x["symbol"]), reverse=True)
    # Tavan serisi sıralaması (aynı uzunluktakiler aynı sırayı paylaşır).
    streaks = sorted((x["streak"] for x in out), reverse=True)
    for x in out:
        x["streak_rank"] = streaks.index(x["streak"]) + 1
    return out


def yearly(records: list[dict]) -> list[dict]:
    rows = []
    for year in sorted({r["first_day"].year for r in records}, reverse=True):
        rs = [r for r in records if r["first_day"].year == year]
        done = [r["n20"] for r in rs if r["n20"] is not None]
        rows.append({
            "year": year, "count": len(rs),
            "streak_mean": float(np.mean([r["streak"] for r in rs])),
            "streak_share": float(np.mean([r["streak"] >= 1 for r in rs])),
            "lost20": float(np.mean([v < 0 for v in done])) if done else None,
            "median20": float(np.median(done)) if done else None,
        })
    return rows


# ---------------------------------------------------------------------------------------------
# Sayfa parçaları
# ---------------------------------------------------------------------------------------------
def page(title: str, description: str, body: str, depth: int, base_url: str | None, path: str) -> str:
    root = "../" * depth or "./"
    canonical = f'\n<link rel="canonical" href="{esc(base_url.rstrip("/") + "/" + path)}">' if base_url else ""
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">{canonical}
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta name="theme-color" content="#0a1020">
<link rel="stylesheet" href="{root}assets/site.css">
</head>
<body>
<header class="top">
  <a class="brand" href="{root}">{SITE_NAME}</a>
  <nav><a href="{root}">Halka arzlar</a><a href="{root}analiz/">Analiz</a><a href="{root}yontem/">Yöntem</a></nav>
</header>
<main>
{body}
</main>
<footer>
  <p><strong>Yatırım tavsiyesi değildir.</strong> Bu sitedeki her şey geçmiş veriden hesaplanmış bilgidir; alım-satım
  önerisi içermez. Geçmiş getiriler geleceği göstermez.</p>
  <p>Veri: Borsa İstanbul resmî Pay Piyasası günlük bültenleri. Hesaplama ayrıntıları için
  <a href="{root}yontem/">yöntem</a> sayfasına bakın.</p>
</footer>
<script src="{root}assets/site.js" defer></script>
</body>
</html>
"""


def stat(label: str, value: str, cls: str = "", note: str = "", attrs: str = "") -> str:
    note_html = f'<div class="n">{note}</div>' if note else ""
    return f'<div class="stat"><div class="k">{label}</div><div class="v {cls}"{attrs}>{value}</div>{note_html}</div>'


def chart_svg(rec: dict) -> str:
    """İlk 60 seansın getiri eğrisi (halka arz fiyatına ya da ilk kapanışa göre)."""
    ys = rec["chart"]
    if len(ys) < 2:
        return ""
    w, h, left, right, top, bottom = 640, 260, 52, 14, 14, 30
    lo, hi = min(min(ys), 0.0), max(max(ys), 0.0)
    span = (hi - lo) or 1.0
    lo, hi = lo - 0.06 * span, hi + 0.06 * span
    n = max(len(ys) - 1, 1)

    def x(i):
        return left + (w - left - right) * i / max(n, CHART_SESSIONS if len(ys) > CHART_SESSIONS // 2 else n)

    def y(v):
        return top + (hi - v) / (hi - lo) * (h - top - bottom)

    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(ys))
    ticks = ""
    for v in sorted({lo + (hi - lo) * k / 4 for k in range(5)} | {0.0}):
        if not lo <= v <= hi:
            continue
        zero = abs(v) < 1e-9
        ticks += (f'<line x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="{"zero" if zero else "grid"}"/>'
                  f'<text x="{left - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{pct(v, 0)}</text>')
    marker = ""
    k = rec["chart_open"]
    if 0 < k < len(ys):
        marker = (f'<line x1="{x(k):.1f}" x2="{x(k):.1f}" y1="{top}" y2="{h - bottom}" class="mark"/>'
                  f'<text x="{x(k) + 6:.1f}" y="{top + 12}" class="marklbl">tavan bozuldu</text>')
    last_x = x(len(ys) - 1)
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="İlk {len(ys) - 1} işlem gününde getiri">'
            f'{ticks}{marker}<polyline points="{points}" class="line"/>'
            f'<text x="{left}" y="{h - 8}">ilk gün</text>'
            f'<text x="{last_x:.1f}" y="{h - 8}" text-anchor="end">{len(ys) - 1}. işlem günü</text></svg>')


def result_line(rec: dict, h: int) -> str:
    r, m = rec[f"r{h}"], rec[f"m{h}"]
    if r is None:
        return "henüz dolmadı"
    return f'<span class="{tone(r)}">{pct(r)}</span> <span class="muted">(piyasa {pct(m)})</span>'


# ---------------------------------------------------------------------------------------------
# Sayfalar
# ---------------------------------------------------------------------------------------------
def render_stock(rec: dict, records: list[dict], base_url: str | None) -> str:
    sym, n_all = rec["symbol"], len(records)
    basis = "halka arz fiyatına" if rec["ipo_price"] else "ilk gün kapanışına"
    facts = [
        ("İlk işlem günü", long_day(rec["first_day"])),
        ("Pazar", MARKET_NAMES.get(rec["market"], "—")),
        ("Halka arz fiyatı", f'≈ {num(rec["ipo_price"])} TL <span class="muted">(ilk gün kapanışından hesaplandı)</span>'
         if rec["ipo_price"] else '<span class="muted">bültenlerden hesaplanamıyor</span>'),
        ("İlk gün kapanışı", f'{num(rec["first_close"])} TL'),
        ("Tavan serisi", f'{rec["streak"]} işlem günü' if rec["streak"] else "yok"),
    ]
    if rec["streak"]:
        facts.append(("Tavanın bozulduğu gün", long_day(rec["open_day"])))
    if rec["streak_gain"] is not None:
        facts.append(("Tavan serisi sonundaki kazanç", f'<span class="pos">{pct(rec["streak_gain"])}</span> '
                      '<span class="muted">(halka arz fiyatından, son tavan kapanışına)</span>'))
    facts += [
        ("Tavan sonrası 20 işlem günü", result_line(rec, 20)),
        ("Tavan sonrası 60 işlem günü", result_line(rec, 60)),
    ]
    rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in facts)

    if rec["streak"]:
        story = (f'Paylar {long_day(rec["first_day"])} tarihinde işlem görmeye başladı ve ilk {rec["streak"]} işlem gününü '
                 f'tavanda kilitli geçirdi. Tavan serisi {long_day(rec["open_day"])} tarihinde bozuldu; dışarıdan birinin '
                 f'alabildiği ilk gün budur. Bu seri, incelenen {n_all} halka arz içinde uzunluk sıralamasında '
                 f'{rec["streak_rank"]}. sırada.')
    else:
        story = (f'Paylar {long_day(rec["first_day"])} tarihinde işlem görmeye başladı ve tavan serisi yapmadı: ilk günden '
                 f'itibaren serbest işlem gördü. İncelenen {n_all} halka arzın '
                 f'{sum(1 for r in records if r["streak"] == 0)} tanesi böyle başladı.')
    if rec["r20"] is not None:
        verb = "kazandı" if rec["r20"] > 0 else "kaybetti"
        story += (f' Tavan bozulduktan sonraki sabah açılışta alıp 20 işlem günü tutan biri masraflar hariç '
                  f'{pct(abs(rec["r20"]), sign=False)} {verb}; aynı günlerde bütün hisselerin ortalaması {pct(rec["m20"])} oldu.')
    else:
        story += " Tavan sonrası 20 işlem günü henüz dolmadığı için o sonuç hesaplanmadı."

    order = sorted(records, key=lambda r: (r["first_day"], r["symbol"]))
    i = next(k for k, r in enumerate(order) if r["symbol"] == sym)
    prev_link = f'<a href="../{order[i - 1]["symbol"]}/">← {order[i - 1]["symbol"]}</a>' if i > 0 else "<span></span>"
    next_link = f'<a href="../{order[i + 1]["symbol"]}/">{order[i + 1]["symbol"]} →</a>' if i + 1 < len(order) else "<span></span>"
    chart = chart_svg(rec)
    chart_block = (f'<section class="card"><h2>İlk {len(rec["chart"]) - 1} işlem günü</h2>'
                   f'<p class="muted">Getiri, {basis} göre; bedelsiz, bedelli ve temettü düzeltilmiştir.</p>{chart}</section>'
                   if chart else "")
    live = "".join([
        stat("Son kapanış", "—", attrs=' data-live="last"', note='<span data-live="last_day"></span>'),
        stat("Halka arz fiyatından bugüne" if rec["ipo_price"] else "İlk gün kapanışından bugüne", "—",
             attrs=f' data-live="{"since_ipo" if rec["ipo_price"] else "since_first"}"'),
        stat("Tavan serisi", f'{rec["streak"]} gün' if rec["streak"] else "yok",
             note=f'{n_all} halka arz içinde {rec["streak_rank"]}. sırada' if rec["streak"] else ""),
    ])
    body = f"""<article data-symbol="{esc(sym)}">
<p class="crumb"><a href="../../">Halka arzlar</a> › {esc(sym)}</p>
<h1>{esc(sym)} halka arz karnesi</h1>
<p class="lead">{esc(rec["name"])}</p>
<div class="stats">{live}</div>
<noscript><p class="muted">Güncel fiyat ve bugüne kadarki getiri için JavaScript gerekir.</p></noscript>
<section class="card"><h2>Özet</h2><p>{story}</p></section>
{chart_block}
<section class="card"><h2>Karne</h2><table class="facts">{rows}</table>
<p class="muted">"Tavan sonrası" sonuçlar, tavan serisinin bozulduğu günün ertesi sabahı açılış fiyatından alım varsayar;
parantez içindeki değer aynı günlerde bütün hisselerin eşit ağırlıklı ortalamasıdır.</p></section>
<section class="card"><h2>Genel tablo</h2><p>İncelenen halka arzlarda tavan bozulduktan sonra alıp 20 işlem günü tutanların
çoğu zarar etti. Ayrıntısı: <a href="../../analiz/">Halka arzı tavan bozunca almak kazandırıyor mu?</a></p></section>
<nav class="pager">{prev_link}<a href="../../">Tüm halka arzlar</a>{next_link}</nav>
</article>"""
    title = f"{sym} halka arz karnesi: tavan serisi ve sonrası | {SITE_NAME}"
    desc = (f'{rec["name"]} ({sym}) halka arzı: {rec["streak"]} gün tavan serisi, tavan sonrası 20 ve 60 işlem günü '
            f'getirisi, bugüne kadarki performans. Resmî bülten verisiyle.')
    return page(title, desc, body, 2, base_url, f"hisse/{sym}/")


def render_index(records: list[dict], study: dict, as_of, base_url: str | None) -> str:
    lot = study["lottery"].get(20, {})
    rows = []
    for r in records:
        rows.append(
            f'<tr data-year="{r["first_day"].year}">'
            f'<td><a href="hisse/{esc(r["symbol"])}/"><b>{esc(r["symbol"])}</b></a><span class="name">{esc(r["name"])}</span></td>'
            f'<td data-v="{r["first_day"]:%Y%m%d}">{day(r["first_day"])}</td>'
            f'<td data-v="{r["streak"]}">{r["streak"] or "—"}</td>'
            f'<td data-v="{r["r20"] if r["r20"] is not None else ""}" class="{tone(r["r20"])}">{pct(r["r20"])}</td>'
            f'<td data-v="{r["since_first"] if r["since_first"] is not None else ""}" class="{tone(r["since_first"])}">{pct(r["since_first"], 0)}</td></tr>'
        )
    years = sorted({r["first_day"].year for r in records}, reverse=True)
    chips = '<button type="button" data-year="" aria-pressed="true">Tümü</button>' + "".join(
        f'<button type="button" data-year="{y}" aria-pressed="false">{y}</button>' for y in years)
    yr = "".join(
        f'<tr><td>{y["year"]}</td><td>{y["count"]}</td><td>{num(y["streak_mean"], 1)}</td>'
        f'<td>{pct(y["streak_share"], 0, sign=False)}</td>'
        f'<td>{pct(y["lost20"], 0, sign=False)}</td><td class="{tone(y["median20"])}">{pct(y["median20"])}</td></tr>'
        for y in yearly(records))
    first_year = min(years)
    body = f"""<section class="hero">
<h1>Halka arzlar kaç tavan yaptı, sonra ne oldu?</h1>
<p class="lead">Borsa İstanbul'da {first_year} yılından bugüne halka arz olan {len(records)} hissenin karnesi. Hepsi resmî günlük
bültenlerden hesaplanır; yorum yok, yalnızca veri.</p>
<div class="stats">
{stat("İncelenen halka arz", str(len(records)), note=f"{first_year} – {max(years)}")}
{stat("Tavan bozunca alıp 20 gün tutan", pct(lot.get("lost_money"), 0, sign=False) + " zararda", "neg", note=f'{lot.get("n", 0)} alım, masraflar dahil')}
{stat("Tipik sonuç (ortanca)", pct(lot.get("net_median")), tone(lot.get("net_median")), note="20 işlem gününde")}
</div>
<p><a class="cta" href="analiz/">Analizi oku: tavan bozunca almak kazandırıyor mu?</a></p>
</section>

<section class="card">
<h2>Bütün halka arzlar</h2>
<div class="tools"><input type="search" id="q" placeholder="Kod ya da şirket ara" aria-label="Halka arzlarda ara">
<div class="chips" id="years">{chips}</div></div>
<div class="scroll"><table class="list" id="list">
<thead><tr><th data-sort="text">Hisse</th><th data-sort="num">İlk işlem</th><th data-sort="num" title="Tavanda kilitli geçen işlem günü sayısı">Tavan serisi (gün)</th>
<th data-sort="num" title="Tavan bozulduktan sonraki sabah alıp 20 işlem günü tutanın getirisi">Tavan sonrası 20 gün</th>
<th data-sort="num" title="İlk işlem günü kapanışından bugüne, düzeltilmiş">İlk kapanıştan bugüne</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="muted">Son güncelleme: {long_day(as_of)}. Sütun başlıklarına dokunarak sıralayabilirsiniz. "İlk kapanıştan bugüne" getirisi
bedelsiz, bedelli ve temettüye göre düzeltilmiştir.</p>
</section>

<section class="card">
<h2>Yıllara göre</h2>
<div class="scroll"><table class="list"><thead><tr><th>Yıl</th><th>Halka arz</th><th>Ortalama tavan serisi (gün)</th><th>Tavan yapanların payı</th>
<th>20 günde zarar edenlerin payı</th><th>20 günde tipik sonuç</th></tr></thead><tbody>{yr}</tbody></table></div>
<p class="muted">Son iki sütun, tavan bozulduktan sonraki sabah alıp 20 işlem günü tutan biri içindir (masraflar dahil).</p>
</section>"""
    title = f"{SITE_NAME}: halka arzlar kaç tavan yaptı, sonra ne oldu?"
    desc = (f"Borsa İstanbul'da {first_year}'den bugüne {len(records)} halka arzın karnesi: tavan serisi, tavan sonrası "
            "getiri ve bugüne kadarki performans. Resmî bülten verisiyle, her gün güncellenir.")
    return page(title, desc, body, 0, base_url, "")


def _bars_svg(values: list[float]) -> str:
    """Bütün alımların getirisi, küçükten büyüğe (analiz sayfası)."""
    vs = sorted(values)
    n, w, h, left = len(vs), 640, 300, 52
    lo, hi = min(vs[0], -0.1), max(vs[-1], 0.1)
    bw = (w - left - 10) / n

    def y(v):
        return 12 + (hi - v) / (hi - lo) * (h - 40)

    bars = "".join(
        f'<rect x="{left + i * bw:.2f}" y="{min(y(v), y(0)):.1f}" width="{max(bw - 0.4, 0.8):.2f}" '
        f'height="{max(abs(y(v) - y(0)), 0.8):.1f}" class="{"up" if v > 0 else "down"}"/>' for i, v in enumerate(vs))
    ticks = "".join(
        f'<line x1="{left}" x2="{w - 10}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="{"zero" if v == 0 else "grid"}"/>'
        f'<text x="{left - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{pct(v, 0)}</text>'
        for v in (-0.5, 0.0, 0.5, 1.0, 2.0) if lo <= v <= hi)
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Her alımın 20 işlem günlük getirisi, küçükten büyüğe">'
            f'{ticks}{bars}<text x="{left}" y="{h - 8}">en kötü</text>'
            f'<text x="{w - 10}" y="{h - 8}" text-anchor="end">en iyi</text></svg>')


def render_analysis(records: list[dict], study: dict, as_of, base_url: str | None) -> str:
    lot = study["lottery"]
    l20 = lot.get(20, {})
    lost = round((l20.get("lost_money") or 0) * 100)
    dots = "".join(f'<i class="{"down" if i < lost else "up"}"></i>' for i in range(100))
    net20 = [r["n20"] for r in records if r["n20"] is not None]
    top10 = sorted(net20)[-10:] if len(net20) > 10 else []
    without = (sum(net20) - sum(top10)) / max(len(net20) - len(top10), 1) if net20 else None
    recent = [r["n20"] for r in records if r["n20"] is not None and r["first_day"].year >= 2024]
    recent_lost = float(np.mean([v < 0 for v in recent])) if recent else None
    cold = [r for r in records if r["streak"] == 0]
    table = "".join(
        f'<tr><td>{h} işlem günü</td><td>{s["n"]}</td><td>{pct(s["lost_money"], 0, sign=False)}</td>'
        f'<td>{pct(s["below_cash"], 0, sign=False)}</td><td class="{tone(s["net_median"])}">{pct(s["net_median"])}</td>'
        f'<td class="{tone(s["net_mean"])}">{pct(s["net_mean"])}</td></tr>' for h, s in lot.items())
    best = sorted((r for r in records if r["n20"] is not None), key=lambda r: r["n20"], reverse=True)[:10]
    best_rows = "".join(
        f'<tr><td><a href="../hisse/{esc(r["symbol"])}/"><b>{esc(r["symbol"])}</b></a></td><td>{day(r["first_day"])}</td>'
        f'<td>{r["streak"]}</td><td class="pos">{pct(r["r20"])}</td></tr>' for r in best)
    verdict = ("Önceden belirlenen 18 kuralın hiçbiri, yine önceden belirlenen istatistik eşiğini geçemedi."
               if study["verdict"] == "kesif-yok" else "Kurallardan biri keşif örnekleminde eşiği geçti; ayrıntı yöntem sayfasında.")
    body = f"""<article>
<p class="crumb"><a href="../">Halka arzlar</a> › Analiz</p>
<h1>Halka arzı tavan bozunca almak kazandırıyor mu?</h1>
<p class="lead">{study["events"]} halka arzın resmî verisine göre: çoğu zaman hayır. Ortalama iyi görünüyor, çünkü birkaç hisse
tabloyu tek başına taşıyor.</p>

<section class="card"><h2>Soru</h2>
<p>Halka arzdan pay alamayan yatırımcının sık sorduğu soru şu: hisse tavan serisini bitirip serbest işlem görmeye başlayınca
almak mantıklı mı? Bunu görüşle değil veriyle yanıtlamak için Borsa İstanbul'da {min(r["first_day"] for r in records).year}
yılından bugüne halka arz olan {study["events"]} hissenin hepsine aynı kuralı uyguladık:</p>
<ul><li>Tavan serisinin bozulduğu günü bekle (dışarıdan birinin alabildiği ilk gün).</li>
<li>Ertesi sabah açılış fiyatından al.</li><li>20 işlem günü sonra kapanışta sat. Komisyon ve alım-satım farkı düşülür.</li></ul>
<p>Tavan serisi yapmayan halka arzlarda alım, ilk işlem gününün ertesi sabahıdır.</p></section>

<section class="card"><h2>Her 100 alımın {lost} tanesi zarar etti</h2>
<div class="dots" role="img" aria-label="100 alımdan {lost} tanesi zararda">{dots}</div>
<p>{l20.get("n", 0)} alımın {pct(l20.get("lost_money"), 0, sign=False)} kadarı 20 işlem günü sonunda zarardaydı;
{pct(l20.get("below_cash"), 0, sign=False)} kadarı aynı sürede gecelik faizin gerisinde kaldı. Tipik (ortanca) sonuç
<b class="{tone(l20.get("net_median"))}">{pct(l20.get("net_median"))}</b>.</p></section>

<section class="card"><h2>Ortalamayı birkaç hisse taşıyor</h2>
{_bars_svg(net20) if net20 else ""}
<p>Grafikte her çubuk bir alım. Soldaki geniş kırmızı alan zarar edenler; sağdaki birkaç yüksek çubuk ise 20 günde ikiye,
üçe katlayanlar. Bütün alımların ortalaması <b class="{tone(l20.get("net_mean"))}">{pct(l20.get("net_mean"))}</b>; en iyi
10 alım çıkarıldığında ortalama <b class="{tone(without)}">{pct(without)}</b>. Yani "ortalamada kazandırıyor" cümlesi doğru
ama yanıltıcı: kazanç, hangisinin uçacağını önceden bilmeye bağlı.</p>
<div class="scroll"><table class="list"><thead><tr><th>En iyi 10 alım</th><th>İlk işlem</th><th>Tavan serisi (gün)</th><th>20 günde</th></tr></thead>
<tbody>{best_rows}</tbody></table></div></section>

<section class="card"><h2>Elde tutma süresine göre</h2>
<div class="scroll"><table class="list"><thead><tr><th>Süre</th><th>Alım</th><th>Zarar eden</th><th>Faizin altında kalan</th>
<th>Tipik (ortanca)</th><th>Ortalama</th></tr></thead><tbody>{table}</tbody></table></div>
<p class="muted">Getiriler masraflar düşülmüş net getiridir. "Faiz": aynı günlerde gecelik faiz.</p></section>

<section class="card"><h2>Diğer bulgular</h2><ul>
<li><b>Son yıllarda tablo daha kötü.</b> 2024 ve sonrasında halka arz olanlarda 20 günde zarar edenlerin payı
{pct(recent_lost, 0, sign=False)} ({len(recent)} alım).</li>
<li><b>Tavan yapmayan halka arzlar ilk hafta zayıf kalıyor.</b> {len(cold)} halka arz hiç tavan serisi yapmadı; bunlar ilk
5 işlem gününde piyasanın ortalama birkaç puan gerisinde kaldı.</li>
<li><b>Sınanan kurallar.</b> Tavan bozulduğu gün alım, bozulduğu gün artıda ya da ekside kapatanlar, hiç tavan yapmayanlar,
uzun seri yapanlar ve zirveden %30 düşünce alım; her biri 5, 20 ve 60 işlem günü için. {verdict}</li></ul></section>

<section class="card"><h2>Bu analiz neyi ölçmüyor?</h2>
<p>Halka arza <b>katılmayı</b>, yani dağıtımdan pay alıp tavan serisinde satmayı ölçmüyor. O ayrı bir konu: kazanç tavan
serisinin uzunluğuna ve kişi başına düşen lot sayısına bağlı. Buradaki soru yalnızca şu: pay alamadım, tavan bozunca
piyasadan alsam ne olur?</p>
<p class="muted">Veri sonu: {long_day(as_of)}. Hesaplama ayrıntıları: <a href="../yontem/">yöntem</a>.</p></section>
</article>"""
    title = f"Halka arzı tavan bozunca almak kazandırıyor mu? {study['events']} halka arzın verisi | {SITE_NAME}"
    desc = (f"{study['events']} halka arzın resmî verisi: tavan bozulduktan sonra alıp 20 gün tutanların "
            f"{pct(l20.get('lost_money'), 0, sign=False)} kadarı zarar etti. Ortalamayı birkaç hisse taşıyor.")
    return page(title, desc, body, 1, base_url, "analiz/")


def render_method(study: dict, as_of, base_url: str | None) -> str:
    body = f"""<article>
<p class="crumb"><a href="../">Halka arzlar</a> › Yöntem</p>
<h1>Yöntem</h1>
<p class="lead">Bu sitedeki rakamların nasıl hesaplandığı ve sınırları.</p>
<section class="card"><h2>Veri</h2><ul>
<li>Kaynak, Borsa İstanbul'un resmî Pay Piyasası günlük bültenleridir. Her bülten o gün işlem gören bütün payları içerir;
sonradan kottan çıkanlar da hesaba katılır.</li>
<li>Bedelsiz, bedelli sermaye artırımı ve temettü için fiyatlar düzeltilir (kaynak: İş Yatırım düzeltme katsayıları).</li>
<li>Site her işlem günü kapanıştan sonra kendiliğinden güncellenir. Veri sonu: {long_day(as_of)}.</li></ul></section>
<section class="card"><h2>Tanımlar</h2><ul>
<li><b>Halka arz:</b> bültende ilk kez görünen ve Yıldız, Ana, Kolektif Yatırım Ürünleri ya da Gelişen İşletmeler pazarında
işlem görmeye başlayan pay. Kod değişiklikleri yeni halka arz sayılmaz.</li>
<li><b>Tavan serisi:</b> payın bütün gün tavan fiyatından işlem gördüğü (tavanda kilitli kaldığı) ardışık işlem günü sayısı.
O günlerde dışarıdan alım yapmak gerçekçi değildir.</li>
<li><b>Tavanın bozulduğu gün:</b> payın tavanın altında işlem gördüğü ilk gün.</li>
<li><b>Tavan sonrası getiri:</b> o günün ertesi sabahı açılış fiyatından alınıp 20 (ya da 60) işlem günü sonra kapanışta
satıldığı varsayılır. Karne sayfalarındaki değer masraflar hariçtir; analizdeki oranlar komisyon (binde 2 + BSMV) ve
alım-satım farkı (binde 1) düşülmüş net getiridir.</li>
<li><b>Piyasa:</b> aynı günlerde Yıldız ve Ana pazardaki bütün payların eşit ağırlıklı getirisi.</li>
<li><b>Halka arz fiyatı:</b> bültenlerde yer almaz. Pay ilk iki günü tavanda kilitli geçirdiyse ilk gün kapanışı halka arz
fiyatının %10 üstüdür; fiyat yalnızca bu durumda hesaplanır ve "≈" ile gösterilir. Diğer halka arzlarda getiriler ilk gün
kapanışına göre verilir.</li></ul></section>
<section class="card"><h2>Analiz nasıl yapıldı?</h2>
<p>Sınanacak 18 kural, yöntem ve geçme ölçütleri sonuçlara bakılmadan önce yazıldı. Veri ikiye ayrıldı: 2024 öncesi halka
arzlar keşif, sonrası doğrulama içindir. Keşif örnekleminde bir kuralın "aday" sayılması için en az 30 işlem ve giriş ayına
göre kümelenmiş t-istatistiğinin 3 ya da üstü olması gerekir. {study["discovery_events"]} halka arzlık keşif örnekleminde
hiçbir kural bu eşiği geçemedi; bu yüzden doğrulama örneklemi ({study["holdout_events"]} halka arz) yalnızca bilgi için
raporlandı.</p></section>
<section class="card"><h2>Sınırlar</h2><ul>
<li>Halka arza katılım (dağıtımdan pay alma) ölçülmez; dağıtılan lot sayısı bültenlerde yoktur.</li>
<li>İlk işlem günü tek fiyattan geçen pay tavanda kilitli sayılır.</li>
<li>Geçmiş getiriler geleceği göstermez. Bu site yatırım tavsiyesi vermez.</li></ul></section>
</article>"""
    return page(f"Yöntem | {SITE_NAME}", "Halka Arz Karnesi'ndeki rakamların nasıl hesaplandığı: veri kaynağı, tanımlar ve sınırlar.",
                body, 1, base_url, "yontem/")


# ---------------------------------------------------------------------------------------------
# Yazma
# ---------------------------------------------------------------------------------------------
CSS = """:root{--bg:#f6f7fb;--surface:#fff;--ink:#131a2b;--muted:#5d6880;--line:#e1e5ee;--brand:#0a1020;--gold:#b7811a;
--pos:#0f8a5f;--neg:#c9383d;--pos-bg:#e3f4ec;--neg-bg:#fbe7e7}
@media (prefers-color-scheme:dark){:root{--bg:#0a1020;--surface:#121a2e;--ink:#eef1f8;--muted:#93a0bb;--line:#243049;
--gold:#f6c453;--pos:#2fd08f;--neg:#ff6b70;--pos-bg:#12382b;--neg-bg:#3d1c20}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:inherit}a:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.top{background:var(--brand);color:#fff;padding:14px 16px;display:flex;flex-wrap:wrap;gap:8px 20px;align-items:center;justify-content:space-between}
.brand{font-weight:800;font-size:19px;text-decoration:none;color:#f6c453;letter-spacing:-.01em}
.top nav{display:flex;gap:16px;font-size:15px}.top nav a{color:#dfe5f3;text-decoration:none}.top nav a:hover{text-decoration:underline}
main{max-width:860px;margin:0 auto;padding:20px 16px 8px}
h1{font-size:clamp(26px,5vw,36px);line-height:1.15;letter-spacing:-.02em;margin:6px 0 10px}
h2{font-size:19px;margin:0 0 10px;letter-spacing:-.01em}
.lead{font-size:18px;color:var(--muted);margin:0 0 18px}.muted{color:var(--muted);font-size:14px}
.crumb{font-size:14px;color:var(--muted);margin:0}.crumb a{text-decoration:none}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:18px;margin:0 0 16px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:0 0 16px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.stat .k{font-size:13px;color:var(--muted)}.stat .v{font-size:24px;font-weight:750;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.stat .n{font-size:13px;color:var(--muted)}
.pos{color:var(--pos)}.neg{color:var(--neg)}
.cta{display:inline-block;background:var(--brand);color:#f6c453;padding:12px 18px;border-radius:12px;text-decoration:none;font-weight:700}
@media (prefers-color-scheme:dark){.cta{background:#f6c453;color:#0a1020}}
.tools{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 12px}
input[type=search]{flex:1 1 220px;font:inherit;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chips button{font:inherit;font-size:14px;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.chips button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.scroll{overflow-x:auto;margin:0 -18px;padding:0 18px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
.list th,.list td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap;font-size:15px}
.list th:first-child,.list td:first-child{text-align:left;padding-left:0}
.list th{font-size:13px;font-weight:600;color:var(--muted);vertical-align:bottom;white-space:normal;min-width:84px}
.list th[data-sort]{cursor:pointer;user-select:none}.list th[aria-sort]::after{content:" ↓"}.list th[aria-sort=ascending]::after{content:" ↑"}
.list tr:last-child td{border-bottom:0}.list a{text-decoration:none}.list a:hover b{text-decoration:underline}
.name{display:block;font-size:12px;color:var(--muted);max-width:190px;overflow:hidden;text-overflow:ellipsis}
.facts th{text-align:left;font-weight:500;color:var(--muted);padding:9px 12px 9px 0;vertical-align:top;width:44%;font-size:15px;border-bottom:1px solid var(--line)}
.facts td{padding:9px 0;border-bottom:1px solid var(--line);font-size:15px}.facts tr:last-child th,.facts tr:last-child td{border-bottom:0}
svg{display:block;width:100%;height:auto}svg text{font-size:12px;fill:var(--muted)}
svg .grid{stroke:var(--line);stroke-width:1}svg .zero{stroke:var(--muted);stroke-width:1.2}
svg .line{fill:none;stroke:var(--gold);stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}
svg .mark{stroke:var(--muted);stroke-width:1;stroke-dasharray:4 4}svg .marklbl{fill:var(--ink);font-weight:600}
svg .up{fill:var(--pos)}svg .down{fill:var(--neg)}
.dots{display:grid;grid-template-columns:repeat(20,1fr);gap:5px;max-width:520px;margin:4px 0 14px}
.dots i{aspect-ratio:1;border-radius:50%;display:block}.dots .down{background:var(--neg)}.dots .up{background:var(--pos)}
.pager{display:flex;justify-content:space-between;gap:10px;font-size:15px;margin:0 0 16px}.pager a{text-decoration:none;font-weight:600}
ul{padding-left:20px;margin:0 0 10px}li{margin:0 0 6px}p{margin:0 0 10px}
footer{max-width:860px;margin:0 auto;padding:8px 16px 40px;color:var(--muted);font-size:14px}
"""

JS = """(function(){
  'use strict';
  var fmt=function(v,d){var s=(Math.abs(v)*100).toLocaleString('tr-TR',{minimumFractionDigits:d,maximumFractionDigits:d});
    return (v<0?'\\u2212':'+')+'%'+s;};
  // Karne sayfası: günlük değişen rakamlar
  var art=document.querySelector('article[data-symbol]');
  if(art){fetch('../../data/ozet.json').then(function(r){return r.json();}).then(function(d){
    var x=d.items[art.getAttribute('data-symbol')];if(!x)return;
    Array.prototype.forEach.call(document.querySelectorAll('[data-live]'),function(el){
      var k=el.getAttribute('data-live');
      if(k==='last'){el.textContent=x.last.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2})+' TL';}
      else if(k==='last_day'){el.textContent=x.last_day+(x.active?'':' (işlem görmüyor)');}
      else if(x[k]!=null){el.textContent=fmt(x[k],0);el.classList.add(x[k]<0?'neg':'pos');}
    });}).catch(function(){});}
  // Ana sayfa: arama, yıl süzgeci, sıralama
  var list=document.getElementById('list');if(!list)return;
  var body=list.tBodies[0],rows=Array.prototype.slice.call(body.rows),q=document.getElementById('q'),year='';
  function apply(){var t=(q.value||'').toLocaleLowerCase('tr');
    rows.forEach(function(r){var ok=(!year||r.getAttribute('data-year')===year)&&(!t||r.cells[0].textContent.toLocaleLowerCase('tr').indexOf(t)>=0);
      r.hidden=!ok;});}
  q.addEventListener('input',apply);
  document.getElementById('years').addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
    year=b.getAttribute('data-year');
    Array.prototype.forEach.call(this.querySelectorAll('button'),function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});apply();});
  Array.prototype.forEach.call(list.tHead.rows[0].cells,function(th,i){
    th.addEventListener('click',function(){var asc=th.getAttribute('aria-sort')==='descending';
      Array.prototype.forEach.call(list.tHead.rows[0].cells,function(x){x.removeAttribute('aria-sort');});
      th.setAttribute('aria-sort',asc?'ascending':'descending');
      var num=th.getAttribute('data-sort')==='num';
      var key=function(r){var c=r.cells[i];if(!num)return c.textContent.trim();var v=c.getAttribute('data-v');return v===''||v==null?null:Number(v);};
      rows.sort(function(a,b){var x=key(a),y=key(b);if(x===null)return y===null?0:1;if(y===null)return -1;
        var c=num?x-y:String(x).localeCompare(String(y),'tr');return asc?c:-c;});
      rows.forEach(function(r){body.appendChild(r);});});});
})();
"""


def _write(path: Path, text: str) -> bool:
    """Yalnızca içerik değiştiyse yazar; yazdıysa ``True``."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def build_site(panel: MarketPanel, rf: pd.Series, out: Path, factor: pd.DataFrame | None = None,
               cost: CostConfig | None = None, base_url: str | None = None) -> dict:
    """Siteyi ``out`` klasörüne üretir. Dönen sözlük: sayfa sayısı ve değişen dosya sayısı."""
    out = Path(out)
    records = build_records(panel, rf, factor, cost)
    if not records:
        raise ValueError("halka arz bulunamadı")
    study = ipo.study(panel, rf, cost, factor=factor)
    as_of = panel.dates[-1]
    files: dict[str, str] = {
        "index.html": render_index(records, study, as_of, base_url),
        "analiz/index.html": render_analysis(records, study, as_of, base_url),
        "yontem/index.html": render_method(study, as_of, base_url),
        "assets/site.css": CSS, "assets/site.js": JS,
    }
    for rec in records:
        files[f"hisse/{rec['symbol']}/index.html"] = render_stock(rec, records, base_url)
    summary = {"as_of": str(as_of.date()), "items": {
        r["symbol"]: {"last": r["last_close"], "last_day": day(r["last_day"]), "active": r["active"],
                      "since_first": r["since_first"], "since_ipo": r["since_ipo"]} for r in records}}
    files["data/ozet.json"] = json.dumps(summary, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    if base_url:
        root = base_url.rstrip("/") + "/"
        urls = [root, root + "analiz/", root + "yontem/"] + [f"{root}hisse/{r['symbol']}/" for r in records]
        files["sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                + "".join(f"<url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    changed = sum(_write(out / name, text) for name, text in files.items())
    # Artık listede olmayan (ör. kodu değişen) payların eski sayfalarını kaldır.
    keep = {r["symbol"] for r in records}
    stale = [p for p in (out / "hisse").iterdir() if p.is_dir() and p.name not in keep] if (out / "hisse").exists() else []
    for p in stale:
        for f in p.iterdir():
            f.unlink()
        p.rmdir()
    return {"pages": len(records) + 3, "files": len(files), "changed": changed, "removed": len(stale), "as_of": str(as_of.date())}
