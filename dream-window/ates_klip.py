"""Bir sahnenin şöminesi için Replicate'te gerçek ateş videosu üretir ve sahneye bağlar.

Yalnızca şömine bölgesi kırpılıp düşük çözünürlükte üretilir (tüm sahneyi üretmekten çok daha ucuz),
sonu başına yumuşak geçişle bağlanarak kusursuz döngü yapılır ve sahne.json'a "ates_klip" eklenir.
uret.py bu klibi şöminenin içine yerleştirir; odanın geri kalanı orijinal görsel olarak kalır.

Kullanım:
  python ates_klip.py 05-snowy-library                  # Kling, 10 sn (≈ 0,70 $), 8,5 sn'lik döngü
  python ates_klip.py 05-snowy-library --model bytedance/seedance-1-pro --cozunurluk 480p   # daha ucuz (≈ 0,30 $), daha yumuşak

Model karşılaştırması (kütüphane şöminesi, Kasım 2026): Kling orijinal görsele daha sadık, daha keskin ve
çevresi daha sabit çıktı; bu yüzden varsayılan Kling.
  python ates_klip.py 03-christmas-cabin --klipten tum_sahne.mp4   # hazır bir tam sahne klibinden kırpar (ücretsiz)

API anahtarı ortamın ağ geçidi tarafından eklenir; bu betikte anahtar yoktur.
"""
import argparse
import json
import pathlib
import subprocess
import time

import cv2
import numpy as np

KOK = pathlib.Path(__file__).parent
API = "https://api.replicate.com/v1"
ISTEM = ("Static locked-off close-up shot of a fireplace, the camera does not move at all. The fire burns naturally: "
         "flames flicker and dance around the logs, embers glow and small sparks rise. The stone and brick around the fire "
         "and everything outside the fireplace stay completely still. No camera movement, no zoom, no people, no smoke filling the room.")
YASAK = "camera movement, zoom, pan, people, hands, text, smoke filling the room, sparks or glow outside the fireplace, flickering walls, morphing objects"


def girdi_kur(model: str, adres: str, g) -> dict:
    """Her modelin alan adları farklı; bitiş karesi zorlanmaz (doğal hareket için), döngüyü dongu_yap kurar."""
    if model.startswith("kwaivgi/kling"):
        return {"start_image": adres, "prompt": ISTEM, "negative_prompt": YASAK, "duration": 5 if g.sure <= 5 else 10}
    if model.startswith("bytedance/seedance"):
        return {"image": adres, "prompt": ISTEM, "duration": g.sure, "resolution": g.cozunurluk, "fps": 24, "camera_fixed": True}
    raise SystemExit(f"Bu model için girdi tanımlı değil: {model}")


def curl(*arg, cikti=None):
    yeniden = [] if "POST" in arg else ["--retry", "3"]   # gönderme isteği yeniden denenmez: çift (ücretli) üretim olmasın
    komut = ["curl", "-sS", "-m", "300", *yeniden, *arg]
    if cikti:
        komut += ["-o", str(cikti)]
    r = subprocess.run(komut, capture_output=True, text=cikti is None, check=True)
    return None if cikti else json.loads(r.stdout)


def kirpma_kutusu(ayar, gen, yuk, pay=0.35, oran=4 / 3):
    """Şömine kutusunu çevresinden pay bırakarak genişletir ve 4:3 orana getirir (kaynak görsel pikseli)."""
    x0, y0, x1, y1 = ayar["ates"]["kutu"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * (1 + 2 * pay), (y1 - y0) * (1 + 2 * pay)
    if w / h < oran:
        w = h * oran
    else:
        h = w / oran
    w, h = min(w, gen), min(h, yuk)
    x0 = int(round(min(max(cx - w / 2, 0), gen - w)))
    y0 = int(round(min(max(cy - h / 2, 0), yuk - h)))
    return [x0, y0, x0 + int(round(w)), y0 + int(round(h))]


def dongu_yap(kaynak: pathlib.Path, hedef: pathlib.Path, kutu_px=None, gecis=36):
    """Klibin sonunu başına yumuşak geçişle bağlar; kutu_px verilirse önce o bölgeyi kırpar."""
    cap = cv2.VideoCapture(str(kaynak))
    kareler = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if kutu_px:
            x0, y0, x1, y1 = kutu_px
            f = f[y0:y1, x0:x1]
        kareler.append(f.astype(np.float32))
    n = len(kareler)
    yuk, gen = kareler[0].shape[:2]
    yuk, gen = yuk - yuk % 2, gen - gen % 2
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{gen}x{yuk}", "-r", "24", "-i", "-",
                           "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", str(hedef)], stdin=subprocess.PIPE)
    for i in range(n - gecis):
        if i < gecis:
            a = (i + 0.5) / gecis
            a = a * a * (3 - 2 * a)
            kare = kareler[n - gecis + i] * (1 - a) + kareler[i] * a
        else:
            kare = kareler[i]
        ff.stdin.write(np.clip(kare[:yuk, :gen] + 0.5, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close()
    assert ff.wait() == 0
    return (n - gecis) / 24


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sahne")
    p.add_argument("--model", default="kwaivgi/kling-v2.5-turbo-pro")
    p.add_argument("--cozunurluk", default="480p")
    p.add_argument("--sure", type=int, default=10)
    p.add_argument("--cikti", default="ates_klip.mp4")
    p.add_argument("--baglama", action="store_true", help="sahne.json'a yazma (yalnızca karşılaştırma için üret)")
    p.add_argument("--klipten", help="hazır tam sahne klibi (1920x1080); Replicate'e gitmeden kırpılır")
    g = p.parse_args()

    klasor = KOK / g.sahne
    ayar_yolu = klasor / "sahne.json"
    ayar = json.loads(ayar_yolu.read_text(encoding="utf-8"))
    gorsel = cv2.imread(str(klasor / ayar["gorsel"]))
    yuk, gen = gorsel.shape[:2]
    kutu = kirpma_kutusu(ayar, gen, yuk)
    hedef = klasor / g.cikti
    bilgi = {"dosya": hedef.name, "kutu": kutu}

    if g.klipten:
        olcek = 1920 / gen
        sure = dongu_yap(pathlib.Path(g.klipten), hedef, [int(round(v * olcek)) for v in kutu])
        bilgi["kaynak"] = "tam sahne klibinden kırpıldı"
    else:
        gecici = klasor / f"_kirpma_{hedef.stem}.jpg"
        x0, y0, x1, y1 = kutu
        kirpma = gorsel[y0:y1, x0:x1]
        if kirpma.shape[1] < 960:                                  # model girdisi en az 960x720 olsun
            kirpma = cv2.resize(kirpma, (960, 720), interpolation=cv2.INTER_LANCZOS4)
        cv2.imwrite(str(gecici), kirpma, [cv2.IMWRITE_JPEG_QUALITY, 94])
        dosya = curl("-X", "POST", f"{API}/files", "-F", f"content=@{gecici};type=image/jpeg;filename=ates.jpg")
        gecici.unlink()
        adres = dosya["urls"]["get"]
        girdi = girdi_kur(g.model, adres, g)
        tahmin = curl("-X", "POST", f"{API}/models/{g.model}/predictions", "-H", "Content-Type: application/json",
                      "-d", json.dumps({"input": girdi}))
        print("Üretim başladı:", tahmin["id"], flush=True)
        while tahmin["status"] not in ("succeeded", "failed", "canceled"):
            time.sleep(10)
            tahmin = curl(f"{API}/predictions/{tahmin['id']}")
        if tahmin["status"] != "succeeded":
            raise SystemExit(f"Üretim başarısız: {tahmin.get('error')}")
        cikti = tahmin["output"] if isinstance(tahmin["output"], str) else tahmin["output"][0]
        ham = klasor / f"_ham_{hedef.stem}.mp4"
        curl(cikti, cikti=ham)
        sure = dongu_yap(ham, hedef, gecis=24 if g.sure <= 5 else 36)
        ham.unlink()
        bilgi.update(model=g.model, cozunurluk=g.cozunurluk, tahmin=tahmin["id"],
                     sure_sn=round(tahmin.get("metrics", {}).get("predict_time", 0)))

    if g.baglama:
        print(f"Hazır: {hedef} ({sure:.1f} sn döngü); sahne.json değiştirilmedi. Bilgi: {json.dumps(bilgi, ensure_ascii=False)}")
        return
    ayar["ates_klip"] = bilgi
    ayar_yolu.write_text(json.dumps(ayar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Hazır: {hedef} ({sure:.1f} sn döngü), sahne.json güncellendi")


if __name__ == "__main__":
    main()
