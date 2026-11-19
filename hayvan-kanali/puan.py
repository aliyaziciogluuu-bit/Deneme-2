"""Ofis puan kartı: denetçilerin puanlarını ağırlıklı toplama çevirir, tabloya yazar ve gerçek YouTube verisiyle karşılaştırır.

Kullanım:
  python puan.py ekle 05-baykus --tur 2 --dogruluk 9 --guvenlik 9 --kanca 8 --anlatim 8 --baslik 8 --shorts 8 --ses 9 --gorsel 9 --teknik 9
  python puan.py gercek 01-sagir-yilan --to 2.7 --tutma30 59 --tutma80 25 --ortizleme 20.2
  python puan.py tablo          # kanal/puan_tablosu.md dosyasını yeniden yazar ve ekrana basar

Ölçütler (her biri 0-10, ağırlıklar toplam 100):
  Bilgi kontrolcüsü : dogruluk (20) doğruluk ve kaynak · guvenlik (10) güvenlik tavsiyeleri ve çekinceler
  Metin editörü     : kanca (20) giriş ve ilk iki dakikada izleyici tutma · anlatim (10) anlatım ve Türkçe
                      baslik (10) başlık, küçük resim yazısı, açıklama · shorts (5) Shorts kancası
  Kalite kontrol    : ses (10) seslendirme ve ses · gorsel (10) görsel, anatomi, kadraj · teknik (5) testler ve teslim
Eşikler: 85+ çok iyi · 80-84 teslim · 70-79 düzeltme turu · 70 altı RET (kanal sahibinin kararı, 19 Kasım).
Kırmızı çizgi: dogruluk ya da guvenlik 5 ve altıysa, ya da herhangi bir ölçüt 3 ve altıysa toplam ne olursa olsun RET.
"""
import argparse
import datetime
import json
import pathlib

KOK = pathlib.Path(__file__).parent
VERI = KOK / "kanal" / "puanlar.json"
TABLO = KOK / "kanal" / "puan_tablosu.md"

OLCUTLER = [  # (anahtar, ağırlık, denetçi, açıklama, sorumlu çalışan)
    ("dogruluk", 20, "bilgi kontrolcüsü", "Doğruluk ve kaynak", "senarist"),
    ("guvenlik", 10, "bilgi kontrolcüsü", "Güvenlik ve çekinceler", "senarist"),
    ("kanca", 20, "metin editörü", "Giriş ve izleyici tutma", "senarist"),
    ("anlatim", 10, "metin editörü", "Anlatım ve Türkçe", "senarist"),
    ("baslik", 10, "metin editörü", "Başlık, küçük resim, açıklama", "senarist"),
    ("shorts", 5, "metin editörü", "Shorts kancası", "senarist"),
    ("ses", 10, "kalite kontrol", "Seslendirme ve ses", "patron"),
    ("gorsel", 10, "kalite kontrol", "Görsel, anatomi, kadraj", "yapımcı"),
    ("teknik", 5, "kalite kontrol", "Testler ve teslim", "patron"),
]
assert sum(o[1] for o in OLCUTLER) == 100


def yukle():
    return json.loads(VERI.read_text(encoding="utf-8")) if VERI.exists() else {"videolar": {}}


def kaydet(veri):
    VERI.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def hesapla(p):
    toplam = round(sum(p[k] * a / 10 for k, a, *_ in OLCUTLER), 1)
    kirmizi = [k for k, *_ in OLCUTLER if p[k] <= 3] + [k for k in ("dogruluk", "guvenlik") if p[k] <= 5]
    if kirmizi:
        sonuc = "RET (kırmızı çizgi: " + ", ".join(sorted(set(kirmizi))) + ")"
    elif toplam >= 85:
        sonuc = "TESLİM (çok iyi)"
    elif toplam >= 80:
        sonuc = "TESLİM"
    elif toplam >= 70:
        sonuc = "DÜZELTME"
    else:
        sonuc = "RET"
    return toplam, sonuc


def tablo_yaz(veri):
    s = ["# Ofis puan tablosu – Avludaki Komşular", "",
         "Her denetçi kendi ölçütlerini 0–10 arası puanlar; ağırlıklı toplam 100 üzerindendir. "
         "**85+ çok iyi · 80–84 teslim · 70–79 düzeltme turu · 70 altı RET.** "
         "Kırmızı çizgi: doğruluk ya da güvenlik 5 ve altı, ya da herhangi bir ölçüt 3 ve altı ise toplam ne olursa olsun RET.",
         "", "Ölçütler ve ağırlıklar:", ""]
    s += [f"- **{acik}** ({a} puan): {den} puanlar · sorumlu: {sor}" for k, a, den, acik, sor in OLCUTLER]
    s += ["", "## Video puanları", "",
          "| Video | Tur | Tarih | Doğruluk | Güvenlik | Kanca | Anlatım | Başlık | Shorts | Ses | Görsel | Teknik | **Toplam** | Sonuç |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for ad, v in sorted(veri["videolar"].items()):
        for t in v.get("turlar", []):
            p = t["puan"]
            t["toplam"], t["sonuc"] = hesapla(p)
            s.append(f"| {ad} | {t['tur']} | {t['tarih']} | " + " | ".join(str(p[k]) for k, *_ in OLCUTLER)
                     + f" | **{t['toplam']}** | {t['sonuc']} |")
    s += ["", "## Gerçek performans (yayından sonra)", "",
          "Puanın işe yarayıp yaramadığını burada görürüz: kanca puanı yüksek videoların 0:30 ve 1:20 tutması da yüksek mi?", "",
          "| Video | Son puan | Kanca puanı | Tıklama oranı % | Tutma 0:30 % | Tutma 1:20 % | Ort. izleme % |",
          "|---|---|---|---|---|---|---|"]
    for ad, v in sorted(veri["videolar"].items()):
        g = v.get("gercek")
        if not g:
            continue
        son = v["turlar"][-1] if v.get("turlar") else None
        s.append(f"| {ad} | {son['toplam'] if son else '–'} | {son['puan']['kanca'] if son else '–'} | "
                 f"{g.get('to', '–')} | {g.get('tutma30', '–')} | {g.get('tutma80', '–')} | {g.get('ortizleme', '–')} |")
    s += ["", "## Çalışan karnesi", "",
          "İlk turdaki puanlar çalışanın işinin ilk teslimdeki kalitesini gösterir (düzeltmeden önce).", "",
          "| Çalışan | Video sayısı | İlk tur ortalaması (kendi ölçütleri, 10 üzerinden) | İlk turda RET/DÜZELTME |", "|---|---|---|---|"]
    for calisan in ("senarist", "yapımcı", "patron"):
        anahtarlar = [k for k, _, _, _, sor in OLCUTLER if sor == calisan]
        ilkler = [v["turlar"][0] for v in veri["videolar"].values() if v.get("turlar")]
        if not ilkler:
            continue
        ort = sum(sum(t["puan"][k] for k in anahtarlar) / len(anahtarlar) for t in ilkler) / len(ilkler)
        kotu = sum(1 for t in ilkler if any(t["puan"][k] < 7 for k in anahtarlar))
        s.append(f"| {calisan} | {len(ilkler)} | {ort:.1f} | {kotu} |")
    # Ölçüt eğilimi: çalışanların ilk turda ne kadar iyi iş teslim ettiği videodan videoya izlenir
    s += ["", "## Ölçüt eğilimi (ilk tur → son tur, videolar tarih sırasıyla)", "",
          "Hedef: her ölçütte ilk turda 9. Bir ölçüt yerinde sayıyorsa dersler defterindeki \"Puandan dersler\" satırı sertleştirilir.", "",
          "| Ölçüt | " + " | ".join(ad for ad, v in sorted(veri["videolar"].items()) if v.get("turlar")) + " |",
          "|---|" + "---|" * sum(1 for v in veri["videolar"].values() if v.get("turlar"))]
    for k, _, _, acik, _ in OLCUTLER:
        hucre = []
        for ad, v in sorted(veri["videolar"].items()):
            if not v.get("turlar"):
                continue
            ilk, son = v["turlar"][0]["puan"][k], v["turlar"][-1]["puan"][k]
            hucre.append(f"{ilk:g} → {son:g}" if ilk != son else f"{ilk:g}")
        s.append(f"| {acik} | " + " | ".join(hucre) + " |")
    kacan = [(ad, k) for ad, v in veri["videolar"].items() for k in v.get("kacirilan", [])]
    s += ["", "## Denetçilerin kaçırdığı hatalar", "",
          "Onaydan sonra ortaya çıkan hatalar denetçinin karnesine yazılır."]
    s += [f"- {ad}: {k}" for ad, k in kacan] or ["- (yok)"]
    TABLO.write_text("\n".join(s) + "\n", encoding="utf-8")
    return "\n".join(s)


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    e = alt.add_parser("ekle")
    e.add_argument("video"); e.add_argument("--tur", type=int, required=True)
    for k, *_ in OLCUTLER:
        e.add_argument(f"--{k}", type=float, required=True)
    g = alt.add_parser("gercek")
    g.add_argument("video")
    for k in ("to", "tutma30", "tutma80", "ortizleme"):
        g.add_argument(f"--{k}", type=float)
    k_ = alt.add_parser("kacirilan")
    k_.add_argument("video"); k_.add_argument("aciklama")
    alt.add_parser("tablo")
    a = ap.parse_args()
    veri = yukle()
    if a.komut == "ekle":
        p = {k: getattr(a, k) for k, *_ in OLCUTLER}
        assert all(0 <= x <= 10 for x in p.values()), "puanlar 0-10 arası olmalı"
        toplam, sonuc = hesapla(p)
        v = veri["videolar"].setdefault(a.video, {"turlar": []})
        v["turlar"] = [t for t in v["turlar"] if t["tur"] != a.tur] + [
            {"tur": a.tur, "tarih": datetime.date.today().isoformat(), "puan": p, "toplam": toplam, "sonuc": sonuc}]
        v["turlar"].sort(key=lambda t: t["tur"])
        print(f"{a.video} tur {a.tur}: {toplam}/100 → {sonuc}")
    elif a.komut == "gercek":
        v = veri["videolar"].setdefault(a.video, {"turlar": []})
        v["gercek"] = {k: getattr(a, k) for k in ("to", "tutma30", "tutma80", "ortizleme") if getattr(a, k) is not None}
    elif a.komut == "kacirilan":
        veri["videolar"].setdefault(a.video, {"turlar": []}).setdefault("kacirilan", []).append(a.aciklama)
    kaydet(veri)
    metin = tablo_yaz(veri)
    if a.komut == "tablo":
        print(metin)


if __name__ == "__main__":
    main()
