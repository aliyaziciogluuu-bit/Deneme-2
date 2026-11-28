# Bağlı araçlar (25 Kasım 2026)

## Windsor.ai (deneme planı)
- YouTube bağlantısı: Avludaki Komşular hesabı (Windsor hesap no 124319) ve Dream Window.
- **Okuma:** günlük görüntüleme, izlenme dakikası, abone kazanç/kayıp, video bazında veri, trafik kaynağı, abone/abone olmayan, izleyici tutma eğrisi, yorumlar, oynatma listeleri. Veri YouTube Analytics API'sinden ~2–3 gün gecikmeli gelir. Gösterim, tıklama oranı, tekil izleyici ve Shorts "izlemeye devam" YOK (bunlar için Studio ekran görüntüsü ya da bilgisayardaki asistan).
- Bir sorguda trafik kaynağı ile abone durumu birlikte istenemez.
- **Yazma (her biri kanal sahibinin o işe açık onayıyla):** yoruma cevap, yorum gizleme/silme, başlık/açıklama/etiket/kategori/görünürlük değiştirme, oynatma listesine ekleme/çıkarma, video yükleme (herkese açık bir URL'den, en fazla 100 MB, publish_at ile planlama).
- Yüklemede "değiştirilmiş/yapay içerik" beyanı, küçük resim, altyazı, bitiş ekranı, kart, A/B testi YOK → yüklemeler bilgisayardaki asistanla sürer.
- Kural: planlı videoların görünürlüğü değiştirilmez; yazma işlemi onaysız yapılmaz.

## vidIQ (ücretsiz plan, 150 kredi/ay)
- Şu an yalnızca Dream Window kanalına bağlı. Avludaki Komşular için kanal sahibinin vidIQ'da bu kanalı da bağlaması gerekir.
- Kullanım: konu seçmeden önce Türkçe anahtar kelime araştırması, nişteki "outlier" videolar, rakip kanal listesi, başlık puanı. Kredi az: video başına en fazla birkaç sorgu.

## İlk Windsor okuması (16–23 Kasım, kanal geneli)
- Görüntüleme: reklam 7.651 · Shorts akışı 3.621 · göz atma (ana sayfa/abonelikler) 554 · önerilen 252 · arama 172 · kanal 28.
- İzlenme dakikası: reklam 15.563 (≈ 259 saat, %92) · diğer her şey ≈ 1.210 (≈ 20 saat).
- Sonuç: 2 haftada organik izlenme ≈ 20 saat. 8.000 saat şartı için organik uzun video izlenmesi asıl darboğaz.

## vidIQ notu (25 Kasım)
- Ücretsiz plan tek kanal bağlıyor; Dream Window bağlı kalır. Araştırma araçları (anahtar kelime, outlier, başlık puanı) kanal bağlamadan da çalışıyor; başlık puanına Avludaki kanal ID'si elle verilebilir.
- İlk deneme (5 kredi): "yılan zehirli mi" TR → çoğu uzun ifade "<750/ay" (veri yok sayılır); geniş terimler: "yılan" ≈ 12.000/ay, "belgesel" ≈ 204.000/ay (%87 TR), "doğa" ≈ 8.000/ay. Türkçe uzun kuyruk verisi zayıf → vidIQ'yu yalnızca geniş terim karşılaştırması ve outlier için kullan, kredi idareli.

## Google Drive (25 Kasım)
- Klasörler: "Avludaki Komşular" (1g6QeyxK0-Dv4JaOawPfyKEx2pWBhjaJv) → "teslim" (1vCvdkb4fHFGOcUo194IYKBL2XkIKtZTX) → "09-yilan-inek" (12eIkfEMuKBhJVHhHOepsY4Ngxgw0gUxy).
- Bağlantı sınırı: istek başına ~4,2 MB (dosya ≈ 3 MB). Çözüm (kanal sahibi 25 Kas: "videoları ben yüklemeyeyim"): `python3 drive_parca.py teslim/<klasör>` → `_drive/` içinde 3 MB'lık parçalar + BIRLESTIR.ps1 (SHA-256 doğrulamalı) + yukle.json. Parçalar `create_file` ile dosya referansı (sha256:<özet>:<yol>) olarak yüklenir; bilgisayardaki Claude klasörü indirip `powershell -ExecutionPolicy Bypass -File BIRLESTIR.ps1` çalıştırır.
- Bir parça referansla gitmezse (09'da p12) parçayı ikiye böl (p12a/p12b), BIRLESTIR.ps1'deki listeyi düzelt, eski betiği çöpe at, yenisini yükle.
- 09-yilan-inek: tamamı Drive'da (11 küçük dosya, 14 Shorts parçası, 59 uzun video parçası, BIRLESTIR.ps1). Birleştirme yerelde sınandı (özet birebir).
- 27 Kasım: `.p12` parçası iki teslimde de (yılan–inek, semender) "can't be sent by reference" ile reddedildi; neden büyük olasılıkla `.p12` uzantısının sertifika dosyası (PKCS#12) sayılması (`.p10` da "pkcs10" etiketi aldı). drive_parca.py artık parçaları `.parcaNN` diye adlandırıyor. Semender teslimi: p12 → p12a/p12b bölündü, BIRLESTIR.ps1 güncellendi, eski kopya çöpe atıldı. Drive klasörü: teslim/10-semender (1ghNy-8erUh11-Zgx6UpQutvnmgUP5qQ6), 64 dosya.
- 27 Kasım: Drive teslim/11-bahce-yilani (1G7Cu4phmTVy7kNYUrXzUGsNRt4LWmaQ2, 59 dosya) ve teslim/3d-seri-1 (1wLLLKmYOVSyeR-ZKbxoyCO3oRziDrN7h, 67 dosya) yüklendi, eksiksiz; .parcaNN adlandırmasıyla hiç red yok.
- 28 Kasım: teslim/3d-seri-2 Drive klasörü 1hJJg3pcBzggorFdRWtISYG_M5_nlHxaW (50 dosya: 10 Shorts × 3–4 parça, yükleme metinleri, BIRLESTIR.ps1, YUKLEME_LISTESI.txt).
- 28 Kasım: teslim/12-ev-orumcegi Drive klasörü 18ezVlEM1xicxQockgFqZ4iNaCkf1DNa3 (61 dosya: video 40 parça, 3 Shorts, 3 kapak, altyazı, yükleme metinleri, BIRLESTIR.ps1, YUKLEME_LISTESI.txt).
