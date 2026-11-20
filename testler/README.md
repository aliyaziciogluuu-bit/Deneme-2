# Döviz Kasası tarayıcı sınamaları

`doviz-kasasi.html` ve `vitrin.html` dosyalarını gerçek tarayıcıda (telefon ve masaüstü boyutunda) sınar.
Ağ gerekmez: fiyat servisleri kapatılır, sayfalar diskten sunulur.

```bash
npm install playwright && npx playwright install chromium   # bir kez
for f in testler/*.js; do node "$f" || break; done
```

| Dosya | Kapsam |
|---|---|
| `hesap.js` | Kuyum hesabı: satış, bozdurma, ziynet, has fiyatı, liste, fiş, kasaya işleme ve geri alma |
| `analiz.js` | Kâr analizi: varlık başına makas ve kâr, aylık grafik |
| `defterler.js` | Toptancı has hesabı ve vitrin defteri |
| `kar-birimleri.js` | Kârın TL, dolar ve has olarak gösterimi |
| `vitrin-ekrani.js` | Vitrin fiyat ekranı (`vitrin.html`) |
| `vitrin-kasa-paylasim.js` | Vitrin defterinden alış/satışın kasaya işlenmesi, rapor paylaşımı |
| `sade-gorunum.js` | Sade görünüm: tek satır başlık, açılır bölümler, dokununca açılan satırlar, sayfa uzunlukları |
| `guncelleme.js` | Yeni sürümün ulaşması: “yeni sürüm hazır” uyarısı, önbelleğe rağmen güncel sayfa, çevrimdışı açılış |
| `yeni-ozellikler.js` | Otomatik kur, eski seri farkı, borç hatırlatma, hızlı işlem şablonları, gün sonu kapanışı |
| `kolayliklar.js` | Zararına satış uyarısı, satış kârı bildirimi, hızlı tutar, başparmakla kaydet, büyük yazı, titreşim |
| `iade.js` | Satış iadesi: kârın geri alınması, stok ve kasa, kısmi iade, silme/düzenleme koruması |
| `veri-koruma.js` | Okunamayan kaydın ezilmemesi, ham kaydı indirme, okunabilenlerle devam, depolama dolu uyarısı |
| `paket1.js` | Eski fiyat uyarısı, tek altın fiyatı, belge no, hesap dökümü, büyük tutar ve açıklayıcı bildirim, doğrudan kasaya işleme, kayıp kaydı, yedek |

Yayın notu: her yayında `doviz-kasasi.html` başındaki `surum` etiketinin değerini değiştirin; açık duran uygulama yeni
sürümü bu değerle fark edip “Yenile” uyarısını gösterir.
