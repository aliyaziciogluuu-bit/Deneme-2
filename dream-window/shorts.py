"""Bir sahneden dikey (1080x1920) YouTube Shorts videosu üretir.

Kadraj sahnenin bir ucundan diğerine yavaşça kayar ve başladığı yere döner; görüntü döngüsüyle
birlikte video başa kusursuz bağlanır (Shorts otomatik tekrar oynar).

Kullanım:  python shorts.py 03-christmas-cabin
Ayarlar sahne.json içindeki "shorts" bölümündedir:
  "bas", "son": kadraj merkezinin başlangıç ve dönüş noktası (kaynak görseldeki x pikseli)
  "baslik", "alt": üstte duran yazılar;  "tur": kaç görüntü döngüsü sürsün (2 = 48 sn)
"""
import pathlib
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import uret

SG, SY = 1080, 1920


def yazi_katmani(baslik: str, alt: str):
    kat = Image.new("RGBA", (SG, SY), (0, 0, 0, 0))
    golge = Image.new("RGBA", (SG, SY), (0, 0, 0, 0))
    buyuk = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", 84)
    while buyuk.getlength(baslik) > SG - 120:
        buyuk = buyuk.font_variant(size=buyuk.size - 4)
    kucuk = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 44)
    for katman, r1, r2 in ((golge, (0, 0, 0, 230), (0, 0, 0, 230)), (kat, (255, 244, 220, 255), (244, 206, 106, 255))):
        ciz = ImageDraw.Draw(katman)
        ciz.text((SG / 2, 300), baslik, font=buyuk, fill=r1, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, r1[3]))
        ciz.text((SG / 2, 392), alt, font=kucuk, fill=r2, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, r2[3]))
    golge = golge.filter(ImageFilter.GaussianBlur(12))
    golge.alpha_composite(golge)
    golge.alpha_composite(kat)
    dizi = np.asarray(golge).astype(np.float32) / 255
    return dizi[..., 2::-1].copy() * 255, dizi[..., 3:4].copy()


def main():
    klasor = uret.KOK / sys.argv[1]
    sahne = uret.Sahne(klasor)
    a = sahne.ayar["shorts"]
    tur = int(a.get("tur", 2))
    kare_sayisi = tur * uret.T * uret.FPS
    gen = uret.Y * SG // SY                                   # 1080p karede dikey kadrajın genişliği
    bas, son = (min(max(sahne.o(v)[0], gen // 2), uret.G - gen // 2) for v in (a["bas"], a["son"]))
    renk, saydam = yazi_katmani(a["baslik"], a["alt"])

    gecici = klasor / "_shorts.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{SG}x{SY}", "-r", str(uret.FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", str(gecici)], stdin=subprocess.PIPE)
    for n in range(kare_sayisi):
        kare = sahne.kare(n % (uret.T * uret.FPS))
        merkez = bas + (son - bas) * (1 - np.cos(2 * np.pi * n / kare_sayisi)) / 2      # git ve yumuşakça geri dön
        x0 = merkez - gen / 2
        m = np.float32([[SG / gen, 0, -x0 * SG / gen], [0, SY / uret.Y, 0]])            # piksel altı kaydırma: hareket titremez
        dikey = cv2.warpAffine(kare, m, (SG, SY), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
        dikey += 0.35 * (dikey - cv2.GaussianBlur(dikey, (0, 0), 2.0))                  # büyütmenin yumuşattığı ayrıntıyı biraz keskinleştir
        dikey = dikey * (1 - saydam) + renk * saydam
        ff.stdin.write(np.clip(dikey + 0.5, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close()
    assert ff.wait() == 0

    ses = klasor / "_shorts.m4a"
    uret.ses_kur(klasor, ses, kare_sayisi / uret.FPS, giris=0.6, cikis=0.8)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(gecici), "-i", str(ses), "-c:v", "copy",
                    "-af", f"volume={a.get('ses_kazanc', 9)}dB,alimiter=limit=0.89:level=disabled", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(klasor / "shorts.mp4")], check=True)
    gecici.unlink()
    ses.unlink()
    print(f"Hazır: {klasor / 'shorts.mp4'} ({kare_sayisi / uret.FPS:.0f} sn)")


if __name__ == "__main__":
    main()
