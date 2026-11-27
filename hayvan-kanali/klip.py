"""Seçilen görsellerden kısa animasyon klipleri üretir (Replicate, Kling 2.5 Turbo Pro, görselden videoya).

Kullanım:
  python klip.py 01-sagir-yilan            # eksik klipleri üretir (önce maliyeti gösterir)
  python klip.py 01-sagir-yilan --onay     # harcamayı onaylar
  python klip.py 01-sagir-yilan --onay goz # yalnızca adı verilen klibi üretir (varsa atlar; yeniden üretmek için --yeniden)

Bütçe koruması: <video>/gorsel_denetim.txt içinde her görsel için "ad: KABUL" satırı yoksa klip üretilmez
(görsel denetçisi onaylamadan klip yok; zorunlu istisna için --denetimsiz).

Girdi:  <video>/klipler.json  {"klipler": [{"ad": "goz", "gorsel": "goz", "istem": "...", "sure": 5}]}
Çıktı:  <video>/klipler/<ad>.mp4  →  cekimler.json'da bir çekime "klip": "<ad>" yazınca video.py görsel yerine klibi oynatır.

Tüm videoyu animasyon yapmak pahalı ve izlenmeye katkısı orantılı değil; yalnızca açılış ve kilit anlar canlandırılır,
geri kalan görseller video.py'nin kamera hareketiyle (yakınlaşma/kaydırma) hareketlenir.
API anahtarı ortamın ağ geçidi tarafından eklenir; bu betikte anahtar yoktur.
"""
import base64
import io
import json
import pathlib
import subprocess
import sys
import time

from PIL import Image

KOK = pathlib.Path(__file__).parent
MODEL, FIYAT_5SN = "kwaivgi/kling-v2.5-turbo-pro", 0.35
OLUMSUZ = ("legs, feet, claws, paws, extra limbs, mutated anatomy, morphing, melting, text, letters, watermark, "
           "flicker, sudden camera cut, blurry, distorted face, extra fingers")


def curl(*a, cikti=None):
    yeniden = [] if "POST" in a else ["--retry", "3"]
    r = subprocess.run(["curl", "-sS", "-m", "600", *yeniden, *a] + (["-o", str(cikti)] if cikti else []),
                       capture_output=True, text=cikti is None, check=True)
    return None if cikti else json.loads(r.stdout)


def sabirli_curl(*a, cikti=None, deneme=40):
    """Ağ kopmasında (curl hata 7, 28, 56...) ödenmiş klibi kaybetmemek için uzun süre yeniden dener (27 Kasım dersi)."""
    for i in range(deneme):
        try:
            return curl(*a, cikti=cikti)
        except subprocess.CalledProcessError as e:
            print(f"    ağ hatası ({e.returncode}), {i + 1}. yeniden deneme 30 sn sonra", flush=True)
            time.sleep(30)
    return curl(*a, cikti=cikti)


def veri_adresi(yol: pathlib.Path) -> str:
    im = Image.open(yol).convert("RGB")
    im.thumbnail((1920, 1080))
    tampon = io.BytesIO()
    im.save(tampon, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(tampon.getvalue()).decode()


def main():
    klasor = KOK / sys.argv[1]
    arg = sys.argv[2:]
    tanim = json.loads((klasor / "klipler.json").read_text(encoding="utf-8"))["klipler"]
    hedef = klasor / "klipler"
    hedef.mkdir(exist_ok=True)
    adlar = [a for a in arg if not a.startswith("--")]
    if adlar:
        liste = [k for k in tanim if k["ad"] in adlar
                 and ("--yeniden" in arg or not (hedef / f"{k['ad']}.mp4").exists())]  # var olan klip --yeniden olmadan tekrar üretilmez
    else:
        liste = [k for k in tanim if not (hedef / f"{k['ad']}.mp4").exists()]
    maliyet = sum(FIYAT_5SN * k.get("sure", 5) / 5 for k in liste)
    print(f"{len(liste)} klip, tahmini maliyet ≈ {maliyet:.2f} $")
    if not liste:
        return
    if "--onay" not in arg:
        raise SystemExit("Harcama yapılmadı. Onaylıyorsan aynı komutu --onay ile çalıştır.")
    # Bütçe koruması (26 Kasım, kanal sahibi: "hataları önceden görün, bütçeyi boşuna harcamayalım"):
    # klip görselden ~6 kat pahalı; görsel denetçisinin KABUL etmediği görselden klip üretilmez.
    denetim = klasor / "gorsel_denetim.txt"
    kabul = set()
    if denetim.exists():
        for satir in denetim.read_text(encoding="utf-8").splitlines():
            if ":" in satir and "KABUL" in satir.split(":", 1)[1].upper():
                kabul.add(satir.split(":", 1)[0].strip())
    eksik = [k["gorsel"] for k in liste if k["gorsel"] not in kabul]
    if eksik and "--denetimsiz" not in arg:
        raise SystemExit(f"Harcama yapılmadı: şu görseller için gorsel_denetim.txt'de KABUL yok: {', '.join(sorted(set(eksik)))}. "
                         "Önce avlu-gorsel-denetci'ye denetlet ve 'ad: KABUL' satırlarını yaz.")
    for k in liste:
        kayit = hedef / f"_{k['ad']}_tahmin.txt"  # ödenen işin kimliği: yarıda kalırsa yeniden çalıştırınca tekrar ödemeden kaldığı yerden alınır
        if kayit.exists():
            print(f"  {k['ad']}: yarım kalan iş {kayit.read_text().strip()} kaldığı yerden alınıyor", flush=True)
            t = sabirli_curl(f"https://api.replicate.com/v1/predictions/{kayit.read_text().strip()}")
            if t["status"] == "succeeded" and not t.get("output"):
                print(f"  {k['ad']}: çıktının süresi dolmuş; --yeniden-ode ile yeniden üretilebilir", flush=True)
                if "--yeniden-ode" not in arg:
                    continue
                kayit.unlink()
        if not kayit.exists():
            t = None
        girdi = {"prompt": k["istem"], "start_image": veri_adresi(next((klasor / "gorseller").glob(k["gorsel"] + ".*"))),
                 "duration": k.get("sure", 5), "negative_prompt": OLUMSUZ}
        istek = hedef / f"_{k['ad']}_istek.json"  # görsel verisi komut satırına sığmadığı için dosyadan gönderilir
        istek.write_text(json.dumps({"input": girdi}))
        for bekle in ((15, 30, 60, 90, 0) if t is None else ()):
            t = curl("-X", "POST", f"https://api.replicate.com/v1/models/{MODEL}/predictions",
                     "-H", "Content-Type: application/json", "-d", f"@{istek}")
            if "id" in t or not bekle:  # id yoksa istek kabul edilmedi (hız sınırı); yeniden denemek güvenli
                break
            time.sleep(bekle)
        istek.unlink()
        if "id" not in t:
            print(f"  {k['ad']}: İSTEK KABUL EDİLMEDİ {t}", flush=True)
            continue
        kayit.write_text(t["id"])
        while t["status"] not in ("succeeded", "failed", "canceled"):
            time.sleep(8)
            t = sabirli_curl(f"https://api.replicate.com/v1/predictions/{t['id']}")
        if t["status"] != "succeeded":
            print(f"  {k['ad']}: BAŞARISIZ {t.get('error')}", flush=True)
            kayit.unlink()
            continue
        sabirli_curl(t["output"] if isinstance(t["output"], str) else t["output"][0], cikti=hedef / f"{k['ad']}.mp4")
        kayit.unlink()
        print(f"  {k['ad']}: hazır ({t.get('metrics', {}).get('predict_time', 0):.0f} sn)", flush=True)


if __name__ == "__main__":
    main()
