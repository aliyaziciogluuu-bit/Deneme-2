"""Tek bir sahne görselinden uzun, döngülü bir rahatlama videosu üretir.

Sahne canlandırılır (yağmur ya da kar, oynayan ateş, titreyen mum ışığı, akan su, buhar);
ses, klasördeki gerçek kayıtlardan kurulur. Her sahnenin ayarı kendi klasöründeki
sahne.json dosyasındadır (koordinatlar o sahnenin görselindeki piksellerdir).

Kullanım:
  python uret.py 02-snowy-castle --kare             # kontrol kareleri (onizleme.jpg)
  python uret.py 02-snowy-castle --dakika 60        # tam video (video.mp4)
  python uret.py 02-snowy-castle --dakika 60 --crf 32   # daha küçük dosya
  python uret.py 02-snowy-castle --sesdegistir      # mevcut videonun yalnızca sesini yeniden kur
  python uret.py 03-christmas-cabin --dakika 180 --720 --hevc --crf 35 --ses-kbps 96 --cikti video_3saat.mp4
                                                    # 3 saatlik sürüm, 400 MB altına sığar

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
if "--4k" in sys.argv:                   # 4K: sahne.json'da "gorsel_4k" (yapay zekâyla büyütülmüş görsel) varsa o kullanılır
    G, Y = 3840, 2160
K = G / 1920                             # sabit piksel ölçüleri (kar tanesi, yazı, bulanıklık) 1080p'ye göre yazıldı; 4K'da 2 kat
T = 24                      # görüntü döngüsünün süresi (sn); bütün hareketler bu sürede başa döner
DONGU = T                   # videonun tekrar birimi (sn, T'nin katı); sahne.json "dongu_sn" ile uzatılır (örn. kuzey ışıkları)
SR = 48000
KOK = pathlib.Path(__file__).parent


_TUR_RNG = np.random.default_rng(99)


def uzun(c):
    """T saniyedeki tur sayısını DONGU'ya taşır: hız aynı kalır, küçük rastgele sapma eklenir. Böylece kar tanesi, alev,
    ışık titremesi gibi öğeler 24 sn'de bir aynı düzene dönmez; bütün görüntü ancak DONGU sonunda başa döner."""
    M = DONGU // T
    c = np.asarray(c)
    if M == 1:
        return c
    tek = np.array([v for v in range(-(M // 2), M // 2 + 1) if v % 2 != 0] or [0])
    j = tek[_TUR_RNG.integers(0, len(tek), c.shape)]               # tek sapma: frekanslar çift kalıp döngüyü yarıya bölmesin
    return np.where(c == 0, 0, np.maximum(c * M + j, 1))


def titresim(tohum, donguler=(2, 3, 5, 8, 13, 21, 34)):
    """DONGU saniyede kusursuz başa dönen, -1..1 arası düzensiz bir titreşim fonksiyonu."""
    rng = np.random.default_rng(tohum)
    donguler = uzun(donguler)
    faz = rng.uniform(0, 2 * np.pi, len(donguler))
    guc = 1 / np.sqrt(np.array(donguler, dtype=float))
    return lambda t: float(np.sum(guc * np.sin(2 * np.pi * np.array(donguler) * t / DONGU + faz)) / guc.sum() * 1.8)


class Dalga:
    """Bir bölgeyi akışkan gibi oynatan, zamanda döngülü yer değiştirme alanı."""

    def __init__(self, tohum, yuk, gen, bilesenler, yon=1.0, olcek=1.0):
        rng = np.random.default_rng(tohum)
        yy, xx = np.mgrid[0:yuk, 0:gen].astype(np.float32)
        self.terimler = []
        for dalga_boyu_y, dalga_boyu_x, dongu, genlik in bilesenler:
            faz = (2 * np.pi * yy / (dalga_boyu_y * olcek) * yon + 2 * np.pi * xx / (dalga_boyu_x * olcek) * rng.choice([-1, 1])
                   + rng.uniform(0, 2 * np.pi)).astype(np.float32)
            self.terimler.append((faz, int(uzun(dongu)), genlik * olcek))

    def __call__(self, t):
        return sum(g * np.sin(f + np.float32(2 * np.pi * d * t / DONGU)) for f, d, g in self.terimler)


class KlipDizi:
    """Uzun klip dizisi: kareler bellekte tutulmaz, istenince iki kaynak karenin karışımı olarak hesaplanır."""
    def __init__(self, kareler, oran, tarif):
        self.kareler, self.oran, self.tarif = kareler, oran, tarif

    def __len__(self):
        return len(self.tarif)

    def __getitem__(self, i):
        a, b, w = self.tarif[i]
        k = self.kareler[a] if w < 1e-3 else self.kareler[a] * np.float32(1 - w) + self.kareler[b] * np.float32(w)
        return np.clip(k * self.oran, 0, 1)


class Sahne:
    def __init__(self, klasor: pathlib.Path):
        global _TUR_RNG
        _TUR_RNG = np.random.default_rng(99)        # aynı sahne her seferinde aynı hareketi üretsin
        self.klasor = klasor
        self.ayar = json.loads((klasor / "sahne.json").read_text(encoding="utf-8"))
        ham = cv2.imread(str(klasor / self.ayar["gorsel"]))
        self.olcek = G / ham.shape[1]          # sahne.json koordinatları kaynak görselin pikselleridir
        if K > 1 and self.ayar.get("gorsel_4k"):
            ham = cv2.imread(str(klasor / self.ayar["gorsel_4k"]))
        buyut = lambda g: cv2.resize(g, (G, Y), interpolation=cv2.INTER_LANCZOS4).astype(np.float32) / 255
        self.temiz = buyut(ham)
        self.acilis_gorseli = buyut(cv2.imread(str(klasor / self.ayar["acilis_gorseli"]))) if self.ayar.get("acilis_gorseli") else None
        self.acilis_yazi = self._yazi() if self.ayar.get("acilis_yazi") else None
        self._cam()
        self.klip, self.ates_kutu = None, None
        if "ates" in self.ayar:              # şöminesi olmayan sahnelerde ateş adımı atlanır
            self._ates()
        self._isik()
        self._pirilti()
        self.ek_klipler = [self._klip_yukle(k, k["kutu"]) for k in self.ayar.get("ek_klipler", [])]   # örn. gerçek deniz
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
        buyuk = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", int(150 * K))
        kucuk = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", int(30 * K))
        for katman, renk in ((golge, (0, 0, 0, 210)), (kat, (255, 240, 214, 255))):
            ciz = ImageDraw.Draw(katman)
            ciz.text((G / 2, 430 * K), y["baslik"], font=buyuk, fill=renk, anchor="mm")
            ciz.text((G / 2, 560 * K), "   •   ".join(y["alt"]), font=kucuk, fill=renk, anchor="mm")
            gen = ciz.textlength("   •   ".join(y["alt"]), font=kucuk)
            for x0, x1 in ((G / 2 - gen / 2 - 110 * K, G / 2 - gen / 2 - 30 * K), (G / 2 + gen / 2 + 30 * K, G / 2 + gen / 2 + 110 * K)):
                ciz.line((x0, 560 * K, x1, 560 * K), fill=renk, width=int(2 * K))
        golge = golge.filter(ImageFilter.GaussianBlur(14 * K))
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
        if c.get("daire"):                                            # yuvarlak pencere: dairenin dışını at
            cx, cy, r = c["daire"]
            (cx, cy), r = self.o(cx, cy), r * self.olcek
            yy, xx = np.ogrid[0:Y, 0:G]
            maske &= (((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r).astype(np.uint8)
        for cokgen in c.get("haric", []):
            cv2.fillPoly(maske, [np.array([self.o(*p) for p in cokgen], np.int32)], 0)
        for k in c.get("yesil_haric", []):                           # camın önündeki yapraklar
            x0, y0, x1, y1 = self.o(*k)
            maske[y0:y1, x0:x1][(g - b)[y0:y1, x0:x1] > 0.06] = 0
        acik = int(c.get("temizlik", 7) * K)
        maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (acik, acik)))
        self.cam = cv2.GaussianBlur(maske.astype(np.float32), (0, 0), 2.0 * K)
        kutular = np.array([self.o(*k) for k in c["kutular"]])
        self.cam_kutu = (max(int(kutular[:, 0].min()), 0), max(int(kutular[:, 1].min()), 0),
                         min(int(kutular[:, 2].max()), G), min(int(kutular[:, 3].max()), Y))

    def _ates(self):
        a = self.ayar["ates"]
        s = a.get("olcek", 1.0) * K                                   # 1.0: yaklaşık 250 piksel boyunda alev (1080p)
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
        self.kivilcim = [dict(x=rng.uniform(0.3, 0.7) * gen, faz=rng.uniform(0, 1), tur=int(uzun(rng.integers(4, 10))),
                              sal=rng.uniform(4, 14) * s, salfaz=rng.uniform(0, 6.28), saltur=int(uzun(rng.integers(6, 20))),
                              boy=rng.uniform(0.5, 0.95)) for _ in range(int(a.get("kivilcim", 14)))]
        self._ates_klip()

    def _klip_yukle(self, k, varsayilan_maske):
        """Bir video klibini sahnedeki yerine hazırlar: boyut, 24 sn'lik döngüye uyum, yumuşak maske, renk eşitleme."""
        ax0, ay0, ax1, ay1 = self.o(*k["kutu"])
        gen, yuk = ax1 - ax0, ay1 - ay0
        # başka sahneden uyarlanan klip görüntünün dışına taşabilir: taşan kısım kırpılır
        kx0, ky0, kx1, ky1 = kutu = (max(ax0, 0), max(ay0, 0), min(ax1, G), min(ay1, Y))
        kes = (slice(ky0 - ay0, ky1 - ay0), slice(kx0 - ax0, kx1 - ax0))
        cap = cv2.VideoCapture(str(self.klasor / k["dosya"]))
        kareler = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            kareler.append(cv2.resize(f, (gen, yuk), interpolation=cv2.INTER_AREA)[kes].astype(np.float32) / 255)
        if k.get("zaman_bukme") or k.get("karisik"):
            sira = None                                                # aşağıda: klip DONGU boyunca ileri-geri, değişken hızla oynar
        else:
            donus = T * FPS
            hedef = min((d for d in range(donus // 4, donus + 1) if donus % d == 0), key=lambda d: abs(d - len(kareler)))
            sira = [int(round(i * len(kareler) / hedef)) % len(kareler) for i in range(hedef)]   # 24 sn'lik döngüye tam sığsın
        maske = np.zeros((Y, G), np.float32)
        for m in k.get("maskeler", [k.get("maske", varsayilan_maske)]):   # örn. iki camlı kapakta iki cam
            ix0, iy0, ix1, iy1 = self.o(*m)
            maske[iy0:iy1, ix0:ix1] = 1
        for m in k.get("haric", []):                                   # kapak çerçevesi, kulp gibi önde kalanlar
            ix0, iy0, ix1, iy1 = self.o(*m)
            maske[iy0:iy1, ix0:ix1] = 0
        maske = cv2.GaussianBlur(maske, (0, 0), k.get("yumusaklik", 7) * K)
        if k.get("maske_cam"):                                         # pencere çerçevesi önde kalsın
            maske *= self.cam
        maske = maske[ky0:ky1, kx0:kx1, None]
        orta = np.mean(kareler[::max(len(kareler) // 20, 1)], axis=0)
        m = maske[..., 0] > 0.5                                        # renkleri orijinal görsele eşitle
        oran = ((self.temiz[ky0:ky1, kx0:kx1][m].mean(axis=0) + 1e-3) / (orta[m].mean(axis=0) + 1e-3)).astype(np.float32)
        if sira is None and k.get("karisik"):
            return self._karisik(kareler, oran, k.get("parca_sn", 4.0), int(k.get("gecis_sn", 1.0) * FPS)), kutu, maske   # deniz: uzun parça, az karışım
        if sira is None:
            return self._zaman_buk(kareler, oran, k.get("zaman_bukme")), kutu, maske
        return [np.clip(kareler[i] * oran, 0, 1) for i in sira], kutu, maske

    @staticmethod
    def _karisik(kareler, oran, parca_sn=4.0, gecis=24):
        """Ateş, deniz gibi geri oynatılamayan klipler için: döngü klibinin rastgele yerlerinden ileri oynayan parçalar
        yumuşak geçişle art arda eklenir; DONGU boyunca aynı düzen tekrar etmez, son parça ilkine bağlanır (kusursuz döngü)."""
        N, L = DONGU * FPS, len(kareler)
        m = max(int(round(N / (parca_sn * FPS))), 2)
        while N % m:
            m += 1
        S = N // m
        rng = np.random.default_rng(len(kareler) * 7919 + N)
        bas = [0]
        for _ in range(m - 1):                                         # ardışık parçalar klibin uzak yerlerinden başlasın
            bas.append(int((bas[-1] + rng.uniform(0.3, 0.7) * L) % L))
        print(f"karışık döngü: {N} kare, {m} parça × {S / FPS:.1f} sn", flush=True)
        tarif = []
        for i in range(N):
            j, yerel = divmod(i, S)
            kalan, w = S - yerel, 0.0
            if kalan <= gecis:                                         # parçanın sonu bir sonrakinin başına karışır
                w = 1 - (kalan - 0.5) / gecis
                w = w * w * (3 - 2 * w)
            tarif.append(((bas[j] + yerel) % L, (bas[(j + 1) % m] - kalan) % L, w))
        return KlipDizi(kareler, oran, tarif)

    @staticmethod
    def _zaman_buk(kareler, oran, _):
        """Kısa klibi DONGU süresince tekrar etmeden oynatır: konum birkaç sinüsün toplamı (ileri-geri, değişken hız).
        Yön değişimleri hız sıfırken olur, bu yüzden fark edilmez; aradaki kareler komşu karelerin karışımıdır."""
        N, L = DONGU * FPS, len(kareler)
        u = np.arange(N) / N
        f = sum(a * np.sin(2 * np.pi * k * u + faz) for k, a, faz in
                [(1, 1.0, 0.4), (2, 0.6, 1.9), (5, 0.35, 4.1), (7, 0.25, 0.7), (11, 0.1, 2.5)])   # ort. ~0,34x, en çok ~1,1x
        f = (f - f.min()) / (f.max() - f.min())
        konum = f * (L - 1)
        hiz_k = np.abs(np.diff(np.append(konum, konum[0])))
        print(f"zaman bükme: {N} kare, ortalama hız {hiz_k.mean():.2f}x, en yüksek {hiz_k.max():.2f}x", flush=True)
        return KlipDizi(kareler, oran, [(int(p), min(int(p) + 1, L - 1), p - int(p)) for p in konum])

    def _ates_klip(self):
        """sahne.json'da "ates_klip" varsa şöminenin içi gerçek ateş videosuyla değiştirilir (ates_klip.py üretir)."""
        self.klip = None
        k = self.ayar.get("ates_klip")
        if k:
            self.klip, self.klip_kutu, self.klip_maske = self._klip_yukle(k, self.ayar["ates"]["ic"])

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
            maske = cv2.GaussianBlur(parlak, (0, 0), 2.5 * K)
            hucre = int(14 * K)                                              # her hücre kendi hızında ve fazında yanıp söner
            ky, kx = (y1 - y0) // hucre + 1, (x1 - x0) // hucre + 1
            buyut = lambda d: np.kron(d, np.ones((hucre, hucre), np.float32))[:y1 - y0, :x1 - x0]
            self.piriltilar.append(((x0, y0, x1, y1), maske * p.get("genlik", 0.4),
                                    buyut(rng.uniform(0, 2 * np.pi, (ky, kx)).astype(np.float32)), buyut(uzun(rng.integers(3, 11, (ky, kx))).astype(np.float32))))

    def _su_ve_buhar(self):
        self.su_kutu = self.buhar_kutu = None
        if "su" in self.ayar:
            x0, y0, x1, y1 = self.su_kutu = self.o(*self.ayar["su"]["kutu"])
            b, g, r = cv2.split(self.temiz[y0:y1, x0:x1])
            su = ((b > self.ayar["su"].get("esik", 0.42)) & (b > r + 0.04)).astype(np.float32)
            self.su_agirlik = cv2.GaussianBlur(su, (0, 0), 3 * K)
            yuk, gen = su.shape
            self.su_dx = Dalga(20, yuk, gen, [(60, 45, 9, 2.2), (34, 28, 15, 1.3), (22, 60, 21, 0.8)], yon=-1.0, olcek=K)
            self.su_dy = Dalga(21, yuk, gen, [(40, 50, 12, 1.2), (24, 36, 19, 0.7)], yon=-1.0, olcek=K)
            self.su_izgara = np.mgrid[0:yuk, 0:gen].astype(np.float32)
        if "buhar" in self.ayar:
            x0, y0, x1, y1 = self.buhar_kutu = self.o(*self.ayar["buhar"]["kutu"])
            yuk, gen = y1 - y0, x1 - x0
            yy, xx = np.mgrid[0:yuk, 0:gen].astype(np.float32)
            self.buhar_agirlik = np.exp(-((xx - gen / 2) ** 2 / (2 * (gen / 4) ** 2) + (yy - yuk * 0.45) ** 2 / (2 * (yuk / 3.4) ** 2))) * self.ayar["buhar"].get("genlik", 1.0)   # genlik: arkada düz çizgiler varsa küçült
            self.buhar_dx = Dalga(30, yuk, gen, [(90, 400, 4, 5.0), (55, 300, 7, 3.0), (34, 200, 11, 1.5)], olcek=K)
            self.buhar_izgara = np.mgrid[0:yuk, 0:gen].astype(np.float32)

    def _yagis(self):
        x0, y0, x1, y1 = self.cam_kutu
        self.yg, self.yy_ = x1 - x0, y1 - y0
        self.tur_boyu = self.yy_ + 140 * K                    # damlanın ya da tanenin bir turda kat ettiği yol (px)
        self.tur_eni = self.yg + 80 * K
        rng = np.random.default_rng(40)
        self.tur = self.ayar.get("yagis", "yagmur")

        # tur: T saniyede kaç kez baştan düşer (tam sayı olduğu için döngü kusursuz kapanır)
        if self.tur == "yagmur":
            def katman(adet, tur, boy, parlak, kalin):
                return dict(x=rng.uniform(-20 * K, self.yg + 20 * K, adet), y=rng.uniform(0, self.tur_boyu, adet),
                            tur=uzun(rng.integers(tur[0], tur[1] + 1, adet)), boy=rng.uniform(*boy, adet) * K,
                            parlak=rng.uniform(*parlak, adet), kalin=max(int(round(kalin * K)), 1))
            self.yagmur = [katman(520, (30, 48), (14, 30), (0.07, 0.17), 1),      # uzak, ince
                           katman(170, (52, 84), (36, 80), (0.14, 0.34), 1),      # yakın, hızlı
                           katman(30, (62, 90), (60, 110), (0.22, 0.40), 1),      # cama en yakın, uzun
                           katman(34, (1, 4), (10, 34), (0.35, 0.7), 1)]          # camdan süzülen damlalar
            self.egim = np.tan(np.radians(1.5))
            self.yagis_renk = np.array([1.0, 0.93, 0.86], np.float32)             # BGR: soğuk beyaz
        else:
            def katman(adet, tur, yatay, yaricap, parlak, bulanik):
                return dict(x=rng.uniform(0, self.tur_eni, adet), y=rng.uniform(0, self.tur_boyu, adet),
                            tur=uzun(rng.integers(tur[0], tur[1] + 1, adet)), yatay=uzun(rng.integers(yatay[0], yatay[1] + 1, adet)),
                            yaricap=rng.uniform(*yaricap, adet) * K, parlak=rng.uniform(*parlak, adet),
                            sal=rng.uniform(3, 16, adet) * K, salfaz=rng.uniform(0, 6.28, adet), saltur=uzun(rng.integers(2, 7, adet)), bulanik=bulanik * K)
            yogunluk = self.yg * self.yy_ / (1300 * 800 * K * K)
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
                ypos = (y["y"] + y["tur"] * self.tur_boyu * t / DONGU) % self.tur_boyu - 110 * K
                for x, yp, boy, par in zip(y["x"], ypos, y["boy"], y["parlak"]):
                    xa = x + yp * self.egim
                    cv2.line(katman, (int(xa - boy * self.egim), int(yp - boy)), (int(xa), int(yp)), int(par * 255), y["kalin"], cv2.LINE_AA)
            return cv2.GaussianBlur(katman, (0, 0), 0.7 * K).astype(np.float32) / 255
        toplam = np.zeros((self.yy_, self.yg), np.float32)
        for k in self.kar:
            katman = np.zeros((self.yy_, self.yg), np.uint8)
            ypos = (k["y"] + k["tur"] * self.tur_boyu * t / DONGU) % self.tur_boyu - 70 * K
            xpos = (k["x"] - k["yatay"] * self.tur_eni * t / DONGU + k["sal"] * np.sin(k["salfaz"] + 2 * np.pi * k["saltur"] * t / DONGU)) % self.tur_eni - 40 * K
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
        if self.ates_kutu is None:
            pass
        elif self.klip is not None:
            kx0, ky0, kx1, ky1 = self.klip_kutu
            b = kare[ky0:ky1, kx0:kx1]
            kare[ky0:ky1, kx0:kx1] = b * (1 - self.klip_maske) + self.klip[n % len(self.klip)] * self.klip_maske
        else:
            x0, y0, x1, y1 = self.ates_kutu
            self._buk(kare, self.ates_kutu, self.ates_izgara, self.ates_dx(t) * self.ates_agirlik, self.ates_dy(t) * self.ates_agirlik)
            kare[y0:y1, x0:x1] *= (1 + 0.09 * self.ates_parlaklik(t) * self.alev)[..., None]
        kivilcimlar = self.kivilcim if (self.ates_kutu is not None and self.klip is None) else []   # gerçek ateş klibi kendi kıvılcımlarını taşır
        if kivilcimlar:
            x0, y0, x1, y1 = self.ates_kutu
            yuk, gen = y1 - y0, x1 - x0
        for k in kivilcimlar:
            p = (k["faz"] + k["tur"] * t / DONGU) % 1.0
            ky = yuk * (0.72 - p * k["boy"] * 0.62)
            kx = k["x"] + k["sal"] * np.sin(k["salfaz"] + 2 * np.pi * k["saltur"] * t / DONGU) + p * 10 * K
            guc = (1 - p) ** 1.5 * min(p * 8, 1.0)
            if 2 < kx < gen - 2 and 2 < ky < yuk - 2 and guc > 0.03:
                yama = kare[y0 + int(ky) - 1:y0 + int(ky) + 2, x0 + int(kx) - 1:x0 + int(kx) + 2]
                yama += np.array([0.15, 0.55, 1.0], np.float32) * guc * np.array([[0.3, 0.6, 0.3], [0.6, 1.0, 0.6], [0.3, 0.6, 0.3]], np.float32)[..., None]

        # ek gerçek video klipleri (örn. pencereden görünen deniz)
        for klip, (ex0, ey0, ex1, ey1), maske in self.ek_klipler:
            kare[ey0:ey1, ex0:ex1] = kare[ey0:ey1, ex0:ex1] * (1 - maske) + klip[n % len(klip)] * maske

        # akan su ve buhar
        if self.su_kutu:
            self._buk(kare, self.su_kutu, self.su_izgara, self.su_dx(t) * self.su_agirlik, self.su_dy(t) * self.su_agirlik)
        if self.buhar_kutu:
            self._buk(kare, self.buhar_kutu, self.buhar_izgara, self.buhar_dx(t) * self.buhar_agirlik, 0 * self.buhar_agirlik)

        # ateş ve mum ışığının odaya vuran titremesi
        kazanc = sum(harita * (f(t) * genlik) for harita, f, genlik in self.isiklar)
        kare[self.isik_dilim] *= 1 + kazanc[..., None] * self.sicak
        for (px0, py0, px1, py1), guc, faz, hiz in self.piriltilar:
            kare[py0:py1, px0:px1] *= (1 + guc * np.sin(faz + np.float32(2 * np.pi * t / DONGU) * hiz))[..., None]

        # yağmur ya da kar
        x0, y0, x1, y1 = self.cam_kutu
        kare[y0:y1, x0:x1] += (self._yagis_katmani(t) * self.cam[y0:y1, x0:x1])[..., None] * self.yagis_renk

        if self.ayar.get("sallanti"):                       # tren gibi hareketli sahnelerde hafif, ritmik sallantı
            sa = self.ayar["sallanti"]
            a, z = sa.get("genlik", 1.5) * self.olcek, sa.get("olcek", 1.012)
            w = 2 * np.pi * t / DONGU                         # bütün frekanslar tam sayı: döngü kusursuz kalır
            if not hasattr(self, "_sal_f"):
                M = DONGU // T                                 # frekanslar döngü kare sayısıyla ortak çarpansız: yarı/üçte bir döngüde dönmez
                self._sal_f = [int(f) if M == 1 else int(f) for f in ([24, 37, 61, 7, 5] if M == 1 else
                               [next(v for v in range(c * M + 1, c * M + 50) if np.gcd(v, DONGU) == 1) for c in (24, 37, 61, 7, 5)])]
            f1, f2, f3, f4, f5 = self._sal_f
            dy = a * (0.55 * np.sin(f1 * w) + 0.3 * np.sin(f2 * w + 1.0) + 0.15 * np.sin(f3 * w + 2.0))
            dx = a * 0.35 * np.sin(f4 * w + 0.5)
            M = cv2.getRotationMatrix2D((G / 2, Y / 2), 0.04 * np.sin(f5 * w), z)
            M[0, 2] += dx; M[1, 2] += dy
            kare = cv2.warpAffine(kare, M, (G, Y), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if acilis and self.acilis_yazi is not None:         # kanal adı birkaç saniye görünüp kaybolur
            renk, saydam = self.acilis_yazi
            a = saydam * (min(max((t - 1.0) / 1.5, 0.0), 1.0) * (1 - gecis))
            kare = kare * (1 - a) + renk * a
        if acilis:
            kare = kare * min(t / 2.5, 1.0)
        if kapanis:
            kare = kare * min(max((DONGU - t) / 6.0, 0.0), 1.0)
        return (np.clip(kare, 0, 1) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ ses
def kayit_coz(dosya, kanal, ek=()):
    ham = subprocess.run(["ffmpeg", "-v", "error", *ek, "-i", str(dosya), "-f", "f32le", "-ac", str(kanal), "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(ham, np.float32).reshape(-1, kanal).copy()


def uzat(kayit, n: int, rng, parca=(9, 24), gecis_sn=0.4) -> np.ndarray:
    """Kısa bir kayıttan rastgele parçalar seçip yumuşak geçişle ekleyerek n örneğe uzatır; düzen tekrar etmez."""
    gecis = int(gecis_sn * SR)
    iz = np.zeros(n + int(parca[1] * SR) + SR, np.float32)
    konum = 0
    kayitlar = kayit if isinstance(kayit, list) else [kayit]     # birden fazla temiz bölüm verilebilir
    while konum < n:
        kayit = kayitlar[int(rng.integers(0, len(kayitlar)))]
        uzunluk = min(int(rng.uniform(*parca) * SR), len(kayit) - 1)
        bas = int(rng.integers(0, len(kayit) - uzunluk))
        p = kayit[bas:bas + uzunluk].copy()
        p[:gecis] *= np.sin(np.linspace(0, np.pi / 2, gecis)) ** 2
        p[-gecis:] *= np.cos(np.linspace(0, np.pi / 2, gecis)) ** 2
        iz[konum:konum + uzunluk] += p
        konum += uzunluk - gecis
    return iz[:n]


# ITU-R BS.1770 K-ağırlıklı ses yüksekliği (LUFS): kulağın algıladığı yüksekliği ölçer
K_RAF = (np.array([1.53512485958697, -2.69169618940638, 1.19839281085285]), np.array([1.0, -1.69065929318241, 0.73248077421585]))
K_GECIREN = (np.array([1.0, -2.0, 1.0]), np.array([1.0, -1.99004745483398, 0.99007225036621]))
HEDEF_LUFS = -24.0                       # bütün uzun videolar aynı yükseklikte (uyku için rahat, YouTube'un -14 sınırının çok altında)


def lufs(ses: np.ndarray) -> float:
    """Tüm parça için kapılı (gated) bütünleşik ses yüksekliği; 3 saatlik seste bellek yetsin diye parça parça."""
    sos = np.vstack([signal.tf2sos(*K_RAF), signal.tf2sos(*K_GECIREN)])
    zi = np.zeros((sos.shape[0], 2, 2))
    blok = int(0.4 * SR)
    enerjiler = []
    for i in range(0, len(ses) - blok, SR * 120):
        p, zi = signal.sosfilt(sos, ses[i:i + SR * 120], axis=0, zi=zi)
        m = len(p) // blok * blok
        enerjiler.append((p[:m] ** 2).reshape(-1, blok, 2).mean(axis=1).sum(axis=1))
    e = np.concatenate(enerjiler)
    e = e[-0.691 + 10 * np.log10(e + 1e-12) > -70]                    # mutlak kapı
    esik = -0.691 + 10 * np.log10(e.mean()) - 10                       # göreli kapı
    e = e[-0.691 + 10 * np.log10(e) > esik]
    return float(-0.691 + 10 * np.log10(e.mean()))


def ses_kur(klasor: pathlib.Path, yol: pathlib.Path, sure: float, giris: float = 4, cikis: float = 8, hedef: float = None):
    """Sesi gerçek kayıtlardan kurar: isteğe bağlı bir zemin sesi (yağmur ya da rüzgâr) ve şömine çıtırtısı."""
    a = json.loads((klasor / "sahne.json").read_text(encoding="utf-8"))["ses"]
    n = int(sure * SR)
    import zlib
    rng = np.random.default_rng(11 + zlib.crc32(klasor.name.encode()) % 100000)   # her sahnenin ses düzeni farklı olsun

    zemin = np.zeros((n, 2), np.float32)
    if a.get("zemin"):               # zemin sesi isteğe bağlı; yoksa yalnızca şömine duyulur
        zemin_dosya = klasor / a["zemin"]
        uzunluk = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(zemin_dosya)],
                                       capture_output=True, text=True).stdout)
        bas = a.get("zemin_bas", 0)
        # Uzun sürümlerde (3 saat ≈ 4 GB ses) bellek yetsin diye her adım yerinde ve parça parça yapılır.
        if uzunluk - bas >= sure:        # kayıt yeterince uzun: kesintisiz kullan
            ham = kayit_coz(zemin_dosya, 2, ("-ss", str(bas), "-t", str(sure)))[:n]
            zemin[:len(ham)] = ham
            del ham
        else:                            # kısa kayıt: iki kanal için ayrı ayrı uzat, böylece ses geniş duyulur
            tek = kayit_coz(zemin_dosya, 1)[:, 0]
            if a.get("zemin_parcalar"):      # yalnızca seçilen temiz bölümler (örn. trenin sabit hızla gittiği yerler)
                tek = [tek[int(b * SR):int(e * SR)].copy() for b, e in a["zemin_parcalar"]]
                uzunluklar = (min(20, min(len(t) for t in tek) / SR - 1), min(55, min(len(t) for t in tek) / SR - 1))
            else:
                tek = [tek[int(bas * SR):].copy()]
                uzunluklar = (20, 55)
            if a.get("zemin_ek"):            # ek kayıtlar (örn. farklı yağmurlar): ana kayıtla aynı düzeye getirilip havuza katılır
                hedef_rms = np.sqrt(np.mean(np.concatenate([t[::50] for t in (tek if isinstance(tek, list) else [tek])]) ** 2))
                tek = tek if isinstance(tek, list) else [tek]
                for d in a["zemin_ek"]:
                    ek = kayit_coz(klasor / d, 1)[:, 0]
                    ek = ek[int(0.5 * SR):len(ek) - int(0.5 * SR)]
                    tek.append(ek * np.float32(hedef_rms / (np.sqrt(np.mean(ek[::50] ** 2)) + 1e-9)))
                uzunluklar = (min(uzunluklar[0], min(len(t) for t in tek) / SR - 1), min(uzunluklar[1], min(len(t) for t in tek) / SR - 1))
            for kanal in (0, 1):
                zemin[:, kanal] = uzat(tek, n, rng, uzunluklar, 3.0)
            del tek
        sos = signal.butter(4, a.get("alt_kesim", 100), "highpass", fs=SR, output="sos")
        if a.get("ust_kesim"):
            sos = np.vstack([sos, signal.butter(a.get("ust_kesim_derece", 2), a["ust_kesim"], "lowpass", fs=SR, output="sos")])
        zi = np.zeros((sos.shape[0], 2, 2))
        for i in range(0, n, SR * 120):
            parca, zi = signal.sosfilt(sos, zemin[i:i + SR * 120], axis=0, zi=zi)
            zemin[i:i + SR * 120] = parca

        def duzelt(pencere_sn, yumusat, kazanc_hesabi):
            pencere = int(SR * pencere_sn)
            adet = n // pencere
            rms = np.empty(adet)
            blok = max(1, (SR * 120) // pencere)
            for b in range(0, adet, blok):
                e = min(b + blok, adet)
                m = zemin[b * pencere:e * pencere].mean(axis=1).reshape(e - b, pencere)
                rms[b:e] = np.sqrt((m.astype(np.float64) ** 2).mean(axis=1))
            rms += 1e-9
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
    # "ates" tek dosya ya da dosya listesi olabilir: birden fazla kayıt varsa uzat() parçaları hepsinden seçer (çıtırtı tekrar etmez)
    ates_dosyalar = ([a["ates"]] if isinstance(a.get("ates"), str) else a.get("ates")) or []
    ates = [kayit_coz(klasor / d, 1)[:, 0] for d in ates_dosyalar] or [np.zeros(SR * 30, np.float32)]
    ates = [x[int(0.5 * SR):len(x) - int(0.5 * SR)] for x in ates]
    ates = [x / (np.percentile(np.abs(x[::5]), 99.9) + 1e-6) for x in ates]     # kayıtlar arasında düzey farkı olmasın
    sol, sag = a.get("ates_denge", [1.0, 0.45])                  # şöminenin görüntüdeki yerine göre sol/sağ düzeyi
    kesim = a.get("ates_govde_kesim", 600)
    alcak = np.vstack([signal.butter(2, 70, "highpass", fs=SR, output="sos"), signal.butter(2, kesim, "lowpass", fs=SR, output="sos")])
    yuksek = signal.butter(2, kesim, "highpass", fs=SR, output="sos")
    tavan = a.get("ates_tavan", 0.32)
    for k in range(int(a.get("ates_katman", 1)) if a.get("ates") else 0):
        iz = uzat(ates, n, rng)
        iz *= a.get("ates_duzey", 0.22) / np.percentile(np.abs(iz[::5]), 99.95)
        kay = (0.0, 0.12, -0.08)[k % 3]                                          # katmanlar biraz farklı yerlerden gelsin
        zi_y, zi_a = np.zeros((yuksek.shape[0], 2)), np.zeros((alcak.shape[0], 2))
        for i in range(0, n, SR * 120):                                          # uzun sürümlerde bellek yetsin diye parça parça
            p = iz[i:i + SR * 120]
            citirti, zi_y = signal.sosfilt(yuksek, p, zi=zi_y)
            citirti = tavan * np.tanh(citirti / tavan)                           # en sert çıtırtıları yumuşat
            govde, zi_a = signal.sosfilt(alcak, p, zi=zi_a)                      # alevin alçak uğultusu
            p = (citirti + govde * a.get("ates_govde", 1.0)).astype(np.float32)
            zemin[i:i + len(p), 0] += p * (sol + kay)
            zemin[i:i + len(p), 1] += p * (sag - kay)
        del iz
    hedef = a.get("hedef_lufs", HEDEF_LUFS) if hedef is None else hedef
    once = lufs(zemin)
    kazanc = np.float32(10 ** ((hedef - once) / 20))                   # her video aynı yükseklikte duyulsun
    for i in range(0, n, SR * 120):      # tepe değerini sınırla; sıkıştırılmış seste taşma olmasın
        zemin[i:i + SR * 120] = np.tanh(zemin[i:i + SR * 120] * kazanc * 1.6) / 1.6
    duzeltme = np.float32(10 ** ((hedef - lufs(zemin)) / 20))         # sınırlayıcının yuttuğu küçük farkı geri ver
    for i in range(0, n, SR * 120):
        zemin[i:i + SR * 120] *= duzeltme
    print(f"ses yüksekliği: {once:.1f} → {hedef:.1f} LUFS", flush=True)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                           "-af", f"alimiter=limit=0.7:attack=2:release=80:level=disabled,afade=t=in:d={giris},afade=t=out:st={max(n / SR - cikis, 0)}:d={cikis}", "-c:a", "aac", "-b:a", f"{SES_KBPS}k", str(yol)], stdin=subprocess.PIPE)
    for i in range(0, n, SR * 30):
        ff.stdin.write(zemin[i:i + SR * 30].tobytes())
    ff.stdin.close()
    assert ff.wait() == 0


# ------------------------------------------------------------------ çıktı
def secenek(ad, varsayilan):
    return sys.argv[sys.argv.index(ad) + 1] if ad in sys.argv else varsayilan


CRF = secenek("--crf", "27")             # büyüdükçe dosya küçülür
SES_KBPS = secenek("--ses-kbps", "160")
CIKTI = secenek("--cikti", "video.mp4")
# Her parça tek anahtar kareyle kodlanır: dosya küçülür, parçalar yeniden kodlanmadan uç uca eklenir.
if "--hevc" in sys.argv:                 # uzun sürümler için: aynı kalitede yaklaşık yarı boyut (YouTube kabul eder)
    KODLAMA = ["-c:v", "libx265", "-preset", "medium", "-crf", CRF, "-pix_fmt", "yuv420p", "-tag:v", "hvc1",
               "-x265-params", f"keyint={T * FPS}:min-keyint={T * FPS}:scenecut=0:log-level=error"]
else:
    KODLAMA = ["-c:v", "libx264", "-preset", "slow", "-crf", CRF, "-pix_fmt", "yuv420p", "-bf", "3",
               "-g", str(T * FPS), "-keyint_min", str(T * FPS), "-sc_threshold", "0"]
if "--720" in sys.argv:                  # dosya gönderme sınırına sığmayan uzun sürümler için
    KODLAMA = ["-vf", "scale=1280:720:flags=lanczos", *KODLAMA]


def gorunum_yaz(sahne: Sahne, yol: pathlib.Path, **secenek):
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{G}x{Y}", "-r", str(FPS),
                           "-i", "-", *KODLAMA, "-video_track_timescale", "12288", str(yol)], stdin=subprocess.PIPE)
    for n in range(DONGU * FPS):
        ff.stdin.write(sahne.kare(n, **secenek).tobytes())
    ff.stdin.close()
    assert ff.wait() == 0


def main():
    klasor = KOK / sys.argv[1]
    if "--sesdegistir" in sys.argv:      # görüntüyü yeniden üretmeden yalnızca sesi yenile
        sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(klasor / CIKTI)],
                                    capture_output=True, text=True).stdout)
        ses_kur(klasor, klasor / "_ses.m4a", sure)  # ses bit hızı --ses-kbps ile
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(klasor / CIKTI), "-i", str(klasor / "_ses.m4a"), "-map", "0:v", "-map", "1:a",
                        "-c", "copy", "-shortest", "-movflags", "+faststart", str(klasor / "_video.mp4")], check=True)
        (klasor / "_video.mp4").replace(klasor / CIKTI)
        (klasor / "_ses.m4a").unlink()
        return
    global DONGU
    DONGU = int(json.loads((klasor / "sahne.json").read_text(encoding="utf-8")).get("dongu_sn", T))
    assert DONGU % T == 0, "dongu_sn 24'ün katı olmalı"
    sahne = Sahne(klasor)
    if "--kare" in sys.argv:
        kareler = [sahne.kare(72, acilis=True), sahne.kare(200), sahne.kare(201), sahne.kare(400)]
        cv2.imwrite(str(klasor / "onizleme.jpg"), cv2.resize(np.vstack([np.hstack(kareler[:2]), np.hstack(kareler[2:])]), (G, Y)), [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(str(klasor / "onizleme_tam.jpg"), kareler[1], [cv2.IMWRITE_JPEG_QUALITY, 92])
        return

    dakika = float(sys.argv[sys.argv.index("--dakika") + 1]) if "--dakika" in sys.argv else 60
    tur = max(int(np.ceil(dakika * 60 / DONGU - 1e-9)), 3)       # en az istenen süre ("3 saat" başlığı doğru kalsın)
    gecici = klasor / f"_gecici_{pathlib.Path(CIKTI).stem}_{secenek('--paket', '')}_{G}"   # aynı sahnede aynı anda iki iş çakışmasın
    gecici.mkdir(exist_ok=True)
    def hazir(yol):                      # yarıda kalan işten sağlam kalan parça yeniden üretilmez
        if not yol.exists():
            return False
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(yol)], capture_output=True, text=True)
        try:
            return abs(float(r.stdout) - DONGU) < 0.05
        except ValueError:
            return False
    for ad, secim in (("acilis", dict(acilis=True)), ("dongu", {}), ("kapanis", dict(kapanis=True))):
        if hazir(gecici / f"{ad}.mp4"):
            print(f"{ad}.mp4 hazır, atlanıyor", flush=True)
        else:
            gorunum_yaz(sahne, gecici / f"{ad}.mp4", **secim)
    del sahne                            # 4K sahnenin belleği ses hazırlanmadan önce boşalsın (yoksa bellek yetmiyor)
    import gc
    gc.collect()
    ses_kur(klasor, gecici / "ses.m4a", tur * DONGU)
    (gecici / "liste.txt").write_text("file 'acilis.mp4'\n" + "file 'dongu.mp4'\n" * (tur - 2) + "file 'kapanis.mp4'\n")
    if "--paket" in sys.argv:            # büyük (4K) videolar: parçalar gönderilir, kanal sahibi kendi bilgisayarında birleştirir
        ad = secenek("--paket", klasor.name)
        hedef = klasor / f"paket_{ad}"
        if hedef.exists():
            for d in hedef.iterdir():
                d.unlink()
        gecici.rename(hedef)
        (hedef / "BIRLESTIR.bat").write_text(
            "@echo off\r\ncd /d \"%~dp0\"\r\necho Video birlestiriliyor, lutfen bekleyin...\r\n"
            f"ffmpeg -v error -y -f concat -safe 0 -i liste.txt -i ses.m4a -map 0:v -map 1:a -c copy -shortest -movflags +faststart \"{ad}.mp4\"\r\n"
            f"if exist \"{ad}.mp4\" (echo HAZIR: {ad}.mp4) else (echo HATA: ffmpeg.exe bu klasorde mi?)\r\npause\r\n", encoding="ascii")
        print(f"Paket hazır: {hedef}")
        return
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(gecici / "liste.txt"), "-i", str(gecici / "ses.m4a"),
                    "-c", "copy", "-shortest", "-movflags", "+faststart", str(klasor / CIKTI)], check=True)
    for d in gecici.iterdir():
        d.unlink()
    gecici.rmdir()
    print(f"Hazır: {klasor / CIKTI} ({tur * DONGU / 60:.0f} dk)")


if __name__ == "__main__":
    main()
