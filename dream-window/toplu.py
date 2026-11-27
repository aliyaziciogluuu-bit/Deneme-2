"""Toplu içerik üretimi: bir fikir listesinden API ile sahne görselleri üretir, seçilenleri otomatik kurgular.

fikirler.json örneği (kanal/fikirler.json):
  [{"klasor": "13-forest-cabin", "ad": "Forest Cabin", "yagis": "kar", "ates": "var", "noel": false,
    "istem": "a small wooden cabin bedroom deep in a snowy pine forest, big window on the right, stone fireplace on the left"}]

Adımlar (her adım bir öncekinin çıktısını kullanır; istediğin yerde durup kontrol edebilirsin):
  1) python toplu.py gorseller --adet 2            → her fikir için 2 aday görsel (Replicate, Flux 1.1 Pro)
       Önce maliyeti gösterir; harcamak için --onay gerekir. adaylar/<klasor>/aday_N.png ve adaylar/secim.jpg
  2) fikirler.json'da her fikre "secim": N yaz (beğenilmeyen fikri "secim": 0 ile atla)
  3) python toplu.py taslak                        → seçilen görselleri yeni_sahne.py taslak ile hazırlar (algılama + önizleme)
  4) python toplu.py uret [--k4-yok]               → hepsini sırayla üretir (3 saatlik video, Shorts, küçük resim, 4K paket, tekrar testi)

Neden tek seferde her şeyi yapmıyor: YouTube seri üretilmiş, birbirinin aynı içeriği "özgün olmayan içerik" sayıp
para kazanmayı kapatabiliyor. Her görselin seçilmesi, algılamanın gözden geçirilmesi ve her videoya ayrı öykü yazılması
kanalın özgün kalmasını sağlar. Öyküler yükleme metninde [ÖYKÜ] olarak bırakılır; Claude her sahne için ayrı yazar.

API anahtarı ortamın ağ geçidi tarafından eklenir; bu betikte anahtar yoktur. Gönderme (POST) istekleri yeniden denenmez.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

import cv2
import numpy as np

KOK = pathlib.Path(__file__).parent
API = "https://api.replicate.com/v1"
MODELLER = {"pro": ("black-forest-labs/flux-1.1-pro", 0.04), "hizli": ("black-forest-labs/flux-schnell", 0.003)}
# kanalın görsel dili: diğer sahnelerle uyumlu olsun
STIL = ("Cozy interior at night seen from inside, wide 16:9 composition, a large window showing the outside scene, "
        "warm candle and lamp light inside, rich textures, detailed digital painting with photorealistic lighting, "
        "calm and peaceful mood, no people, no animals, no text, no watermark, no logo.")


def curl(*arg, cikti=None):
    yeniden = [] if "POST" in arg else ["--retry", "3"]
    komut = ["curl", "-sS", "-m", "300", *yeniden, *arg] + (["-o", str(cikti)] if cikti else [])
    r = subprocess.run(komut, capture_output=True, text=cikti is None, check=True)
    return None if cikti else json.loads(r.stdout)


def fikirleri_oku(yol):
    return json.loads(pathlib.Path(yol).read_text(encoding="utf-8"))


def gorseller(g):
    fikirler = [f for f in fikirleri_oku(g.fikirler) if not (KOK / "adaylar" / f["klasor"]).exists() or g.zorla]
    model, fiyat = MODELLER[g.model]
    adet = len(fikirler) * g.adet
    print(f"{len(fikirler)} fikir × {g.adet} aday = {adet} görsel, model {model}, tahmini maliyet ≈ {adet * fiyat:.2f} $")
    if adet * fiyat > g.butce:
        raise SystemExit(f"Bütçe sınırı ({g.butce} $) aşılıyor; --butce ile artır ya da --adet'i azalt.")
    if not g.onay:
        raise SystemExit("Harcama yapılmadı. Onaylıyorsan aynı komutu --onay ile çalıştır.")
    for f in fikirler:
        hedef = KOK / "adaylar" / f["klasor"]
        hedef.mkdir(parents=True, exist_ok=True)
        hava = {"kar": "heavy snow falling outside the window", "yagmur": "rain streaming down the window glass, rainy night"}[f.get("yagis", "kar")]
        ates = "a crackling fireplace with visible flames inside the room" if f.get("ates", "var") == "var" else "no fireplace"
        istem = f"{f['istem']}. {hava}. {ates}. {'Christmas decorations, a small lit Christmas tree. ' if f.get('noel') else ''}{STIL}"
        for n in range(1, g.adet + 1):
            girdi = {"prompt": istem, "aspect_ratio": "16:9", "output_format": "png"}
            if g.model == "pro":
                girdi.update(output_quality=100, safety_tolerance=2, prompt_upsampling=False, seed=1000 + n)
            t = curl("-X", "POST", f"{API}/models/{model}/predictions", "-H", "Content-Type: application/json", "-H", "Prefer: wait=60",
                     "-d", json.dumps({"input": girdi}))
            while t["status"] not in ("succeeded", "failed", "canceled"):
                time.sleep(4)
                t = curl(f"{API}/predictions/{t['id']}")
            if t["status"] != "succeeded":
                print(f"  {f['klasor']} aday {n}: BAŞARISIZ {t.get('error')}")
                continue
            adres = t["output"] if isinstance(t["output"], str) else t["output"][0]
            curl(adres, cikti=hedef / f"aday_{n}.png")
            print(f"  {f['klasor']} aday {n}: hazır")
        (hedef / "istem.txt").write_text(istem + "\n", encoding="utf-8")
    secim_sayfasi(g)


def secim_sayfasi(g):
    """Bütün adayları numaralı tek bir sayfada gösterir (seçim kolaylığı için)."""
    satirlar = []
    for f in fikirleri_oku(g.fikirler):
        adaylar = sorted((KOK / "adaylar" / f["klasor"]).glob("aday_*.png"))
        if not adaylar:
            continue
        kucuk = []
        for a in adaylar:
            im = cv2.resize(cv2.imread(str(a)), (640, 360))
            cv2.putText(im, f"{f['klasor']}  #{a.stem.split('_')[1]}", (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 5)
            cv2.putText(im, f"{f['klasor']}  #{a.stem.split('_')[1]}", (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            kucuk.append(im)
        while len(kucuk) < 3:
            kucuk.append(np.zeros((360, 640, 3), np.uint8))
        satirlar.append(np.hstack(kucuk[:3]))
    if satirlar:
        cv2.imwrite(str(KOK / "adaylar" / "secim.jpg"), np.vstack(satirlar), [cv2.IMWRITE_JPEG_QUALITY, 85])
        print(f"Seçim sayfası: {KOK / 'adaylar' / 'secim.jpg'}  →  fikirler.json'da her fikre \"secim\": N yaz")


def taslak(g):
    for f in fikirleri_oku(g.fikirler):
        if not f.get("secim"):
            continue
        if (KOK / f["klasor"] / "sahne.json").exists():
            print(f"{f['klasor']}: taslak zaten var, atlanıyor")
            continue
        gorsel = KOK / "adaylar" / f["klasor"] / f"aday_{f['secim']}.png"
        komut = [sys.executable, "yeni_sahne.py", "taslak", f["klasor"], str(gorsel), "--yagis", f.get("yagis", "kar"),
                 "--ad", f["ad"], "--ates", f.get("ates", "oto")] + (["--noel"] if f.get("noel") else []) \
                + (["--ates-klip", f["ates_klip"]] if f.get("ates_klip") else [])
        print("$", " ".join(komut), flush=True)
        subprocess.run(komut, cwd=KOK, check=True)


def uret(g):
    hatalar = []
    for f in fikirleri_oku(g.fikirler):
        if not f.get("secim") or not (KOK / f["klasor"] / "sahne.json").exists():
            continue
        komut = [sys.executable, "yeni_sahne.py", "uret", f["klasor"]] + (["--k4-yok"] if g.k4_yok else [])
        print("$", " ".join(komut), flush=True)
        if subprocess.run(komut, cwd=KOK).returncode:
            hatalar.append(f["klasor"])
    if hatalar:
        raise SystemExit(f"Sorunlu sahneler (gönderme, önce düzelt): {', '.join(hatalar)}")
    print("Hepsi hazır. Sıradaki iş: her sahnenin yukleme_3saat.txt dosyasındaki [ÖYKÜ] kısmını yazmak.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fikirler", default=str(KOK / "kanal" / "fikirler.json"))
    alt = p.add_subparsers(dest="adim", required=True)
    a = alt.add_parser("gorseller")
    a.add_argument("--adet", type=int, default=2)
    a.add_argument("--model", choices=list(MODELLER), default="pro")
    a.add_argument("--butce", type=float, default=1.0, help="bu çalıştırmada en fazla harcanacak tutar ($)")
    a.add_argument("--onay", action="store_true")
    a.add_argument("--zorla", action="store_true", help="adayı olan fikirler için de yeniden üret")
    alt.add_parser("secim")
    alt.add_parser("taslak")
    u = alt.add_parser("uret")
    u.add_argument("--k4-yok", action="store_true")
    g = p.parse_args()
    {"gorseller": gorseller, "secim": secim_sayfasi, "taslak": taslak, "uret": uret}[g.adim](g)


if __name__ == "__main__":
    main()
