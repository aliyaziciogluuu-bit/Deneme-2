"""Shorts için kanalın kendi müzik altlıkları (telifsiz, kendi sentezimiz). 27 Kasım 2026.

Freesound dosya indirme bu ortamda kapalı olduğu için müzik burada üretilir.
  merak.wav    : pizzicato benzeri tıngırtı + yumuşak bas, ~96 vuruş/dk, meraklı ve hafif muzip (bilgi Shorts'ları)
  gerilim.wav  : alçak uğultu + tik-tak nabız + yükselen dalga ("X olursa ne olur?" Shorts'ları)
Her biri 48 sn, döngü olarak tekrarlanabilir. Kullanım: python sentez_muzik.py, ardından ffmpeg loudnorm I=-20 ile .ogg yapılır (depoda .ogg tutulur).
"""
import pathlib
import wave

import numpy as np

SR = 48000
KLASOR = pathlib.Path(__file__).parent
rng = np.random.default_rng(7)


def nota(n):  # MIDI → Hz
    return 440.0 * 2 ** ((n - 69) / 12)


def tingirti(f, sure, parlaklik=0.5):
    """Karplus-Strong telli çalgı (pizzicato benzeri)."""
    N = int(SR * sure)
    p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(N)
    for i in range(N):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * (0.990 + 0.008 * parlaklik)
    return out * np.exp(-np.linspace(0, 6, N))


def sinus(f, sure, zarf=None):
    t = np.arange(int(SR * sure)) / SR
    s = np.sin(2 * np.pi * f * t)
    return s * (zarf(t) if zarf else 1)


def ekle(iz, ses, t):
    i = int(t * SR)
    j = min(len(iz), i + len(ses))
    iz[i:j] += ses[: j - i]


def yumusat(x, k=0.15):
    """Basit tek kutuplu alçak geçiren süzgeç."""
    y = np.empty_like(x)
    a = 0.0
    for i, v in enumerate(x):
        a += k * (v - a)
        y[i] = a
    return y


def kaydet(ad, iz):
    iz = iz / (np.max(np.abs(iz)) + 1e-9) * 0.85
    kenar = int(0.05 * SR)  # döngü dikişinde tık olmasın
    iz[:kenar] *= np.linspace(0, 1, kenar)
    iz[-kenar:] *= np.linspace(1, 0, kenar)
    veri = (np.stack([iz, iz], 1) * 32767).astype("<i2")
    with wave.open(str(KLASOR / ad), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes(veri.tobytes())
    print(ad, f"{len(iz) / SR:.0f} sn")


def merak(sure=48.0):
    bpm, iz = 96, np.zeros(int(SR * sure))
    v = 60 / bpm / 2  # sekizlik
    # La minör: Am – F – C – E (merak, hafif gizem)
    akor = [(57, [69, 72, 76, 72]), (53, [69, 72, 77, 72]), (48, [67, 72, 76, 79]), (52, [68, 71, 76, 71])]
    adim, t = 0, 0.0
    desen = [0, 1, 2, 1, 3, 1, 2, 1]
    while t < sure - 2:
        bas, ust = akor[(adim // 16) % 4]
        k = adim % 8
        if k in (0, 3, 6) and rng.random() > 0.15:
            ekle(iz, tingirti(nota(ust[desen[k] % 4]), 0.6, 0.6) * 0.5, t)
        elif rng.random() > 0.55:
            ekle(iz, tingirti(nota(ust[desen[k] % 4] + 12), 0.4, 0.3) * 0.25, t)
        if k == 0:
            ekle(iz, sinus(nota(bas - 12), 0.9, lambda x: np.exp(-x * 3)) * 0.55, t)
        if k == 4:
            ekle(iz, sinus(nota(bas - 5), 0.5, lambda x: np.exp(-x * 5)) * 0.25, t)
        adim += 1
        t += v
    # çok hafif fırça/şıkırtı: her vuruşta yumuşak gürültü
    gur = yumusat(rng.normal(0, 1, int(SR * 0.05)), 0.6) * np.exp(-np.linspace(0, 8, int(SR * 0.05)))
    t = v
    while t < sure - 1:
        ekle(iz, gur * 0.08, t)
        t += 2 * v
    kaydet("merak.wav", iz)


def gerilim(sure=48.0):
    n = int(SR * sure)
    t = np.arange(n) / SR
    iz = np.zeros(n)
    # alçak uğultu: iki hafif kaymış sinüs + beşli
    for f, a in ((nota(38), 0.5), (nota(38) * 1.004, 0.4), (nota(45), 0.25)):
        iz += a * np.sin(2 * np.pi * f * t)
    iz *= 0.7 + 0.3 * np.sin(2 * np.pi * t / 8)  # 8 sn'lik nefes
    # yükselen dalga: her 12 sn'de bir yavaşça açılan yüksek ton
    dalga = np.zeros(n)
    for b in np.arange(0, sure, 12):
        i0 = int(b * SR)
        L = min(n - i0, int(12 * SR))
        x = np.arange(L) / SR
        zarf = (x / 12) ** 2 * np.exp(-np.maximum(x - 11, 0) * 8)
        dalga[i0:i0 + L] += 0.18 * np.sin(2 * np.pi * (nota(62) + 6 * x / 12) * x) * zarf
    iz += dalga
    # tik-tak nabız (saat gibi), 104 vuruş/dk
    tik = yumusat(rng.normal(0, 1, int(SR * 0.03)), 0.5) * np.exp(-np.linspace(0, 10, int(SR * 0.03)))
    tok = sinus(nota(50), 0.12, lambda x: np.exp(-x * 30))
    adim, s = 0, 0.0
    while s < sure - 1:
        ekle(iz, tik * (0.35 if adim % 2 == 0 else 0.22), s)
        if adim % 4 == 0:
            ekle(iz, tok * 0.6, s)
        adim += 1
        s += 60 / 104
    kaydet("gerilim.wav", iz)


if __name__ == "__main__":
    merak()
    gerilim()
