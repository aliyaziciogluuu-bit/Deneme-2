"""Tekrar testi: bir videoda hareketin kaç saniyede bir birebir başa döndüğünü ölçer.

Kanal sahibinin isteği (Kasım 2026): göndermeden önce her videoya bu test uygulanır; kare kare bakmak tekrarı göstermez.
Videonun ortasından birkaç dakika alınır, küçültülmüş kareler zaman kaydırmalarıyla karşılaştırılır.
Görüntünün neredeyse aynısına dönen en kısa kaydırma = izleyicinin fark edeceği tekrar süresi.
Bölge verilirse (örn. pencere) yalnızca o bölge ölçülür; hareketli kısımların tekrarı orada daha net görünür.

Kullanım:
  python kontrol.py 11-aurora-igloo/video_3saat.mp4
  python kontrol.py video.mp4 --bolge 0.33 0 0.87 0.5     # oranlarla x0 y0 x1 y1
  python kontrol.py video.mp4 --en-az 60                   # 60 sn'den kısa tekrar varsa hata kodu döner
"""
import argparse
import subprocess
import sys

import numpy as np

FPS = 4          # saniyede örnek kare
GEN, YUK = 192, 108


def kareler(yol, bas, sure):
    ham = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(bas), "-t", str(sure), "-i", yol, "-vf", f"fps={FPS},scale={GEN}:{YUK}",
                          "-pix_fmt", "gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(ham, np.uint8).reshape(-1, YUK, GEN).astype(np.float32)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--bolge", type=float, nargs=4)
    p.add_argument("--sure", type=float, default=300, help="incelenecek süre (sn)")
    p.add_argument("--en-az", type=float, default=60, help="bundan kısa tekrar hata sayılır (sn)")
    g = p.parse_args()

    toplam = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", g.video],
                                  capture_output=True, text=True).stdout)
    bas = max(toplam / 2 - g.sure / 2, 0)
    k = kareler(g.video, bas, min(g.sure, toplam))
    if g.bolge:
        x0, y0, x1, y1 = g.bolge
        k = k[:, int(y0 * YUK):int(y1 * YUK), int(x0 * GEN):int(x1 * GEN)]
    hareket = np.abs(np.diff(k, axis=0)).mean()             # ardışık kareler arası ortalama fark: hareketin ölçeği
    if hareket < 0.05:
        print("Bölgede hareket yok denecek kadar az; tekrar ölçülemedi.")
        return 0
    n = len(k)
    sonuc = []
    for kay in range(2 * FPS, n // 2):                       # 2 sn'den itibaren
        fark = np.abs(k[kay:] - k[:-kay]).mean()
        sonuc.append((kay / FPS, fark))
    farklar = np.array([f for _, f in sonuc])
    esik = np.median(farklar) * 0.35                          # tipik farkın üçte birinin altına düşen kaydırma: göze çarpan tekrar
    tekrar = next((s for s, f in sonuc if f < esik), None)
    print(f"İncelenen: {bas / 60:.0f}. dakikadan itibaren {n / FPS:.0f} sn · hareket ölçeği {hareket:.2f} · "
          f"en benzer kaydırma {sonuc[int(farklar.argmin())][0]:.1f} sn (fark {farklar.min():.2f})")
    if tekrar is None:
        print(f"TAMAM: {n / FPS / 2:.0f} sn içinde birebir tekrar yok.")
        return 0
    durum = "TAMAM" if tekrar >= g.en_az else "SORUN"
    print(f"{durum}: görüntü her {tekrar:.1f} sn'de bir başa dönüyor (sınır {g.en_az:.0f} sn).")
    return 0 if durum == "TAMAM" else 1


if __name__ == "__main__":
    sys.exit(main())
