"""4K olarak yüklenen videoların küçük resimlerine sağ üst köşede "4K" etiketi ekler.

  kapak_3saat.jpg → kapak_3saat_4K.jpg (B ve C seçenekleri de varsa onlar da)
Kullanım:  python kapak4k.py 03-christmas-cabin [06-rainy-cafe ...]
Yalnızca gerçekten 4K yüklenen videolarda kullan (1080p yüklemede "4K" yazmak yanıltıcı olur).
"""
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

KOK = pathlib.Path(__file__).parent
KALIN = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"


def etiketle(kaynak: pathlib.Path, hedef: pathlib.Path):
    im = Image.open(kaynak).convert("RGBA")
    G, Y = im.size
    o = G / 1280
    f = ImageFont.truetype(KALIN, int(64 * o))
    ciz = ImageDraw.Draw(im)
    w = ciz.textlength("4K", font=f)
    x1, y0 = G - int(34 * o), int(30 * o)
    kutu = (x1 - w - int(44 * o), y0, x1, y0 + int(92 * o))
    golge = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(golge).rounded_rectangle([kutu[0] + 4, kutu[1] + 6, kutu[2] + 4, kutu[3] + 6], radius=int(18 * o), fill=(0, 0, 0, 170))
    im.alpha_composite(golge.filter(ImageFilter.GaussianBlur(10 * o)))
    ciz = ImageDraw.Draw(im)
    ciz.rounded_rectangle(kutu, radius=int(18 * o), fill=(244, 206, 106, 255), outline=(255, 240, 200, 255), width=max(2, int(3 * o)))
    ciz.text(((kutu[0] + kutu[2]) / 2, (kutu[1] + kutu[3]) / 2 + 2 * o), "4K", font=f, fill=(25, 18, 8), anchor="mm")
    im.convert("RGB").save(hedef, quality=92)


def main():
    for ad in sys.argv[1:]:
        klasor = KOK / ad
        for k in ("kapak_3saat", "kapak_3saat_B", "kapak_3saat_C"):
            if (klasor / f"{k}.jpg").exists():
                etiketle(klasor / f"{k}.jpg", klasor / f"{k}_4K.jpg")
        print(f"{ad}: 4K küçük resimler hazır")


if __name__ == "__main__":
    main()
