"""Gerçek hayvan görüntüsü bulucu: Wikimedia Commons'tan lisansı uygun fotoğraf ve videoları aday olarak indirir.

Neden: Yapay zekâ görsellerinde anatomi hataları (bacaklı yılan, pençeli kurbağa, delik gibi yuva) en çok para ve
zaman kaybettiren iş. Gerçek fotoğrafta bu hata olmaz ve belgesel izleyicisi gerçek görüntüye daha çok güvenir.
Kural: önce gerçek görüntü aranır; uygun aday yoksa gorsel.py ile yapay zekâ görseli üretilir.

Kullanım (hayvan-kanali/ içinde):
  python3 gercek_gorsel.py 08-kara-kurbagasi ara portre "Bufo bufo portrait"      # fotoğraf adayları
  python3 gercek_gorsel.py 08-kara-kurbagasi ara goc "Bufo bufo migration" --video  # video adayları
  python3 gercek_gorsel.py 08-kara-kurbagasi ara yol "toad road crossing" --baslik toad   # başlıkta geçmesi gereken söz
  python3 gercek_gorsel.py 08-kara-kurbagasi inat portre "Bufo bufo" --turkiye  # iNaturalist (tür doğrulanmış), Türkiye'den
  python3 gercek_gorsel.py 08-kara-kurbagasi sec portre 3                            # 3. adayı gorseller/portre.jpg yap
  python3 gercek_gorsel.py 08-kara-kurbagasi kunye                                   # açıklama için atıf listesi

Lisans: yalnızca kamu malı, CC0, CC BY ve CC BY-SA kabul edilir (ticari kullanım ve değiştirme serbest).
NC (ticari olmayan) ve ND (değiştirilemez) lisanslar elenir. CC BY / BY-SA için açıklamada yazar ve lisans belirtilir
(`kunye` komutu bu satırları üretir). Aday bilgileri <video>/gercek_adaylar/<ad>.json dosyasında tutulur.
"""
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse

from PIL import Image, ImageDraw, ImageFont

KOK = pathlib.Path(__file__).parent
API = "https://commons.wikimedia.org/w/api.php"
UA = "AvluKomsularDocBot/0.1 (non-commercial educational documentary script)"
UYGUN = re.compile(r"^(public domain|pd|cc0|cc[ -]by(-sa)?[ -]?\d|cc[ -]by(-sa)?$|attribution)", re.I)
YASAK = re.compile(r"\b(nc|nd)\b|non-?commercial|noderiv", re.I)
EN_AZ = 1600  # piksel (uzun kenar); 1920x1080 videoda yakınlaşma payı için


def istek(params, deneme=4):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    for bekle in (0, 20, 60, 120)[:deneme]:
        time.sleep(bekle or 1)
        r = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, "-w", "\n%{http_code}", url], capture_output=True, text=True)
        govde, _, kod = r.stdout.rpartition("\n")
        if kod == "200":
            return json.loads(govde)
        print(f"  Commons yanıtı {kod}, {bekle or 1} sn sonra yeniden", flush=True)
    raise SystemExit("Commons'a ulaşılamadı (çok istek ya da ağ). Biraz sonra yeniden dene.")


def temiz(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def ara(klasor, ad, sorgu, video=False, adet=8, baslik_suzgec=None):
    tur = "filetype:video" if video else "filetype:bitmap"
    d = istek({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{sorgu} {tur}",
               "gsrlimit": 30, "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
               "iiextmetadatafilter": "LicenseShortName|Artist|ImageDescription|Credit"})
    sayfalar = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    hedef = klasor / "gercek_adaylar"
    hedef.mkdir(exist_ok=True)
    adaylar, elenen = [], 0
    tur_adi = baslik_suzgec or (" ".join(sorgu.split()[:2]) if re.match(r"^[A-Z][a-z]+ [a-z]+", sorgu) else "")
    for p in sayfalar:
        if tur_adi and tur_adi.lower().replace(" ", "") not in p["title"].lower().replace(" ", "").replace("_", "").replace("-", ""):
            elenen += 1  # başka tür (ör. "Bufo bufo" aramasında Bufo alvarius) gelmesin
            continue
        ii = (p.get("imageinfo") or [{}])[0]
        m = ii.get("extmetadata", {})
        lisans = temiz(m.get("LicenseShortName", {}).get("value", ""))
        if not UYGUN.search(lisans) or YASAK.search(lisans):
            elenen += 1
            continue
        if max(ii.get("width", 0), ii.get("height", 0)) < EN_AZ:
            elenen += 1
            continue
        n = len(adaylar) + 1
        uzanti = ".webm" if video else ".jpg"
        dosya = hedef / f"{ad}_{n}{uzanti}"
        kaynak = ii["url"]  # upload.wikimedia.org (thumb.wikimedia.org ağ izninde yok)
        for bekle in (8, 45, 120, 240):  # upload.wikimedia.org hızlı indirmede 429 veriyor: yavaşla ve yeniden dene
            r = subprocess.run(["curl", "-s", "-L", "-m", "180", "-A", UA, "-o", str(dosya), "-w", "%{http_code}", kaynak], capture_output=True, text=True)
            time.sleep(bekle)
            if r.stdout.strip() != "429":
                break
        if r.returncode or r.stdout.strip() != "200":
            print(f"  indirilemedi ({r.stdout.strip() or r.returncode}): {p['title'][:60]}")
            dosya.unlink(missing_ok=True)
            continue
        if not video:
            try:
                im = Image.open(dosya).convert("RGB")
                im.thumbnail((3000, 3000))
                im.save(dosya, quality=93)
            except Exception:
                dosya.unlink(missing_ok=True)
                continue
        adaylar.append({"n": n, "dosya": dosya.name, "baslik": p["title"], "sayfa": ii.get("descriptionurl"),
                        "yazar": temiz(m.get("Artist", {}).get("value", "")) or "bilinmiyor", "lisans": lisans,
                        "boyut": f"{ii.get('width')}x{ii.get('height')}", "aciklama": temiz(m.get("ImageDescription", {}).get("value", ""))[:200]})
        if len(adaylar) >= adet:
            break
    (hedef / f"{ad}.json").write_text(json.dumps({"sorgu": sorgu, "video": video, "adaylar": adaylar}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{ad}: {len(adaylar)} aday indirildi, {elenen} dosya lisans ya da boyut yüzünden elendi → {hedef}")
    if adaylar and not video:
        sayfa_yap(hedef, ad, adaylar)
    for a in adaylar:
        print(f"  {a['n']}. {a['baslik'][:70]} | {a['lisans']} | {a['yazar'][:40]} | {a['boyut']}")


INAT = "https://api.inaturalist.org/v1/observations"
TURKIYE = 7183  # iNaturalist yer kimliği


def inat(klasor, ad, tur, turkiye=False, adet=8):
    """iNaturalist: türü topluluk tarafından doğrulanmış (research grade) gözlemlerin serbest lisanslı fotoğrafları."""
    # Ad benzerliğiyle başka canlı gelmesin ("Bufo" → Bassaniodes bufo örümceği): önce tam adla tür kimliğini bul.
    tx = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, "https://api.inaturalist.org/v1/taxa?" + urllib.parse.urlencode({"q": tur, "per_page": 30})],
                        capture_output=True, text=True)
    eslesen = [x for x in json.loads(tx.stdout).get("results", []) if x.get("name", "").lower() == tur.lower()]
    if not eslesen:
        raise SystemExit(f"iNaturalist'te tam adı '{tur}' olan takson yok; bilimsel adı kontrol et.")
    print(f"  takson: {eslesen[0]['name']} ({eslesen[0].get('rank')}, kimlik {eslesen[0]['id']})")
    params = {"taxon_id": eslesen[0]["id"], "photos": "true", "photo_license": "cc0,cc-by,cc-by-sa", "quality_grade": "research",
              "per_page": 40, "order_by": "votes"}
    if turkiye:
        params["place_id"] = TURKIYE
    url = INAT + "?" + urllib.parse.urlencode(params)
    r = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, url], capture_output=True, text=True)
    sonuc = json.loads(r.stdout).get("results", [])
    hedef = klasor / "gercek_adaylar"
    hedef.mkdir(exist_ok=True)
    adaylar = []
    for g in sonuc:
        for foto in g.get("photos", [])[:1]:  # gözlem başına bir fotoğraf (çeşitlilik)
            lisans = (foto.get("license_code") or "").upper()
            if lisans not in ("CC0", "CC-BY", "CC-BY-SA"):
                continue
            n = len(adaylar) + 1
            dosya = hedef / f"{ad}_{n}.jpg"
            kaynak = foto["url"].replace("/square.", "/original.")
            k = subprocess.run(["curl", "-s", "-L", "-m", "120", "-A", UA, "-o", str(dosya), "-w", "%{http_code}", kaynak], capture_output=True, text=True)
            time.sleep(1)
            if k.stdout.strip() != "200":
                dosya.unlink(missing_ok=True)
                continue
            try:
                im = Image.open(dosya).convert("RGB")
            except Exception:
                dosya.unlink(missing_ok=True)
                continue
            if max(im.size) < 1400:
                dosya.unlink(missing_ok=True)
                continue
            im.save(dosya, quality=93)
            yer = g.get("place_guess") or ""
            adaylar.append({"n": n, "dosya": dosya.name, "baslik": f"iNaturalist gözlem {g['id']} ({g.get('taxon', {}).get('name', tur)})",
                            "sayfa": f"https://www.inaturalist.org/observations/{g['id']}",
                            "yazar": foto.get("attribution", "").replace("(c) ", "© "), "lisans": lisans.replace("-", " ").replace("CC ", "CC "),
                            "boyut": f"{im.size[0]}x{im.size[1]}", "aciklama": yer[:120]})
        if len(adaylar) >= adet:
            break
    (hedef / f"{ad}.json").write_text(json.dumps({"sorgu": f"iNaturalist: {tur}" + (" (Türkiye)" if turkiye else ""), "video": False, "adaylar": adaylar}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{ad}: iNaturalist'ten {len(adaylar)} aday → {hedef}")
    if adaylar:
        sayfa_yap(hedef, ad, adaylar)
    for a in adaylar:
        print(f"  {a['n']}. {a['baslik']} | {a['lisans']} | {a['yazar'][:50]} | {a['boyut']} | {a['aciklama'][:40]}")


def sayfa_yap(hedef, ad, adaylar):
    w, h = 640, 400
    sayfa = Image.new("RGB", (w * 4, h * ((len(adaylar) + 3) // 4)), "black")
    try:
        font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 28)
    except OSError:
        font = None
    for i, a in enumerate(adaylar):
        try:
            im = Image.open(hedef / a["dosya"]).convert("RGB")
        except Exception:
            continue
        im.thumbnail((w, h))
        sayfa.paste(im, ((i % 4) * w, (i // 4) * h))
        ImageDraw.Draw(sayfa).text(((i % 4) * w + 10, (i // 4) * h + 8), f"#{a['n']}", fill="yellow", font=font)
    sayfa.save(hedef / f"{ad}_secim.jpg", quality=85)
    print(f"  seçim sayfası: {hedef / (ad + '_secim.jpg')}")


def sec(klasor, ad, n):
    bilgi = json.loads((klasor / "gercek_adaylar" / f"{ad}.json").read_text(encoding="utf-8"))
    a = next(x for x in bilgi["adaylar"] if x["n"] == int(n))
    kaynak = klasor / "gercek_adaylar" / a["dosya"]
    if bilgi["video"]:
        (klasor / "klipler").mkdir(exist_ok=True)
        hedef = klasor / "klipler" / f"{ad}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(kaynak), "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(hedef)], check=True)
    else:
        (klasor / "gorseller").mkdir(exist_ok=True)
        hedef = klasor / "gorseller" / f"{ad}.jpg"
        Image.open(kaynak).convert("RGB").save(hedef, quality=95)
    kayit_yol = klasor / "gercek_kaynaklar.json"
    kayit = json.loads(kayit_yol.read_text(encoding="utf-8")) if kayit_yol.exists() else {}
    kayit[ad] = {k: a[k] for k in ("baslik", "sayfa", "yazar", "lisans", "boyut")} | {"tur": "video" if bilgi["video"] else "fotoğraf"}
    kayit_yol.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{ad}: aday {n} seçildi → {hedef.relative_to(KOK)} ({a['lisans']}, {a['yazar'][:40]})")


def kunye(klasor):
    kayit_yol = klasor / "gercek_kaynaklar.json"
    if not kayit_yol.exists():
        print("Gerçek görüntü kullanılmadı.")
        return
    kayit = json.loads(kayit_yol.read_text(encoding="utf-8"))
    print("Gerçek görüntüler (Wikimedia Commons / iNaturalist):")
    for ad, a in kayit.items():
        dosya = a["baslik"].replace("File:", "").replace("Dosya:", "")
        print(f"- {dosya} – {a['yazar']} – {a['lisans']} – {a['sayfa'].replace('https://', '').replace('www.', '')}")


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    klasor, komut = KOK / sys.argv[1], sys.argv[2]
    if komut == "ara" and len(sys.argv) >= 5:
        suzgec = sys.argv[sys.argv.index("--baslik") + 1] if "--baslik" in sys.argv else None
        ara(klasor, sys.argv[3], sys.argv[4], video="--video" in sys.argv, baslik_suzgec=suzgec)
    elif komut == "inat" and len(sys.argv) >= 5:
        inat(klasor, sys.argv[3], sys.argv[4], turkiye="--turkiye" in sys.argv)
    elif komut == "sec" and len(sys.argv) >= 5:
        sec(klasor, sys.argv[3], sys.argv[4])
    elif komut == "kunye":
        kunye(klasor)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
