"""Sahne görselini Replicate'te Real-ESRGAN ile 4 kat büyütür, 3840x2160'a indirir, sahne.json'a "gorsel_4k" yazar.

Maliyet: görsel başına yaklaşık 0,005 $ (Kasım 2026). Kullanım: python buyut4k.py 05-snowy-library [06-rainy-cafe ...]
API anahtarı ortamın ağ geçidi tarafından eklenir. Gönderme (POST) isteği yeniden denenmez: çift ücret olmasın.
"""
import json
import pathlib
import subprocess
import sys

import cv2

KOK = pathlib.Path(__file__).parent
API = "https://api.replicate.com/v1"
SURUM = "b3ef194191d13140337468c916c2c5b96dd0cb06dffc032a022a31807f6a5ea8"   # nightmareai/real-esrgan


def curl(*arg, cikti=None):
    yeniden = [] if "POST" in arg else ["--retry", "3"]
    komut = ["curl", "-sS", "-m", "300", *yeniden, *arg] + (["-o", str(cikti)] if cikti else [])
    r = subprocess.run(komut, capture_output=True, text=cikti is None, check=True)
    return None if cikti else json.loads(r.stdout)


for ad in sys.argv[1:]:
    klasor = KOK / ad
    ayar_yolu = klasor / "sahne.json"
    ayar = json.loads(ayar_yolu.read_text(encoding="utf-8"))
    if ayar.get("gorsel_4k") and (klasor / ayar["gorsel_4k"]).exists():
        print(ad, "zaten var"); continue
    kaynak = klasor / ayar["gorsel"]
    dosya = curl("-X", "POST", f"{API}/files", "-F", f"content=@{kaynak};type=image/png;filename=sahne.png")
    tahmin = curl("-X", "POST", f"{API}/predictions", "-H", "Content-Type: application/json", "-H", "Prefer: wait=60",
                  "-d", json.dumps({"version": SURUM, "input": {"image": dosya["urls"]["get"], "scale": 4, "face_enhance": False}}))
    while tahmin["status"] not in ("succeeded", "failed", "canceled"):
        subprocess.run(["sleep", "5"]); tahmin = curl(f"{API}/predictions/{tahmin['id']}")
    if tahmin["status"] != "succeeded":
        print(ad, "BAŞARISIZ", tahmin.get("error")); continue
    ham = klasor / "_x4.png"
    curl(tahmin["output"], cikti=ham)
    g = cv2.imread(str(ham)); ham.unlink()
    cv2.imwrite(str(klasor / "sahne_4k.png"), cv2.resize(g, (3840, 2160), interpolation=cv2.INTER_AREA))
    ayar = json.loads(ayar_yolu.read_text(encoding="utf-8"))
    ayar["gorsel_4k"] = "sahne_4k.png"
    ayar_yolu.write_text(json.dumps(ayar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(ad, "hazır", round(tahmin.get("metrics", {}).get("predict_time", 0), 1), "sn")
