# Avludaki Komşular – YouTube Studio asistanı talimatı

Bu dosya, kanal sahibinin bilgisayarındaki Claude oturumu içindir (Claude masaüstü uygulaması, Yerel oturum,
"avludaki komşular" klasörü + Claude in Chrome eklentisi). Yükleme için `YUKLEME_ASISTANI.md` kullanılır; bu dosya
yükleme dışındaki işler içindir. Kanal sahibi hangi görevi istediğini söyler ("yayın sonrası işleri yap",
"haftalık veriyi topla" gibi). Bütün yazışma Türkçe.

Başlarken: Chrome'da yeni sekmede `https://studio.youtube.com` aç; kanal "Avludaki Komşular" olmalı, değilse dur ve sor.

## Görev 1 – Yayın sonrası işler (bir uzun video yayına girdikten sonra)
1. Videonun `YUKLEME_LISTESI.txt` dosyasını oku (klasörde). Yoksa kanal sahibine sor.
2. **Sabit yorum:** Videonun izleme sayfasında (youtube.com) listedeki yorumu kanal adına yaz ve **Sabitle**.
3. **Shorts ilgili video:** Bu uzun videoya ait Shorts'ları Studio → İçerik → Shorts'ta bul (başlıkları
   `shorts*-yukleme.txt` dosyalarında). Her birinde Ayrıntılar → **İlgili video** = bu uzun video → Kaydet.
   Görünürlüğe ve plana dokunma.
4. **Önceki videonun bitiş ekranı:** yayın zincirinde bir önceki uzun videonun bitiş ekranındaki video öğesini
   **bu yeni videoya** çevir. Zincir (yayın sırası): sağır yılan → geko → kirpi → yarasa → baykuş → karga → kırlangıç →
   kara kurbağası. Ayrıca kartı en iyi tutulan videoya ya da yeni videoya güncelle.
5. Özet yaz: ne yapıldı, ne kaldı.

## Görev 2 – Haftalık veri toplama (her pazartesi)
Studio → Analytics. Son 7 gün ve son 28 gün için şu sayıları **oku** ve klasöre `analiz_YYYY-AA-GG.md` dosyası olarak
tablo hâlinde yaz (değiştirme, yalnızca oku):
- Kanal: abone (toplam, son 7 gün +/−), görüntüleme, izlenme süresi (saat), en iyi 5 video.
- Her uzun video (son 28 günde yayında olanlar): görüntüleme, izlenme süresi, ortalama izleme süresi ve yüzdesi,
  küçük resim gösterimleri, küçük resim tıklama oranı, trafik kaynakları (yüzdeler), bu videodan gelen abone.
- Her uzun videonun **Kitleyi elde tutma** grafiği: 0:30, 1:00, 2:00 ve son noktadaki yüzdeleri yaz; grafikte sert
  düşüş varsa kaçıncı saniyede olduğunu yaz. Grafiğin ekran görüntüsünü de klasöre kaydet (`tutma_<video>.png`).
- Shorts: her Shorts için görüntüleme, aktif izlenme, izlemeye devam oranı (izlemeye devam / kaydırıp geçti), abone.
- Varsa tanıtım (reklam): harcanan tutar, görüntüleme, izlenme başına maliyet.
Bitince kanal sahibine dosyanın adını söyle; o dosyayı patrona (bulut oturumu) iletecek.

## Görev 3 – Küçük resim değişikliği / testi
Kanal sahibinin söylediği videoda: Ayrıntılar → Küçük resim. Klasördeki dosyaları yükle; birden fazla seçenek varsa
**Test ve karşılaştır** ile hepsini ekle. Başlığı ya da açıklamayı değiştirme. Kaydet ve önceki küçük resmi özette yaz.

## Görev 4 – Eksik ayar taraması (ayda bir ya da istenince)
Studio → İçerik'teki bütün videoları ve Shorts'ları tek tek aç, şunları kontrol et ve **önce listele, sonra kanal
sahibine sorup düzelt**:
- "Değiştirilmiş veya yapay içerik": Evet mi?
- Kitle: çocuklara özel değil mi?
- Uzun videolarda altyazı (Türkçe) var mı? Eksikse klasörde `*-altyazi.srt` varsa yükle.
- Uzun videolar "Evin Çevresindeki Hayvanlar" oynatma listesinde mi?
- Uzun videolarda bitiş ekranı var mı?
- Shorts'larda ilgili video dolu mu?
- Planlanmış videoların tarihleri `YUKLEME_LISTESI.txt` dosyalarıyla aynı mı?

## Görev 5 – Yorumlar
Studio → Topluluk → Yorumlar. Yanıtlanmamış yorumları listele (kullanıcı adı yazma, yalnızca yorum metni ve video).
Her birine kısa, sıcak, bilgili bir cevap **taslağı** yaz; **kanal sahibi onaylamadan gönderme.** Hakaret/spam içeren
yorumu gizlemek ya da silmek için de önce sor. Tıbbi/veteriner sorularda "bölgendeki veteriner / Doğa Koruma ve Milli
Parklar şube müdürlüğü" yönlendirmesi yap; telefon numarası yazma.

## Görev 6 – İzlenmeyi artıracak ayarlar ("izlenme ayarlarını yap")
Kanal sahibi bu görevi istediğinde aşağıdaki maddeleri **sormadan uygulayabilirsin** (bu liste onun onayıdır).
Önce her maddenin mevcut durumunu kontrol et; doğruysa dokunma. Listede olmayan hiçbir ayarı değiştirme.

**Kanal (Ayarlar ve Özelleştirme):**
- Kitle: "Hayır, bu kanal çocuklara özel değil".
- Ülke: Türkiye. Kanal anahtar kelimeleri dolu mu (boşsa: avludaki komşular, hayvan belgeseli, doğa belgeseli,
  bahçedeki hayvanlar, hayvan efsaneleri, kertenkele, kirpi, yarasa, baykuş, karga, kırlangıç, yılan).
- Yükleme varsayılanları: görünürlük Gizli, kategori Evcil ve Yabani Hayvanlar, dil Türkçe, açıklamada kanal imzası,
  "Otomatik bölümlere izin ver" açık, "Yerleştirmeye izin ver" açık, yorumlar açık (uygunsuz olanlar incelemeye).
- Özelleştirme → Düzen: abone olmayanlar için kanal fragmanı = son 28 günde en çok izlenen uzun video; aboneler için
  öne çıkan video = en yeni uzun video; bölümler: Popüler videolar, Shorts, "Evin Çevresindeki Hayvanlar" listesi.
- Marka → video filigranı yüklü mü (yoksa klasördeki `filigran.png`); görüntüleme süresi "Tüm video" (kanal sahibi kararı, 22 Kasım).

**Her uzun video (yayındaki ve planlı):**
- "Evin Çevresindeki Hayvanlar" oynatma listesinde.
- Kitle çocuklara özel değil; "Değiştirilmiş veya yapay içerik" Evet.
- Türkçe altyazı var (klasörde `*-altyazi.srt` varsa).
- **Bitiş ekranı:** bir video öğesi (kanalın başka bir uzun videosu; tercihen "Sıradaki komşu" olarak anılan video,
  yoksa "İzleyici için en iyisi") + **abone ol** öğesi; son 10–15 saniyede.
- **Kart:** videonun ortasına yakın bir yerde kanalın en çok izlenen başka bir uzun videosuna kart (bir tane yeter).
- "Abone akışında yayınla ve abonelere bildir" açık (Daha fazla göster altında, varsa).
- Yerleştirmeye izin açık.

**Her Shorts:**
- İlgili video = ait olduğu uzun video (yayındaysa).
- Kitle çocuklara özel değil; yapay içerik Evet.

**Yapma:** başlık, açıklama, etiket, küçük resim, görünürlük ve plan tarihlerini bu görevde değiştirme; reklam/tanıtım
açma; video silme. Bitince değiştirdiğin her şeyi madde madde özetle (video adı → ne değişti).

## Kurallar
- Silme, gizleme, yayınlama, plan tarihini değiştirme, ödeme, reklam/tanıtım, kanal ayarı: **önce kanal sahibine sor.**
- Planlı bir videonun görünürlük ekranını açıp kaydetme (plan iptal olup video hemen yayına girebilir).
- Bir adım 2–3 denemede olmazsa dur, ne denediğini anlat ve sor.
- Telefon numarası, e-posta, şifre yazma/isteme; yorumcuların kişisel bilgisini dosyalara yazma.
- Bittiğinde kısa özet: ne yapıldı, ne kaldı, varsa ekran görüntüsü dosya adları.

## Görev 7 – Büyüme düzenlemesi (kanal sahibi onayı: 22 Kasım, "önerdiklerinin hepsini yap")
Bu görevdeki maddeler kanal sahibinin onayıdır; sormadan uygula. Planlı videolarda yalnızca **Ayrıntılar** ve **Video öğeleri**
ekranlarında çalış, görünürlük ekranını açma.
1. **Ücretli tanıtımı durdur:** Studio → İçerik → geko videosu → Tanıt (ya da YouTube'da tanıtım sayfası) → kampanyayı **Duraklat**
   (yoksa Sonlandır). Yeni tanıtım açma. Harcanan son tutarı özette yaz.
2. **Oynatma listeleri:** aşağıdaki listeleri oluştur (yoksa), görünürlük Herkese açık, açıklamaya "Yanlış Tanınan Komşular serisi" yaz;
   videoları ekle (planlı videolar da eklenebilir; eklenemiyorsa özette not et). "Evin Çevresindeki Hayvanlar" listesi kalır.
   - **Yılan Sanılanlar:** sağır yılan
   - **Zehirli Sanılanlar:** ev kertenkelesi (geko), kara kurbağası, sağır yılan
   - **Gece Gelen Komşular:** yarasa, baykuş, geko, kirpi
   - **Uğursuz Sanılanlar:** baykuş, karga, yarasa
   - **Kuşlar ve Yuvalar:** kırlangıç, karga, baykuş
3. **Bitiş ekranları (yayındaki ve planlı uzun videolar):** mevcut video öğesi ve abone ol kalır; yanına **oynatma listesi öğesi**
   ekle: sağır yılan → Yılan Sanılanlar; geko ve kara kurbağası → Zehirli Sanılanlar; kirpi ve yarasa → Gece Gelen Komşular;
   baykuş → Uğursuz Sanılanlar; karga ve kırlangıç → Kuşlar ve Yuvalar.
4. **Başlık testleri** (Ayrıntılar → Başlık → "Test et" / Test ve karşılaştır; başlık testi yoksa yalnızca B başlığını yaz):
   - Sağır yılan: A = mevcut başlık · B = `Sağır Yılan Zehirli mi? (Bacaklarına Ne Oldu?)` · C = `Sağır Yılanı Sakın Öldürme! (Bacaklarına Ne Oldu?)`
   - Geko: A = mevcut başlık · B = `Ev Kertenkelesi Zehirli mi? (Yemeğe Düşerse Ne Olur?)` · C = `Duvardaki Kertenkeleyi Sakın Öldürme! (Sinekleri O Avlıyor)`
     (geko'da süren küçük resim testine dokunma; aynı anda başlık testi açılamıyorsa başlık testini atla ve özette yaz).
   - Yarasa (planlı): başlığı `Yarasa Saça Yapışır mı? (Karanlıkta Nasıl Görüyor?)` yap. Açıklamaya dokunma.
5. **Topluluk gönderileri:** `topluluk_gonderileri.md` dosyasındaki gönderileri **dosyadaki tarihlerde** Topluluk sekmesinden paylaş
   (Studio → Oluştur → Gönderi oluştur; tarih ileriyse "Planla"). Metni birebir kopyala, anket seçeneklerini aynen yaz.
6. Özet: madde madde ne yapıldı, ne yapılamadı, ekran görüntüsü dosya adları.

## Görev 8 – Abone düzenlemesi (kanal sahibi onayı: 24 Kasım, "bunları kaydet başlayacağız")
Bu görevdeki maddeler kanal sahibinin onayıdır; sormadan uygula. Planlı videoların görünürlük ekranını açma. Para harcayan hiçbir şey yapma.
1. **Kontrol:** kanal kitlesi "çocuklara özel değil"; Gönderiler (Topluluk) sekmesi kanal sayfasında herkese görünüyor mu, planlı anketler (25 Kas, 29 Kas, 2 Ara) duruyor mu; "Uğursuz Sanılanlar" ve "Kuşlar ve Yuvalar" listeleri herkese açık ve kanal sayfasında görünüyor mu. Görünmeyeni düzelt.
2. **Kanal açıklaması:** `kanal/kanal_aciklamasi.md` dosyasındaki "Kanal açıklaması – YENİ" metnini birebir yapıştır (eskisinin yerine). Abone bağlantısındaki @ adı kanalın gerçek @ adıyla aynı değilse gerçek @ adını yaz.
3. **Şemsiye liste:** "Yanlış Tanınan Komşular" adlı, herkese açık bir oynatma listesi oluştur; kanaldaki ve planlı bütün UZUN videoları yayın sırasıyla ekle (Shorts hariç). Açıklama: vaat cümlesi.
4. **Ana sayfa düzeni:** abone olmayanlara gösterilen video (kanal fragmanı) = sağır yılan videosu (geko'nun izlenmesi reklamla şişti; fragman hazır olunca değişecek). Geri dönen abonelere öne çıkan video = en yeni yayındaki uzun video. Bölüm sırası: 1) Yanlış Tanınan Komşular listesi, 2) Kısa videolar, 3) beş konu listesi, 4) Popüler videolar.
5. **Shorts ilgili video (geriye dönük):** kanaldaki bütün Shorts'larda "İlgili video" dolu mu bak; boşsa ait olduğu uzun videoyu seç (yayında olanlar). "Göz Kırpıyorsa Yılan Değildir" → sağır yılan ile başla.
6. **Kart:** her yayındaki uzun videoda videonun ortasına yakın bir yere, aynı konu listesine giden bir kart (zaten bir kart varsa ikinciyi ekleme, var olanı bırak).
7. **Filigran:** "Tüm video" olarak kaldığını doğrula (değiştirme).
8. **Yükleme varsayılanları → açıklama:** en başa vaat cümlesini ve abone bağlantısını ekle, mevcut imzayı koru.
9. **Raporla:** Analytics → Gelişmiş mod → "Abonelik kaynağı" ve video bazında "Kazanılan aboneler" tablosunu oku, `analiz_abone_YYYY-AA-GG.md` olarak klasöre yaz (yalnızca oku).
10. Özet: madde madde ne yapıldı, ne yapılamadı, ekran görüntüleri.
