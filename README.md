# Deneme-2

## Yazıcıoğlu Çilek Döviz

`doviz-kasasi.html` — döviz, altın ve gümüş alış–satışlarını takip eden tek sayfalık uygulama:
TL kasası, kendi alış–satış kur tablonuz, arbitraj, kupür bazında kasa sayımı, masraf ve
net kâr, cari (borç–alacak) defteri, çevirici, müşteri kur panosu, gün sonu özeti ve aylık rapor.
Uygulamada beş ana sekme vardır: Ana sayfa (günün kârı ve yeni işlem), Hesap, Kasa (Bakiyeler · Kurlarım · Vitrin),
Defter (Cari · Toptancı · Bekleyenler) ve Rapor (Rapor · İşlemler).

Kuyum tarafı:

- **Hesap:** satış fiyatı (ayar, gram, milyem, işçilik), bozdurma (hurda alış, taş/kir düşümü) ve ziynet (çeyrek, yarım,
  tam, ata, reşat, hamit, gremse…) hesabı; birden çok parçayı listeleyip takasta net tutarı verir, tek dokunuşla kasaya
  işler, müşteriye döküm (fiş) çıkarır. Gram hesabı “Has altın fiyatım” kartına yazdığınız alış–satış fiyatından yapılır.
- **Ayar dönüştürücü** (Hesap): bir ayardaki ağırlığın has karşılığı ve öteki ayarlardaki karşılığı (standart milyemle).
- **Toptancı has hesabı** (Defter → Toptancı): toptancılarla borç–alacak has gramı üzerinden, işçilik ayrı.
- **Vitrin defteri** (Kasa → Vitrin): parça parça ürün listesi, has karşılığı, en uzun süredir bekleyenler. Ürün eklerken alış,
  “Sat” ile satış kasaya işlenebilir.
- **Envanter listesi** (Rapor → Envanter listesi): seçilen günün akşamı elde kalan döviz ve altın, miktarı, has karşılığı,
  ortalama maliyeti ve toplamıyla; TL kasası ve vitrin defteri özeti. “31 Aralık” düğmesiyle yıl sonu; paylaşılır ya da CSV
  olarak iner. Bilgi amaçlıdır.
- **Hurda altın günlüğü** (Kasa → Vitrin): bugün / bu hafta / bu ay alınan 22, 21, 18, 14 ve 8 ayar altın (gram, has,
  ödenen, has gramının ortalama fiyatı) ve elde bekleyen ayar altın; toptancıya giderken “Listeyi paylaş”.
- **Sarrafiye stoku** (Kasa → Bakiyeler): çeyrek, yarım, tam… için yeni ve eski tarihli adetler. Ziynette işlem formundaki
  kutu “Eski tarihli” olur (alışta da satışta da); indirim hesaptaki eski tarih indiriminden gelir.
- **Kâr analizi** (Rapor → Analiz): varlık başına ortalama alış–satış kuru, makas ve kâr; aylık net kâr grafiği.
  Net kâr TL’nin yanında dolar ve has altın olarak da gösterilir. Açık rapor “Paylaş” ile WhatsApp ya da e-postaya gönderilir.
- **Makas kârı ve fiyat farkı:** alım-satım kârı ikiye ayrılır: makas (satış kuru − satış anındaki kendi alış kurunuz) ve
  fiyat farkı (elinizdeki malın siz tutarken değer kazanması). Ana sayfada, raporda, analizde ve paylaşılan raporda görünür.
- **Vitrin ekranı** (`vitrin.html`, Kasa → Kurlarım içinden açılır): dükkândaki TV için tam ekran fiyat panosu. Aynı cihazda uygulamanın kur
  tablosunu canlı gösterir; ayrı bir TV ya da tablette piyasa fiyatına kendi farkınızı ekleyerek çalışır.
  Fiyatın yanında ▲ / ▼ oku, günün ilk fiyatına göre yükseldiğini ya da düştüğünü gösterir (Ayarlar’dan kapatılabilir).

Günlük işler için:

- **Sepet (toplu işlem):** bir müşteriye dolar, euro ve çeyrek gibi birden çok varlık satıldığında (ya da alış-satış
  karışık) satırlar “＋ Sepete ekle” ile toplanır, net tutar tek seferde görünür ve “Sepeti kaydet” hepsini birlikte yazar;
  “Geri al” hepsini birden geri alır.
- **Hızlı işlemler:** sık yapılan işlemi (ör. “100 USD sat”) formdaki “☆ Şablon” ile kaydedin; ana sayfada tek dokunuşla o anki
  kurla girilir, “Geri al” ile geri alınır.
- **Otomatik kur** (Kasa → Kurlarım): piyasa fiyatına eklenecek farkı bir kez yazın; fiyatlar güncellendikçe kurunuz değişir.
- **Hafta sonu makası** (Kasa → Kurlarım → Otomatik kur): cuma akşamından pazartesi sabahına kadar (saatleri siz seçersiniz)
  otomatik kura ayrı alış–satış farkı uygulanır; pazartesi kendiliğinden hafta içi farkına döner.
- **Eski seri / yıpranmış döviz:** dövizi alırken işaretlenir; kurdan sizin farkınız düşülür, işleme “Eski seri” notu düşer.
  Gram altında aynı kutu “Kartı açılmış / yıpranmış” olarak çıkar.
- **Makas uyarısı:** kur tablonuzda satış kuru alıştan düşükse, ikisi aynıysa ya da kurunuz piyasanın aleyhineyse (alış piyasa
  satışının üstünde, satış piyasa alışının altında) uygulamanın üstünde uyarı çıkar. İşlem formunda alışı satış kurunuzdan
  yükseğe, satışı alış kurunuzdan aşağıya yazınca da uyarır. Piyasa karşılaştırması yalnızca fiyatlar son 24 saatte alındıysa yapılır.
- **Sınırlar** (Kasa → Sınırlar): varlık başına en fazla miktar (ör. “en fazla 5.000 USD”) ve TL kasasının en az tutarı.
  Aşılınca uyarı çıkar; sınırı aşacak işlemi kaydederken sorulur.
- **Bekleyen müşteri** (Defter → Bekleyenler): “dolar 50’ye inerse haber verin” diyen müşteriyi ve hedef fiyatı yazın; kurunuz
  hedefe gelince uygulamanın üstünde uyarı çıkar, “Mesaj gönder” hazır WhatsApp mesajını açar.
- **Yorum ve yol tarifi bağlantısı:** hesap dökümünde “Bağlantılar” ile Google yorum ve harita bağlantınızı bir kez yazın;
  müşteriye gönderilen her dökümün altına eklenir.
- **Borç hatırlatma** (Defter → Cari): size borcu olan müşteriye hazır WhatsApp mesajı.
- **Gün sonu kapanışı** (Rapor): “Günü kapat” o günü ve öncesini kilitler; işlemler yanlışlıkla değişmez. Son kapanış geri açılabilir. “Günü kapat” üç adımlı bir sihirbazdır: kasa sayımı (bugün için; farklar
  isteğe bağlı olarak sayım farkı olarak işlenir) → günün özeti → kapat ve yedeği gönder.
- **Zararına satış uyarısı:** satış kuru elinizdeki malın ortalama maliyetinin altındaysa kaydetmeden önce tahmini zararı gösterip sorar.
- **Hızlı tutar düğmeleri:** tutar kutusunun altında varlığa göre 100 · 500 · 1.000 gibi düğmeler.
- **Görünüm** (Rapor → İşlemler → Görünüm): tema Otomatik / Açık / Koyu ve renk (yeşil, lacivert, bordo, altın).
- **Ana ekran kısayolları** (Android): uygulama simgesine basılı tutunca “Dolar al”, “Dolar sat”, “Altın hesabı”, “Kurlarım”.
- **Büyük yazı** (başlıktaki “Aa”): bütün uygulama büyür; tercih hatırlanır.
- **İade** (Rapor → İşlemler → satışın “İade” düğmesi): mal satıştaki maliyetiyle stoğa döner, para geri ödenir, satışın kârı
  geri alınır; kısmi iade yapılabilir.
- **Satış kârı bildirimi:** satışı kaydedince “bu satıştan +₺X kâr” yazar.
- **Başparmakla kaydet:** telefonda “İşlemi kaydet” düğmesi ekranın altında sabit durur.
- **Müşteriye göster:** işlem formunda “Müşteriye göster”, kuyum hesabında “Göster”: tutar tam ekranda iri yazıyla; dokununca kapanır.
- **Kayıt titreşimi:** kayıt ve silmede kısa titreşim (Android; iPhone desteklemez).

Güvenilirlik:

- **Eski fiyat uyarısı:** otomatik kur kullanılırken fiyatlar 30 dakikadan uzun süre alınamazsa uygulamada ve TV vitrininde
  uyarı çıkar; uygulama açık dururken fiyatlar dakikada bir tazelenir.
- **Tek altın fiyatı** (Hesap → Has altın fiyatım): işaretlenirse kur tablosundaki gram altın kurları (22, 18, 14 ayar…) has
  fiyatınızdan, milyem ve işçiliğinizden hesaplanır; kuyum hesabıyla aynı fiyat çıkar.
- **Belge no:** işleme kestiğiniz resmî belgenin numarası yazılabilir; belge no kullanıyorsanız gün sonunda numarası eksik
  işlemler gösterilir; CSV'de ayrı sütundur. Uygulama numara üretmez.
- **Hesap dökümü:** müşteriye verilen döküm “BELGE DEĞİLDİR” ibaresiyle; resmî fiş ya da fatura yerine geçmez.
- **Kayıp kaydı** (Kasa → bakiye satırı → Kayıp): sahte çıkan para, ayarı düşük çıkan mal; maliyeti kârdan düşer.
- **Yedek:** son yedekten beri işlem varsa her gün (20 işlem birikirse hemen) hatırlatır; gün kapatılınca yedek göndermeyi önerir.
- **Şifreli yedek** (Rapor → İşlemler → Yedek parolası): parola belirlenirse yedekler şifrelenir (AES-GCM, PBKDF2 600.000 tur);
  dosya parolasız açılamaz. Parola yalnızca bu telefonda durur; unutulursa yedek açılamaz.
- **Otomatik kopyalar** (Rapor → İşlemler): telefon içinde her günün bir kopyası (son 7 gün) ve yedek yükleme / geri yükleme
  öncesi durum (son 3) saklanır; tek dokunuşla geri yüklenir, geri alınabilir.

**Veri koruma:** kayıt okunamazsa uygulama hiçbir şeyi ezmez; ham kayıt saklanır, indirilebilir ve okunabilen işlemlerle
devam edilebilir. Depolama dolup kayıt yapılamazsa uyarır. Tarayıcıdan verinin kalıcı tutulması istenir.

Tarayıcı sınamaları [`testler/`](testler/README.md) klasöründedir.
Veriler yalnızca kullanılan cihazın tarayıcısında saklanır. Resmî fiş ve yasal bildirimlerin
yerini tutmaz.

Telefonun ana ekranına eklenebilmesi için sayfanın HTTPS üzerinden yayınlanması gerekir
(örneğin GitHub Pages). Yayınlandıktan sonra:

- **Android (Chrome):** sayfadaki “Ana ekrana ekle” düğmesi ya da menü → “Ana ekrana ekle”.
- **iPhone (Safari):** Paylaş → “Ana Ekrana Ekle”.

Fiyat kaynakları: finans.truncgil.com (asıl), open.er-api.com / api.frankfurter.dev ve
api.gold-api.com (yedek).

## BIST Bot — Borsa İstanbul için kurallı al-sat botu

`borsa-bot/` klasörü Yazıcıoğlu Çilek Döviz uygulamasından bağımsız ikinci bir araçtır: her işlem günü kapanıştan sonra
BIST 100 hisselerini temel + teknik analizle (hibrit) puanlar, bir kâğıt portföy tutar ve ertesi sabahın
emir listesini hazırlar. İsteğe bağlı olarak, Windows'ta Matriks IQ açıkken emirleri Telegram onayınızla
aracı kuruma kendisi gönderir. Kurulum, geçmiş testi sonuçları ve riskler için
[`borsa-bot/README.md`](borsa-bot/README.md) dosyasına bakın. Panel: sayfa adresinizin sonuna
`borsa-bot/web/` ekleyin.

## Hecemece — günlük hece bulmacası

`hecemece/` klasörü öteki iki araçtan bağımsız, tek dosyalık bir kelime oyunudur. Her gün herkese aynı 6 kelime gelir:
beşinin ipucu yazar, altıncısı gizlidir ve elde kalan hecelerden çıkarılır. Oyuncu hece fişlerine dokunarak kelimeyi kurar;
yuvalar dolunca kelime kendiliğinden kontrol edilir.

- **Not ve paylaşım:** bulmaca bitince Pekiyi / İyi / Orta / Geçer notu verilir; “Sonucu paylaş” renkli kareleri, süreyi ve
  gün serisini kelimeleri ele vermeden paylaşır.
- **İpucu:** ilk basışta ilk heceyi yerine koyar, ikinci basışta cevabı açar; ikisi de notu düşürür.
- **Karne:** çözülen bulmaca, gün serisi, en uzun seri, Pekiyi sayısı, en iyi süre. Yalnızca o cihazda saklanır.
- **Alıştırma:** günün bulmacası bitince rastgele bulmacalarla devam edilir; karneyi etkilemez.
- **Kelime havuzu:** `index.html` içindeki `HAVUZ` listesi (`kelime|ipucu`, 540 kelime, 90 günde bir tur). Heceler
  kendiliğinden ayrılır; yeni kelime eklemek için satır eklemek yeter. Tek heceli kelime konmaz.
- **Paylaşılan adres:** sonuca sayfanın kendi adresi eklenir; başka bir adres için dosyanın başındaki `ADRES` doldurulur.

Açmak için sayfa adresinizin sonuna `hecemece/` ekleyin. Sınaması: `testler/hecemece.js`.

## TV Kumandası — Philips Android TV için telefon kumandası

`tv-kumanda/philips_kumanda.py`: TV ile aynı Wi-Fi'daki bir bilgisayarda ya da Android telefonda (Termux) çalışan,
telefon tarayıcısından kullanılan kumanda paneli. Yön tuşları, ses ve kanal, uygulama kısayolları, uyku zamanlayıcısı ve
Ambilight kontrolü (hazır stiller, istenen sabit renk ve parlaklık). Yalnızca Python 3 gerekir; kurulum ve eşleştirme
adımları `tv-kumanda/README.md` içinde.
