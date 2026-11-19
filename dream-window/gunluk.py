"""O günün yüklenecek dosyalarını tarihli, karışmayan isimlerle tek klasörde toplar.

Kullanım:  python gunluk.py 2026-11-15
Çıktı:     bugun/2026-11-15/ içinde videolar, küçük resim, metinler ve TALIMAT.txt
           (dosyalar kopyalanmaz, sabit bağlantı oluşturulur; disk dolmaz)
"""
import json
import os
import pathlib
import sys
import zipfile

KOK = pathlib.Path(__file__).parent
AD = {"01-rainy-cabin": "yagmurlu_kulube", "03-christmas-cabin": "noel_kulubesi", "04-snowy-village": "karli_kasaba",
      "05-snowy-library": "kutuphane", "06-rainy-cafe": "yagmurlu_kafe", "07-christmas-eve": "noel_arifesi",
      "08-attic-bedroom": "cati_kati", "09-lighthouse": "deniz_feneri", "10-japanese-garden": "japon_bahcesi",
      "11-aurora-igloo": "kuzey_isiklari", "12-christmas-train": "noel_treni",
      "13-forest-cabin": "orman_kulubesi", "14-new-year-loft": "yilbasi_cati_kati", "15-rainy-bookshop": "yagmurlu_kitapci", "16-mountain-chalet": "alp_dag_evi", "17-dining-car": "yemekli_vagon", "18-rainy-greenhouse": "yagmurlu_sera", "19-castle-library": "kale_kutuphanesi", "20-lake-cabin": "gol_kulubesi",
      "21-paris-apartment": "paris_dairesi", "22-tokyo-apartment": "tokyo_dairesi", "23-seaside-cottage": "deniz_kenari_kulube", "24-canal-houseboat": "kanal_teknesi", "25-rainforest-treehouse": "orman_agac_evi", "26-mountain-temple": "dag_tapinagi", "27-snowy-observatory": "karli_gozlemevi", "28-cherry-blossom-teahouse": "kiraz_cay_evi"}
TR = {"yagmurlu_kulube": "Yağmurlu kulübe", "noel_kulubesi": "Noel kulübesi", "karli_kasaba": "Karlı kasaba", "kutuphane": "Kütüphane",
      "yagmurlu_kafe": "Yağmurlu kafe", "noel_arifesi": "Noel arifesi", "cati_kati": "Çatı katı", "deniz_feneri": "Deniz feneri",
      "japon_bahcesi": "Japon bahçesi", "kuzey_isiklari": "Kuzey ışıkları iglo", "noel_treni": "Noel treni",
      "orman_kulubesi": "Karlı orman kulübesi", "yilbasi_cati_kati": "Yılbaşı çatı katı", "yagmurlu_kitapci": "Yağmurlu kitapçı", "alp_dag_evi": "Alp dağ evi", "yemekli_vagon": "Kış treni yemekli vagon", "yagmurlu_sera": "Yağmurlu sera", "kale_kutuphanesi": "Kale kütüphanesi", "gol_kulubesi": "Göl kenarı kulübe",
      "paris_dairesi": "Karlı Paris dairesi", "tokyo_dairesi": "Yağmurlu Tokyo dairesi", "deniz_kenari_kulube": "Fırtınalı deniz kenarı kulübe", "kanal_teknesi": "Kanal teknesi", "orman_agac_evi": "Yağmur ormanı ağaç evi", "dag_tapinagi": "Karlı dağ tapınağı", "karli_gozlemevi": "Karlı gözlemevi", "kiraz_cay_evi": "Kiraz çiçekli çay evi"}

# takvimde "uzun" olarak geçmeyen, doğrudan YouTube'da planlanan uzun videolar (yayın tarihi)
YOUTUBEDA_PLANLI = {"05-snowy-library": "2026-11-15", "12-christmas-train": "2026-12-23", "06-rainy-cafe": "2026-11-21",
                    "08-attic-bedroom": "2026-11-25"}


def bagla(kaynak: pathlib.Path, hedef: pathlib.Path):
    if not kaynak.exists():
        raise SystemExit(f"Eksik dosya: {kaynak}")
    if hedef.exists():
        hedef.unlink()
    os.link(kaynak, hedef)


def uzun_surum(klasor: pathlib.Path):
    """3 saatlik sürüm varsa onu, yoksa 1 saatlik sürümü döndürür."""
    if (klasor / "video_3saat.mp4").exists():
        return klasor / "video_3saat.mp4", klasor / "kapak_3saat.jpg", klasor / "yukleme_3saat.txt", "3 saatlik"
    return klasor / "video.mp4", klasor / "kapak.jpg", klasor / "yukleme.txt", "1 saatlik"


def main():
    tarih = sys.argv[1]
    takvim = json.loads((KOK / "kanal" / "takvim.json").read_text(encoding="utf-8"))
    if tarih not in takvim:
        raise SystemExit(f"{tarih} için plan yok")
    gun = takvim[tarih]
    if not any(k in gun for k in ("uzun", "shorts", "not")):
        raise SystemExit(f"{tarih} için plan yok (bugünkü yüklemeler önceden planlandı)")
    hedef = KOK / "bugun" / tarih
    hedef.mkdir(parents=True, exist_ok=True)
    adimlar, sira = [f"DREAM WINDOW – {tarih} YÜKLEME TALİMATI", ""], 1
    if "uzun" in gun:
        k = gun["uzun"]; ad = AD[k]
        video, kapak, metin, tur = uzun_surum(KOK / k)
        bagla(video, hedef / f"{sira}_UZUN_{ad}_video.mp4")
        bagla(kapak, hedef / f"{sira}_UZUN_{ad}_kucuk_resim.jpg")
        bagla(metin, hedef / f"{sira}_UZUN_{ad}_metin.txt")
        secenekler = [h for h in "BC" if (kapak.parent / f"{kapak.stem}_{h}.jpg").exists()]
        for h in secenekler:                                           # YouTube "Test et ve karşılaştır" için ek küçük resimler
            bagla(kapak.parent / f"{kapak.stem}_{h}.jpg", hedef / f"{sira}_UZUN_{ad}_kucuk_resim_{h}.jpg")
        adimlar += [f"{sira}) UZUN VİDEO (saat 20:00): {TR[ad]} ({tur})",
                    f"   - Video: {sira}_UZUN_{ad}_video.mp4",
                    f"   - Başlık, açıklama, etiketler: {sira}_UZUN_{ad}_metin.txt",
                    f"   - Küçük resim: {sira}_UZUN_{ad}_kucuk_resim.jpg (yükledikten sonra Studio'dan ekle)",
                    *([f"   - Bilgisayardaysan: Küçük resim > 'Test et ve karşılaştır' ile _kucuk_resim, _B ve _C dosyalarının üçünü birden yükle;"
                       , "     YouTube en çok tıklananı kendisi seçer."] if secenekler else []),
                    "   - Çocuklara özel değil · Herkese açık · Açıklamadaki öyküyü ve Sound credits satırlarını silme",
                    "   - Video öğeleri adımında BİTİŞ EKRANI ekle: Abone ol + En son yüklenen video (son 20 sn; telefonda yoksa bilgisayardan)",
                    "   - Yayından sonra şu yorumu yazıp sabitle: New 3-hour sleep ambience every week 🌙 Subscribe so you don't miss the next one.", ""]
        ceviri = KOK / "kanal" / "ceviriler" / f"{k}.txt"
        if ceviri.exists():                                            # başka dillerde başlık ve açıklama (aramada bulunmak için)
            bagla(ceviri, hedef / f"{sira}_UZUN_{ad}_ceviriler.txt")
            adimlar[-1:-1] = [f"   - Bilgisayardaysan (yayından sonra da olur): Studio > Altyazılar > videoyu seç > DİL EKLE ile",
                              f"     Almanca, İspanyolca, Portekizce, Fransızca, Japonca ekle; her dilde 'Başlık ve açıklama' kısmına",
                              f"     {sira}_UZUN_{ad}_ceviriler.txt içindeki o dilin TITLE (4K yüklediysen TITLE_4K) ve DESCRIPTION'ını yapıştır."]
        paket = sorted(d for d in (KOK / k).glob("paket_*4K") if (d / "BIRLESTIR.bat").exists())
        if paket:                                                      # 4K sürümü: parçalar tek zip içinde (sıkıştırmasız)
            zip_ad = f"{sira}_UZUN_{ad}_4K_paket.zip"
            if not (hedef / zip_ad).exists():
                with zipfile.ZipFile(hedef / zip_ad, "w", zipfile.ZIP_STORED) as z:
                    for d in sorted(paket[-1].iterdir()):
                        z.write(d, f"{ad}_4K/{d.name}")
            import kapak4k                                             # 4K yüklemede küçük resimlerde "4K" etiketi olsun
            for son in ["", *[f"_{h}" for h in secenekler]]:
                k4 = kapak.parent / f"{kapak.stem}{son}_4K.jpg"
                if not k4.exists():
                    kapak4k.etiketle(kapak.parent / f"{kapak.stem}{son}.jpg", k4)
                bagla(k4, hedef / f"{sira}_UZUN_{ad}_kucuk_resim{son}_4K.jpg")
            baslik4k = json.loads((KOK / "kanal" / "baslik_4k.json").read_text(encoding="utf-8")).get(k)
            adimlar[-1:-1] = [f"   - 4K SÜRÜM (yalnızca bilgisayardaysan): {zip_ad}",
                              "     Zip'i aç, ffmpeg.exe'yi açılan klasöre koy, BIRLESTIR.bat'a çift tıkla;",
                              "     çıkan 4K videoyu yukarıdaki video yerine yükle. 4K yüklüyorsan:",
                              *([f"     · Başlık olarak bunu kullan: {baslik4k}"] if baslik4k else []),
                              "     · Küçük resim olarak sonu _4K.jpg ile biten dosyaları kullan; etiketlere 4k ekle.",
                              "     (1080p yüklüyorsan 4K başlığını ve _4K küçük resimleri KULLANMA.)"]
        sira += 1
    if "shorts" in gun:
        k, anahtar = gun["shorts"]; ad = AD[k]
        bagla(KOK / k / f"{anahtar}.mp4", hedef / f"{sira}_SHORTS_{ad}.mp4")
        bagla(KOK / k / f"{anahtar}_yukleme.txt", hedef / f"{sira}_SHORTS_{ad}_metin.txt")
        ilgili = [t for t, g in sorted(takvim.items()) if g.get("uzun") == k and t <= tarih] \
            + [t for t in [YOUTUBEDA_PLANLI.get(k)] if t and t <= tarih]
        ilgili_metin = (f"{TR[ad]} uzun videosu" if ilgili or k in ("01-rainy-cabin", "03-christmas-cabin", "04-snowy-village")
                        else "henüz yok (uzun sürüm yayınlanınca bağla)")
        adimlar += [f"{sira}) SHORTS (saat 19:30): {TR[ad]}",
                    f"   - Video: {sira}_SHORTS_{ad}.mp4",
                    f"   - Başlık ve açıklama: {sira}_SHORTS_{ad}_metin.txt",
                    "   - YouTube'un önerdiği müziği ekleme · Çocuklara özel değil · Herkese açık",
                    f"   - İlgili video: {ilgili_metin}", ""]
    if gun.get("planli_shorts"):
        adimlar += ["Bugünün Shorts'u önceden planlandı, 19:30'da kendiliğinden yayınlanacak (tekrar yükleme).", ""]
    if gun.get("not"):
        adimlar += ["NOT: " + gun["not"], ""]
    adimlar.append("Bu klasördeki dosyalar yalnızca bugüne ait. Eski mesajlardaki dosyalarla karıştırmamak için bugün gelenleri kullan.")
    (hedef / "0_TALIMAT.txt").write_text("\n".join(adimlar) + "\n", encoding="utf-8")
    for p in sorted(hedef.iterdir()):
        print(p)


if __name__ == "__main__":
    main()
