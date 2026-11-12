"""Tek bir sahne görselinden uzun, döngülü bir rahatlama videosu üretir.

Sahne canlandırılır (yağmur ya da kar, oynayan ateş, titreyen mum ışığı, akan su, buhar);
ses, klasördeki gerçek kayıtlardan kurulur. Her sahnenin ayarı kendi klasöründeki
sahne.json dosyasındadır (koordinatlar o sahnenin görselindeki piksellerdir).

Kullanım:
  python uret.py 02-snowy-castle --kare             # kontrol kareleri (onizleme.jpg)
  python uret.py 02-snowy-castle --dakika 60        # tam video (video.mp4)
  python uret.py 02-snowy-castle --dakika 60 --crf 32   # daha küçük dosya
  python uret.py 02-snowy-castle --sesdegistir      # mevcut videonun yalnızca sesini yeniden kur

Gerekenler: ffmpeg, pip install numpy scipy opencv-python-headless pillow
"""
import json
import pathlib
import subprocess
import sys

import cv2
import numpy as np
from scipy import signal

G, Y, FPS = 1920, 1080, 24
T = 24                      # görüntü döngüsünün süresi (sn); bütün hareketler bu sürede başa döner
SR = 48000
KOK = pathlib.Path(__file__).parent


def titresim(tohum, donguler=(2, 3, 5, 8, 13, 21, 34)):
    """T saniyede kusursuz başa dönen, -1..1 arası düzensiz bir titreşim fonksiyonu."""
    rng = np.random.default_rng(tohum)
    faz = rng.uniform(0, 2 * np.pi, len(donguler))
    guc = 1 / np.sqrt(np.array(donguler, dtype=float))
    return lambda t: float(np.sum(guc * np.sin(2 * np.pi * np.array(donguler) * t / T + faz)) / guc.sum() * 1.8)


class Dalga:
    """Bir bölgeyi akışkan gibi oynatan, zamanda döngülü yer değiştirme alanı."""

    def __init__(self, tohum, yuk, gen, bilesenler, yon=1.0, olcek=1.0):
        rng = np.random.default_rng(tohum)
        yy, xx = np.mgrid[0:yuk, 0:gen].astype(np.float32)
        self.terimler = []
        for dalga_boyu_y, dalga_boyu_x, dongu, genlik in bilesenler:
            faz = (2 * np.pi * yy / (dalga_boyu_y * olcek) * yon + 2 * np.pi * xx / (dalga_boyu_x * olcek) * rng.choice([-1, 1])
                   + rng.uniform(0, 2 * np.pi)).astype(np.float32)
            self.terimler.append((faz, dongu, genlik * olcek))

    def __call__(self, t):
        return sum(g * np.sin(f + np.float32(2 * np.pi * d * t / T)) for f, d, g in self.terimler)


class Sahne:
    def __init__(self, klasor: pathlib.Path):
        self.klasor = klasor
        self.ayar = json.loads((klasor / "sahne.json").read_text(encoding="utf-8"))
        ham = cv2.imread(str(klasor / self.ayar["gorsel"]))
        self.olcek = G / ham.shape[1]          # sahne.json koordinatları kaynak görselin pikselleridir
        buyut = lambda g: cv2.resize(g, (G, Y), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
        self.temiz = buyut(ham)
        self.acilis_gorseli = buyut(cv2.imread(str(klasor / self.ayar["acilis_gorseli"]))) if self.ayar.get("acilis_gorseli") else None
        self.acilis_yazi = self._yazi() if self.ayar.get("acilis_yazi") else None
        self._cam()
        self._ates()
        self._isik()
        self._pirilti()
        self._su_ve_buhar()
        self._yagis()

    def o(self, *v):
        """Kaynak görsel koordinatını çıktı çözünürlüğüne çevirir."""
        return [int(round(x * self.olcek)) for x in v]

    # -------------------------------------------------------------- hazırlık
    def _yazi(self):
        """Açılışta birkaç saniye görünen kanal adı (saydam katman)."""
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
        y = self.ayar["acilis_yazi"]
        kat = Image.new("RGBA", (G, Y), (0, 0, 0, 0))
        golge = Image.new("RGBA", (G, Y), (0, 0, 0, 0))
        buyuk = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", 150)
        kucuk = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 30)
        for katman, renk in ((golge, (0, 0, 0, 210)), (kat, (255, 240, 214, 255))):
            ciz = ImageDraw.Draw(katman)
            ciz.text((G / 2, 430), y["baslik"], font=buyuk, fill=renk, anchor="mm")
            ciz.text((G / 2, 560), "   •   ".join(y["alt"]), font=kucuk, fill=renk, anchor="mm")
            gen = ciz.textlength("   •   ".join(y["alt"]), font=kucuk)
            for x0, x1 in ((G / 2 - gen / 2 - 110, G / 2 - gen / 2 - 30), (G / 2 + gen / 2 + 30, G / 2 + gen / 2 + 110)):
                ciz.line((x0, 560, x1, 560), fill=renk, width=2)
        golge = golge.filter(ImageFilter.GaussianBlur(14))
        golge.alpha_composite(golge)
        golge.alpha_composite(kat)
        dizi = np.asarray(golge).astype(np.float32) / 255
        return dizi[..., 2::-1].copy(), dizi[..., 3:4].copy()      # (BGR renk, saydamlık)

    def _cam(self):
        """Yağışın görüneceği cam alanı: pencere kutularındaki soğuk renkli pikseller, çerçeveler ve öndeki eşyalar hariç."""
        c = self.ayar["cam"]
        b, g, r = cv2.split(self.temiz)
        parlaklik = 0.114 * b + 0.587 * g + 0.299 * r
        maske = (((r - b) < c.get("esik", 0.03)) & (parlaklik >= c.get("min_parlaklik", 0.0))).astype(np.uint8)
        kutu = np.zeros((Y, G), np.uint8)
        for k in c["kutular"]:
            x0, y0, x1, y1 = self.o(*k)
            kutu[y0:y1, x0:x1] = 1
        maske &= kutu
        for cokgen in c.get("haric", []):
            cv2.fillPoly(maske, [np.array([self.o(*p) for p in cokgen], np.int32)], 0)
        for k in c.get("yesil_haric", []):                           # camın önündeki yapraklar
            x0, y0, x1, y1 = self.o(*k)
            maske[y0:y1, x0:x1][(g - b)[y0:y1, x0:x1] > 0.06] = 0
        acik = int(c.get("temizlik", 7))
        maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (acik, acik)))
        self.cam = cv2.GaussianBlur(maske.astype(np.float32), (0, 0), 2.0)
        kutular = np.array([self.o(*k) for k in c["kutular"]])
        self.cam_kutu = (max(int(kutular[:, 0].min()), 0), max(int(kutular[:, 1].min()), 0),
                         min(int(kutular[:, 2].max()), G), min(int(kutular[:, 3].max()), Y))

    def _ates(self):
        a = self.ayar["ates"]
        s = a.get("olcek", 1.0)                                       # 1.0: yaklaşık 250 piksel boyunda alev
        x0, y0, x1, y1 = self.ates_kutu = self.o(*a["kutu"])
        bolge = self.temiz[y0:y1, x0:x1]
        b, g, r = cv2.split(bolge)
        alev = ((r > 0.78) & (g > a.get("alev_g", 0.35)) & (b < 0.55) & (r - b > 0.35)).astype(np.uint8)   # alev_g: turuncu tuğlayı alevden ayırır
        ic = np.zeros_like(alev)
        ax, ay, bx, by = self.o(*a["ic"])                             # ocağın iç boşluğu; taş çerçeve oynamasın
        ic[ay - y0:by - y0, ax - x0:bx - x0] = 1
        alev &= ic
        cap = max(int(25 * s) | 1, 5)
        genis = cv2.dilate(alev, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (cap, cap)))
        yuk, gen = alev.shape
        ys = np.arange(yuk, dtype=np.float32)[:, None]
        taban, tepe = self.o(a["taban"])[0] - y0, self.o(a["tepe"])[0] - y0
        rampa = np.clip((taban - ys) / (taban - tepe), 0, 1) ** 0.7  # alevin ucu çok, dibi az oynar
        self.ates_agirlik = (cv2.GaussianBlur(genis.astype(np.float32), (0, 0), 9 * s) * rampa
                             * cv2.GaussianBlur(ic.astype(np.float32), (0, 0), max(5 * s, 1.5)) ** 2)
        self.alev = cv2.GaussianBlur(alev.astype(np.float32), (0, 0), max(4 * s, 1.2))
        self.ates_dx = Dalga(1, yuk, gen, [(120, 260, 18, 4.0), (75, 180, 26, 3.0), (52, 140, 34, 2.2), (38, 110, 46, 1.4), (26, 90, 60, 0.9)], olcek=s)
        self.ates_dy = Dalga(2, yuk, gen, [(95, 200, 22, 2.4), (48, 120, 38, 1.4), (30, 80, 54, 0.8)], olcek=s)
        self.ates_izgara = np.mgrid[0:yuk, 0:gen].astype(np.float32)
        self.ates_parlaklik = titresim(3, (5, 9, 14, 23, 37, 55))
        rng = np.random.default_rng(4)                                # yükselen kıvılcımlar
        self.kivilcim = [dict(x=rng.uniform(0.3, 0.7) * gen, faz=rng.uniform(0, 1), tur=int(rng.integers(4, 10)),
                              sal=rng.uniform(4, 14) * s, salfaz=rng.uniform(0, 6.28), saltur=int(rng.integers(6, 20)),
                              boy=rng.uniform(0.5, 0.95)) for _ in range(int(a.get("kivilcim", 14)))]

    def _isik(self):
        """Ateşin ve mumların çevreye vurduğu ışığın oynaması için kazanç haritaları."""
        yy, xx = np.mgrid[0:Y, 0:G].astype(np.float32)
        ic = 1 - self.cam                                             # ışık yalnızca oda içine vurur
        self.isiklar = []
        for i, l in enumerate(self.ayar["isiklar"]):
            cx, cy = self.o(l["x"], l["y"])
            harita = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (l["sigma"] * self.olcek) ** 2)) * ic
            donguler = (3, 5, 8, 13, 21, 34, 47) if l["sigma"] > 150 else tuple(int(v) for v in np.random.default_rng(50 + i).choice(np.arange(3, 36), 5, replace=False))
            self.isiklar.append((harita, titresim(10 + i, donguler), l["genlik"]))
        etki = np.max([h for h, _, _ in self.isiklar], axis=0) > 0.004
        sutun, satir = np.where(etki.any(axis=0))[0], np.where(etki.any(axis=1))[0]
        self.isik_dilim = (slice(satir[0], satir[-1] + 1), slice(sutun[0], sutun[-1] + 1))   # hız için yalnızca etkilenen alan
        self.isiklar = [(h[self.isik_dilim], f, g) for h, f, g in self.isiklar]
        self.sicak = np.array([0.55, 0.85, 1.0], np.float32)          # BGR: sıcak ışık maviyi az etkiler

    def _pirilti(self):
        """Ağaç ve süs ışıklarının göz kırpması: kutulardaki küçük parlak noktalar ayrı ayrı yanıp söner."""
        self.piriltilar = []
        rng = np.random.default_rng(70)
        for p in self.ayar.get("pirilti", []):
            x0, y0, x1, y1 = self.o(*p["kutu"])
            b, g, r = cv2.split(self.temiz[y0:y1, x0:x1])
            parlak = (((0.114 * b + 0.587 * g + 0.299 * r) > p.get("esik", 0.72)) & ((r - b) >= p.get("sicak", -1.0))).astype(np.float32)   # sicak: yalnızca sıcak renkli ışıklar (kar parlamasın)
            maske = cv2.GaussianBlur(parlak, (0, 0), 2.5)
            hucre = 14                                               # her hücre kendi hızında ve fazında yanıp söner
            ky, kx = (y1 - y0) // hucre + 1, (x1 - x0) // hucre + 1
            buyut = lambda d: np.kron(d, np.ones((hucre, hucre), np.float32))[:y1 - y0, :x1 - x0]
            self.piriltilar.append(((x0, y0, x1, y1), maske * p.get("genlik", 0.4),
                                    buyut(rng.uniform(0, 2 * np.pi, (ky, kx)).astype(np.float32)), buyut(rng.integers(3, 11, (ky, kx)).astype(np.float32))))

    def _su_ve_buhar(self):
        self.su_kutu = self.buhar_kutu = None
        if "su" in self.ayar:
            x0, y0, x1, y1 = self.su_kutu = self.o(*self.ayar["su"]["kutu"])
            b, g, r = cv2.split(self.temiz[y0:y1, x0:x1])
            su = ((b > self.ayar["su"].get("esik", 0.42)) & (b > r + 0.04)).astype(np.float32)
            self.su_agirlik = cv2.GaussianBlur(su, (0, 0), 3)
            yuk, gen = su.shape
            self.su_dx = Dalga(20, yuk, gen, [(60, 45, 9, 2.2), (34, 28, 15, 1.3), (22, 60, 21, 0.8)], yon=-1.0)
            self.su_dy = Dalga(21, yuk, gen, [(40, 50, 12, 1.2), (24, 36, 19, 0.7)], yon=-1.0)
            self.su_izgara = np.mgrid[0:yuk, 0:gen].astype(np.float32)
        if "buhar" in self.ayar:
            x0, y0, x1, y1 = self.buhar_kutu = self.o(*self.ayar["buhar"]["kutu"])
            yuk, gen = y1 - y0, x1 - x0
            yy, xx = np.mgrid[0:yuk, 0:gen].astype(np.float32)
            self.buhar_agirlik = np.exp(-((xx - gen / 2) ** 2 / (2 * (gen / 4) ** 2) + (yy - yuk * 0.45) ** 2 / (2 * (yuk / 3.4) ** 2))) * self.ayar["buhar"].get("genlik", 1.0)   # genlik: arkada düz çizgiler varsa küçült
            self.buhar_dx = Dalga(30, yuk, gen, [(90, 400, 4, 5.0), (55, 300, 7, 3.0), (34, 200, 11, 1.5)])
            self.buhar_izgara = np.mgrid[0:yuk, 0:gen].astype(np.float32)

    def _yagis(self):
        x0, y0, x1, y1 = self.cam_kutu
        self.yg, self.yy_ = x1 - x0, y1 - y0
        self.tur_boyu = self.yy_ + 140                    # damlanın ya da tanenin bir turda kat ettiği yol (px)
        self.tur_eni = self.yg + 80
        rng = np.random.default_rng(40)
        self.tur = self.ayar.get("yagis", "yagmur")

        # tur: T saniyede kaç kez baştan düşer (tam sayı olduğu için döngü kusursuz kapanır)
        if self.tur == "yagmur":
            def katman(adet, tur, boy, parlak, kalin):
                return dict(x=rng.uniform(-20, self.yg + 20, adet), y=rng.uniform(0, self.tur_boyu, adet),
                            tur=rng.integers(tur[0], tur[1] + 1, adet), boy=rng.uniform(*boy, adet),
                            parlak=rng.uniform(*parlak, adet), kalin=kalin)
            self.yagmur = [katman(520, (30, 48), (14, 30), (0.07, 0.17), 1),      # uzak, ince
                           katman(170, (52, 84), (36, 80), (0.14, 0.34), 1),      # yakın, hızlı
                           katman(30, (62, 90), (60, 110), (0.22, 0.40), 1),      # cama en yakın, uzun
                           katman(34, (1, 4), (10, 34), (0.35, 0.7), 1)]          # camdan süzülen damlalar
            self.egim = np.tan(np.radians(1.5))
            self.yagis_renk = np.array([1.0, 0.93, 0.86], np.float32)             # BGR: soğuk beyaz
        else:
            def katman(adet, tur, yatay, yaricap, parlak, bulanik):
                return dict(x=rng.uniform(0, self.tur_eni, adet), y=rng.uniform(0, self.tur_boyu, adet),
                            tur=rng.integers(tur[0], tur[1] + 1, adet), yatay=rng.integers(yatay[0], yatay[1] + 1, adet),
                            yaricap=rng.uniform(*yaricap, adet), parlak=rng.uniform(*parlak, adet),
                            sal=rng.uniform(3, 16, adet), salfaz=rng.uniform(0, 6.28, adet), saltur=rng.integers(2, 7, adet), bulanik=bulanik)
            yogunluk = self.yg * self.yy_ / (1300 * 800)
            self.kar = [katman(int(900 * yogunluk), (2, 3), (0, 1), (0.6, 1.1), (0.25, 0.55), 0.6),   # uzak, küçük, yavaş
                        katman(int(380 * yogunluk), (3, 5), (1, 1), (1.0, 1.8), (0.40, 0.80), 0.8),   # orta
                        katman(int(70 * yogunluk), (5, 8), (1, 2), (2.0, 3.4), (0.45, 0.75), 1.8)]    # cama yakın, iri, bulanık
            self.yagis_renk = np.array([1.0, 0.97, 0.94], np.float32)

    # -------------------------------------------------------------- kare
    @staticmethod
    def _buk(kare, kutu, izgara, dx, dy):
        x0, y0, x1, y1 = kutu
        bolge = kare[y0:y1, x0:x1]
        kare[y0:y1, x0:x1] = cv2.remap(bolge, izgara[1] + dx, izgara[0] + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def _yagis_katmani(self, t):
        if self.tur == "yagmur":
            katman = np.zeros((self.yy_, self.yg), np.uint8)
            for y in self.yagmur:
                ypos = (y["y"] + y["tur"] * self.tur_boyu * t / T) % self.tur_boyu - 110
                for x, yp, boy, par in zip(y["x"], ypos, y["boy"], y["parlak"]):
                    xa = x + yp * self.egim
                    cv2.line(katman, (int(xa - boy * self.egim), int(yp - boy)), (int(xa), int(yp)), int(par * 255), y["kalin"], cv2.LINE_AA)
            return cv2.GaussianBlur(katman, (0, 0), 0.7).astype(np.float32) / 255
        toplam = np.zeros((self.yy_, self.yg), np.float32)
        for k in self.kar:
            katman = np.zeros((self.yy_, self.yg), np.uint8)
            ypos = (k["y"] + k["tur"] * self.tur_boyu * t / T) % self.tur_boyu - 70
            xpos = (k["x"] - k["yatay"] * self.tur_eni * t / T + k["sal"] * np.sin(k["salfaz"] + 2 * np.pi * k["saltur"] * t / T)) % self.tur_eni - 40
            for x, y, r, par in zip(xpos, ypos, k["yaricap"], k["parlak"]):   # shift=4: piksel altı konum, hareket titremez
                cv2.circle(katman, (int(x * 16), int(y * 16)), int(r * 16), int(par * 255), -1, cv2.LINE_AA, 4)
            toplam += cv2.GaussianBlur(katman, (0, 0), k["bulanik"]).astype(np.float32) / 255
        return toplam

    def kare(self, n: int, acilis=False, kapanis=False) -> np.ndarray:
        t = n / FPS
        gecis = float(np.clip((t - 5.0) / 3.0, 0, 1))
        gecis = gecis * gecis * (3 - 2 * gecis)
        if acilis and self.acilis_gorseli is not None:      # logolu sahneden temiz sahneye yumuşak geçiş
            kare = self.acilis_gorseli * (1 - gecis) + self.temiz * gecis
        else:
            kare = self.temiz.copy()

        # ateş
        x0, y0, x1, y1 = self.ates_kutu
        self._buk(kare, self.ates_kutu, self.ates_izgara, self.ates_dx(t) * self.ates_agirlik, self.ates_dy(t) * self.ates_agirlik)
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

        # akan su ve buhar
        if self.su_kutu:
            self._buk(kare, self.su_kutu, self.su_izgara, self.su_dx(t) * self.su_agirlik, self.su_dy(t) * self.su_agirlik)
        if self.buhar_kutu:
            self._buk(kare, self.buhar_kutu, self.buhar_izgara, self.buhar_dx(t) * self.buhar_agirlik, 0 * self.buhar_agirlik)

        # ateş ve mum ışığının odaya vuran titremesi
        kazanc = sum(harita * (f(t) * genlik) for harita, f, genlik in self.isiklar)
        kare[self.isik_dilim] *= 1 + kazanc[..., None] * self.sicak
        for (px0, py0, px1, py1), guc, faz, hiz in self.piriltilar:
            kare[py0:py1, px0:px1] *= (1 + guc * np.sin(faz + np.float32(2 * np.pi * t / T) * hiz))[..., None]

        # yağmur ya da kar
        x0, y0, x1, y1 = self.cam_kutu
        kare[y0:y1, x0:x1] += (self._yagis_katmani(t) * self.cam[y0:y1, x0:x1])[..., None] * self.yagis_renk

        if acilis and self.acilis_yazi is not None:         # kanal adı birkaç saniye görünüp kaybolur
            renk, saydam = self.acilis_yazi
            a = saydam * (min(max((t - 1.0) / 1.5, 0.0), 1.0) * (1 - gecis))
            kare = kare * (1 - a) + renk * a
        if acilis:
            kare = kare * min(t / 2.5, 1.0)
        if kapanis:
            kare = kare * min(max((T - t) / 6.0, 0.0), 1.0)
        return (np.clip(kare, 0, 1) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ ses
def kayit_coz(dosya, kanal, ek=()):
    ham = subprocess.run(["ffmpeg", "-v", "error", *ek, "-i", str(dosya), "-f", "f32le", "-ac", str(kanal), "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(ham, np.float32).reshape(-1, kanal).copy()


def uzat(kayit: np.ndarray, n: int, rng, parca=(9, 24), gecis_sn=0.4) -> np.ndarray:
    """Kısa bir kayıttan rastgele parçalar seçip yumuşak geçişle ekleyerek n örneğe uzatır; düzen tekrar etmez."""
    gecis = int(gecis_sn * SR)
    iz = np.zeros(n + int(parca[1] * SR) + SR, np.float32)
    konum = 0
    while konum < n:
        uzunluk = min(int(rng.uniform(*parca) * SR), len(kayit) - 1)
        bas = int(rng.integers(0, len(kayit) - uzunluk))
        p = kayit[bas:bas + uzunluk].copy()
        p[:gecis] *= np.sin(np.linspace(0, np.pi / 2, gecis)) ** 2
        p[-gecis:] *= np.cos(np.linspace(0, np.pi / 2, gecis)) ** 2
        iz[konum:konum + uzunluk] += p
        konum += uzunluk - gecis
    return iz[:n]


def ses_kur(klasor: pathlib.Path, yol: pathlib.Path, sure: float):
    """Sesi gerçek kayıtlardan kurar: isteğe bağlı bir zemin sesi (yağmur ya da rüzgâr) ve şömine çıtırtısı."""
    a = json.loads((klasor / "sahne.json").read_text(encoding="utf-8"))["ses"]
    n = int(sure * SR)
    rng = np.random.default_rng(11)

    zemin = np.zeros((n, 2), np.float32)
    if a.get("zemin"):               # zemin sesi isteğe bağlı; yoksa yalnızca şömine duyulur
        zemin_dosya = klasor / a["zemin"]
        uzunluk = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(zemin_dosya)],
                                       capture_output=True, text=True).stdout)
        bas = a.get("zemin_bas", 0)
        if uzunluk - bas >= sure:        # kayıt yeterince uzun: kesintisiz kullan
            zemin = kayit_coz(zemin_dosya, 2, ("-ss", str(bas), "-t", str(sure)))[:n]
            zemin = np.pad(zemin, ((0, n - len(zemin)), (0, 0)))
        else:                            # kısa kayıt: iki kanal için ayrı ayrı uzat, böylece ses geniş duyulur
            tek = kayit_coz(zemin_dosya, 1)[:, 0]
            tek = tek[int(bas * SR):]
            zemin = np.stack([uzat(tek, n, rng, (20, 55), 3.0), uzat(tek, n, rng, (20, 55), 3.0)], axis=1)
        sos = signal.butter(4, a.get("alt_kesim", 100), "highpass", fs=SR, output="sos")
        if a.get("ust_kesim"):
            sos = np.vstack([sos, signal.butter(2, a["ust_kesim"], "lowpass", fs=SR, output="sos")])
        zemin = signal.sosfilt(sos, zemin, axis=0).astype(np.float32)

        def duzelt(pencere_sn, yumusat, kazanc_hesabi):
            pencere = int(SR * pencere_sn)
            adet = n // pencere
            rms = np.sqrt((zemin[:adet * pencere].mean(axis=1).reshape(adet, pencere) ** 2).mean(axis=1)) + 1e-9
            rms = np.convolve(np.pad(rms, yumusat // 2, mode="edge"), np.ones(yumusat) / yumusat, "valid")
            kazanc = kazanc_hesabi(rms)
            merkez = (np.arange(adet) + 0.5) * pencere
            for i in range(0, n, SR * 60):
                j = min(i + SR * 60, n)
                zemin[i:j] *= np.interp(np.arange(i, j), merkez, kazanc).astype(np.float32)[:, None]

        if a.get("duzey_dengele", True):     # kayıt boyunca yavaşça değişen ses düzeyini dengele
            duzelt(5, 13, lambda r: np.clip((np.median(r) / r) ** 0.8, 0.35, 2.8))
        esik = a.get("ani_esik", 1.3)        # ani yükselmeleri bastır: uyuyan birini irkiltmesin
        duzelt(1, 3, lambda r: np.minimum(1.0, (np.median(r) * esik / r) ** 0.85))
        if a.get("dalgalanma"):              # düzeyi sabit bir kayda yavaş, tekrar etmeyen iniş çıkışlar ekle
            d = a["dalgalanma"]
            for i in range(0, n, SR * 60):
                t = np.arange(i, min(i + SR * 60, n), dtype=np.float32) / SR
                zemin[i:i + len(t)] *= (1 + d * (0.5 * np.sin(2 * np.pi * t / 41.3) + 0.3 * np.sin(2 * np.pi * t / 67.1 + 1) + 0.2 * np.sin(2 * np.pi * t / 113.7 + 2)))[:, None]
        zemin *= a.get("zemin_duzey", 0.075) / float(np.sqrt((zemin[::7] ** 2).mean()))


    # şömine: kısa kayıttan birkaç bağımsız katman üst üste biner; ateş daha dolu ve sık çıtırtılı duyulur
    ates = kayit_coz(klasor / a["ates"], 1)[:, 0]
    ates = ates[int(0.5 * SR):len(ates) - int(0.5 * SR)]
    sol, sag = a.get("ates_denge", [1.0, 0.45])                  # şöminenin görüntüdeki yerine göre sol/sağ düzeyi
    kesim = a.get("ates_govde_kesim", 600)
    alcak = np.vstack([signal.butter(2, 70, "highpass", fs=SR, output="sos"), signal.butter(2, kesim, "lowpass", fs=SR, output="sos")])
    yuksek = signal.butter(2, kesim, "highpass", fs=SR, output="sos")
    tavan = a.get("ates_tavan", 0.32)
    for k in range(int(a.get("ates_katman", 1))):
        iz = uzat(ates, n, rng)
        iz *= a.get("ates_duzey", 0.22) / np.percentile(np.abs(iz[::5]), 99.95)
        citirti = signal.sosfilt(yuksek, iz).astype(np.float32)
        citirti = (tavan * np.tanh(citirti / tavan)).astype(np.float32)          # en sert çıtırtıları yumuşat
        govde = signal.sosfilt(alcak, iz).astype(np.float32) * a.get("ates_govde", 1.0)   # alevin alçak uğultusu
        iz = citirti + govde
        kay = (0.0, 0.12, -0.08)[k % 3]                                          # katmanlar biraz farklı yerlerden gelsin
        zemin[:, 0] += iz * (sol + kay)
        zemin[:, 1] += iz * (sag - kay)
    np.tanh(zemin * 1.6, out=zemin)      # tepe değerini sınırla; sıkıştırılmış seste taşma olmasın
    zemin /= 1.6
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                           "-af", f"afade=t=in:d=4,afade=t=out:st={max(n / SR - 8, 0)}:d=8", "-c:a", "aac", "-b:a", "160k", str(yol)], stdin=subprocess.PIPE)
    for i in range(0, n, SR * 30):
        ff.stdin.write(zemin[i:i + SR * 30].tobytes())
    ff.stdin.close()
    assert ff.wait() == 0


# ------------------------------------------------------------------ çıktı
CRF = sys.argv[sys.argv.index("--crf") + 1] if "--crf" in sys.argv else "27"   # büyüdükçe dosya küçülür
# Her parça tek anahtar kareyle kodlanır: dosya küçülür, parçalar yeniden kodlanmadan uç uca eklenir.
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
    if "--sesdegistir" in sys.argv:      # görüntüyü yeniden üretmeden yalnızca sesi yenile
        sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(klasor / "video.mp4")],
                                    capture_output=True, text=True).stdout)
        ses_kur(klasor, klasor / "_ses.m4a", sure)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(klasor / "video.mp4"), "-i", str(klasor / "_ses.m4a"), "-map", "0:v", "-map", "1:a",
                        "-c", "copy", "-shortest", "-movflags", "+faststart", str(klasor / "_video.mp4")], check=True)
        (klasor / "_video.mp4").replace(klasor / "video.mp4")
        (klasor / "_ses.m4a").unlink()
        return
    sahne = Sahne(klasor)
    if "--kare" in sys.argv:
        kareler = [sahne.kare(72, acilis=True), sahne.kare(200), sahne.kare(201), sahne.kare(400)]
        cv2.imwrite(str(klasor / "onizleme.jpg"), cv2.resize(np.vstack([np.hstack(kareler[:2]), np.hstack(kareler[2:])]), (G, Y)), [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(str(klasor / "onizleme_tam.jpg"), kareler[1], [cv2.IMWRITE_JPEG_QUALITY, 92])
        return

    dakika = float(sys.argv[sys.argv.index("--dakika") + 1]) if "--dakika" in sys.argv else 60
    tur = max(int(round(dakika * 60 / T)), 3)
    gecici = klasor / "_gecici"
    gecici.mkdir(exist_ok=True)
    gorunum_yaz(sahne, gecici / "acilis.mp4", acilis=True)
    gorunum_yaz(sahne, gecici / "dongu.mp4")
    gorunum_yaz(sahne, gecici / "kapanis.mp4", kapanis=True)
    ses_kur(klasor, gecici / "ses.m4a", tur * T)
    (gecici / "liste.txt").write_text("file 'acilis.mp4'\n" + "file 'dongu.mp4'\n" * (tur - 2) + "file 'kapanis.mp4'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(gecici / "liste.txt"), "-i", str(gecici / "ses.m4a"),
                    "-c", "copy", "-shortest", "-movflags", "+faststart", str(klasor / "video.mp4")], check=True)
    for d in gecici.iterdir():
        d.unlink()
    gecici.rmdir()
    print(f"Hazır: {klasor / 'video.mp4'} ({tur * T / 60:.0f} dk)")


if __name__ == "__main__":
    main()
