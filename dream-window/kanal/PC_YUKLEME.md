# Dream Window – haftalık yükleme talimatı (bilgisayardaki Claude için)

Bu klasör, Dream Window kanalının (anonim uyku/ortam kanalı) bir haftalık yüklemelerini içerir. Dosyaları bulut oturumundaki Claude hazırladı. Her video tekrar testinden geçti. Senin işin bunları **YouTube Studio'ya yükleyip doğru gün ve saate planlamak**. Kanal sahibi Türkçe konuşur; ona kısa ve Türkçe yaz.

## Kesin kurallar

- **Hiçbir videoyu hemen yayınlama.** Hepsi **Planla** ile, `plan.json`'daki tarih ve saatte (Türkiye saati, Europe/Istanbul) yayınlanacak. Uzun videolar 20:00, Shorts'lar 19:30.
- Yalnızca bu klasördeki dosyaları kullan. Başlık ve açıklamayı **metin dosyasından aynen kopyala**; değiştirme, kısaltma, emoji silme.
- Açıklamadaki öyküyü, "AI-generated illustration" satırını ve **Sound credits** satırlarını silme.
- **Çocuklara özel değil** seç.
- Shorts'a YouTube'un önerdiği müziği ya da sesi **ekleme**.
- Doğru Google hesabında ve **Dream Window** kanalında olduğunu her yüklemeden önce kontrol et. Başka bir kanala (ör. "avludaki komşular") yükleme.
- Şifre, doğrulama kodu ya da ödeme gibi bir adım çıkarsa dur ve kanal sahibine sor.
- `plan.json` > `not` alanı aslında kanal sahibine yazılmış günlük nottur. Ondan yalnızca **İlgili video** ve **oynatma listesi** ile ilgili kısımları uygula. Ekran görüntüsü göndermek, sabit yorum yazmak, Analytics'e bakmak gibi işler kanal sahibinindir, onlara dokunma.
- **Hashtag önerisine dikkat:** YouTube açıklamaya yazarken hashtag'leri otomatik tamamlıyor (ör. `#3hours` → `#3hourstudywithme`, `#cozychristmas` → `#cozychristmasambience`). Açıklamayı yapıştırdıktan sonra öneri listesini seçmeden kapat; kaydetmeden önce açıklamanın son satırını ve karakter sayısını metin dosyasıyla karşılaştır.
- Bir şey ters giderse (yükleme hatası, telif uyarısı, "kısıtlama" uyarısı) o videoyu taslak olarak bırak ve kanal sahibine bildir.

## Klasör düzeni

- `plan.json`: bütün yüklemelerin listesi (tarih, saat, tür, dosya adları, başlık, notlar).
- `<tarih>/0_TALIMAT.txt`: o günün kısa talimatı (kanal sahibi için yazıldı; aynı bilgileri içerir).
- `<tarih>/*_metin.txt`: `TITLE`, `DESCRIPTION`, `TAGS` bölümleri.
- Uzun videolarda ayrıca: `_kucuk_resim*.jpg`, `_ceviriler.txt`, varsa `_4K_paket.zip`.

## Shorts (her biri için)

1. Studio > **Oluştur > Video yükle** > `<tarih>/<n>_SHORTS_<ad>.mp4`.
2. Başlık: metin dosyasındaki `TITLE`. Açıklama: `DESCRIPTION` bölümünün tamamı.
3. Kitle: Çocuklara özel değil.
4. **İlgili video:** `plan.json` > `ilgili_video`. "henüz yok" yazıyorsa boş bırak. Bir uzun video adı yazıyorsa kanaldaki o uzun videoyu seç. O video henüz planlı olduğu için listede çıkmıyorsa boş bırak ve bitiş tablosunda "İlgili video bağlanamadı" yaz.
5. Görünürlük > **Planla** > tarih ve **19:30**.
6. Kaydettikten sonra İçerik listesinde videonun "Planlandı" durumunda ve doğru tarihte göründüğünü kontrol et.

## Uzun video (her biri için)

1. **4K paket varsa** (`_4K_paket.zip`): zip'i aç. Klasöre `ffmpeg.exe` gerekir; bilgisayarda yoksa ffmpeg'in resmî Windows derlemesini indir ve `ffmpeg.exe`'yi klasöre koy. `BIRLESTIR.bat`'ı çalıştır, çıkan 4K videoyu yükle. 4K yüklüyorsan:
   - Başlık: `plan.json` > `baslik_4K`.
   - Küçük resim: `_kucuk_resim_B_4K.jpg`.
   - Etiketlere `4k` ekle.
   4K birleştirme başarısız olursa 1080p videoyu (`_video.mp4`) yükle. O zaman normal başlığı (`TITLE`) ve 4K etiketsiz `_kucuk_resim_B.jpg` küçük resmini kullan. **4K olmayan videoya asla "4K" yazma.**
   8 saatlik videoların paketi **birden çok zip**'tir (`_4K_paket.zip` ve `_4K_paket_ek2.zip` gibi; `plan.json` > `paket_4K` hepsini listeler). Hepsini **aynı yere** aç; aynı klasöre açılırlar. Ses `ses_1.aac`, `ses_2.aac` … parçaları hâlindedir; `BIRLESTIR.bat` bunları kendisi birleştirir, parçaları elle birleştirme. Bir parça eksikse .bat uyarır.
   `plan.json`'da `"yalnizca_4K": true` olan videolarda (8 saatlik videolar) 1080p yedek **yoktur**; `video` alanı boştur. Birleştirme başarısız olursa o videoyu yükleme, kanal sahibine bildir. Birleşen dosya yaklaşık 3 GB'tır, yüklemesi uzun sürebilir; yükleme bitmeden pencereyi kapatma. Bu videolarda başlık zaten 4K içerir.
2. **Küçük resim testi:** Küçük resim bölümünde **Test et ve karşılaştır**'ı seç ve üç dosyayı yükle: `_kucuk_resim_B`, `_kucuk_resim_C`, `_kucuk_resim_D` (D yazısızdır). 4K yüklüyorsan aynılarının `_4K.jpg` ile biten sürümlerini kullan. Test seçeneği çıkmazsa yalnızca B'yi yükle.
3. Açıklama: yalnızca `DESCRIPTION` bölümü (hashtag satırıyla biter). `TAGS` bölümü açıklamaya **değil**, "Etiketler" kutusuna girer.
4. Kitle: Çocuklara özel değil.
5. **Video öğeleri > Bitiş ekranı:** son 20 saniyeye "Abone ol" + "En son yüklenen video".
6. Görünürlük > **Planla** > tarih ve **20:00**.
7. Kaydettikten sonra **Altyazılar > Dil ekle**: Almanca, İspanyolca, Portekizce, Fransızca, Japonca. Her dilde "Başlık ve açıklama"ya `_ceviriler.txt` içindeki o dilin `TITLE` (4K yüklediysen `TITLE_4K`) ve `DESCRIPTION` bölümünü yapıştır.
8. `plan.json` > `not` alanında bir **oynatma listesi** adı geçiyorsa videoyu o listeye ekle. Liste henüz yoksa ve klasörde o listenin metin dosyası varsa (`japon_listesi.md`, `noel_listesi.md`), listeyi oradaki başlık ve açıklamayla **Herkese açık** ve **Manuel sıralama** ile oluştur. Metin dosyası yoksa oluşturma, kanal sahibine sor.

Yayından sonra yapılacak işleri (sabit yorum, Shorts'a İlgili video bağlama) **şimdi yapamazsın**; video yayınlanmadan bu ayarlar görünmez. Onları kanal sahibi o gün yapar ya da yayın günü senden ister.

## Bitirince

Kanal sahibine şu tabloyu Türkçe yaz:

| Tarih | Saat | Tür | Başlık | Durum (Planlandı / Sorun) |

Sonuna şu cümleyi ekle: **"Bulut oturumundaki Claude'a 'hafta planlandı' yaz, takvimi işlesin."**
