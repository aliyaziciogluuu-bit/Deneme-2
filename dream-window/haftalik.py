"""Bir tarih aralığının bütün yüklemelerini tek pakette toplar (bilgisayardaki Claude YouTube Studio'ya yükleyip planlasın diye).

Kullanım:  python3 haftalik.py 2026-11-23 2026-11-30
           python3 haftalik.py --planlandi 2026-11-23 2026-11-30   (bilgisayardaki Claude planladıktan sonra takvimi işler)

- Her gün için gunluk.py'yi çalıştırır, dosyaları hafta/<bas>_<bit>/<tarih>/ altına koyar.
- Her video tekrar testinden (kontrol.py) geçer; SORUN çıkarsa paket üretilmez.
- Kök klasöre PC_YUKLEME.md (bilgisayardaki Claude'un talimatı) ve plan.json yazar.
- Paket 380 MiB'lık sıkıştırmasız zip parçalarına bölünür (sohbetten indirilebilsin diye).
"""
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

KOK = pathlib.Path(__file__).parent
PARCA = 380 * 1024 * 1024


def bolum(metin: str, ad: str) -> str:
    satirlar, al, cikti = metin.splitlines(), False, []
    for s in satirlar:
        if s.strip() in ("TITLE", "DESCRIPTION", "TAGS"):
            al = s.strip() == ad
            continue
        if al:
            cikti.append(s)
    return "\n".join(cikti).strip()


def test(dosya: pathlib.Path, uzun: bool):
    arg = ["--sure", "240"] if uzun else ["--sure", "48", "--en-az", "48"]
    r = subprocess.run([sys.executable, "kontrol.py", str(dosya), *arg], cwd=KOK, capture_output=True, text=True)
    son = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else ""
    if "SORUN" in r.stdout + r.stderr or r.returncode != 0:
        raise SystemExit(f"TEKRAR TESTİ GEÇMEDİ: {dosya.name}\n{r.stdout}{r.stderr}")
    sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dosya)],
                                capture_output=True, text=True).stdout or 0)
    if (uzun and sure < 10800) or (not uzun and abs(sure - 48) > 1):
        raise SystemExit(f"SÜRE HATALI: {dosya.name} {sure:.0f} sn")
    return son


def planlandi(bas, bit):
    """Aralıktaki yüklemeler YouTube'da planlandı: günlük hatırlatma artık dosya göndermesin, yalnızca notları hatırlatsın."""
    p = KOK / "kanal" / "takvim.json"
    takvim = json.loads(p.read_text(encoding="utf-8"))
    for t, g in takvim.items():
        if not (bas.isoformat() <= t <= bit.isoformat()):
            continue
        if g.pop("shorts", None):
            g["planli_shorts"] = True
            # "Bu Shorts'u yüklerken İlgili video olarak X'i seç" → yüklemede yapıldı; planlı uzun video seçilemediyse diye kontrol notuna çevir
            n = re.sub(r"Bu Shorts'u yüklerken İlgili video olarak (.*?) seç(?: \([^)]*\))?\.\s*",
                       lambda m: f"Kontrol: bugünkü Shorts'un İlgili videosu {re.sub(r'videosunu$', 'videosu', m.group(1))} olmalı; boşsa bağla. ", g.get("not", "")).strip()
            if n:
                g["not"] = n
            else:
                g.pop("not", None)
        if "uzun" in g:
            k = g.pop("uzun")
            import gunluk
            g["not"] = (f"{gunluk.TR[gunluk.AD[k]]} uzun videosu bilgisayardaki Claude tarafından YouTube'da planlandı, bugün 20:00'de kendiliğinden "
                        "yayınlanacak (tekrar yükleme). 20:00'den sonra videoya şu yorumu yazıp sabitle: "
                        "\"Where are you listening from tonight? 🌙 Sleep well.\" " + g.get("not", "")).strip()
            g["planli_uzun"] = k
        print(t, g)
    p.write_text(json.dumps(takvim, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    if sys.argv[1] == "--planlandi":
        return planlandi(dt.date.fromisoformat(sys.argv[2]), dt.date.fromisoformat(sys.argv[3]))
    bas, bit = dt.date.fromisoformat(sys.argv[1]), dt.date.fromisoformat(sys.argv[2])
    takvim = json.loads((KOK / "kanal" / "takvim.json").read_text(encoding="utf-8"))
    hedef = KOK / "hafta" / f"{bas}_{bit}"
    if hedef.exists():
        shutil.rmtree(hedef)
    hedef.mkdir(parents=True)
    plan = []
    gun = bas
    while gun <= bit:
        t = gun.isoformat()
        g = takvim.get(t, {})
        if "uzun" in g or "shorts" in g:
            gunluk_klasor = KOK / "bugun" / t
            if gunluk_klasor.exists():
                shutil.rmtree(gunluk_klasor)
            subprocess.run([sys.executable, "gunluk.py", t], cwd=KOK, check=True, capture_output=True)
            klasor = hedef / t
            shutil.copytree(gunluk_klasor, klasor, copy_function=lambda a, b: __import__("os").link(a, b))
            for v in sorted(klasor.glob("*_video.mp4")) + sorted(klasor.glob("*SHORTS_*.mp4")):
                uzun = "_UZUN_" in v.name
                print(f"{t} {v.name}: {test(v, uzun)}")
                metin = (v.parent / v.name.replace("_video.mp4", "_metin.txt").replace(".mp4", "_metin.txt")
                         if not uzun else v.parent / v.name.replace("_video.mp4", "_metin.txt"))
                yazi = metin.read_text(encoding="utf-8")
                oge = {"tarih": t, "saat": "20:00" if uzun else "19:30", "tur": "uzun" if uzun else "shorts",
                       "klasor": t, "video": v.name, "metin": metin.name,
                       "baslik": bolum(yazi, "TITLE"), "not": g.get("not", "")}
                if uzun:
                    k = g["uzun"]
                    oge["kucuk_resim"] = sorted(p.name for p in klasor.glob("*_kucuk_resim_B.jpg"))[:1]
                    oge["kucuk_resim_4K"] = sorted(p.name for p in klasor.glob("*_kucuk_resim_B_4K.jpg"))[:1]
                    oge["paket_4K"] = sorted(p.name for p in klasor.glob("*_4K_paket.zip"))[:1]
                    oge["baslik_4K"] = json.loads((KOK / "kanal" / "baslik_4k.json").read_text(encoding="utf-8")).get(k, "")
                    oge["ceviriler"] = sorted(p.name for p in klasor.glob("*_ceviriler.txt"))[:1]
                else:
                    satir = [s for s in (klasor / "0_TALIMAT.txt").read_text(encoding="utf-8").splitlines() if "İlgili video:" in s]
                    oge["ilgili_video"] = satir[0].split("İlgili video:", 1)[1].strip() if satir else ""
                plan.append(oge)
        gun += dt.timedelta(days=1)
    if not plan:
        raise SystemExit("Bu aralıkta yüklenecek bir şey yok.")
    (hedef / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy(KOK / "kanal" / "PC_YUKLEME.md", hedef / "PC_YUKLEME.md")
    for liste in ("japon_listesi.md", "noel_listesi.md"):                # oynatma listesi gerekirse bilgisayardaki Claude oluşturabilsin
        shutil.copy(KOK / "kanal" / liste, hedef / liste)
    # zip parçaları (sıkıştırmasız; her parça 380 MiB'ı aşmasın; dosyalar tarih sırasıyla, plan ve talimat ilk parçada)
    dosyalar = sorted((p for p in hedef.rglob("*") if p.is_file()), key=lambda p: (p.parent != hedef, str(p.relative_to(hedef))))
    gruplar, simdiki, boy = [], [], 0
    for p in dosyalar:
        b = p.stat().st_size
        if simdiki and boy + b > PARCA:
            gruplar.append(simdiki); simdiki, boy = [], 0
        simdiki.append(p); boy += b
    gruplar.append(simdiki)
    ad = f"DreamWindow_{bas}_{bit}"
    for i, g in enumerate(gruplar, 1):
        z = KOK / "hafta" / f"{ad}_parca{i}of{len(gruplar)}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
            for p in g:
                zf.write(p, f"{ad}/{p.relative_to(hedef)}")
        print(z.name, f"{z.stat().st_size / 1048576:.0f} MiB")
    for o in plan:
        print(o["tarih"], o["saat"], o["tur"], o["baslik"])


if __name__ == "__main__":
    main()
