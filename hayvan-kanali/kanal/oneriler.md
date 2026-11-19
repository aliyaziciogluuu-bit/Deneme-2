# Öneri kutusu – Avludaki Komşular

Ofisteki herkes kanalı büyütecek fikirleri buraya önerir: çalışanlar, denetçiler ve yönetici. Fikirler değerlendirilip kanal sahibine sunulur. Son kararı kanal sahibi verir.

## Nasıl çalışır?

1. **Öneri:** Her ajan raporunun sonunda kendi alanından 0–2 fikir önerir. Patron bunları aşağıdaki "Bekleyen" bölümüne ekler.
2. **Değerlendirme:** Kanal yöneticisi bekleyen fikirleri puanlar:
   - **Etki:** izlenme, abone ya da gelire katkı (1–5)
   - **Emek:** ne kadar iş (1–5, düşük iyi)
   - **Maliyet:** para harcar mı?
   - **Risk:** kanal kuralları, doğruluk, yanıltıcılık
   Sonra gerekçeli bir karar yazar: "sun", "beklet" ya da "ele".
3. **Sunum:** Patron en iyi 1–3 fikri kanal sahibine kısa ve anlaşılır bir dille sunar.
4. **Karar:** Kanal sahibinin kararı "Onaylanan" ya da "Reddedilen" bölümüne yazılır. Reddedilen fikir gerekçesiyle kalır, aynı fikir tekrar önerilmez.

---

## Bekleyen

- **P1 – Girişi yeniden kurgulama kuralı (patron, 19 Kasım):** Yılan videosunda izleyicilerin yarıdan fazlası 0:30–1:20 arasında ayrıldı. Sonraki videolarda başlığın cevabının ilk kanıtı en geç 0:40'ta verilir, ansiklopedi bilgileri sonraya alınır. Baykuş videosu yayından önce bu kurala göre yeniden sıralanacak.
  - Değerlendirme (yönetici, 19 Kasım): etki 5, emek 2, maliyet yok ya da çok az → **sun**. Geko, kirpi ve yarasaya da uygulanması önerildi.
- **P2 – (ALTYAPI HAZIR 19 Kasım: paketleme uzmanı + `video.py --kapak` ile kapak_B/C) Alternatif küçük resimle A/B testi (patron, 17 Kasım):** YouTube'un "Test ve karşılaştır" özelliğiyle her videoya 2–3 küçük resim yüklenir. Tıklama oranı %2'nin altında kalırsa uygulanır; yılan videosunda şu an %2,7.
  - Değerlendirme (yönetici, 19 Kasım): etki 3, emek 2 → **beklet** (tıklama oranı %2,7, koşul oluşmadı).
- **P3 – Gerçek hayvan sesi (patron, 18 Kasım):** Girişte ya da ilgili sahnede, Wikimedia Commons'taki kamu malı kayıtlardan hayvanın gerçek sesi (baykuş ötüşü, kirpi hırıltısı) kısa bir anlığına duyulur. Belgesel hissini ve inandırıcılığı artırır.
  - Değerlendirme (yönetici, 19 Kasım): etki 2, emek 2 → **beklet** (önce izleyici tutma düzelmeli).

- **E1 – Bitiş ekranı ve "sıradaki komşu" ipucu (metin editörü, 19 Kasım):** Her videonun son 10–15 saniyesinde bir sonraki videoyu öneren bitiş ekranı kullanılır. Kapanışta "Sıradaki komşu: …" diye bir merak cümlesi söylenir. İzleyici kanalda kalır, yeni videonun ilk izlenmeleri artar.
  - Değerlendirme (yönetici, 19 Kasım): etki 3, emek 1, maliyet yok → **sun**.

- **Y1 – (YAPILDI 19 Kasım: veri analisti görevi) Erken ayrılma karnesi (kanal yöneticisi, 19 Kasım):** Her videonun yayından 3 gün sonra 0:30, 1:20 ve 2:00'deki izleyici tutma yüzdeleri ilerleme.md'ye yazılır. Dersler veriye bağlı kalır, videolar karşılaştırılabilir.
  - Değerlendirme: iç iş olarak uygulanabilir.

- **S1 – "Bunu sen de dene" cümlesi (senarist, 19 Kasım):** Her videoda izleyicinin uygulayabileceği tek bir eylem (ör. yavru karga için "bir saat uzaktan izle"). Yorumlarda deneyim paylaşımını artırır.
- **S2 – "Bu deney nerede yapıldı?" kartı (senarist, 19 Kasım):** Başka ülkede yapılmış deneyler anlatılırken ekranda kısa bir etiket ("Bu deney Amerika'da, Amerikan kargasıyla yapıldı"). Türe özgü bilgiyi genellememe kuralını izleyiciye görünür kılar; kanalın dürüstlüğünü marka yapar.
- **B1 – "Ne doğruladık, ne doğrulayamadık" notu (bilgi kontrolcüsü, 19 Kasım):** Açıklamanın sonuna iki satırlık şeffaflık notu. "Her bilgi kaynaklı" sözünü görünür kılar.
- **B2 – "Yaralı yaban hayvanı bulursan ilk 5 adım" sabit yorum kartı (bilgi kontrolcüsü, 19 Kasım):** Kurum olarak yalnızca DKMP şube müdürlüğü, telefon yok. Güvenlik bilgisini tek yerde toplar.

- **İ2 – hat.py'ye kuyruk (üretim müdürü, 19 Kasım):** `hat.py ekle <klasörler>` ile işler sıraya eklenir, `hat.py durum` bekleyenleri de gösterir. Kendiliğinden kilitlenen bekleme döngüleri ve aynı işin iki kopyası ortadan kalkar.
- **İ3 – Shorts'ta otomatik yüz–yazı çakışma testi (üretim müdürü, 19 Kasım):** son kontrol, etiketli ve üst yazılı karelerde hayvanın yüzü ile yazı kutusunun çakışmasını ölçer. Dört videoda tekrarlayan kalite kontrol RET'ini kapıya gelmeden yakalar.
- **İ4 – (YAPILDI 19 Kasım) metin_kontrol: ilk 3 dakikada 45 sn'den uzun sorusuz bölüm uyarısı.**

## Onaylanan

## Reddedilen

## İç işler (patron uygular, kanal sahibine sunulmaz)

- **İ1 – (YAPILDI 19 Kasım: `metin_kontrol.py`) Kanca denetimi betiği:** `son_kontrol.py`'ye bir uyarı eklenir: ilk 60 saniyede bilimsel ad (Latince), "santimetre", "metre yüksekliğe" gibi ansiklopedi kalıpları varsa uyarı verir.
