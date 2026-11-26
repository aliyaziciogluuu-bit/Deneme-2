"""Shorts geçiş ve vurgu efektlerini sentezler (telifsiz, kanalın kendi üretimi).
whoosh.wav: süpürme sesi (filtrelenmiş gürültü, frekans kayması)  pop.wav: kısa vurgu  parilti.wav: ince çan dizisi
"""
import numpy as np, wave, pathlib
SR = 48000
KOK = pathlib.Path(__file__).parent

def yaz(ad, x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.8
    st = np.stack([x, x], 1)
    with wave.open(str(KOK / ad), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

def whoosh(sure=0.55, f0=300, f1=3000, seed=1):
    n = int(SR * sure); t = np.arange(n) / SR
    rng = np.random.default_rng(seed); g = rng.standard_normal(n)
    # zamanla değişen tek kutuplu alçak geçiren + yüksek geçiren = kayan bant
    fc = f0 * (f1 / f0) ** (t / sure)
    y = np.zeros(n); lp = 0.0; hp_prev = 0.0; hp = 0.0
    for i in range(n):
        a = np.exp(-2 * np.pi * fc[i] / SR)
        lp = (1 - a) * g[i] + a * lp
        b = np.exp(-2 * np.pi * (fc[i] * 0.35) / SR)
        hp = b * (hp + lp - hp_prev); hp_prev = lp
        y[i] = hp
    env = np.sin(np.pi * np.clip(t / sure, 0, 1)) ** 2
    return y * env

def pop(sure=0.12):
    t = np.arange(int(SR * sure)) / SR
    f = 900 * np.exp(-t * 25) + 180
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35)

def parilti(sure=1.2):
    t = np.arange(int(SR * sure)) / SR; y = np.zeros_like(t)
    for k, (bas, fr) in enumerate([(0, 2637), (0.12, 3136), (0.24, 3951), (0.36, 5274)]):
        m = t >= bas; tt = t[m] - bas
        y[m] += np.sin(2 * np.pi * fr * tt) * np.exp(-tt * 6) * (0.9 ** k)
    return y

if __name__ == "__main__":
    yaz("whoosh.wav", whoosh())
    yaz("whoosh_ters.wav", whoosh(0.45, 2500, 400, seed=2))
    yaz("pop.wav", pop())
    yaz("parilti.wav", parilti())
    print("efektler hazır")
