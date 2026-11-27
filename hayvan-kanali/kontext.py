"""Tek görselde küçük düzeltme (Flux Kontext Pro, ~0,04 $). Kullanım: python kontext.py <girdi.jpg> <çıktı.jpg> "<istem>" """
import base64, io, json, subprocess, sys, time
from PIL import Image
API = "https://api.replicate.com/v1"

def c(*a):
    return json.loads(subprocess.run(["curl", "-sS", "-m", "300", *a], capture_output=True, text=True, check=True).stdout)

def main(girdi, cikti, istem):
    im = Image.open(girdi).convert("RGB"); b = io.BytesIO(); im.save(b, "JPEG", quality=93)
    istek = {"input": {"prompt": istem, "input_image": "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode(),
                       "output_format": "jpg", "aspect_ratio": "match_input_image"}}
    yol = cikti + ".istek.json"; open(yol, "w").write(json.dumps(istek))
    t = c("-X", "POST", f"{API}/models/black-forest-labs/flux-kontext-pro/predictions", "-H", "Content-Type: application/json", "-d", f"@{yol}")
    while t.get("status") not in ("succeeded", "failed", "canceled"):
        time.sleep(4); t = c(f"{API}/predictions/{t['id']}")
    import os; os.remove(yol)
    if t["status"] != "succeeded":
        raise SystemExit(f"BAŞARISIZ: {t.get('error')}")
    out = t["output"] if isinstance(t["output"], str) else t["output"][0]
    subprocess.run(["curl", "-sS", "-m", "300", "-o", cikti, out], check=True)
    print("hazır:", cikti)

if __name__ == "__main__":
    main(*sys.argv[1:4])
