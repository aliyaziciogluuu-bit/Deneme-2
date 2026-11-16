"""Bir videonun bütün üretim adımlarını sırayla, kaldığı yerden devam ederek çalıştırır.

Kullanım:  python hepsi.py 02-ev-kertenkelesi            # bir video
           python hepsi.py 02-ev-kertenkelesi 03-kirpi   # birden fazla video art arda

Her adım zaten yapılmışsa atlanır; bir adım yarıda kalırsa (ör. kredi biterse) aynı komut kaldığı yerden sürdürür.
Durduğu iki kontrol noktası bilerek insan/Claude onayı ister (kanalın doğruluk sözü):
  A) Görsel seçimi: adaylar/secim.jpg incelenip "python gorsel.py <video> --sec ad=N ..." ile seçilir
     (anatomisi yanlış aday kullanılmaz). Bütün görseller seçilmeden devam edilmez.
  B) cekimler.json: kadrajlar --onizleme ile kontrol edilip yazılır.
Senaryo bilgi kontrolü bu betikten ÖNCE yapılır (bağımsız kontrolcü ajan).

Whisper gerektiren adımlar (seslendirme, son kontrol) PYTHON_WHISPER ortam değişkenindeki Python ile çalışır
(faster-whisper kurulu ortam); yoksa bu betiği çalıştıran Python kullanılır.
"""
import json
import os
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).parent
PY = sys.executable
PY_W = os.environ.get("PYTHON_WHISPER", PY)


def calistir(*komut, py=PY):
    print("$", " ".join(komut), flush=True)
    subprocess.run([py, *komut], cwd=KOK, check=True)


def video(ad):
    k = KOK / ad
    gorseller = [g["ad"] for g in json.loads((k / "gorseller.json").read_text(encoding="utf-8"))["gorseller"]]
    secilmemis = [g for g in gorseller if not list((k / "gorseller").glob(g + ".*"))]
    if secilmemis:
        calistir("gorsel.py", ad, "--onay")
        raise SystemExit(f"[{ad}] KONTROL NOKTASI A: adaylar/secim.jpg'yi incele, seç: python gorsel.py {ad} --sec "
                         + " ".join(f"{g}=N" for g in secilmemis))
    if (k / "klipler.json").exists():
        calistir("klip.py", ad, "--onay")
    calistir("seslendir_bulut.py", ad, py=PY_W)
    rapor = json.loads((k / "ses" / "rapor.json").read_text(encoding="utf-8"))
    if not all(r["uygun"] for r in rapor.values()):
        raise SystemExit(f"[{ad}] Doğrulanamayan cümleler var; ses/rapor.json'a bak, gerekirse senaryoyu sadeleştir.")
    if not (k / "cekimler.json").exists():
        raise SystemExit(f"[{ad}] KONTROL NOKTASI B: cekimler.json yaz, python video.py {ad} --onizleme ile kontrol et.")
    calistir("video.py", ad)
    calistir("son_kontrol.py", ad, py=PY_W)
    print(f"[{ad}] HAZIR: video.mp4, kapak.jpg, altyazi.srt, yukleme.txt", flush=True)


if __name__ == "__main__":
    for ad in sys.argv[1:]:
        video(ad)
