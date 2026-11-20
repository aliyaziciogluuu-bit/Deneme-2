# Deneme-2

## Yazıcıoğlu Çilek Döviz — Döviz Kasası

`doviz-kasasi.html` — döviz, altın ve gümüş alış–satışlarını takip eden tek sayfalık uygulama:
TL kasası, kendi alış–satış kur tablonuz, arbitraj, kupür bazında kasa sayımı, masraf ve
net kâr, cari (borç–alacak) defteri, çevirici, müşteri kur panosu, gün sonu özeti ve aylık rapor.
Uygulamada beş ana sekme vardır: Ana sayfa (günün kârı ve yeni işlem), Hesap, Kasa (Bakiyeler · Kurlarım · Vitrin),
Defter (Cari · Toptancı) ve Rapor (Rapor · İşlemler).

Kuyum tarafı:

- **Hesap:** satış fiyatı (ayar, gram, milyem, işçilik), bozdurma (hurda alış, taş/kir düşümü) ve ziynet (çeyrek, yarım,
  tam, ata, reşat, hamit, gremse…) hesabı; birden çok parçayı listeleyip takasta net tutarı verir, tek dokunuşla kasaya
  işler, müşteriye döküm (fiş) çıkarır. Gram hesabı “Has altın fiyatım” kartına yazdığınız alış–satış fiyatından yapılır.
- **Toptancı has hesabı** (Defter → Toptancı): toptancılarla borç–alacak has gramı üzerinden, işçilik ayrı.
- **Vitrin defteri** (Kasa → Vitrin): parça parça ürün listesi, has karşılığı, en uzun süredir bekleyenler. Ürün eklerken alış,
  “Sat” ile satış kasaya işlenebilir.
- **Kâr analizi** (Rapor → Analiz): varlık başına ortalama alış–satış kuru, makas ve kâr; aylık net kâr grafiği.
  Net kâr TL’nin yanında dolar ve has altın olarak da gösterilir. Açık rapor “Paylaş” ile WhatsApp ya da e-postaya gönderilir.
- **Vitrin ekranı** (`vitrin.html`, Kasa → Kurlarım içinden açılır): dükkândaki TV için tam ekran fiyat panosu. Aynı cihazda Döviz Kasası’nın kur
  tablosunu canlı gösterir; ayrı bir TV ya da tablette piyasa fiyatına kendi farkınızı ekleyerek çalışır.

Günlük işler için:

- **Hızlı işlemler:** sık yapılan işlemi (ör. “100 USD sat”) formdaki “☆ Şablon” ile kaydedin; ana sayfada tek dokunuşla o anki
  kurla girilir, “Geri al” ile geri alınır.
- **Otomatik kur** (Kasa → Kurlarım): piyasa fiyatına eklenecek farkı bir kez yazın; fiyatlar güncellendikçe kurunuz değişir.
- **Eski seri / yıpranmış döviz:** dövizi alırken işaretlenir; kurdan sizin farkınız düşülür, işleme “Eski seri” notu düşer.
- **Borç hatırlatma** (Defter → Cari): size borcu olan müşteriye hazır WhatsApp mesajı.
- **Gün sonu kapanışı** (Rapor): “Günü kapat” o günü ve öncesini kilitler; işlemler yanlışlıkla değişmez. Son kapanış geri açılabilir.
- **Zararına satış uyarısı:** satış kuru elinizdeki malın ortalama maliyetinin altındaysa kaydetmeden önce tahmini zararı gösterip sorar.
- **Hızlı tutar düğmeleri:** tutar kutusunun altında varlığa göre 100 · 500 · 1.000 gibi düğmeler.
- **Büyük yazı** (başlıktaki “Aa”): bütün uygulama büyür; tercih hatırlanır.
- **İade** (Rapor → İşlemler → satışın “İade” düğmesi): mal satıştaki maliyetiyle stoğa döner, para geri ödenir, satışın kârı
  geri alınır; kısmi iade yapılabilir.
- **Satış kârı bildirimi:** satışı kaydedince “bu satıştan +₺X kâr” yazar.
- **Başparmakla kaydet:** telefonda “İşlemi kaydet” düğmesi ekranın altında sabit durur.
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

`borsa-bot/` klasörü Döviz Kasası'ndan bağımsız ikinci bir araçtır: her işlem günü kapanıştan sonra
BIST 100 hisselerini temel + teknik analizle (hibrit) puanlar, bir kâğıt portföy tutar ve ertesi sabahın
emir listesini hazırlar. İsteğe bağlı olarak, Windows'ta Matriks IQ açıkken emirleri Telegram onayınızla
aracı kuruma kendisi gönderir. Kurulum, geçmiş testi sonuçları ve riskler için
[`borsa-bot/README.md`](borsa-bot/README.md) dosyasına bakın. Panel: sayfa adresinizin sonuna
`borsa-bot/web/` ekleyin.
