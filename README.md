# Deneme-2

## Yazıcıoğlu Çilek Döviz — Döviz Kasası

`doviz-kasasi.html` — döviz, altın ve gümüş alış–satışlarını takip eden tek sayfalık uygulama:
TL kasası, kendi alış–satış kur tablonuz, arbitraj, kupür bazında kasa sayımı, masraf ve
net kâr, cari (borç–alacak) defteri, çevirici, müşteri kur panosu, gün sonu özeti ve aylık rapor.
Kuyum tarafı:

- **Hesap:** satış fiyatı (ayar, gram, milyem, işçilik), bozdurma (hurda alış, taş/kir düşümü) ve ziynet (çeyrek, yarım,
  tam, ata, reşat, hamit, gremse…) hesabı; birden çok parçayı listeleyip takasta net tutarı verir, tek dokunuşla kasaya
  işler, müşteriye döküm (fiş) çıkarır. Gram hesabı “Has altın fiyatım” kartına yazdığınız alış–satış fiyatından yapılır.
- **Toptancı has hesabı** (Cari): toptancılarla borç–alacak has gramı üzerinden, işçilik ayrı.
- **Vitrin defteri** (Kasa): parça parça ürün listesi, has karşılığı, en uzun süredir bekleyenler.
- **Kâr analizi** (Gün sonu → Analiz): varlık başına ortalama alış–satış kuru, makas ve kâr; aylık net kâr grafiği.
  Net kâr TL’nin yanında dolar ve has altın olarak da gösterilir.
- **Vitrin ekranı** (`vitrin.html`): dükkândaki TV için tam ekran fiyat panosu. Aynı cihazda Döviz Kasası’nın kur
  tablosunu canlı gösterir; ayrı bir TV ya da tablette piyasa fiyatına kendi farkınızı ekleyerek çalışır.
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
