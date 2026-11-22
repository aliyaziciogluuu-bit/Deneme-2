"""Her uzun video için 3 küçük resim seçeneği üretir (YouTube Studio > "Test et ve karşılaştır" için).

  A  kapak_3saat.jpg     – kanalın alışılmış stili: koyu kutu, altın "3 HOURS", büyük başlık (zaten var, dokunulmaz)
  B  kapak_3saat_B.jpg   – sade: kutu yok, sol üstte büyük başlık, sıcak ve canlı renkler, sol altta "3 HOURS" etiketi
  C  kapak_3saat_C.jpg   – yakın plan: pencere ve ateş arasına yakınlaşır, başlık altta ortada, ışıltılı alt yazı
  D  kapak_3saat_D.jpg   – yazısız: yalnızca sahne (büyük rakip kanalların tarzı); hafif canlılık, kenarlarda yumuşak kararma

Kullanım:  python kapak.py 06-rainy-cafe [08-attic-bedroom ...]    (sahne verilmezse bütün sahneler)
Metinler kanal/kapak_metinleri.json'dan okunur; yoksa sahne.json'daki "ad" kullanılır.
"""
import json
import pathlib
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

KOK = pathlib.Path(__file__).parent
KALIN = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
YARI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
ALTIN, KREM, BEYAZ = (244, 206, 106), (255, 244, 220), (240, 244, 250)
G, Y = 1280, 720


def font_sigdir(ciz, metin, font, boy, en_fazla):
    f = ImageFont.truetype(font, boy)
    while ciz.textlength(metin, font=f) > en_fazla and boy > 20:
        boy -= 2
        f = ImageFont.truetype(font, boy)
    return f


def golgeli_yazi(im, konum, metin, font, renk, golge=10, cizgi=4, hiza="la"):
    """Yazının arkasına yumuşak koyu gölge, üstüne ince kontur: her arka planda okunur."""
    kat = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(kat).text(konum, metin, font=font, fill=(0, 0, 0, 200), anchor=hiza, stroke_width=cizgi + 6, stroke_fill=(0, 0, 0, 200))
    im.alpha_composite(kat.filter(ImageFilter.GaussianBlur(golge)))
    ImageDraw.Draw(im).text(konum, metin, font=font, fill=renk, anchor=hiza, stroke_width=cizgi, stroke_fill=(0, 0, 0))


def odak(ayar, gen):
    """Görselin en çekici yeri: pencere ile ateşin ortası (kaynak görsel pikselinde, 0-1 arası oran)."""
    noktalar = [((k[0] + k[2]) / 2, (k[1] + k[3]) / 2) for k in ayar.get("cam", {}).get("kutular", [])]
    if "ates" in ayar:
        a = ayar["ates"]["kutu"]
        noktalar += [((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)] * 2        # ateş daha ağır basar: kadrajdan kesilmesin
    if not noktalar:
        return 0.5, 0.45
    x = float(np.mean([p[0] for p in noktalar])) / gen
    y = float(np.mean([p[1] for p in noktalar])) / (gen * 9 / 16)
    return min(max(x, 0.3), 0.7), min(max(y, 0.35), 0.6)


def secenek_B(kaynak, baslik, alt):
    im = kaynak.copy()
    im = ImageEnhance.Color(im).enhance(1.18)
    im = ImageEnhance.Contrast(im).enhance(1.08)
    sicak = Image.new("RGB", im.size, (255, 170, 90))                 # hafif sıcak ton
    im = Image.blend(im, sicak, 0.06).convert("RGBA")
    karart = Image.new("L", im.size, 0)                               # sol üst köşeyi yazı için hafif karart
    ImageDraw.Draw(karart).ellipse((-500, -420, 820, 380), fill=150)
    im = Image.composite(Image.new("RGBA", im.size, (0, 0, 0, 255)), im, karart.filter(ImageFilter.GaussianBlur(120)))
    ciz = ImageDraw.Draw(im)
    f1 = font_sigdir(ciz, baslik, KALIN, 92, 700)
    satirlar = [baslik] if ciz.textlength(baslik, font=f1) <= 700 or " " not in baslik else baslik.rsplit(" ", 1)
    if len(satirlar) > 1:
        f1 = font_sigdir(ciz, max(satirlar, key=len), KALIN, 96, 680)
    y = 60
    for s in satirlar:
        golgeli_yazi(im, (56, y), s, f1, KREM)
        y += int(f1.size * 1.08)
    golgeli_yazi(im, (58, y + 6), alt, ImageFont.truetype(YARI, 40), ALTIN, golge=8, cizgi=3)
    rozet = ImageFont.truetype(KALIN, 44)                             # sol altta "3 HOURS" etiketi (sağ altı YouTube'un süre yazısı kapatır)
    w = ciz.textlength("3 HOURS", font=rozet)
    x0, y0 = 60, Y - 110
    ImageDraw.Draw(im).rounded_rectangle((x0 - 24, y0 - 14, x0 + w + 24, y0 + 62), radius=16, fill=(244, 206, 106, 240))
    ImageDraw.Draw(im).text((x0, y0), "3 HOURS", font=rozet, fill=(25, 18, 8))
    return im.convert("RGB")


def secenek_C(kaynak, baslik, alt, odak_xy, sol_ust=False, sag=False):
    ox, oy = odak_xy
    z = 1.18                                                          # hafif yakınlaş (ateş ve pencere kadrajda kalsın)
    w, h = G / z, Y / z
    x0 = min(max(ox * G - w / 2, 0), G - w)
    y0 = min(max(oy * Y - h / 2, 0), Y - h)
    im = kaynak.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((G, Y), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2)).convert("RGBA")
    if sol_ust:                                                       # ateş alt yarıda görünür kalsın: başlık sol üstte
        karart = Image.new("L", im.size, 0)
        ImageDraw.Draw(karart).ellipse((G - 900, -420, G + 500, 380) if sag else (-500, -420, 900, 380), fill=150)
        im = Image.composite(Image.new("RGBA", im.size, (0, 0, 0, 255)), im, karart.filter(ImageFilter.GaussianBlur(120)))
        ciz = ImageDraw.Draw(im)
        f1 = font_sigdir(ciz, baslik, KALIN, 80, 760)
        hz, px = ("ra", G - 56) if sag else ("la", 56)
        golgeli_yazi(im, (px, 56), baslik, f1, BEYAZ, hiza=hz)
        t = f"3 HOURS  ·  {alt.upper()}"
        golgeli_yazi(im, (px, 56 + int(f1.size * 1.15)), t, font_sigdir(ciz, t, YARI, 34, 760), ALTIN, golge=6, cizgi=3, hiza=hz)
        return im.convert("RGB")
    alt_karart = Image.new("L", im.size, 0)                           # alt bandı koyulaştır
    ImageDraw.Draw(alt_karart).rectangle((0, 470, G, Y), fill=190)
    im = Image.composite(Image.new("RGBA", im.size, (0, 0, 0, 255)), im, alt_karart.filter(ImageFilter.GaussianBlur(70)))
    ciz = ImageDraw.Draw(im)
    f1 = font_sigdir(ciz, baslik, KALIN, 98, G - 140)
    golgeli_yazi(im, (G // 2, 560), baslik, f1, BEYAZ, hiza="mm")
    golgeli_yazi(im, (G // 2, 645), f"3 HOURS  ·  {alt.upper()}", font_sigdir(ciz, f"3 HOURS  ·  {alt.upper()}", YARI, 36, G - 160),
                 ALTIN, golge=6, cizgi=3, hiza="mm")
    return im.convert("RGB")


def secenek_D(kaynak):
    im = ImageEnhance.Color(kaynak).enhance(1.12)
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2))
    kenar = Image.new("L", im.size, 0)                                # köşeleri hafifçe karart, göz ortaya gitsin
    ImageDraw.Draw(kenar).ellipse((-160, -120, G + 160, Y + 120), fill=255)
    kenar = kenar.filter(ImageFilter.GaussianBlur(140)).point(lambda v: 150 + v * 105 // 255)
    return Image.composite(im, Image.new("RGB", im.size, (0, 0, 0)), kenar)


def main():
    metinler = json.loads((KOK / "kanal" / "kapak_metinleri.json").read_text(encoding="utf-8"))
    sahneler = sys.argv[1:] or sorted(metinler)
    for ad in sahneler:
        klasor = KOK / ad
        ayar = json.loads((klasor / "sahne.json").read_text(encoding="utf-8"))
        baslik, alt = metinler.get(ad, [ayar.get("ad", ad).upper(), "Deep Sleep & Relaxation"])
        kaynak = Image.open(klasor / ayar.get("gorsel_4k", ayar["gorsel"])).convert("RGB").resize((G, Y), Image.LANCZOS)
        gen = cv2.imread(str(klasor / ayar["gorsel"])).shape[1]
        secenek_B(kaynak, baslik, alt).save(klasor / "kapak_3saat_B.jpg", quality=92)
        secenek_C(kaynak, baslik, alt, odak(ayar, gen), ayar.get("kapak_yazi") in ("sol_ust", "sag_ust"), ayar.get("kapak_yazi") == "sag_ust").save(klasor / "kapak_3saat_C.jpg", quality=92)
        secenek_D(kaynak).save(klasor / "kapak_3saat_D.jpg", quality=92)
        print(f"{ad}: B, C ve D hazır ({baslik} / {alt})")


if __name__ == "__main__":
    main()
