"""Üretim hattı: video oluşturma, önizleme ve son kontrolü TEK SIRADA çalıştırır.

Neden: 19 Kasım'da karga videosu oluşturulurken aynı anda kirpi önizlemesi de çalıştı; ikisinin geçici
dosyaları (her biri 3–6 GB) diski doldurdu, video ve seslendirme yarıda kaldı. Bu betik bir kilit dosyasıyla
aynı anda yalnızca bir işin çalışmasını sağlar; diğerleri sırasını bekler. Her işten önce boş yeri kontrol eder,
işten sonra `_gecici` klasörünü siler.

Kullanım (hayvan-kanali/ içinde; ajanlar dahil herkes video.py yerine bunu kullanır):
  python3 hat.py uret 06-karga 06-karga/shorts/s1-maske   # her klasör için video.py + son_kontrol.py
  python3 hat.py onizleme 03-kirpi                        # video.py --onizleme (sıraya girer)
  python3 hat.py kapak 06-karga                           # video.py --kapak (sıraya girer)
  python3 hat.py durum                                    # şu an çalışan iş ve boş yer

Çıktı: her klasör için tek satırlık sonuç (GEÇTİ / KALDI) ve 1 kelimeden fazla duyulan farklar.
"""
import fcntl
import os
import pathlib
import shutil
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).parent
KILIT = KOK / "kanal" / ".hat.kilit"
DURUM = KOK / "kanal" / ".hat.durum"
EN_AZ_GB = 7  # bir uzun video _gecici için 6 GB'a kadar yer kullanabiliyor
PYTHON = os.environ.get("AVLU_PYTHON", "/tmp/claude-0/-home-user-Deneme-2/fdddad94-111a-5afb-8da5-24e84d67e505/scratchpad/venv/bin/python")
if not pathlib.Path(PYTHON).exists():
    PYTHON = sys.executable


def bos_gb():
    return shutil.disk_usage(KOK).free / 1e9


def gecici_temizle():
    for g in list(KOK.glob("*/_gecici")) + list(KOK.glob("*/shorts/*/_gecici")):
        shutil.rmtree(g, ignore_errors=True)


def calistir(komut, klasor):
    if bos_gb() < EN_AZ_GB:
        gecici_temizle()
    if bos_gb() < EN_AZ_GB:
        raise SystemExit(f"DUR: boş yer {bos_gb():.1f} GB (en az {EN_AZ_GB} GB gerekli). Eski klip/aday dosyalarını temizle.")
    DURUM.write_text(f"{time.strftime('%H:%M')} {' '.join(komut)}\n")
    env = dict(os.environ, HF_HUB_DISABLE_XET="1")
    s = subprocess.run([PYTHON, *komut], cwd=KOK, capture_output=True, text=True, env=env)
    shutil.rmtree(KOK / klasor / "_gecici", ignore_errors=True)
    return s.returncode, (s.stdout + s.stderr)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("uret", "onizleme", "kapak", "durum"):
        raise SystemExit(__doc__)
    is_ = sys.argv[1]
    if is_ == "durum":
        print("çalışan:", DURUM.read_text().strip() if DURUM.exists() else "yok", f"| boş yer {bos_gb():.1f} GB")
        return
    klasorler = sys.argv[2:]
    KILIT.parent.mkdir(exist_ok=True)
    with open(KILIT, "w") as k:
        try:
            fcntl.flock(k, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Hat dolu, sıra bekleniyor…", flush=True)
            fcntl.flock(k, fcntl.LOCK_EX)
        try:
            for d in klasorler:
                if is_ == "onizleme":
                    kod, cikti = calistir(["video.py", d, "--onizleme"], d)
                    print(f"== {d} önizleme: {'tamam' if kod == 0 else 'HATA'} → {d}/onizleme.jpg")
                    if kod:
                        print(cikti[-800:])
                    continue
                if is_ == "kapak":
                    kod, cikti = calistir(["video.py", d, "--kapak"], d)
                    print(f"== {d} kapak: {'tamam' if kod == 0 else 'HATA'}")
                    if kod:
                        print(cikti[-800:])
                    continue
                kod, cikti = calistir(["video.py", d], d)
                son = [l for l in cikti.splitlines() if l.strip()][-1:] or [""]
                print(f"== {d}: {son[0]}")
                if kod:
                    print(cikti[-800:])
                    continue
                kod, cikti = calistir(["son_kontrol.py", d], d)
                for l in cikti.splitlines():
                    if "KALDI" in l or "SONUÇ" in l or "birebir" in l:
                        print("  ", l.strip())
                duyulan = KOK / d / "son_kontrol_duyulan.txt"
                if duyulan.exists():
                    for l in duyulan.read_text(encoding="utf-8").splitlines():
                        if "fark=" in l and "fark=0" not in l:
                            print("   fark:", l[:220])
        finally:
            DURUM.unlink(missing_ok=True)
    print(f"Bitti. Boş yer {bos_gb():.1f} GB.")


if __name__ == "__main__":
    main()
