"""Tek bir sahne görselinden uzun, döngülü bir rahatlama videosu üretir.

Sahne canlandırılır (yağan yağmur, oynayan ateş, titreyen mum ışığı, akan dere),
ses sıfırdan üretilir (yağmur + şömine çıtırtısı). Hazır ses ya da video kullanılmaz.

Kullanım:
  python uret.py 01-rainy-cabin --kare        # kontrol için birkaç kare (onizleme.jpg)
  python uret.py 01-rainy-cabin --ses 20      # 20 saniyelik ses denemesi (ses_deneme.wav)
  python uret.py 01-rainy-cabin --dakika 60   # tam video (video.mp4)
  python uret.py 01-rainy-cabin --sesdegistir # mevcut videonun yalnızca sesini yeniden kur
  python uret.py 01-rainy-cabin --dakika 60 --crf 32   # daha küçük dosya

Gerekenler: ffmpeg, pip install numpy scipy opencv-python-headless
"""
import pathlib
import subprocess
import sys

import cv2
import numpy as np
from scipy import signal

G, Y, FPS = 1920, 1080, 24
T = 24                      # görüntü döngüsünün süresi (sn); bütün hareketler bu sürede başa döner
OLCEK = G / 1672            # sahne koordinatları 1672x941 kaynak görsele göre yazıldı
SR = 48000
KOK = pathlib.Path(__file__).parent


def o(*v):
    """Kaynak görsel koordinatını çıktı çözünürlüğüne çevirir."""
    return [int(round(x * OLCEK)) for x in v]


def titresim(tohum, donguler=(2, 3, 5, 8, 13, 21, 34)):
    """T saniyede kusursuz başa dönen, -1..1 arası düzensiz bir titreşim fonksiyonu."""
    rng = np.random.default_rng(tohum)
    faz = rng.uniform(0, 2 * np.pi, len(donguler))
    guc = 1 / np.sqrt(np.array(donguler, dtype=float))
    return lambda t: float(np.sum(guc * np.sin(2 * np.pi * np.array(donguler) * t / T + faz)) / guc.sum() * 1.8)


class Dalga:
    """Bir bölgeyi akışkan gibi oynatan, zamanda döngülü yer değiştirme alanı."""

    def __init__(self, tohum, yuk, gen, bilesenler, yon=1.0):
        rng = np.random.default_rng(tohum)
        yy, xx = np.mgrid[0:yuk, 0:gen].astype(np.float32)
        self.terimler = []
        for dalga_boyu_y, dalga_boyu_x, dongu, genlik in bilesenler:
            faz = (2 * np.pi * yy / dalga_boyu_y * yon + 2 * np.pi * xx / dalga_boyu_x * rng.choice([-1, 1])
                   + rng.uniform(0, 2 * np.pi)).astype(np.float32)
            self.terimler.append((faz, dongu, genlik))

    def __call__(self, t):
        return sum(g * np.sin(f + np.float32(2 * np.pi * d * t / T)) for f, d, g in self.terimler)


class Sahne:
    def __init__(self, klasor: pathlib.Path):
        self.klasor = klasor
        oku = lambda ad: cv2.resize(cv2.imread(str(klasor / ad)), (G, Y), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
        self.temiz = oku("temiz.png")      # logosuz sahne
        self.logolu = oku("kaynak.png")    # açılışta birkaç saniye görünen logolu sahne
        self._cam()
        self._ates()
        self._isik()
        self._su_ve_buhar()
        self._yagmur()

    # -------------------------------------------------------------- hazırlık
    def _cam(self):
        """Yağmurun görüneceği cam alanı: pencere içindeki soğuk renkli pikseller, çerçeveler hariç."""
        b, g, r = cv2.split(self.temiz)
        maske = ((r - b) < 0.03).astype(np.uint8)
        kutu = np.zeros((Y, G), np.uint8)
        x0, y0, x1, y1 = o(428, 0, 1592, 692)
        kutu[y0:y1, x0:x1] = 1
        maske &= kutu
        for xa, xb in ((652, 698), (1048, 1100)):                 # dikey çerçeveler
            maske[:, o(xa)[0]:o(xb)[0]] = 0
        xs = np.arange(G) / OLCEK                                 # eğik yatay çerçeve
        merkez = (135 - 0.148 * (xs - 450)) * OLCEK
        ys = np.arange(Y)[:, None]
        maske[np.abs(ys - merkez[None, :]) < 20 * OLCEK] = 0
        for xa, ya, xb, yb in ((982, 570, 1085, 700), (395, 585, 482, 665)):   # fener ve saksı camın önünde
            ax, ay, bx, by = o(xa, ya, xb, yb)
            maske[ay:by, ax:bx] = 0
        ax, ay, bx, by = o(428, 0, 650, 112)                      # sarkan yapraklar
        maske[ay:by, ax:bx] &= ~((g - b) > 0.06)[ay:by, ax:bx].astype(np.uint8) & 1
        maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        self.cam = cv2.GaussianBlur(maske.astype(np.float32), (0, 0), 2.0)
        self.cam_kutu = (x0, y0, x1, y1)

    def _ates(self):
        x0, y0, x1, y1 = self.ates_kutu = o(80, 425, 330, 660)
        bolge = self.temiz[y0:y1, x0:x1]
        b, g, r = cv2.split(bolge)
        alev = ((r > 0.78) & (g > 0.35) & (b < 0.55) & (r - b > 0.35)).astype(np.uint8)
        ic = np.zeros_like(alev)
        ax, ay, bx, by = o(98 - 80, 452 - 425, 298 - 80, 640 - 425)   # ocağın iç boşluğu; taş çerçeve oynamasın
        ic[ay:by, ax:bx] = 1
        alev &= ic
        genis = cv2.dilate(alev, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
        yuk, gen = alev.shape
        ys = np.arange(yuk, dtype=np.float32)[:, None]
        taban, tepe = (628 - 425) * OLCEK, (450 - 425) * OLCEK
        rampa = np.clip((taban - ys) / (taban - tepe), 0, 1) ** 0.7     # alevin ucu çok, dibi az oynar
        self.ates_agirlik = cv2.GaussianBlur(genis.astype(np.float32), (0, 0), 9) * rampa * cv2.GaussianBlur(ic.astype(np.float32), (0, 0), 5) ** 2
        self.alev = cv2.GaussianBlur(alev.astype(np.float32), (0, 0), 4)
        self.ates_dx = Dalga(1, yuk, gen, [(120, 260, 18, 4.0), (75, 180, 26, 3.0), (52, 140, 34, 2.2), (38, 110, 46, 1.4), (26, 90, 60, 0.9)])
        self.ates_dy = Dalga(2, yuk, gen, [(95, 200, 22, 2.4), (48, 120, 38, 1.4), (30, 80, 54, 0.8)])
        self.ates_izgara = np.mgrid[0:yuk, 0:gen].astype(np.float32)
        self.ates_parlaklik = titresim(3, (5, 9, 14, 23, 37, 55))
        rng = np.random.default_rng(4)                                   # yükselen kıvılcımlar
        self.kivilcim = [dict(x=rng.uniform(0.3, 0.7) * gen, faz=rng.uniform(0, 1), tur=int(rng.integers(4, 10)),
                              sal=rng.uniform(4, 14), salfaz=rng.uniform(0, 6.28), saltur=int(rng.integers(6, 20)),
                              boy=rng.uniform(0.5, 0.95)) for _ in range(14)]

    def _isik(self):
        """Ateşin ve mumların çevreye vurduğu ışığın oynaması için kazanç haritaları."""
        yy, xx = np.mgrid[0:Y, 0:G].astype(np.float32)

        def leke(x, y, sigma):
            cx, cy = o(x, y)
            return np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (sigma * OLCEK) ** 2))

        ic = 1 - self.cam                                               # ışık yalnızca oda içine vurur
        self.isiklar = [
            (leke(200, 545, 360) * ic, titresim(10, (3, 5, 8, 13, 21, 34, 47)), 0.085),   # şömine
            (leke(272, 262, 55) * ic, titresim(11, (4, 7, 12, 19, 31)), 0.10),            # raf feneri
            (leke(330, 280, 40) * ic, titresim(12, (5, 8, 13, 22, 35)), 0.10),            # küçük fener
            (leke(1030, 705, 70) * ic, titresim(13, (3, 6, 11, 18, 29)), 0.10),           # masa feneri
        ]
        self.sicak = np.array([0.55, 0.85, 1.0], np.float32)             # BGR: sıcak ışık maviyi az etkiler
        self.isik_sinir = o(1250)[0]                                     # sağ taraf etkilenmez; hız için kırp

    def _su_ve_buhar(self):
        x0, y0, x1, y1 = self.su_kutu = o(1235, 545, 1600, 692)
        bolge = self.temiz[y0:y1, x0:x1]
        b, g, r = cv2.split(bolge)
        su = ((b > 0.42) & (b > r + 0.04)).astype(np.float32)
        self.su_agirlik = cv2.GaussianBlur(su, (0, 0), 3)
        yuk, gen = su.shape
        self.su_dx = Dalga(20, yuk, gen, [(60, 45, 9, 2.2), (34, 28, 15, 1.3), (22, 60, 21, 0.8)], yon=-1.0)
        self.su_dy = Dalga(21, yuk, gen, [(40, 50, 12, 1.2), (24, 36, 19, 0.7)], yon=-1.0)
        self.su_izgara = np.mgrid[0:yuk, 0:gen].astype(np.float32)

        x0, y0, x1, y1 = self.buhar_kutu = o(700, 535, 805, 674)
        yuk, gen = y1 - y0, x1 - x0
        yy, xx = np.mgrid[0:yuk, 0:gen].astype(np.float32)
        self.buhar_agirlik = np.exp(-((xx - gen / 2) ** 2 / (2 * (gen / 4) ** 2) + (yy - yuk * 0.45) ** 2 / (2 * (yuk / 3.4) ** 2)))
        self.buhar_dx = Dalga(30, yuk, gen, [(90, 400, 4, 5.0), (55, 300, 7, 3.0), (34, 200, 11, 1.5)])
        self.buhar_izgara = np.mgrid[0:yuk, 0:gen].astype(np.float32)

    def _yagmur(self):
        x0, y0, x1, y1 = self.cam_kutu
        self.yg, self.yy_ = x1 - x0, y1 - y0
        self.tur_boyu = self.yy_ + 140                    # damlanın bir turda kat ettiği yol (px)
        rng = np.random.default_rng(40)

        def katman(adet, tur, boy, parlak, kalin):
            return dict(x=rng.uniform(-20, self.yg + 20, adet), y=rng.uniform(0, self.tur_boyu, adet),
                        tur=rng.integers(tur[0], tur[1] + 1, adet), boy=rng.uniform(*boy, adet),
                        parlak=rng.uniform(*parlak, adet), kalin=kalin)

        # tur: T saniyede kaç kez baştan düşer (tam sayı olduğu için döngü kusursuz kapanır)
        self.yagmur = [katman(520, (30, 48), (14, 30), (0.07, 0.17), 1),      # uzak, ince
                       katman(170, (52, 84), (36, 80), (0.14, 0.34), 1),      # yakın, hızlı
                       katman(30, (62, 90), (60, 110), (0.22, 0.40), 1)]      # cama en yakın, uzun
        self.suzulen = katman(34, (1, 4), (10, 34), (0.35, 0.7), 1)           # camdan süzülen damlalar
        self.egim = np.tan(np.radians(1.5))
        self.yagmur_renk = np.array([1.0, 0.93, 0.86], np.float32)            # BGR: soğuk beyaz

    # -------------------------------------------------------------- kare
    @staticmethod
    def _bük(kare, kutu, izgara, dx, dy):
        x0, y0, x1, y1 = kutu
        bolge = kare[y0:y1, x0:x1]
        kare[y0:y1, x0:x1] = cv2.remap(bolge, izgara[1] + dx, izgara[0] + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def kare(self, n: int, acilis=False, kapanis=False) -> np.ndarray:
        t = n / FPS
        if acilis:      # logolu sahneden temiz sahneye yumuşak geçiş
            a = np.clip((t - 5.0) / 3.0, 0, 1)
            a = a * a * (3 - 2 * a)
            kare = self.logolu * (1 - a) + self.temiz * a
        else:
            kare = self.temiz.copy()

        # ateş
        x0, y0, x1, y1 = self.ates_kutu
        self._bük(kare, self.ates_kutu, self.ates_izgara, self.ates_dx(t) * self.ates_agirlik, self.ates_dy(t) * self.ates_agirlik)
        kare[y0:y1, x0:x1] *= (1 + 0.09 * self.ates_parlaklik(t) * self.alev)[..., None]
        yuk, gen = y1 - y0, x1 - x0
        for k in self.kivilcim:
            p = (k["faz"] + k["tur"] * t / T) % 1.0
            ky = yuk * (0.72 - p * k["boy"] * 0.62)
            kx = k["x"] + k["sal"] * np.sin(k["salfaz"] + 2 * np.pi * k["saltur"] * t / T) + p * 10
            guc = (1 - p) ** 1.5 * min(p * 8, 1.0)
            if 2 < kx < gen - 2 and 2 < ky < yuk - 2 and guc > 0.03:
                yama = kare[y0 + int(ky) - 1:y0 + int(ky) + 2, x0 + int(kx) - 1:x0 + int(kx) + 2]
                yama += np.array([0.15, 0.55, 1.0], np.float32) * guc * np.array([[0.3, 0.6, 0.3], [0.6, 1.0, 0.6], [0.3, 0.6, 0.3]], np.float32)[..., None]

        # dere ve buhar
        self._bük(kare, self.su_kutu, self.su_izgara, self.su_dx(t) * self.su_agirlik, self.su_dy(t) * self.su_agirlik)
        self._bük(kare, self.buhar_kutu, self.buhar_izgara, self.buhar_dx(t) * self.buhar_agirlik, 0 * self.buhar_agirlik)

        # ateş ve mum ışığının odaya vuran titremesi
        s = self.isik_sinir
        kazanc = sum(harita[:, :s] * (f(t) * genlik) for harita, f, genlik in self.isiklar)
        kare[:, :s] *= 1 + kazanc[..., None] * self.sicak

        # yağmur
        katman = np.zeros((self.yy_, self.yg), np.uint8)
        for y in self.yagmur + [self.suzulen]:
            ypos = (y["y"] + y["tur"] * self.tur_boyu * t / T) % self.tur_boyu - 110
            for x, yp, boy, par in zip(y["x"], ypos, y["boy"], y["parlak"]):
                xa = x + yp * self.egim
                cv2.line(katman, (int(xa - boy * self.egim), int(yp - boy)), (int(xa), int(yp)), int(par * 255), y["kalin"], cv2.LINE_AA)
        x0, y0, x1, y1 = self.cam_kutu
        yagmur = cv2.GaussianBlur(katman, (0, 0), 0.7).astype(np.float32) / 255 * self.cam[y0:y1, x0:x1]
        kare[y0:y1, x0:x1] += yagmur[..., None] * self.yagmur_renk

        if acilis:
            kare *= min(t / 2.5, 1.0)
        if kapanis:
            kare *= min(max((T - t) / 6.0, 0.0), 1.0)
        return (np.clip(kare, 0, 1) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ ses
class Ses:
    """Yağmur ve şömine sesini parça parça, kesintisiz üretir. Örnek kayıt kullanmaz."""

    def __init__(self, tohum=7):
        self.rng = np.random.default_rng(tohum)
        self.n = 0
        self.durum = {}

    def suz(self, ad, sos, x):
        """Süzgeci parçalar arasında durumunu koruyarak uygular (ek yerinde tıkırtı olmasın)."""
        if ad not in self.durum:
            self.durum[ad] = np.zeros((sos.shape[0], 2))
        y, self.durum[ad] = signal.sosfilt(sos, x, zi=self.durum[ad])
        return y

    def vuruslar(self, adet_sn, n, guc_ustel, sonum_ms, bant, ad, hiz=None):
        """Rastgele anlarda kısa vuruşlar: yağmur damlası ya da odun çıtırtısı."""
        olasilik = adet_sn / SR * (hiz if hiz is not None else 1.0)
        yerler = self.rng.random(n) < olasilik
        x = np.zeros(n)
        adet = int(yerler.sum())
        x[yerler] = self.rng.pareto(guc_ustel, adet).clip(0, 4)      # çoğu hafif, arada bir güçlü vuruş
        a = np.exp(-1 / (SR * sonum_ms / 1000))
        zarf = self.suz(ad + "s", np.array([[1.0, 0, 0, 1, -a, 0]]), x)   # her vuruş hızla sönen bir zarf açar
        return self.suz(ad + "b", signal.butter(2, bant, "bandpass", fs=SR, output="sos"), zarf * self.rng.standard_normal(n))

    def parca(self, sure: float) -> np.ndarray:
        n = int(sure * SR)
        t = (self.n + np.arange(n)) / SR
        self.n += n
        bp = lambda lo, hi: signal.butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
        lp = lambda f: signal.butter(2, f, "lowpass", fs=SR, output="sos")
        # yağmurun yavaşça şiddetlenip hafiflemesi ve ateşin canlanıp sönmesi (hiç tekrar etmeyen periyotlar)
        yagmur_siddet = 1 + 0.16 * np.sin(2 * np.pi * t / 47.3) + 0.10 * np.sin(2 * np.pi * t / 83.9 + 1) + 0.07 * np.sin(2 * np.pi * t / 131.7 + 2)
        ates_canli = 0.75 + 0.45 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 37.1 + 0.5)) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 11.3)) + 0.25 * np.sin(2 * np.pi * t / 59.9 + 2) ** 2

        kanallar = []
        for k in ("L", "R"):
            beyaz = self.rng.standard_normal(n)
            govde = self.suz("govde" + k, bp(200, 2600), beyaz) * 0.050           # yağmurun dolgun uğultusu
            tis = self.suz("tis" + k, bp(1800, 10000), beyaz) * 0.026              # yaprak ve çatıdaki ince hışırtı
            gurul = self.suz("gurul" + k, lp(110), self.rng.standard_normal(n)) * 0.028   # uzak, derin uğultu
            ince = self.vuruslar(420, n, 3.0, 1.2, [1800, 7000], "ince" + k) * 0.040      # sık, ince damlalar
            iri = self.vuruslar(22, n, 2.5, 6.0, [500, 2200], "iri" + k) * 0.030          # cama ve pervaza düşen iri damlalar
            kanallar.append((govde + tis + ince + iri) * yagmur_siddet + gurul)

        # şömine solda: çıtırtılar ve alevin hafif uğultusu
        citir = self.vuruslar(7, n, 1.6, 1.5, [1500, 7500], "citir", ates_canli) * 0.070
        pat = self.vuruslar(1.3, n, 1.8, 9.0, [450, 2600], "pat", ates_canli) * 0.060
        oynama = 0.6 + 0.4 * self.suz("oyn", lp(4), self.rng.standard_normal(n)) * 25
        alev = self.suz("alev", bp(45, 320), self.rng.standard_normal(n)) * 0.055 * np.clip(oynama, 0.2, 1.6)
        ates = citir + pat + alev
        sol, sag = kanallar[0] + ates * 1.0, kanallar[1] + ates * 0.45
        ses = np.stack([sol, sag], axis=1) * 3.0
        return np.tanh(ses * 1.2) / 1.2      # ani yüksek çıtırtıları yumuşatır


def ses_yaz(yol: pathlib.Path, sure: float, kodek=("-c:a", "aac", "-b:a", "128k")):
    ses, kalan = Ses(), sure
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                           "-af", f"afade=t=in:d=4,afade=t=out:st={max(sure - 8, 0)}:d=8", *kodek, str(yol)], stdin=subprocess.PIPE)
    while kalan > 0:
        ff.stdin.write(ses.parca(min(10.0, kalan)).astype(np.float32).tobytes())
        kalan -= 10.0
    ff.stdin.close()
    assert ff.wait() == 0


def ses_kayittan(klasor: pathlib.Path, yol: pathlib.Path, sure: float):
    """Sesi gerçek kayıtlardan kurar: ses_kaynak/yagmur.* (uzun yağmur kaydı) ve ses_kaynak/ates.* (kısa ateş kaydı)."""
    kaynak = klasor / "ses_kaynak"
    yagmur_dosya, ates_dosya = next(kaynak.glob("yagmur.*")), next(kaynak.glob("ates.*"))

    def coz(dosya, kanal, ek=()):
        ham = subprocess.run(["ffmpeg", "-v", "error", *ek, "-i", str(dosya), "-f", "f32le", "-ac", str(kanal), "-ar", str(SR), "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(ham, np.float32).reshape(-1, kanal).copy()

    # yağmur: baştaki 20 sn atlanır, 100 Hz altındaki uğultu ve darbeler süzülür
    yagmur = coz(yagmur_dosya, 2, ("-ss", "20", "-t", str(sure)))
    yagmur = signal.sosfilt(signal.butter(4, 100, "highpass", fs=SR, output="sos"), yagmur, axis=0).astype(np.float32)
    n = len(yagmur)
    assert n >= int(sure * SR) - SR, "yağmur kaydı istenen süreden kısa"
    # kayıt boyunca yavaşça değişen ses düzeyini dengele (yağmurun şiddeti kayıtta 10 dB oynuyor)
    pencere = SR * 5
    adet = n // pencere
    rms = np.sqrt((yagmur[:adet * pencere].mean(axis=1).reshape(adet, pencere) ** 2).mean(axis=1)) + 1e-9
    yumusak = np.convolve(np.pad(rms, 6, mode="edge"), np.ones(13) / 13, "valid")
    kazanc = np.clip((np.median(rms) / yumusak) ** 0.8, 0.35, 2.8)
    merkez = (np.arange(adet) + 0.5) * pencere
    for i in range(0, n, SR * 60):
        j = min(i + SR * 60, n)
        yagmur[i:j] *= np.interp(np.arange(i, j), merkez, kazanc).astype(np.float32)[:, None]
    # kısa süreli ani yükselmeleri (sağanak, rüzgâr, uzak gürültü) bastır: uyuyan birini irkiltmesin
    saniye = n // SR
    rms1 = np.sqrt((yagmur[:saniye * SR].mean(axis=1).reshape(saniye, SR) ** 2).mean(axis=1)) + 1e-9
    rms1 = np.convolve(np.pad(rms1, 1, mode="edge"), np.ones(3) / 3, "valid")
    esik = np.median(rms1) * 1.3
    kisma = np.minimum(1.0, (esik / rms1) ** 0.85)
    merkez1 = (np.arange(saniye) + 0.5) * SR
    for i in range(0, n, SR * 60):
        j = min(i + SR * 60, n)
        yagmur[i:j] *= np.interp(np.arange(i, j), merkez1, kisma).astype(np.float32)[:, None]
    duzey = float(np.sqrt((yagmur[::7] ** 2).mean()))
    yagmur *= 0.075 / duzey

    # ateş: kısa kayıttan rastgele uzunlukta parçalar seçip yumuşak geçişle eklenir; böylece çıtırtı düzeni tekrar etmez
    ates = coz(ates_dosya, 1)[:, 0]
    ates = ates[int(0.5 * SR):len(ates) - int(0.5 * SR)]
    rng, gecis = np.random.default_rng(11), int(0.4 * SR)
    iz = np.zeros(n + SR * 30, np.float32)
    konum = 0
    while konum < n:
        uzunluk = int(rng.uniform(9, 24) * SR)
        bas = int(rng.integers(0, len(ates) - uzunluk))
        parca = ates[bas:bas + uzunluk].copy()
        parca[:gecis] *= np.sin(np.linspace(0, np.pi / 2, gecis)) ** 2
        parca[-gecis:] *= np.cos(np.linspace(0, np.pi / 2, gecis)) ** 2
        iz[konum:konum + uzunluk] += parca
        konum += uzunluk - gecis
    iz = iz[:n]
    iz *= 0.22 / np.percentile(np.abs(iz[::5]), 99.95)      # çıtırtılar yağmurun biraz üstünde kalsın
    iz = (0.32 * np.tanh(iz / 0.32)).astype(np.float32)     # en sert çıtırtıları yumuşat

    ses = yagmur
    ses[:, 0] += iz            # şömine solda
    ses[:, 1] += iz * 0.45
    np.tanh(ses * 1.3, out=ses)
    ses /= 1.3
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                           "-af", f"afade=t=in:d=4,afade=t=out:st={max(n / SR - 8, 0)}:d=8", "-c:a", "aac", "-b:a", "160k", str(yol)], stdin=subprocess.PIPE)
    for i in range(0, n, SR * 30):
        ff.stdin.write(ses[i:i + SR * 30].tobytes())
    ff.stdin.close()
    assert ff.wait() == 0


# ------------------------------------------------------------------ çıktı
# Her parça tek anahtar kareyle kodlanır: dosya küçülür, parçalar yeniden kodlanmadan uç uca eklenir.
CRF = sys.argv[sys.argv.index("--crf") + 1] if "--crf" in sys.argv else "27"   # büyüdükçe dosya küçülür
KODLAMA = ["-c:v", "libx264", "-preset", "slow", "-crf", CRF, "-pix_fmt", "yuv420p", "-bf", "3",
           "-g", str(T * FPS), "-keyint_min", str(T * FPS), "-sc_threshold", "0"]


def gorunum_yaz(sahne: Sahne, yol: pathlib.Path, **secenek):
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{G}x{Y}", "-r", str(FPS),
                           "-i", "-", *KODLAMA, "-video_track_timescale", "12288", str(yol)], stdin=subprocess.PIPE)
    for n in range(T * FPS):
        ff.stdin.write(sahne.kare(n, **secenek).tobytes())
    ff.stdin.close()
    assert ff.wait() == 0


def main():
    klasor = KOK / sys.argv[1]
    if "--ses" in sys.argv:
        ses_yaz(klasor / "ses_deneme.wav", float(sys.argv[sys.argv.index("--ses") + 1]), ("-c:a", "pcm_s16le"))
        return
    if "--sesdegistir" in sys.argv:      # görüntüyü yeniden üretmeden yalnızca sesi yenile
        sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(klasor / "video.mp4")],
                                    capture_output=True, text=True).stdout)
        ses_kayittan(klasor, klasor / "_ses.m4a", sure)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(klasor / "video.mp4"), "-i", str(klasor / "_ses.m4a"), "-map", "0:v", "-map", "1:a",
                        "-c", "copy", "-shortest", "-movflags", "+faststart", str(klasor / "_video.mp4")], check=True)
        (klasor / "_video.mp4").replace(klasor / "video.mp4")
        (klasor / "_ses.m4a").unlink()
        return
    sahne = Sahne(klasor)
    if "--kare" in sys.argv:
        kareler = [sahne.kare(0, acilis=True) * 0 + sahne.kare(72, acilis=True), sahne.kare(200), sahne.kare(201), sahne.kare(400)]
        ust, alt = np.hstack(kareler[:2]), np.hstack(kareler[2:])
        cv2.imwrite(str(klasor / "onizleme.jpg"), cv2.resize(np.vstack([ust, alt]), (G, Y)), [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(str(klasor / "onizleme_tam.jpg"), kareler[1], [cv2.IMWRITE_JPEG_QUALITY, 92])
        return

    dakika = float(sys.argv[sys.argv.index("--dakika") + 1]) if "--dakika" in sys.argv else 60
    tur = max(int(round(dakika * 60 / T)), 3)
    gecici = klasor / "_gecici"
    gecici.mkdir(exist_ok=True)
    gorunum_yaz(sahne, gecici / "acilis.mp4", acilis=True)
    gorunum_yaz(sahne, gecici / "dongu.mp4")
    gorunum_yaz(sahne, gecici / "kapanis.mp4", kapanis=True)
    if (klasor / "ses_kaynak").is_dir():      # gerçek kayıt varsa onu kullan, yoksa sesi üret
        ses_kayittan(klasor, gecici / "ses.m4a", tur * T)
    else:
        ses_yaz(gecici / "ses.m4a", tur * T)
    (gecici / "liste.txt").write_text("file 'acilis.mp4'\n" + "file 'dongu.mp4'\n" * (tur - 2) + "file 'kapanis.mp4'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(gecici / "liste.txt"), "-i", str(gecici / "ses.m4a"),
                    "-c", "copy", "-shortest", "-movflags", "+faststart", str(klasor / "video.mp4")], check=True)
    for d in gecici.iterdir():
        d.unlink()
    gecici.rmdir()
    print(f"Hazır: {klasor / 'video.mp4'} ({tur * T / 60:.0f} dk)")


if __name__ == "__main__":
    main()
