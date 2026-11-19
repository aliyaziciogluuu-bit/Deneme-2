"""Bir uzun videonun shorts.json dosyasından dikey Shorts klasörlerini kurar.

Kullanım:  python shorts_kur.py 01-sagir-yilan     → 01-sagir-yilan/shorts/<ad>/ {senaryo.json, cekimler.json, gorseller→, klipler→}
Sonra her Shorts için:  python seslendir_bulut.py 01-sagir-yilan/shorts/<ad>
                        python video.py 01-sagir-yilan/shorts/<ad>
                        python son_kontrol.py 01-sagir-yilan/shorts/<ad>

shorts.json biçimi: {"shorts": [{"ad": "s1-goz", "baslik": "...", "aciklama": "...", "etiketler": [...],
                                  "ust_yazi": ["YILAN DEĞİL!", "Göz kırpıyor"],
                                  "cumleler": [{"yazi": "...", "gorsel": "portre", "x": 0.75, "klip": "goz", "kx": 0.4, "etiket": "..."}]}]}
Kural: Shorts'larda yalnızca ana videoda bilgi kontrolünden geçmiş bilgiler kullanılır (yeni iddia eklenmez).
"x" dikey kesitin yatay merkezi (0-1); kamera yavaşça yakınlaşır. "x2" verilirse kamera x'ten x2'ye kayar; "aw"/"ay" başlangıç kadrajının genişliği ve dikey merkezi (etiket ya da üst yazı hayvanın yüzüne biniyorsa).
"""
import json
import os
import pathlib
import sys

KOK = pathlib.Path(__file__).parent



def yaz_degistiyse(yol, metin):
    """İçerik aynıysa dosyaya dokunma: otomatik bekçi videonun eski kalıp kalmadığını dosya tarihinden anlar."""
    if yol.exists() and yol.read_text(encoding="utf-8") == metin:
        return
    yol.write_text(metin, encoding="utf-8")

def kur(video: str):
    ana = KOK / video
    tanim = json.loads((ana / "shorts.json").read_text(encoding="utf-8"))
    ana_senaryo = json.loads((ana / "senaryo.json").read_text(encoding="utf-8"))
    for sh in tanim["shorts"]:
        k = ana / "shorts" / sh["ad"]
        k.mkdir(parents=True, exist_ok=True)
        for alt in ("gorseller", "klipler"):
            bag = k / alt
            if not bag.exists() and (ana / alt).exists():
                os.symlink(os.path.join("..", "..", alt), bag)
        amb = dict(ana_senaryo.get("ambiyans") or {})
        if amb:
            amb["dosya"] = os.path.join("..", "..", amb["dosya"])
        senaryo = {"dikey": True, "baslik": sh["baslik"], "aciklama": sh["aciklama"], "etiketler": sh["etiketler"],
                   "ust_yazi": sh["ust_yazi"], "kaynaklar": [], "beyan": sh.get("beyan", "Görseller yapay zekâ ile üretilmiş çizimlerdir; seslendirme yapay zekâ ile yapılmıştır."),
                   "ambiyans": amb, "ana_video": ana_senaryo["baslik"],
                   "sahneler": [{"ad": sh["baslik"], "cumleler": [{k2: v for k2, v in c.items() if k2 in ("yazi", "ses")} for c in sh["cumleler"]]}]}
        yaz_degistiyse(k / "senaryo.json", json.dumps(senaryo, ensure_ascii=False, indent=2) + "\n")
        cekimler = []
        for c in sh["cumleler"]:
            x = c.get("x", 0.5)
            ck = {"n": 1, "gorsel": c["gorsel"], "a": [x, c.get("ay", c.get("y", 0.5)), c.get("aw", 1.0)], "b": [c.get("x2", x), c.get("y", 0.5), c.get("w", 0.85)]}
            for anahtar in ("klip", "kx", "kz", "ky", "etiket", "karart"):
                if anahtar in c:
                    ck[anahtar] = c[anahtar]
            cekimler.append(ck)
        yaz_degistiyse(k / "cekimler.json", json.dumps({"cekimler": cekimler}, ensure_ascii=False, indent=1))
        print("kuruldu:", k.relative_to(KOK), len(cekimler), "cümle")


if __name__ == "__main__":
    for v in sys.argv[1:]:
        kur(v)
