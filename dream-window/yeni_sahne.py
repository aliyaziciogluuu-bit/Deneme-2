"""Yeni bir sahneyi baştan sona otomatik hazırlar: görselden pencere, ateş ve ışıkları bulur, sahne.json'u yazar,
videoları, Shorts'ları, 4K paketini, küçük resmi ve yükleme metinlerini üretir, hepsini tekrar testinden geçirir.

Adımlar:
  1) Taslak (birkaç dakika):  python yeni_sahne.py taslak 13-forest-cabin gorsel.png --yagis kar --ad "Forest Cabin"
     → 13-forest-cabin/ klasörü, sahne.json, algilama.jpg (bulunan bölgeler), onizleme.jpg (canlandırılmış kareler)
     Algılamayı kontrol et; gerekirse sahne.json'da kutuları düzelt ve taslağı --yeniden ile tekrar çalıştır.
  2) Üretim (birkaç saat):    python yeni_sahne.py uret 13-forest-cabin
     → video_3saat.mp4 (1080p/720p, gönderilebilir boyutta), shorts.mp4, shorts2.mp4, kapak_3saat.jpg,
       yukleme_3saat.txt, shorts(2)_yukleme.txt, sahne_4k.png ve paket_<ad>_4K/ (bilgisayarda birleştirilecek parçalar)
     Her video kontrol.py ile test edilir; tekrar eden video "SORUN" olarak raporlanır.

Yükleme metinlerindeki öykü kısmı [ÖYKÜ] olarak bırakılır; Claude her sahne için ayrı öykü yazar.
Mevcut bir ateş klibini yeni ocağa oturtmak için (ücretsiz): --ates-klip 05-snowy-library (açık şömine) ya da 06-rainy-cafe (camlı soba).
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

import cv2
import numpy as np

KOK = pathlib.Path(__file__).parent
PY = sys.executable


# ---------------------------------------------------------------- algılama
def bilesenler(maske, en_az):
    n, etiket, ist, merkez = cv2.connectedComponentsWithStats(maske.astype(np.uint8), 8)
    return [(ist[i], merkez[i], etiket == i) for i in range(1, n) if ist[i, cv2.CC_STAT_AREA] >= en_az]


def kutu_al(ist):
    x, y, w, h = ist[cv2.CC_STAT_LEFT], ist[cv2.CC_STAT_TOP], ist[cv2.CC_STAT_WIDTH], ist[cv2.CC_STAT_HEIGHT]
    return [int(x), int(y), int(x + w), int(y + h)]


def ates_bul(gorsel):
    """Alev renginin (çok parlak, doygun turuncu-sarı) en yoğun olduğu bölge. (yoğunluk, iç kutu) döndürür.
    Lamba ve mumlar da parlak olduğu için yoğunluk tek başına ateşin varlığını kesin söylemez; --ates ile belirtilmesi önerilir."""
    H, W = gorsel.shape[:2]
    h, s, v = cv2.split(cv2.cvtColor(gorsel, cv2.COLOR_BGR2HSV))
    alev = ((v > 235) & (s > 140) & (h >= 8) & (h <= 30)).astype(np.float32)
    yog = cv2.boxFilter(alev, -1, (140 * W // 1672, 140 * W // 1672))
    y, x = np.unravel_index(yog.argmax(), yog.shape)
    cekirdek = ((v > 240) & (s > 120) & (h >= 5) & (h <= 32)).astype(np.uint8)
    r = 230 * W // 1672
    x0, y0, x1, y1 = max(x - r, 0), max(y - r, 0), min(x + r, W), min(y + r, H)
    alt = cv2.morphologyEx(cekirdek[y0:y1, x0:x1], cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    n, etiket, ist, _ = cv2.connectedComponentsWithStats(alt, 8)
    adaylar = [i for i in range(1, n) if ist[i, cv2.CC_STAT_AREA] > 300]
    if not adaylar:
        return 0.0, None
    i = min(adaylar, key=lambda i: ((ist[i, 0] + ist[i, 2] / 2 - (x - x0)) ** 2 + (ist[i, 1] + ist[i, 3] / 2 - (y - y0)) ** 2) / ist[i, 4] ** 0.5)
    bx, by, bw, bh = ist[i, :4]
    return float(yog.max()), [int(x0 + bx), int(y0 + by), int(x0 + bx + bw), int(y0 + by + bh)]


def algila(gorsel, ates="oto", susler=False):
    """Kaynak görsel pikselinde pencere kutuları, ateş, ışıklar ve süs ışıkları. ates: "oto", "var" ya da "yok"."""
    H, W = gorsel.shape[:2]
    f = gorsel.astype(np.float32) / 255
    b, g, r = cv2.split(f)
    parlak = 0.114 * b + 0.587 * g + 0.299 * r
    sonuc = {}

    # pencere: soğuk renkli (mavi gece, kar, yağmur) geniş bölgeler; oda sıcak renkli
    soguk = ((r - b) < 0.0).astype(np.uint8)
    k = max(W // 80, 5)
    soguk = cv2.morphologyEx(soguk, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k * 2, k * 2)))
    soguk = cv2.morphologyEx(soguk, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    acik_soguk = (parlak > 0.45) & ((b - r) > 0)                     # ay, kar, yağmur çizgileri: gerçek camda bulunur, gölgede kalan rafta yok
    adaylar = bilesenler(soguk, W * H * 0.02)
    pencere = [c for c in adaylar if acik_soguk[c[2]].mean() > 0.008]
    if not pencere and adaylar:                                        # çok karanlık gece camı: en büyük soğuk bölge pencere sayılır
        pencere = [max(adaylar, key=lambda c: c[0][cv2.CC_STAT_AREA])]
    pencere = sorted(pencere, key=lambda c: -c[0][cv2.CC_STAT_AREA])[:3]
    sonuc["kutular"] = [kutu_al(c[0]) for c in pencere]
    cam_maske = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in sonuc["kutular"]:
        cam_maske[y0:y1, x0:x1] = True

    # ateş: alev renginin en yoğun olduğu bölge
    yogunluk, ic = ates_bul(gorsel)
    sonuc["ates_yogunluk"] = round(yogunluk, 3)
    if ic and (ates == "var" or (ates == "oto" and yogunluk > 0.38)):
        x0, y0, x1, y1 = ic
        w, h = x1 - x0, y1 - y0
        sonuc["ates"] = {"kutu": [max(x0 - w // 4, 0), max(y0 - h // 3, 0), min(x1 + w // 4, W), min(y1 + h // 6, H)],
                         "ic": [max(x0 - w // 10, 0), max(y0 - h // 10, 0), min(x1 + w // 10, W), min(y1 + h // 20, H)],
                         "taban": int(y1), "tepe": int(y0), "olcek": round(float(np.clip(h / 220, 0.6, 1.4)), 2), "kivilcim": 14}
        ates_maske = np.zeros((H, W), bool)
        ax0, ay0, ax1, ay1 = sonuc["ates"]["kutu"]
        ates_maske[ay0:ay1, ax0:ax1] = True
    else:
        ates_maske = np.zeros((H, W), bool)

    # ışıklar: parlak, sıcak renkli lamba ve mumlar (ateş ve cam dışında); ateşin odaya vuran geniş ışığı ayrıca
    isik = ((parlak > 0.8) & (r - b > 0.12) & ~cam_maske & ~ates_maske).astype(np.uint8)
    isik = cv2.dilate(isik, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    lambalar = sorted(bilesenler(isik, 40), key=lambda c: -c[0][cv2.CC_STAT_AREA])[:7]
    isiklar = []
    if "ates" in sonuc:
        a = sonuc["ates"]["ic"]
        isiklar.append({"x": (a[0] + a[2]) // 2, "y": (a[1] + a[3]) // 2, "sigma": 340, "genlik": 0.085})
    for ist, merkez, _ in lambalar:
        boy = max(ist[cv2.CC_STAT_WIDTH], ist[cv2.CC_STAT_HEIGHT])
        isiklar.append({"x": int(merkez[0]), "y": int(merkez[1]), "sigma": int(np.clip(boy * 1.5, 30, 90)), "genlik": 0.1})
    sonuc["isiklar"] = isiklar or [{"x": W // 4, "y": H // 2, "sigma": 200, "genlik": 0.04}]

    # süs ışıkları (yılbaşı ağacı, girlanda): küçük parlak noktaların yoğun olduğu bölgeler
    sonuc["pirilti"] = []
    if not susler:                                                     # yalnızca Noel sahnelerinde (yanlışlıkla masa, halı parlamasın)
        return sonuc
    nokta = ((parlak > 0.72) & (r - b > 0.08) & ~ates_maske & ~(cam_maske & (r - b < 0.3))).astype(np.uint8)   # camdaki ay ve kar parlamasın
    yogunluk = np.zeros((H, W), np.float32)
    for ist, merkez, _ in bilesenler(nokta, 3):
        if ist[cv2.CC_STAT_AREA] <= 120:
            yogunluk[int(merkez[1]), int(merkez[0])] += 1
    yogunluk = cv2.GaussianBlur(yogunluk, (0, 0), W / 60) * (W / 60) ** 2 * 2 * np.pi
    kume = (yogunluk > 10).astype(np.uint8)
    sonuc["pirilti"] = [{"kutu": kutu_al(c[0]), "genlik": 0.3, "esik": 0.7, "sicak": 0.1}
                        for c in bilesenler(kume, W * H * 0.004) if c[0][cv2.CC_STAT_AREA] < W * H * 0.05][:4]
    return sonuc


def algilama_resmi(gorsel, a, yol):
    """Bulunan bölgeleri görsel üzerinde gösterir: mavi cam, kırmızı ateş, sarı ışık, mor süs ışığı."""
    g = gorsel.copy()
    for x0, y0, x1, y1 in a["kutular"]:
        cv2.rectangle(g, (x0, y0), (x1, y1), (255, 160, 0), 4)
    if "ates" in a:
        x0, y0, x1, y1 = a["ates"]["kutu"]
        cv2.rectangle(g, (x0, y0), (x1, y1), (0, 0, 255), 4)
    for l in a["isiklar"]:
        cv2.circle(g, (l["x"], l["y"]), l["sigma"] // 3, (0, 230, 255), 3)
    for p in a["pirilti"]:
        x0, y0, x1, y1 = p["kutu"]
        cv2.rectangle(g, (x0, y0), (x1, y1), (255, 0, 200), 3)
    cv2.imwrite(str(yol), g, [cv2.IMWRITE_JPEG_QUALITY, 85])


# ---------------------------------------------------------------- yardımcılar
def calistir(*komut, log=None):
    print("$", " ".join(map(str, komut)), flush=True)
    with open(log, "w") if log else open("/dev/null", "w") as f:
        r = subprocess.run(list(map(str, komut)), cwd=KOK, stdout=f if log else None, stderr=subprocess.STDOUT if log else None)
    if r.returncode:
        raise SystemExit(f"Hata: {' '.join(map(str, komut))}" + (f" (ayrıntı: {log})" if log else ""))


def kontrol(video, en_az=60, sure=240, bolge=None):
    komut = [PY, KOK / "kontrol.py", video, "--sure", str(sure), "--en-az", str(en_az)] + (["--bolge", *map(str, bolge)] if bolge else [])
    r = subprocess.run(list(map(str, komut)), capture_output=True, text=True)
    satir = (r.stdout.strip().splitlines() or ["?"])[-1]
    return r.returncode == 0, satir


def sure_sn(video):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                                capture_output=True, text=True).stdout or 0)


def kapak(klasor, satirlar, cikti):
    """Diğer videolarla aynı stilde küçük resim: yazı kutusu görselin daha sade yarısına."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    K = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
    N = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
    renk = [(244, 206, 106), (255, 244, 220), (244, 206, 106), (230, 236, 245)]
    im = Image.open(klasor / "sahne.png").convert("RGB").resize((1280, 720), Image.LANCZOS)
    gri = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY)
    kenar = cv2.Canny(gri, 80, 160)
    sol, sag = kenar[400:, :640].mean(), kenar[400:, 640:].mean()
    kutu = (40, 400, 720, 690) if sol <= sag else (560, 400, 1240, 690)
    cx = (kutu[0] + kutu[2]) // 2
    kat = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(kat).rounded_rectangle(kutu, radius=18, fill=(6, 10, 18, 190))
    im = Image.alpha_composite(im.convert("RGBA"), kat.filter(ImageFilter.GaussianBlur(14))).convert("RGB")
    d = ImageDraw.Draw(im)
    y = kutu[1] + 8
    for (metin, font, boy, ara), rk in zip([(satirlar[0], K, 66, 82), (satirlar[1], K, 58, 76), (satirlar[2], N, 34, 52), (satirlar[3], N, 30, 0)], renk):
        fnt = ImageFont.truetype(font, boy)
        while d.textlength(metin, font=fnt) > (kutu[2] - kutu[0]) - 30 and boy > 20:
            boy -= 2
            fnt = ImageFont.truetype(font, boy)
        d.text((cx - d.textlength(metin, font=fnt) / 2, y), metin, font=fnt, fill=rk, stroke_width=4, stroke_fill=(0, 0, 0))
        y += ara
    im.save(cikti, quality=92)


# ---------------------------------------------------------------- adımlar
def taslak(g):
    klasor = KOK / g.klasor
    ayar_yolu = klasor / "sahne.json"
    if g.yeniden:
        ayar = json.loads(ayar_yolu.read_text(encoding="utf-8"))
    else:
        if klasor.exists() and ayar_yolu.exists():
            raise SystemExit(f"{klasor} zaten var; ayarları korumak için --yeniden kullan")
        (klasor / "ses_kaynak").mkdir(parents=True, exist_ok=True)
        gorsel = cv2.imread(str(g.gorsel))
        if gorsel is None:
            raise SystemExit(f"Görsel okunamadı: {g.gorsel}")
        if gorsel.shape[1] != 1672:                                     # diğer sahnelerle aynı ölçek (sahne.json koordinatları)
            gorsel = cv2.resize(gorsel, (1672, round(1672 * gorsel.shape[0] / gorsel.shape[1])), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(klasor / "sahne.png"), gorsel)
        a = algila(gorsel, g.ates, susler=g.noel)
        ad = g.ad or klasor.name.split("-", 1)[-1].replace("-", " ").title()
        ayar = {"gorsel": "sahne.png",
                "acilis_yazi": {"baslik": "Dream Window", "alt": [x for x in ["CHRISTMAS" if g.noel else None, "SNOW" if g.yagis == "kar" else "RAIN",
                                                                             "FIREPLACE" if "ates" in a else None, "RELAXATION", "SLEEP"] if x]},
                "yagis": g.yagis, "cam": {"kutular": a["kutular"], "esik": 0.0, "temizlik": 5},
                "isiklar": a["isiklar"], "dongu_sn": 96, "ad": ad}
        if a["pirilti"]:
            ayar["pirilti"] = a["pirilti"]
        ses = {}
        if g.yagis == "yagmur":
            shutil.copy(KOK / "06-rainy-cafe/ses_kaynak/yagmur.mp3", klasor / "ses_kaynak/yagmur.mp3")
            ses.update(zemin="ses_kaynak/yagmur.mp3", zemin_bas=20, zemin_duzey=0.08,
                       zemin_ek=["../sesler/yagmur_cam.mp3", "../sesler/yagmur_hafif.mp3"])   # ortak kütüphaneden farklı yağmurlar
        if "ates" in a:
            ayar["ates"] = a["ates"]
            shutil.copy(KOK / "05-snowy-library/ses_kaynak/ates.ogg", klasor / "ses_kaynak/ates.ogg")
            import random                                              # her yeni sahneye kütüphaneden farklı bir ateş karışımı
            havuz = ["../sesler/ates_somine_yumusak.mp3", "../sesler/ates_somine_gur.mp3", "../sesler/ates_gece.mp3", "ses_kaynak/ates.ogg"]
            random.Random(klasor.name).shuffle(havuz)
            ses.update(ates=havuz[:3], ates_katman=3, ates_duzey=0.18, ates_tavan=0.17, ates_govde=3.3, ates_denge=[0.9, 0.5])
        ayar["ses"] = ses
        if g.ates_klip and "ates" in a:                                 # mevcut gerçek ateş klibini yeni ocağa oturt (ücretsiz)
            kaynak = KOK / g.ates_klip
            k = json.loads((kaynak / "sahne.json").read_text(encoding="utf-8"))["ates_klip"]
            shutil.copy(kaynak / k["dosya"], klasor / "ates_klip.mp4")
            x0, y0, x1, y1 = a["ates"]["kutu"]
            kx0, ky0, kx1, ky1 = k["kutu"]
            fx0, fy0, fx1, fy1 = json.loads((kaynak / "sahne.json").read_text(encoding="utf-8"))["ates"]["kutu"]
            # kaynak klipte ateş kutusunun kapladığı oran korunarak yeni ocağa ölçeklenir
            sx, sy = (x1 - x0) / (fx1 - fx0), (y1 - y0) / (fy1 - fy0)
            ayar["ates_klip"] = {"dosya": "ates_klip.mp4", "kaynak": g.ates_klip, "karisik": True,
                                 "kutu": [int(x0 - (fx0 - kx0) * sx), int(y0 - (fy0 - ky0) * sy), int(x1 + (kx1 - fx1) * sx), int(y1 + (ky1 - fy1) * sy)]}
        W = 1672
        cx = [(k[0] + k[2]) // 2 for k in a["kutular"]] or [W // 2]
        fx = [(a["ates"]["kutu"][0] + a["ates"]["kutu"][2]) // 2] if "ates" in a else []
        noktalar = sorted(cx + fx)
        ayar["shorts"] = {"bas": int(noktalar[0]), "son": int(noktalar[-1]) if len(noktalar) > 1 else int(min(noktalar[0] + 500, W - 300)),
                          "tur": 2, "baslik": ad, "alt": "Snowfall & Crackling Fireplace" if g.yagis == "kar" else "Rain & Crackling Fireplace",
                          "ses_kazanc": 7.5 if g.yagis == "kar" else 1.5}
        if "ates" not in a:
            ayar["shorts"]["alt"] = "Snowfall at Night" if g.yagis == "kar" else "Gentle Rain at Night"
        ayar["shorts2"] = dict(ayar["shorts"], bas=ayar["shorts"]["son"], son=ayar["shorts"]["bas"],
                               baslik=f"POV: {ad.lower()} on a {'snowy' if g.yagis == 'kar' else 'rainy'} night", alt="sleep here tonight")
        ayar_yolu.write_text(json.dumps(ayar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        algilama_resmi(gorsel, a, klasor / "algilama.jpg")
        print(f"Algılandı: {len(a['kutular'])} pencere, {'ateş var' if 'ates' in a else 'ateş yok'} (alev yoğunluğu {a['ates_yogunluk']}), "
              f"{len(a['isiklar'])} ışık, {len(a['pirilti'])} süs ışığı bölgesi")
        if g.ates == "oto":
            print("Not: ateşin varlığı otomatik tahmin edildi; şömine varsa --ates var, yoksa --ates yok ile kesinleştir.")
    calistir(PY, "uret.py", g.klasor, "--kare")
    print(f"Kontrol et: {klasor / 'algilama.jpg'} ve {klasor / 'onizleme.jpg'}")


def uret(g):
    klasor = KOK / g.klasor
    ayar = json.loads((klasor / "sahne.json").read_text(encoding="utf-8"))
    ad = ayar.get("ad", klasor.name)
    gunluk_ad = klasor.name.split("-", 1)[-1].replace("-", "_")
    log = lambda s: KOK / klasor / f"_log_{s}.txt"
    rapor = []

    # 1) 3 saatlik 1080p/720p video: 400 MiB gönderme sınırına sığana kadar ses bit hızı düşürülür
    if not (klasor / "video_3saat.mp4").exists() or g.zorla:
        calistir(PY, "uret.py", g.klasor, "--dakika", str(g.dakika), "--720", "--hevc", "--crf", "36", "--ses-kbps", "96", "--cikti", "video_3saat.mp4", log=log("1080"))
    for kbps in (80, 64):
        if (klasor / "video_3saat.mp4").stat().st_size <= 395 * 2 ** 20:
            break
        calistir(PY, "uret.py", g.klasor, "--sesdegistir", "--cikti", "video_3saat.mp4", "--ses-kbps", str(kbps), log=log("ses"))
    tamam, satir = kontrol(klasor / "video_3saat.mp4")
    sn = sure_sn(klasor / "video_3saat.mp4")
    rapor.append(f"3 saatlik video: {(klasor / 'video_3saat.mp4').stat().st_size / 2 ** 20:.0f} MiB, {sn / 3600:.2f} saat · {satir}")
    if sn < g.dakika * 60:
        rapor.append("SORUN: video 3 saatten kısa")

    # 2) Shorts (iki tane), her biri kendi süresince tekrarsız
    for anahtar in ("shorts", "shorts2"):
        if anahtar in ayar and (not (klasor / f"{anahtar}.mp4").exists() or g.zorla):
            calistir(PY, "shorts.py", g.klasor, anahtar, log=log(anahtar))
        if (klasor / f"{anahtar}.mp4").exists():
            rapor.append(f"{anahtar}: {kontrol(klasor / f'{anahtar}.mp4', en_az=48, sure=48)[1]}")

    # 3) küçük resim ve yükleme metinleri (öykü Claude tarafından eklenir)
    kar = ayar.get("yagis") == "kar"
    ates = "ates" in ayar
    if not (klasor / "kapak_3saat.jpg").exists() or g.zorla:
        alt = " & ".join(x for x in ["Snowfall" if kar else "Rain", "Fireplace" if ates else None] if x)
        kapak(klasor, ["3 HOURS", ad.upper(), alt, "DEEP SLEEP  •  RELAXATION"], klasor / "kapak_3saat.jpg")
    import json as _j                                                   # küçük resim seçenekleri B ve C (Test et ve karşılaştır)
    metin_yolu = KOK / "kanal" / "kapak_metinleri.json"
    metinler = _j.loads(metin_yolu.read_text(encoding="utf-8"))
    if g.klasor not in metinler:
        metinler[g.klasor] = [ad.upper(), " & ".join(x for x in ["Snowfall" if kar else "Rain", "Fireplace" if ates else None] if x)]
        metin_yolu.write_text(_j.dumps(metinler, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    calistir(PY, "kapak.py", g.klasor)
    if not (klasor / "yukleme_3saat.txt").exists():
        sesler = " & ".join(x for x in ["Snowfall" if kar else "Rain Sounds", "Crackling Fireplace" if ates else None] if x)
        (klasor / "yukleme_3saat.txt").write_text(
            f"TITLE\n3 Hours {ad} {'❄️' if kar else '🌧️'}{'🔥' if ates else ''} {sesler} for Deep Sleep\n\nDESCRIPTION\nWelcome to Dream Window 🌙\n\n"
            f"[ÖYKÜ]\n\n• 3 hours, no music, no talking\n• Soft, quiet {'winter' if kar else 'rainy'} night atmosphere\n"
            "• Best with headphones or a speaker at low volume\n\n🔔 Subscribe for new rain, snow, fireplace and nature ambience every week.\n\n"
            "The scene is an AI-generated illustration animated for this video.\n\n"
            + ("Sound credits:\n• \"Campfire sound ambience\" by Glaneur de sons, CC BY 3.0 – https://commons.wikimedia.org/wiki/File:Campfire_sound_ambience.ogg\n\n" if ates else "")
            + f"#{'snowfall' if kar else 'rainsounds'} #sleepambience #cozy #relaxing #dreamwindow\n\nTAGS\n3 hours {ad.lower()}, "
            + f"{'snowfall ambience, winter night sleep' if kar else 'rain sounds, rainy night sleep'}, {'fireplace sounds, ' if ates else ''}"
            "sleep ambience, cozy ambience, relaxing sounds, deep sleep, long ambience video, dream window\n", encoding="utf-8")
    for anahtar in ("shorts", "shorts2"):
        if anahtar in ayar and not (klasor / f"{anahtar}_yukleme.txt").exists():
            a = ayar[anahtar]
            (klasor / f"{anahtar}_yukleme.txt").write_text(
                f"TITLE\n{a['baslik']} {'❄️' if kar else '🌧️'} {a['alt']} #shorts\n\nDESCRIPTION\n[KISA ÖYKÜ]\n\n"
                "The full 3-hour version is on the channel – subscribe so you don't miss new windows. 🔔\n\n"
                + ("Sound credits: \"Campfire sound ambience\" by Glaneur de sons, CC BY 3.0 – https://commons.wikimedia.org/wiki/File:Campfire_sound_ambience.ogg\n\n" if ates else "")
                + f"#{'snowfall' if kar else 'rain'} #sleepambience #cozy #shorts\n", encoding="utf-8")

    # 4) 4K: görseli büyüt (yaklaşık 0,005 $), parça paketini üret ve test et
    if not g.k4_yok:
        calistir(PY, "buyut4k.py", g.klasor, log=log("buyut"))
        paket = klasor / f"paket_{gunluk_ad}_4K"
        if not paket.exists() or g.zorla:
            calistir(PY, "uret.py", g.klasor, "--4k", "--hevc", "--crf", "26", "--dakika", str(g.dakika), "--ses-kbps", "128", "--paket", f"{gunluk_ad}_4K", log=log("4k"))
        gecici = KOK / f"_t4k_{gunluk_ad}.mp4"
        liste = KOK / f"_l4k_{gunluk_ad}.txt"
        liste.write_text("".join(f"file '{paket / 'dongu.mp4'}'\n" for _ in range(3)))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy", str(gecici)], check=True)
        satir = kontrol(gecici, sure=280)[1]
        gecici.unlink(); liste.unlink()
        boyut = sum(p.stat().st_size for p in paket.iterdir()) / 2 ** 20
        rapor.append(f"4K paket: {boyut:.0f} MiB · {satir}" + (" · UYARI: 400 MiB üstü, zip gönderilemez" if boyut > 395 else ""))

    print("\n".join(["", "RAPOR – " + ad] + rapor))
    if any("SORUN" in s for s in rapor):
        raise SystemExit("Tekrar testi veya süre kontrolü geçmedi: dosyaları gönderme, önce düzelt.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = p.add_subparsers(dest="adim", required=True)
    t = alt.add_parser("taslak")
    t.add_argument("klasor")
    t.add_argument("gorsel", nargs="?")
    t.add_argument("--yagis", choices=["kar", "yagmur"], default="kar")
    t.add_argument("--ad", help="İngilizce kısa ad, örn. 'Forest Cabin'")
    t.add_argument("--noel", action="store_true", help="açılış yazısına CHRISTMAS ekle")
    t.add_argument("--ates", choices=["oto", "var", "yok"], default="oto", help="sahnede şömine/soba var mı")
    t.add_argument("--ates-klip", help="ateş klibi alınacak mevcut sahne (ücretsiz), örn. 05-snowy-library")
    t.add_argument("--yeniden", action="store_true", help="mevcut sahne.json'u koru, yalnızca önizlemeyi yenile")
    u = alt.add_parser("uret")
    u.add_argument("klasor")
    u.add_argument("--zorla", action="store_true", help="var olan çıktıları yeniden üret")
    u.add_argument("--k4-yok", action="store_true", help="4K paketini atla")
    u.add_argument("--dakika", type=int, default=180, help="uzun video süresi (deneme için kısa verilebilir)")
    g = p.parse_args()
    if g.adim == "taslak" and not g.yeniden and not g.gorsel:
        p.error("taslak için görsel gerekli")
    (taslak if g.adim == "taslak" else uret)(g)


if __name__ == "__main__":
    main()
