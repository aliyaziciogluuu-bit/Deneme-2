"""Senaryo + ses + görsellerden YouTube'a hazır video üretir.

Kullanım:
  python video.py 01-dans-vebasi              # video.mp4, altyazi.srt, kapak.jpg
  python video.py 01-dans-vebasi --onizleme   # sadece onizleme.jpg (her çekimden bir kare)

Girdi (video klasöründe): senaryo.json, cekimler.json, gorseller/, ses/000.wav ...
İsteğe bağlı: senaryo.json'da "ambiyans": {"dosya": "../sesler/bahce.ogg", "seviye": 0.07, "kaynak": "..."}
  → anlatımın altına çok kısık doğa sesi döşenir (CC0 kayıtlar; kaynak açıklamaya yazılır).
Gerekenler: ffmpeg, pip install pillow numpy
"""
import json
import multiprocessing as mp
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

G, Y, FPS = 1920, 1080, 30
SR = 48000
ARA_CUMLE, ARA_SAHNE, GIRIS, BITIS = 0.35, 0.85, 0.7, 2.5
GECIS = 0.35  # çekimler arası geçiş süresi (sn)
YAZI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
YAZI_KALIN = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

KOK = pathlib.Path(__file__).parent


# ---------------------------------------------------------------- zaman çizelgesi
def sesi_oku(yol: pathlib.Path) -> np.ndarray:
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(yol), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    ses = np.frombuffer(ham, dtype=np.int16).astype(np.float32) / 32768
    kenar = int(SR * 0.01)
    ses[:kenar] *= np.linspace(0, 1, kenar)
    ses[-kenar:] *= np.linspace(1, 0, kenar)
    return ses


def cizelge(klasor: pathlib.Path):
    """Cümlelerin başlangıç/bitiş zamanlarını ve birleşik ses kaydını döndürür."""
    senaryo = json.loads((klasor / "senaryo.json").read_text(encoding="utf-8"))
    cumleler, t, parcalar = [], GIRIS, []
    for sahne in senaryo["sahneler"]:
        for j, c in enumerate(sahne["cumleler"]):
            i = len(cumleler)
            dosya = next((d for d in sorted((klasor / "ses").glob(f"{i:03d}.*")) if d.suffix != ".json"), None)
            if dosya:
                ses = sesi_oku(dosya)
                sure = len(ses) / SR
                parcalar.append((t, ses))
            else:  # ses henüz yoksa süreyi metinden tahmin et (önizleme için)
                sure = len(c["yazi"]) / 14
            son = j == len(sahne["cumleler"]) - 1
            cumleler.append({"yazi": c["yazi"], "bas": t, "bit": t + sure, "ara": ARA_SAHNE if son else ARA_CUMLE,
                             "bolum": sahne["ad"] if j == 0 else None})
            t += sure + cumleler[-1]["ara"]
    toplam = cumleler[-1]["bit"] + BITIS
    kayit = np.zeros(int(toplam * SR) + SR, dtype=np.float32)
    for bas, ses in parcalar:
        k = int(bas * SR)
        kayit[k:k + len(ses)] += ses
    return cumleler, toplam, kayit, senaryo


def cekimleri_kur(klasor: pathlib.Path, cumleler, toplam):
    plan = json.loads((klasor / "cekimler.json").read_text(encoding="utf-8"))["cekimler"]
    assert sum(c["n"] for c in plan) == len(cumleler), "cekimler.json cümle sayısıyla uyuşmuyor"
    i = 0
    for k, c in enumerate(plan):
        ilk, son = cumleler[i], cumleler[i + c["n"] - 1]
        c["bas"] = 0.0 if k == 0 else ilk["bas"] - cumleler[i - 1]["ara"] / 2
        c["bit"] = toplam if k == len(plan) - 1 else son["bit"] + son["ara"] / 2
        i += c["n"]
    return plan


# ---------------------------------------------------------------- altyazı
def parcala(metin: str, sinir: int = 74):
    """Cümleyi ekrana sığacak, yaklaşık eşit uzunlukta altyazı parçalarına böler."""
    if len(metin) <= sinir:
        return [metin]
    adet = -(-len(metin) // sinir)
    hedef = len(metin) / adet
    kelimeler, konum, adaylar = metin.split(), 0, []
    for i, k in enumerate(kelimeler[:-1]):
        konum += len(k) + 1
        odul = 14 if k[-1] in ".?!:;" else 8 if k[-1] == "," else 0  # noktalamadan bölmeyi tercih et
        adaylar.append((abs(konum - hedef) - odul, i + 1))
    kes = min(adaylar)[1]
    return [" ".join(kelimeler[:kes])] + parcala(" ".join(kelimeler[kes:]), sinir)


def altyazilar(cumleler):
    liste = []
    for c in cumleler:
        parcalar = parcala(c["yazi"])
        toplam = sum(len(p) for p in parcalar)
        t = c["bas"]
        for p in parcalar:
            sure = (c["bit"] - c["bas"]) * len(p) / toplam
            liste.append({"yazi": p, "bas": t, "bit": t + sure})
            t += sure
        liste[-1]["bit"] += min(0.25, c["ara"] * 0.7)
    return liste


def srt_yaz(liste, yol: pathlib.Path):
    def z(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    yol.write_text("\n".join(f"{i + 1}\n{z(a['bas'])} --> {z(a['bit'])}\n{a['yazi']}\n" for i, a in enumerate(liste)),
                   encoding="utf-8")


def yukleme_yaz(senaryo, cumleler, yol: pathlib.Path):
    """YouTube'a yüklerken kopyalanacak başlık, açıklama, bölümler ve etiketler."""
    bolumler = [(0 if i == 0 else int(c["bas"]), c["bolum"]) for i, c in enumerate(cumleler) if c["bolum"]]
    satirlar = ["BAŞLIK", senaryo["baslik"], "", "AÇIKLAMA", senaryo.get("aciklama", ""), "", "Bölümler:"]
    satirlar += [f"{t // 60}:{t % 60:02d} {ad}" for t, ad in bolumler]
    if senaryo.get("yorum_sorusu"):
        satirlar += ["", "🌿 " + senaryo["yorum_sorusu"]]
    satirlar += ["", "Kaynaklar:"] + [f"- {k}" for k in senaryo.get("kaynaklar", [])]
    satirlar += ["", senaryo.get("beyan", "Görseller yapay zekâ ile üretilmiş çizimlerdir; seslendirme yapay zekâ ile yapılmıştır. "
                                          "Bilgiler yukarıdaki kaynaklardan derlenmiştir.")]
    if senaryo.get("ambiyans", {}).get("kaynak"):
        satirlar += ["Doğa sesi: " + senaryo["ambiyans"]["kaynak"]]
    imza = (KOK / "kanal" / "imza.txt")
    if imza.exists():
        satirlar += ["", imza.read_text(encoding="utf-8").strip()]
    satirlar += ["", "ETİKETLER", ", ".join(senaryo.get("etiketler", []))]
    yol.write_text("\n".join(satirlar) + "\n", encoding="utf-8")


def satirla(metin: str, font, genislik: int):
    """Metni en fazla iki dengeli satıra böler."""
    if font.getlength(metin) <= genislik * 0.62:
        return [metin]
    kelimeler = metin.split()
    en_iyi = min(range(1, len(kelimeler)),
                 key=lambda i: abs(font.getlength(" ".join(kelimeler[:i])) - font.getlength(" ".join(kelimeler[i:]))))
    return [" ".join(kelimeler[:en_iyi]), " ".join(kelimeler[en_iyi:])]


def yazi_katmani(satirlar, font, renk=(255, 255, 255), kontur=4, aralik=1.25):
    """Konturlu ve gölgeli yazıyı saydam bir katman olarak çizer."""
    yuk = int(font.size * aralik)
    gen = int(max(font.getlength(s) for s in satirlar)) + 40
    kat = Image.new("RGBA", (gen, yuk * len(satirlar) + 30), (0, 0, 0, 0))
    golge = Image.new("RGBA", kat.size, (0, 0, 0, 0))
    for katman, dolgu, kaydir in ((golge, (0, 0, 0, 170), 4), (kat, renk + (255,), 0)):
        ciz = ImageDraw.Draw(katman)
        for i, s in enumerate(satirlar):
            x = (gen - font.getlength(s)) / 2
            ciz.text((x + kaydir, 10 + i * yuk + kaydir), s, font=font, fill=dolgu,
                     stroke_width=kontur, stroke_fill=(0, 0, 0, dolgu[3]))
    golge = golge.filter(ImageFilter.GaussianBlur(5))
    golge.alpha_composite(kat)
    return golge


def etiket_katmani(metin: str):
    font = ImageFont.truetype(YAZI, 34)
    gen = int(font.getlength(metin)) + 56
    kat = Image.new("RGBA", (gen, 64), (0, 0, 0, 0))
    ciz = ImageDraw.Draw(kat)
    ciz.rounded_rectangle((0, 0, gen - 1, 63), radius=10, fill=(12, 10, 8, 200))
    ciz.rectangle((0, 0, 7, 63), fill=(214, 164, 62, 255))
    ciz.text((30, 32), metin, font=font, fill=(245, 240, 230, 255), anchor="lm")
    return kat


def soluk(kat: Image.Image, oran: float) -> Image.Image:
    if oran >= 0.999:
        return kat
    kopya = kat.copy()
    kopya.putalpha(kat.getchannel("A").point(lambda a: int(a * oran)))
    return kopya


# ---------------------------------------------------------------- görüntü
def sabit_katman():
    """Köşe karartması ve altyazı okunurluğu için alt gölge."""
    yy, xx = np.mgrid[0:Y, 0:G].astype(np.float32)
    uzak = np.sqrt(((xx - G / 2) / (G / 2)) ** 2 + ((yy - Y / 2) / (Y / 2)) ** 2)
    kose = np.clip((uzak - 0.75) / 0.75, 0, 1) ** 1.6 * 150
    alt = np.clip((yy - Y * 0.68) / (Y * 0.32), 0, 1) ** 1.3 * 175
    alfa = np.clip(kose + alt, 0, 235).astype(np.uint8)
    kat = np.zeros((Y, G, 4), dtype=np.uint8)
    kat[..., 3] = alfa
    return Image.fromarray(kat, "RGBA")


def sigdir_tuvali(gorsel: Image.Image) -> Image.Image:
    """Görseli kırpmadan, kendi bulanık kopyasının üzerinde 16:9 tuvale yerleştirir."""
    tg, ty = 2880, 1620
    olcek = max(tg / gorsel.width, ty / gorsel.height)
    zemin = gorsel.resize((int(gorsel.width * olcek) + 1, int(gorsel.height * olcek) + 1), Image.BICUBIC)
    zemin = zemin.crop(((zemin.width - tg) // 2, (zemin.height - ty) // 2, (zemin.width + tg) // 2, (zemin.height + ty) // 2))
    zemin = Image.blend(zemin.filter(ImageFilter.GaussianBlur(45)), Image.new("RGB", (tg, ty), (14, 11, 8)), 0.62)
    olcek = min(ty * 0.68 / gorsel.height, tg * 0.8 / gorsel.width, 2.0 * tg / G)
    on = gorsel.resize((int(gorsel.width * olcek), int(gorsel.height * olcek)), Image.LANCZOS)
    x, y = (tg - on.width) // 2, int(ty * 0.43 - on.height / 2)  # altyazıya yer bırakmak için biraz yukarıda
    golge = Image.new("RGBA", (tg, ty), (0, 0, 0, 0))
    ImageDraw.Draw(golge).rectangle((x - 6, y + 10, x + on.width + 26, y + on.height + 36), fill=(0, 0, 0, 200))
    zemin = zemin.convert("RGBA")
    zemin.alpha_composite(golge.filter(ImageFilter.GaussianBlur(28)))
    zemin = zemin.convert("RGB")
    ImageDraw.Draw(zemin).rectangle((x - 5, y - 5, x + on.width + 4, y + on.height + 4), fill=(236, 228, 210))
    zemin.paste(on, (x, y))
    return zemin


def klipleri_hazirla(klasor: pathlib.Path):
    """cekimler.json'daki klipleri 1920x1080, 30 fps ham karelere çevirir (işçi süreçler bellek eşlemeyle okur)."""
    plan = json.loads((klasor / "cekimler.json").read_text(encoding="utf-8"))["cekimler"]
    gecici = klasor / "_gecici"
    gecici.mkdir(exist_ok=True)
    for ad in sorted({c["klip"] for c in plan if c.get("klip")}):
        hedef = gecici / f"klip_{ad}.rgb"
        if not (klasor / "klipler" / f"{ad}.mp4").exists():
            print(f"UYARI: klipler/{ad}.mp4 yok, o çekimde görsel kullanılacak")
            continue
        if not hedef.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(klasor / "klipler" / f"{ad}.mp4"), "-an", "-vf",
                            f"scale={G}:{Y}:force_original_aspect_ratio=increase:flags=lanczos,crop={G}:{Y},fps={FPS}",
                            "-pix_fmt", "rgb24", "-f", "rawvideo", str(hedef)], check=True)


class Sahne:
    """Bir video klasörünün tüm çizim verisi; her işçi süreç kendi kopyasını kurar."""

    def __init__(self, klasor: pathlib.Path):
        self.klasor = klasor
        self.cumleler, self.toplam, self.kayit, self.senaryo = cizelge(klasor)
        self.plan = cekimleri_kur(klasor, self.cumleler, self.toplam)
        self.alt = altyazilar(self.cumleler)
        self.kare_sayisi = int(self.toplam * FPS)
        self._gorsel, self._kat, self._klip = {}, {}, {}
        self.sabit = sabit_katman()
        self.siyah = Image.new("RGB", (G, Y), (0, 0, 0))
        self.f_alt = ImageFont.truetype(YAZI, 50)

    def gorsel(self, c):
        anahtar = (c["gorsel"], c.get("kip"))
        if anahtar not in self._gorsel:
            yol = next((self.klasor / "gorseller").glob(c["gorsel"] + ".*"))
            g = Image.open(yol).convert("RGB")
            self._gorsel[anahtar] = sigdir_tuvali(g) if c.get("kip") == "sigdir" else g
        return self._gorsel[anahtar]

    def katman(self, anahtar, uret):
        if anahtar not in self._kat:
            self._kat[anahtar] = uret()
        return self._kat[anahtar]

    def klip_kare(self, c, t):
        """Klipli çekimde t anındaki kare. Klip çekimden kısaysa çekime yayılacak kadar yavaşlatılır."""
        ad = c["klip"]
        if ad not in self._klip:
            yol = self.klasor / "_gecici" / f"klip_{ad}.rgb"
            self._klip[ad] = np.memmap(yol, dtype=np.uint8, mode="r").reshape(-1, Y, G, 3)
        kareler = self._klip[ad]
        uzunluk, sure = len(kareler) / FPS, c["bit"] - c["bas"]
        hiz = min(1.0, uzunluk / sure)
        i = min(int((t - c["bas"]) * FPS * hiz), len(kareler) - 1)
        return Image.fromarray(np.ascontiguousarray(kareler[max(i, 0)]))

    def kamera(self, c, t):
        """t anında c çekiminin görüntüsü (kamera hareketi uygulanmış, 1920x1080)."""
        if c.get("klip") and (self.klasor / "_gecici" / f"klip_{c['klip']}.rgb").exists():
            kare = self.klip_kare(c, t)
            return Image.blend(kare, self.siyah, c["karart"]) if c.get("karart") else kare
        g = self.gorsel(c)
        p = (t - c["bas"]) / (c["bit"] - c["bas"])
        p = p * p * (3 - 2 * p)  # yumuşak başlayıp yumuşak biten kamera hareketi
        cx, cy, w = (a + (b - a) * p for a, b in zip(c.get("a", [0.5, 0.5, 1.0]), c.get("b", [0.5, 0.5, 0.85])))
        gen = min(w, 1.0, g.height * 16 / 9 / g.width) * g.width
        yuk = gen * 9 / 16
        x0 = min(max(cx * g.width - gen / 2, 0), g.width - gen)
        y0 = min(max(cy * g.height - yuk / 2, 0), g.height - yuk)
        kare = g.resize((G, Y), Image.BICUBIC, box=(x0, y0, x0 + gen, y0 + yuk))
        if c.get("karart"):
            kare = Image.blend(kare, self.siyah, c["karart"])
        return kare

    def kare(self, n: int) -> Image.Image:
        t = n / FPS
        k = next((i for i, c in enumerate(self.plan) if t < c["bit"]), len(self.plan) - 1)
        c = self.plan[k]
        kare = self.kamera(c, t)
        if k > 0 and t - c["bas"] < GECIS:  # önceki çekimden yumuşak geçiş
            kare = Image.blend(self.kamera(self.plan[k - 1], t), kare, (t - c["bas"]) / GECIS)
        kare.paste(self.sabit, (0, 0), self.sabit)

        gir = min((t - c["bas"]) / 0.5, 1.0)
        cik = min((c["bit"] - t) / 0.4, 1.0) if k < len(self.plan) - 1 else 1.0
        if c.get("etiket"):
            kat = soluk(self.katman(("e", c["etiket"]), lambda: etiket_katmani(c["etiket"])), max(min(gir, cik), 0))
            kare.paste(kat, (70, 64), kat)
        if c.get("baslik"):
            b = c["baslik"]
            buyuk = self.katman(("b", b["buyuk"]), lambda: yazi_katmani(
                [b["buyuk"]], ImageFont.truetype(YAZI_KALIN, 150 if len(b["buyuk"]) < 14 else 104), (244, 206, 106), 6))
            kucuk = self.katman(("k", b["kucuk"]), lambda: yazi_katmani(
                [b["kucuk"]], ImageFont.truetype(YAZI, 54 if len(b["kucuk"]) < 30 else 42), (240, 234, 222), 3))
            oran = max(min(min((t - c["bas"] - 0.3) / 0.7, 1.0), cik), 0)
            for kat, y in ((buyuk, 330), (kucuk, 330 + buyuk.height + 6)):
                kat = soluk(kat, oran)
                kare.paste(kat, ((G - kat.width) // 2, y), kat)

        a = next((a for a in self.alt if a["bas"] <= t < a["bit"]), None)
        if a:
            kat = self.katman(("a", a["yazi"]), lambda: yazi_katmani(satirla(a["yazi"], self.f_alt, G - 300), self.f_alt))
            kare.paste(kat, ((G - kat.width) // 2, Y - 78 - kat.height), kat)
        return kare


# ---------------------------------------------------------------- çıktı
def parca_uret(gorev):
    klasor, bas, bit, yol = gorev
    sahne = Sahne(klasor)
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{G}x{Y}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-threads", "2", str(yol)],
        stdin=subprocess.PIPE)
    for n in range(bas, bit):
        ff.stdin.write(sahne.kare(n).tobytes())
    ff.stdin.close()
    assert ff.wait() == 0
    return yol


def onizleme(sahne: Sahne, yol: pathlib.Path):
    """Her çekimin ortasından bir kare alıp tek sayfada toplar."""
    kareler = [sahne.kare(int((c["bas"] + c["bit"]) / 2 * FPS)).resize((480, 270), Image.BICUBIC) for c in sahne.plan]
    sutun = 4
    sayfa = Image.new("RGB", (sutun * 480, -(-len(kareler) // sutun) * 270), (20, 20, 20))
    for i, k in enumerate(kareler):
        sayfa.paste(k, (i % sutun * 480, i // sutun * 270))
    sayfa.save(yol, quality=85)


def kapak(sahne: Sahne, yol: pathlib.Path):
    """YouTube küçük resmi (1280x720), senaryo.json'daki "kapak" alanından:
    {"gorsel": "kapak", "buyuk": ["YILAN", "DEĞİL!"], "kucuk": "Sağır da değil", "konum": "sol"}"""
    k = sahne.senaryo["kapak"]
    g = Image.open(next((sahne.klasor / "gorseller").glob(k["gorsel"] + ".*"))).convert("RGB")
    olcek = max(1280 / g.width, 720 / g.height)
    g = g.resize((round(g.width * olcek), round(g.height * olcek)), Image.LANCZOS)
    kare = g.crop(((g.width - 1280) // 2, (g.height - 720) // 2, (g.width - 1280) // 2 + 1280, (g.height - 720) // 2 + 720))
    sol = k.get("konum", "sol") == "sol"
    yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
    uzaklik = xx if sol else 1280 - xx
    golge = np.zeros((720, 1280, 4), dtype=np.uint8)
    golge[..., 3] = (np.clip(1 - uzaklik / 820, 0, 1) ** 0.9 * 200).astype(np.uint8)
    golge = Image.fromarray(golge, "RGBA")
    kare.paste(golge, (0, 0), golge)
    ciz = ImageDraw.Draw(kare)
    buyuk = ImageFont.truetype(YAZI_KALIN, 150)
    while max(buyuk.getlength(s) for s in k["buyuk"]) > 640 and buyuk.size > 80:
        buyuk = ImageFont.truetype(YAZI_KALIN, buyuk.size - 6)
    kucuk = ImageFont.truetype(YAZI_KALIN, 58)
    renkler = [(255, 255, 255), (250, 204, 72)]
    y = 360 - (len(k["buyuk"]) * buyuk.size * 1.02 + (kucuk.size + 24 if k.get("kucuk") else 0)) / 2
    for i, satir in enumerate(k["buyuk"]):
        x = 56 if sol else 1280 - 56 - buyuk.getlength(satir)
        ciz.text((x, y), satir, font=buyuk, fill=renkler[i % 2], stroke_width=8, stroke_fill=(0, 0, 0))
        y += buyuk.size * 1.02
    if k.get("kucuk"):
        gen = kucuk.getlength(k["kucuk"]) + 44
        x = 56 if sol else 1280 - 56 - gen
        ciz.rounded_rectangle((x, y + 20, x + gen, y + 24 + kucuk.size + 18), radius=14, fill=(196, 52, 38))
        ciz.text((x + 22, y + 24), k["kucuk"], font=kucuk, fill=(255, 255, 255))
    kare.save(yol, quality=92)


def ses_yuksekligi_duzelt(video: pathlib.Path, hedef=-14.0, tepe=-2.5):
    """Tek geçişli loudnorm hedefin altında kalabiliyor; ölçüp farkı kazançla kapatır, tepeleri sınırlar (görüntüye dokunmaz)."""
    def olc(yol):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(yol), "-af", "ebur128=peak=true", "-f", "null", "-"],
                           capture_output=True, text=True)
        ozet = r.stderr[r.stderr.rfind("Summary:"):]
        import re as _re
        return (float(_re.search(r"I:\s+(-?[\d.]+) LUFS", ozet).group(1)),
                float(_re.search(r"Peak:\s+(-?[\d.]+) dBFS", ozet).group(1)))
    for _ in range(3):
        olculen, gercek_tepe = olc(video)
        fark = hedef - olculen
        # Kabul aralığı -16..-13 LUFS. Deney (16 Kasım 2026): tek geçiş -15,7 LUFS verip konuşmayı birebir korurken,
        # -14'e zorlamak için eklenen kazanç + sınırlayıcı + ikinci AAC kodlaması konuşma netliğini bozdu ("sağır"→"sahar").
        # YouTube kısık videoları yükseltmez, yalnızca yüksekleri kısar; 1-2 dB kısık olmak netlik kaybından iyidir.
        if -16.0 <= olculen <= -13.0 and gercek_tepe <= -1.0:
            return
        gecici = video.with_name("_ses_duzelt.mp4")
        sinir = 10 ** (tepe / 20)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-map", "0:v", "-map", "0:a", "-c:v", "copy",
                        "-af", f"volume={fark:.2f}dB,alimiter=limit={sinir:.4f}:level=disabled:attack=5:release=50,aresample=48000",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(gecici)], check=True)
        gecici.replace(video)


def main():
    klasor = KOK / sys.argv[1]
    if "--ses-duzelt" in sys.argv:  # yalnızca bitmiş videonun ses yüksekliğini düzelt
        ses_yuksekligi_duzelt(klasor / "video.mp4")
        return
    klipleri_hazirla(klasor)
    sahne = Sahne(klasor)
    if "--onizleme" in sys.argv:
        onizleme(sahne, klasor / "onizleme.jpg")
        return
    eksik = [i for i in range(len(sahne.cumleler)) if not list((klasor / "ses").glob(f"{i:03d}.*"))]
    assert not eksik, f"ses dosyası eksik cümleler: {eksik}"

    gecici = klasor / "_gecici"
    srt_yaz(sahne.alt, klasor / "altyazi.srt")
    kapak(sahne, klasor / "kapak.jpg")
    yukleme_yaz(sahne.senaryo, sahne.cumleler, klasor / "yukleme.txt")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", str(gecici / "ses.wav")],
                   input=sahne.kayit.tobytes(), check=True)

    isci = 4
    sinir = [sahne.kare_sayisi * i // isci for i in range(isci + 1)]
    gorevler = [(klasor, sinir[i], sinir[i + 1], gecici / f"p{i}.mp4") for i in range(isci)]
    with mp.Pool(isci) as havuz:
        parcalar = havuz.map(parca_uret, gorevler)
    (gecici / "liste.txt").write_text("".join(f"file '{p.name}'\n" for p in parcalar))
    amb = sahne.senaryo.get("ambiyans")
    girdiler, filtre = ["-i", str(gecici / "ses.wav")], "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
    if amb:
        son = sahne.toplam - 3
        girdiler += ["-stream_loop", "-1", "-i", str((klasor / amb["dosya"]).resolve())]
        # Anlatıcı konuşurken doğa sesi otomatik kısılır (ducking); yalnızca duraklarda, girişte ve kapanışta duyulur.
        # Deney (16 Kasım 2026): sabit seviyedeki kuş sesi, konuşma tanımada "sağır"ı "sahar" yaptırıyordu.
        filtre = ("[1:a]aresample=48000,aformat=channel_layouts=mono,asplit=2[ses][yan];"
                  f"[2:a]aresample=48000,aformat=channel_layouts=mono,highpass=f=120,volume={amb.get('seviye', 0.07)},"
                  f"afade=t=in:d=2,afade=t=out:st={son:.2f}:d=3[amb0];"
                  "[amb0][yan]sidechaincompress=threshold=0.003:ratio=20:attack=5:release=600:makeup=1[amb];"
                  "[ses][amb]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(gecici / "liste.txt"), *girdiler,
         "-filter_complex", filtre, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", str(klasor / "video.mp4")], check=True)
    ses_yuksekligi_duzelt(klasor / "video.mp4")
    for d in gecici.iterdir():
        d.unlink()
    gecici.rmdir()
    print(f"Hazır: {klasor / 'video.mp4'}  ({sahne.toplam:.0f} sn)")


if __name__ == "__main__":
    main()
