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

## Gölgekuyu — zindan RPG'si

`golgekuyu.html` — tek dosyalık, telefonda dokunarak oynanan sıra tabanlı bir zindan oyunu.
Her kat rastgele üretilir; düşmanlar, sandıklar, tuzaklar, sunaklar ve tüccar vardır.
Seviye atladıkça üç güçten birini seçersiniz, nadirlik seviyeli eşyalar (silah, zırh, takı)
kuşanırsınız, her 5 katta bir patronla karşılaşırsınız. Ölünce kazanılan ruhlarla kalıcı
geliştirmeler ve yeni sınıflar (Okçu, Büyücü) açılır. İlerleme yalnızca cihazın tarayıcısında saklanır.

Android paketi `android-app/` klasöründedir; kurulum ve Google Play adımları için
`android-app/README.md` dosyasına bakın.
