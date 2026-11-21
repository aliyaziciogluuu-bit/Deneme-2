"""Freesound'da ambiyans kaydı arar, indirir ve dinleme örnekleri hazırlar.

API anahtarı bu betikte yoktur: ortamın ağ geçidi freesound.org isteklerine kendisi ekler.

Kullanım:
  python freesound.py ara "fireplace crackling"        # uzun ve telifsiz kayıtları listeler
  python freesound.py ara "rain on window" --sure 600    # en az 10 dakikalık olanlar
  python freesound.py indir 12345 67890 --klasor adaylar # kayıtları indirir, her birinden 40 sn örnek çıkarır

Yalnızca ticari kullanıma açık lisanslar aranır: CC0 (kaynak göstermek gerekmez) ve
CC BY (açıklamada kaynak göstermek zorunlu). Ticari kullanıma kapalı CC BY-NC kayıtlar elenir.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

API = "https://freesound.org/apiv2"
ALANLAR = "id,name,duration,license,avg_rating,num_ratings,num_downloads,username,tags,previews,samplerate,channels,url"


def getir(yol: str, **parametre):
    adres = f"{API}/{yol}?{urllib.parse.urlencode(parametre)}" if parametre else f"{API}/{yol}"
    with urllib.request.urlopen(urllib.request.Request(adres, headers={"User-Agent": "DreamWindow/1.0"}), timeout=60) as r:
        return json.load(r)


def lisans_adi(url: str) -> str:
    if "publicdomain/zero" in url:
        return "CC0"
    if "/by/" in url:
        return "CC BY " + url.rstrip("/").split("/")[-1]
    if "sampling+" in url:
        return "Sampling+"
    return url


def ara(sorgu: str, sure: int, adet: int):
    filtre = f'duration:[{sure} TO *] (license:"Creative Commons 0" OR license:"Attribution")'
    sonuc = getir("search/text/", query=sorgu, filter=filtre, fields=ALANLAR, sort="rating_desc", page_size=adet)
    print(f"{sonuc['count']} kayıt bulundu (en az {sure} sn, CC0 ya da CC BY)\n")
    for s in sonuc["results"]:
        print(f"{s['id']:>8}  {s['name'][:52]:<52}  {s['duration'] / 60:5.1f} dk  {lisans_adi(s['license']):<10}"
              f"  puan {s.get('avg_rating') or 0:.1f} ({s.get('num_ratings', 0)})  indirme {s.get('num_downloads', 0)}  {s['username']}")


def indir(kimlikler, klasor: pathlib.Path, ornek_sn: int):
    klasor.mkdir(parents=True, exist_ok=True)
    kayitlar = []
    for k in kimlikler:
        s = getir(f"sounds/{k}/", fields=ALANLAR)
        # Asıl dosyayı indirmek OAuth2 ister; API anahtarıyla en yüksek kaliteli önizleme (ogg) indirilebilir.
        adres = s["previews"]["preview-hq-ogg"]
        hedef = klasor / f"{k}.ogg"
        if not hedef.exists():
            urllib.request.urlretrieve(adres, hedef)
        ornek = klasor / f"{k}_ornek.mp3"
        orta = max(s["duration"] / 2 - ornek_sn / 2, 0)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(orta), "-t", str(ornek_sn), "-i", str(hedef),
                        "-af", f"afade=t=in:d=1,afade=t=out:st={ornek_sn - 1.5}:d=1.5", "-b:a", "160k", str(ornek)], check=True)
        kayitlar.append({"id": s["id"], "ad": s["name"], "sahibi": s["username"], "lisans": lisans_adi(s["license"]),
                         "lisans_url": s["license"], "sayfa": s["url"], "sure_dk": round(s["duration"] / 60, 1), "dosya": hedef.name})
        print(f"{k}: {s['name'][:50]} ({lisans_adi(s['license'])}) → {hedef.name}, örnek {ornek.name}")
    (klasor / "kayitlar.json").write_text(json.dumps(kayitlar, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    alt = p.add_subparsers(dest="komut", required=True)
    a = alt.add_parser("ara")
    a.add_argument("sorgu")
    a.add_argument("--sure", type=int, default=300)
    a.add_argument("--adet", type=int, default=15)
    i = alt.add_parser("indir")
    i.add_argument("kimlik", nargs="+")
    i.add_argument("--klasor", default="adaylar")
    i.add_argument("--ornek", type=int, default=40)
    g = p.parse_args()
    if g.komut == "ara":
        ara(g.sorgu, g.sure, g.adet)
    else:
        indir(g.kimlik, pathlib.Path(g.klasor), g.ornek)


if __name__ == "__main__":
    sys.exit(main())
