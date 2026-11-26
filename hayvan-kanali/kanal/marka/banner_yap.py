"""Kanal bannerı (2560x1440) ve profil fotoğrafı (800x800) üretir.

YouTube güvenli alanı: tüm cihazlarda görünen orta bölge 1546x423; masaüstünde tam genişlik 2560x423 şerit görünür.
Başlık ve kirpi bu şeride yerleştirilir; TV'de görünen üst/alt bölümler görselin devamı ve bulanık uzantıdır.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KALIN = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
ORTA = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
G, Y = 2560, 1440
SERIT = (Y - 423) // 2  # 508


def banner(kaynak, hedef, kaydir=-30):
    im = Image.open(kaynak).convert("RGB")
    h = round(im.height * G / im.width)
    im = im.resize((G, h), Image.LANCZOS)
    arka = Image.new("RGB", (G, Y))
    arka.paste(im, (0, kaydir))
    # alt boşluk: zeminin son 220 satırı aşağı doğru uzatılır (yakın plan taş zemin gibi görünür), geçiş yumuşatılır
    alt = kaydir + h
    if alt < Y:
        kaynak_bant = im.crop((round(G * 0.36), h - 220, round(G * 0.74), h))  # yalnızca hayvansız taş zemin
        uzatma = kaynak_bant.resize((G, Y - alt + 220), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))
        maske = Image.new("L", uzatma.size, 255)
        gecis = Image.linear_gradient("L").resize((G, 220))
        maske.paste(gecis, (0, 0))
        arka.paste(uzatma, (0, alt - 220), maske)
    c = ImageDraw.Draw(arka, "RGBA")
    # şeridin ortasına yumuşak koyu zemin (yazı okunurluğu)
    zemin = Image.new("L", (G, Y), 0)
    zd = ImageDraw.Draw(zemin)
    zd.rounded_rectangle((G // 2 - 760, SERIT + 40, G // 2 + 760, SERIT + 383), radius=60, fill=150)
    zemin = zemin.filter(ImageFilter.GaussianBlur(45))
    arka = Image.composite(Image.new("RGB", (G, Y), (40, 26, 10)), arka, zemin)
    c = ImageDraw.Draw(arka)
    baslik = "AVLUDAKİ KOMŞULAR"
    f1 = ImageFont.truetype(KALIN, 128)
    w = c.textlength(baslik, font=f1)
    x, y = (G - w) / 2, SERIT + 80
    c.text((x + 6, y + 8), baslik, font=f1, fill=(30, 18, 5))
    c.text((x, y), baslik, font=f1, fill=(255, 236, 180), stroke_width=4, stroke_fill=(120, 60, 10))
    f2 = ImageFont.truetype(ORTA, 48)
    alt1 = "Yanlış tanınan komşularını tanı · Her hafta bir yanlışı düzeltiyoruz"
    w2 = c.textlength(alt1, font=f2)
    c.text(((G - w2) / 2, SERIT + 250), alt1, font=f2, fill=(255, 255, 255), stroke_width=2, stroke_fill=(40, 26, 10))
    f3 = ImageFont.truetype(ORTA, 40)
    alt2 = "Yeni bölüm: Salı ve Cumartesi 18:00 · Her gün Shorts"
    w3 = c.textlength(alt2, font=f3)
    c.text(((G - w3) / 2, SERIT + 320), alt2, font=f3, fill=(255, 214, 120), stroke_width=2, stroke_fill=(40, 26, 10))
    arka.save(hedef, quality=93)


def profil(kaynak, hedef):
    im = Image.open(kaynak).convert("RGB")
    k = min(im.size)
    im = im.crop(((im.width - k) // 2, (im.height - k) // 2, (im.width + k) // 2, (im.height + k) // 2)).resize((800, 800), Image.LANCZOS)
    im.save(hedef)
    # daire önizleme (YouTube daire kırpar) + küçük boy
    maske = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(maske).ellipse((0, 0, 800, 800), fill=255)
    on = Image.new("RGB", (800 + 40 + 98 + 40 + 48, 800), (24, 24, 24))
    on.paste(im, (0, 0), maske)
    kucuk = im.resize((98, 98), Image.LANCZOS); km = maske.resize((98, 98))
    on.paste(kucuk, (840, 351), km)
    kk = im.resize((48, 48), Image.LANCZOS); kkm = maske.resize((48, 48))
    on.paste(kk, (978, 376), kkm)
    on.save(hedef.replace(".png", "_onizleme.jpg"), quality=90)


if __name__ == "__main__":
    banner("gorseller/banner.jpg", "kanal_banner_2560x1440.jpg")
    profil("gorseller/profil.jpg", "profil_800.png")
