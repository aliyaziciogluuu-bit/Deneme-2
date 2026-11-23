"""Bir videonun görsellerini Replicate (Flux 1.1 Pro Ultra) ile üretir.

Kullanım:
  python gorsel.py 01-sagir-yilan                 # eksik görseller için aday üretir (önce maliyeti gösterir)
  python gorsel.py 01-sagir-yilan --onay          # harcamayı onaylar ve üretir
  python gorsel.py 01-sagir-yilan --onay portre   # yalnızca adı verilen görselleri (yeniden) üretir
  python gorsel.py 01-sagir-yilan --sec portre=2  # adaylardan birini gorseller/portre.jpg olarak seçer

Girdi:  <video>/gorseller.json  {"gorseller": [{"ad": "...", "istem": "...", "oran": "16:9"}]}
Çıktı:  <video>/adaylar/<ad>_1.jpg, _2.jpg ...  ve  <video>/adaylar/secim.jpg (karşılaştırma sayfası)

Kanalın görsel dili STIL'de sabittir; her video aynı çizim tarzını kullanır.
API anahtarı ortamın ağ geçidi tarafından eklenir; bu betikte anahtar yoktur. POST istekleri yeniden denenmez.
"""
import json
import pathlib
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont

KOK = pathlib.Path(__file__).parent
API = "https://api.replicate.com/v1"
MODEL, FIYAT = "black-forest-labs/flux-1.1-pro-ultra", 0.06
ADAY = 2
STIL = ("Hand-painted naturalist storybook illustration, gouache and watercolor with fine ink linework, "
        "warm earthy palette of moss green, ochre and terracotta, soft natural light, richly detailed textures, "
        "scientifically accurate anatomy, gentle and calm mood. No text, no letters, no watermark, no logo.")


def curl(*arg, cikti=None):
    yeniden = [] if "POST" in arg else ["--retry", "3"]
    komut = ["curl", "-sS", "-m", "300", *yeniden, *arg] + (["-o", str(cikti)] if cikti else [])
    r = subprocess.run(komut, capture_output=True, text=cikti is None, check=True)
    return None if cikti else json.loads(r.stdout)


def uret(klasor, liste, onay):
    adaylar = klasor / "adaylar"
    adaylar.mkdir(exist_ok=True)
    adet = sum(g.get("aday", ADAY) for g in liste)
    print(f"{len(liste)} görsel, {adet} aday, tahmini maliyet ≈ {adet * FIYAT:.2f} $")
    if not onay:
        raise SystemExit("Harcama yapılmadı. Onaylıyorsan aynı komutu --onay ile çalıştır.")
    for g in liste:
        istem = f"{g['istem']} {STIL}"
        for n in range(1, g.get("aday", ADAY) + 1):  # hayvanın görünmediği sahnelerde "aday": 1 yeterli
            if (adaylar / f"{g['ad']}_{n}.jpg").exists():
                continue
            girdi = {"prompt": istem, "aspect_ratio": g.get("oran", "16:9"), "output_format": "jpg",
                     "safety_tolerance": 2, "raw": False, "seed": 4242 + 97 * n}
            for bekle in (10, 20, 40, 60, 90, 0):
                try:
                    t = curl("-X", "POST", f"{API}/models/{MODEL}/predictions", "-H", "Content-Type: application/json",
                             "-H", "Prefer: wait=60", "-d", json.dumps({"input": girdi}))
                except subprocess.CalledProcessError as hata:  # anlık ağ kopması: bekle, yeniden dene
                    print(f"  {g['ad']} aday {n}: bağlantı hatası (curl {hata.returncode}), {bekle} sn sonra yeniden", flush=True)
                    t = {}
                    time.sleep(bekle or 5)
                    continue
                if "id" in t or not bekle:  # id yoksa istek kabul edilmedi (ör. hız sınırı); tahmin oluşmadığı için yeniden denemek güvenli
                    break
                print(f"  {g['ad']} aday {n}: API yanıtı {str(t)[:160]} ; {bekle} sn sonra yeniden", flush=True)
                time.sleep(bekle)
            if "id" not in t:
                print(f"  {g['ad']} aday {n}: BAŞARISIZ {t}", flush=True)
                continue
            while t.get("status") not in ("succeeded", "failed", "canceled"):
                time.sleep(4)
                t = curl(f"{API}/predictions/{t['id']}")
            if t["status"] != "succeeded":
                print(f"  {g['ad']} aday {n}: BAŞARISIZ {t.get('error')}", flush=True)
                continue
            adres = t["output"] if isinstance(t["output"], str) else t["output"][0]
            curl(adres, cikti=adaylar / f"{g['ad']}_{n}.jpg")
            print(f"  {g['ad']} aday {n}: hazır", flush=True)


def secim_sayfasi(klasor, adlar):
    """Adayları numaralı tek bir sayfada gösterir."""
    font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 30)
    satirlar = []
    for ad in adlar:
        resimler = sorted((klasor / "adaylar").glob(f"{ad}_*.jpg"))
        if not resimler:
            continue
        satir = Image.new("RGB", (ADAY * 800, 450), (20, 20, 20))
        for i, r in enumerate(resimler[:ADAY]):
            im = Image.open(r).convert("RGB")
            im.thumbnail((800, 450))
            satir.paste(im, (i * 800, 0))
            ImageDraw.Draw(satir).text((i * 800 + 14, 10), f"{ad} #{r.stem.rsplit('_', 1)[1]}", font=font,
                                       fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
        satirlar.append(satir)
    if satirlar:
        sayfa = Image.new("RGB", (ADAY * 800, 450 * len(satirlar)))
        for i, s in enumerate(satirlar):
            sayfa.paste(s, (0, i * 450))
        sayfa.save(klasor / "adaylar" / "secim.jpg", quality=85)
        print(f"Seçim sayfası: {klasor / 'adaylar' / 'secim.jpg'}")


def main():
    klasor = KOK / sys.argv[1]
    arg = sys.argv[2:]
    tanim = json.loads((klasor / "gorseller.json").read_text(encoding="utf-8"))["gorseller"]
    tanim = [g for g in tanim if not g.get("gercek") and (g.get("istem") or "").strip()]  # gerçek fotoğraf yer tutucuları üretilmez (23 Kasım)
    if "--sec" in arg:
        (klasor / "gorseller").mkdir(exist_ok=True)
        for s in arg[arg.index("--sec") + 1:]:
            ad, n = s.split("=")
            Image.open(klasor / "adaylar" / f"{ad}_{n}.jpg").convert("RGB").save(klasor / "gorseller" / f"{ad}.jpg", quality=95)
            print(f"{ad}: aday {n} seçildi")
        return
    adlar = [a for a in arg if not a.startswith("--")]
    if adlar:
        liste = [g for g in tanim if g["ad"] in adlar]
    else:
        liste = [g for g in tanim if not list((klasor / "adaylar").glob(f"{g['ad']}_*.jpg"))]
    if liste:
        uret(klasor, liste, "--onay" in arg)
    secim_sayfasi(klasor, [g["ad"] for g in tanim])


if __name__ == "__main__":
    main()
