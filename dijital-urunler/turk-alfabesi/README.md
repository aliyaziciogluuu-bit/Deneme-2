# Türk Alfabesi: resimli harf kartları (dijital ürün)

Yurt dışındaki Türk aileler için Etsy'de satılacak, yazdırılabilir alfabe kartları ve poster. İki ürün:

| Ürün | Dosyalar | İlan metni |
|---|---|---|
| Türkçe–Almanca | `cikti/de/Turkisches-Alphabet-Bildkarten-A4.pdf` | `cikti/de/etsy-ilan.md` |
| Türkçe–İngilizce | `cikti/en/Turkish-Alphabet-Flashcards-A4.pdf`, `cikti/en/Turkish-Alphabet-Flashcards-US-Letter.pdf` | `cikti/en/etsy-ilan.md` |

Her ürünün 5 ilan fotoğrafı kendi klasöründedir (`etsy-1-kapak.png` … `etsy-5-icerik.png`, 2000×1500).

PDF içeriği (8 sayfa): kapak, ebeveyn sayfası (kullanım, 4 oyun, sesli harfler), 29 kart + bilgi kartı (5 sayfa, kesme çizgili), alfabe posteri.

## Etsy'ye yükleme

1. Etsy'de **Shop Manager › Listings › Add a listing**.
2. Fotoğrafları sırayla yükleyin (1 kapak ilk sırada olmalı).
3. Başlık, açıklama ve etiketleri `etsy-ilan.md` dosyasından kopyalayın.
4. **Type: Digital** seçin ve PDF dosyalarını yükleyin.
5. Fiyatı girin, yayınlayın.

## Yeniden üretmek

Resimler `resimler.js` içinde elle yazılmış vektör çizimlerdir; kelimeler ve metinler `kelimeler.js` içindedir.
Değişiklikten sonra:

```bash
NODE_PATH=$(npm root -g) node uret.js
```

Yeni bir dil eklemek için `kelimeler.js` içinde her harfe o dilin karşılığını, `METIN` içine o dilin metinlerini,
`uret.js` içinde `URUNLER` ve `GORSEL` listelerine o dili ekleyin.

Yazı tipleri (Andika, Fredoka) SIL Open Font License ile dağıtılır; ticari PDF'lere gömülebilir (`fontlar/`).
