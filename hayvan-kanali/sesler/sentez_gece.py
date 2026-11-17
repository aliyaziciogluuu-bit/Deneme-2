"""Telifsiz gece ambiyansı sentezler: farklı uzaklıklarda birkaç cırcır böceği + çok hafif gece havası.

Kullanım:  python sentez_gece.py            → gece_cirit.ogg (~8 dk, mono, 48 kHz)

Neden sentez: Commons'taki gece/cırcır kayıtları çoğunlukla CC BY-SA (videonun da aynı lisansla paylaşılmasını
gerektirebilir) ya da gündüz ötüşen ağustos böceği. Cırcır ötüşü fiziksel olarak basittir: ~4-5 kHz taşıyıcı ses,
her ötüş 3-4 kısa darbe; sentez kayıt kadar doğal duyulur ve lisans sorunu yoktur.
"""
import pathlib
import subprocess

import numpy as np

SR = 48000
SURE = 480  # sn
rng = np.random.default_rng(2026)


def cirit(frekans, aralik, darbe_sayisi, uzaklik):
    """Tek bir cırcır: aralik sn'de bir ötüş, her ötüş darbe_sayisi kısa darbe. uzaklik 0 (yakın) - 1 (uzak)."""
    ses = np.zeros(SURE * SR, dtype=np.float32)
    t = rng.uniform(0, aralik)
    darbe = int(0.016 * SR)
    bosluk = int(0.014 * SR)
    zarf = np.sin(np.linspace(0, np.pi, darbe)) ** 2
    while t < SURE - 1:
        bas = int(t * SR)
        f = frekans * rng.uniform(0.995, 1.005)
        for d in range(darbe_sayisi):
            k = bas + d * (darbe + bosluk)
            n = np.arange(darbe) / SR
            ton = np.sin(2 * np.pi * f * n + 0.3 * np.sin(2 * np.pi * 2 * f * n))
            ses[k:k + darbe] += (ton * zarf * rng.uniform(0.85, 1.0)).astype(np.float32)
        t += aralik * rng.uniform(0.92, 1.08)
        if rng.random() < 0.04:  # ara sıra kısa sessizlik: gerçek cırcırlar da durup başlar
            t += rng.uniform(2, 6)
    seviye = 10 ** (-(6 + 18 * uzaklik) / 20)
    return ses * seviye, uzaklik


def main():
    hedef = pathlib.Path(__file__).parent / "gece_cirit.ogg"
    karisim = np.zeros(SURE * SR, dtype=np.float32)
    parcalar = [cirit(4500, 0.62, 3, 0.15), cirit(4200, 0.85, 4, 0.45), cirit(4800, 0.55, 3, 0.7),
                cirit(4350, 1.1, 2, 0.9), cirit(4650, 0.7, 3, 0.8)]
    for ses, uzaklik in parcalar:
        if uzaklik > 0.4:  # uzaktaki cırcırların tizleri biraz kısılır
            k = int(1 + uzaklik * 6)
            ses = np.convolve(ses, np.ones(k) / k, mode="same").astype(np.float32)
        karisim += ses
    # gece havası: çok kısık, kahverengi gürültü
    beyaz = rng.standard_normal(SURE * SR).astype(np.float32)
    kahve = np.cumsum(beyaz)
    kahve -= np.convolve(kahve, np.ones(4800) / 4800, mode="same")
    kahve /= np.abs(kahve).max()
    karisim += kahve.astype(np.float32) * 0.02
    karisim /= np.abs(karisim).max() / 0.7
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "libvorbis", "-q:a", "4", str(hedef)], input=karisim.tobytes(), check=True)
    print("Hazır:", hedef)


if __name__ == "__main__":
    main()
