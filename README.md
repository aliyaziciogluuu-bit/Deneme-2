# Deneme-2

## Yazıcıoğlu Çilek Döviz — Döviz Kasası

`doviz-kasasi.html` — döviz, altın ve gümüş alış–satışlarını takip eden tek sayfalık uygulama:
TL kasası, kendi alış–satış kur tablonuz, arbitraj, kupür bazında kasa sayımı, masraf ve
net kâr, cari (borç–alacak) defteri, çevirici, müşteri kur panosu, gün sonu özeti ve aylık rapor.
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
