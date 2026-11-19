"""Bir videonun teslim dosyalarını teslim/<video>/ klasörüne anlaşılır adlarla kopyalar, kaynakla birebir aynı olduğunu
doğrular (cmp) ve kanal sahibine verilecek yükleme listesini yazar.

Kullanım:  python teslim.py 06-karga

Ders (19 Kasım, baykuş): video yeniden üretildi ama teslim klasöründe eski sürüm kalmıştı. Bu betik her teslimde
eski kopyaları siler, yenilerini kopyalar ve her dosyayı kaynağıyla bayt bayt karşılaştırır. Son kontrolü geçmemiş
(son_kontrol.txt'de KALDI olan ya da videodan eski) bir video teslim edilmez.
"""
import filecmp
import json
import pathlib
import shutil
import sys

KOK = pathlib.Path(__file__).parent


def gecti_mi(klasor):
    sk, v = klasor / "son_kontrol.txt", klasor / "video.mp4"
    if not sk.exists() or not v.exists():
        return False, "son kontrol ya da video yok"
    if sk.stat().st_mtime < v.stat().st_mtime:
        return False, "son kontrol videodan eski (yeniden üretimden sonra test çalıştırılmamış)"
    if "KALDI" in sk.read_text(encoding="utf-8"):
        return False, "son kontrolde KALDI var"
    return True, ""


def main():
    ad = sys.argv[1]
    klasor = KOK / ad
    kisa = ad.split("-", 1)[1]
    hedef = KOK / "teslim" / ad
    if hedef.exists():
        shutil.rmtree(hedef)
    hedef.mkdir(parents=True)
    liste = []
    ok, neden = gecti_mi(klasor)
    if not ok:
        raise SystemExit(f"TESLİM EDİLMEZ: uzun video – {neden}")
    for kaynak, isim in [("video.mp4", "video.mp4"), ("kapak.jpg", "kucuk-resim-A.jpg"), ("kapak_B.jpg", "kucuk-resim-B.jpg"),
                         ("kapak_C.jpg", "kucuk-resim-C.jpg"), ("altyazi.srt", "altyazi.srt"), ("yukleme.txt", "yukleme.txt")]:
        if (klasor / kaynak).exists():
            liste.append((klasor / kaynak, hedef / f"{kisa}-{isim}"))
    for n, sh in enumerate(sorted((klasor / "shorts").glob("*/")) if (klasor / "shorts").exists() else [], 1):
        ok, neden = gecti_mi(sh)
        if not ok:
            raise SystemExit(f"TESLİM EDİLMEZ: Shorts {sh.name} – {neden}")
        liste += [(sh / "video.mp4", hedef / f"shorts{n}-{sh.name}.mp4"), (sh / "yukleme.txt", hedef / f"shorts{n}-{sh.name}-yukleme.txt")]
    for k, h in liste:
        shutil.copy2(k, h)
        if not filecmp.cmp(k, h, shallow=False):
            raise SystemExit(f"KOPYA HATALI: {h.name}")
    sen = json.loads((klasor / "senaryo.json").read_text(encoding="utf-8"))
    yorum = next((l.split(":**", 1)[1].strip() for l in (KOK / "kanal" / "etkilesim.md").read_text(encoding="utf-8").split("\n")
                  if l.startswith(f"- **{ad[:2]} ")), sen.get("yorum_sorusu", ""))
    adimlar = [f"# {sen['baslik']} – yükleme listesi", "",
               "1. Studio → Oluştur → Video yükle → video dosyası.",
               "2. Başlık, açıklama (bölümlerle birlikte) ve etiketleri yükleme metninden kopyala.",
               "3. Küçük resim: A dosyası. B ve C varsa \"Test ve karşılaştır\" ile üçünü birlikte yükle.",
               "4. Kitle: çocuklara özel değil. Oynatma listesi: Evin Çevresindeki Hayvanlar.",
               "5. Video öğeleri → Altyazı → Dosya yükle → Zamanlamayla → altyazı dosyası.",
               "6. Görünürlük → Planla (tarih ve saat teslim raporunda).",
               "7. Shorts'lar: ayrı yüklenir, uzun video yayına girdikten sonraki günlerde 12:00'ye planlanır; İlgili video = bu video.",
               "8. Video yayına girince sabit yorum:", f"   {yorum}", "", "Dosyalar:"]
    adimlar += [f"- {h.name}" for _, h in liste]
    (hedef / "YUKLEME_LISTESI.txt").write_text("\n".join(adimlar) + "\n", encoding="utf-8")
    print(f"{len(liste)} dosya kopyalandı ve doğrulandı → {hedef.relative_to(KOK)}")
    for _, h in liste:
        print("  ", h.name)


if __name__ == "__main__":
    main()
