# Ofisin dersler defteri

Bu defter ofisin hafızası. **Her çalışan ve denetçi işe başlamadan önce okur.** Patron her onay turundan sonra yeni dersleri ekler:
- RET nedenleri
- patronun kendi yakaladığı hatalar
- kullanıcının fark ettiği sorunlar

Amaç aynı hatanın ikinci kez olmaması ve her videonun bir öncekinden iyi olması.

Biçim: tarih ve sahne · ne oldu · bundan sonraki kural · sorumlu.

## Kullanıcının yakaladığı hatalar (en ağır dersler)

- **Kasım 2026, 11 Kuzey ışıkları iglo:** Kuzey ışıkları her 8,5 saniyede tekrar ediyordu ve bunu kullanıcı fark etti.
  - **Kural:** Her videoda `dongu_sn: 96`. Gökyüzü ve deniz gibi klipler `zaman_bukme` ya da `karisik` ile oynatılır.
  - Her video gönderilmeden önce `kontrol.py` testinden geçer.
  - Sorumlu: yapımcı ve kalite kontrol.

## Ofis içinde yakalanan hatalar

- **18 Kasım, 20 göl kulübesi (kalite kontrol RET):** 4K etiketli küçük resimler (`_4K.jpg`) üretilmemişti.
  - **Kural:** Üretim bitince yapımcı `python3 kapak.py <sahne>` ve `python3 kapak4k.py <sahne>` komutlarını çalıştırır.
  - Teslim listesinde altı küçük resim olmalı: A, B, C ve üçünün `_4K` sürümü.
  - Sorumlu: yapımcı.
- **18 Kasım, 25/27/28 (patron yakaladı):** Metin yazarı, yapımcı `sahne.json`'u son hâline getirmeden yazdı. Shorts başlıkları ekrandaki yazılarla tutmadı.
  - **Kural:** Metin yazarı, yapımcının raporu gelmeden ya da `sahne.json` > `shorts`/`shorts2` > `baslik`/`alt` kesinleşmeden Shorts metni yazmaz.
  - Yazdıktan sonra her Shorts başlığını ekran yazısıyla karşılaştırır. POV kancası aynı olmalı.
  - Metin editörü de bunu ayrıca kontrol eder.
  - Sorumlu: metin yazarı ve metin editörü.
- **18 Kasım, 27/28 (patron yakaladı):** Küçük resim alt yazısında "Crackling Fireplace" yazıyordu. Oysa sahnede soba (27) ya da yalnızca kor (28) vardı.
  - **Kural:** Metindeki her öğe görselde gerçekten olan şeyi anlatır: şömine mi, soba mı, kor mu, ateş yok mu?
  - Sorumlu: metin yazarı.
- **18 Kasım, 23 (sistem durdurdu):** Yapımcı ücretli API çağrısı (Kling) yapmaya çalıştı ve izin sistemi engelledi.
  - **Kural:** Para harcayan çağrıları yalnızca patron yapar, o da kullanıcının doğrudan onayıyla.
  - Çalışan, ücretli bir işe ihtiyaç görürse durur ve gerekçesiyle patrona bildirir.
  - Sorumlu: herkes.
- **18 Kasım, 27/28 (yapımcı yakaladı):** Kullanıcının gönderdiği iki görselin dosya adları karışıktı.
  - **Kural:** Görsel numarasına güvenme. Görseli Read ile aç ve içeriğin istenen sahne olduğunu doğrula.
  - Sorumlu: yapımcı.

- **18 Kasım, 21 Paris (patron ve kalite kontrol yakaladı):** Shorts ekran yazısı, Shorts'un kendi kadrajında görünmeyen bir şeyi vaat ediyordu.
  - Birinci Shorts'ta "Crackling Fireplace" yazıyordu ama şömine kadraja hiç girmiyordu.
  - İkinci Shorts'ta "the Eiffel Tower is sparkling" yazıyordu ama kule açılış karesinde yoktu.
  - **Kural:** Shorts yazısındaki her öğe Shorts'un kendi kadrajında görünür. Yazıda adı geçen öğe tercihen açılış karesinde (`bas`) olur.
  - Yapımcı `bas`/`son` noktalarını seçerken kaynak görselden kırpıp bakar. Metin yazarı da yazıyı bu kadraja göre yazar.
  - Aynı sahnenin iki Shorts'u farklı karelerle açılır (örneğin biri ateşle, diğeri pencereyle ya da `yakin` ile).
  - Sorumlu: yapımcı ve metin yazarı.

- **18 Kasım, 22 Tokyo (metin editörü işaretledi, patron düzeltti):** Başlıkta "Lofi Chill" yazıyordu ama videoda müzik yok. Öyküde de "a pot of green tea" geçiyordu, oysa görselde tek bir fincan var.
  - **Kural:** Başlık, etiket ve açıklama videoda olmayan bir şeyi vaat etmez. "Lofi", "music", "piano" gibi kelimeler müziksiz videoda kullanılmaz. Müzik bekleyen izleyici hemen çıkar ve izlenme süresi düşer.
  - Öyküdeki nesnelerin türü ve sayısı (fincan mı, çaydanlık mı) `onizleme.jpg` açılarak görselle karşılaştırılır.
  - Öyküdeki hareket ve ses iddiaları (sallanan fener, geçen tren, uğuldayan rüzgâr) videoda ya da `sahne.json` > `ses` içinde gerçekten olmalı. Olmayanlar sabit bir betimlemeye çevrilir ("parlıyor", "duruyor"). Kalite kontrol 22'de yakaladı.
  - Sorumlu: metin yazarı.

- **19 Kasım, 23 deniz kulübesi (iki denetçi RET):**
  - Fener ışını "dönüyor" (sweeps) diye anlatıldı, oysa videoda sabit. Bu, Shorts ekran yazısında da vardı ve Shorts'un yeniden çizilmesi gerekti.
  - Pusula ve harita öyküde yanlış yerdeydi.
  - Öyküde 09 deniz feneri sahnesiyle aynı kalıplar vardı.
  - Ses listesinde dalga sesi yokken "storm sounds" etiketleri kullanıldı.
  - **Kural:**
    - Metin yazarı her cümlenin fiilini `sahne.json`'daki hareket listesiyle (ateş, yağış, buhar, su, sallantı, ek klip) ve `onizleme.jpg` ile eşleştirir. "sweeps, drifts, swings, sways, boils, hums" gibi fiillere özellikle dikkat eder.
    - Aynı temadaki eski sahnenin öyküsünü yan yana açıp kalıpları karşılaştırır.
    - "sounds" kelimesi yalnızca ses listesinde gerçekten olan şeyler için kullanılır.
  - 24–28'deki benzer hatalar bu ders sayesinde üretimden önce düzeltildi (25: "Jungle Sounds" → "Misty Jungle").
  - Sorumlu: metin yazarı.

- **18 Kasım, ilk fikir toplantısı (patron yakaladı):** İki fikir, Shorts açıklamasına ve yorumuna tıklanabilir bağlantı konabileceğini varsaydı.
  - **Kural:** YouTube bu yüzeylerde bağlantıları tıklanabilir göstermiyor. Shorts'tan uzun videoya tek köprü "İlgili video".
  - Bir yönlendirme fikri önermeden önce o yüzeyde bağlantının gerçekten çalışıp çalışmadığını doğrula.
  - Sorumlu: herkes.
- **18 Kasım, fikir toplantısı:** Aynı görüntünün farklı ses karışımlarıyla ayrı videolar olarak yayınlanması önerildi.
  - **Kural:** Bu yapılmaz. Yeniden kullanılmış içerik riski taşır ve İş Ortağı Programı başvurusunu tehlikeye atar.
  - Sorumlu: herkes.

## Tekrarlayan teknik hatalar (dikkat listesi)

- **Ateş kutusu yanlış yere oturuyor.** Bu dizide altı kez oldu:
  - 19'da koltukta, 20'de fenerde, 26'da mumda, 28'de kâğıt fenerde.
  - 27'de kutu camın yalnızca bir kısmını kaplıyordu.
  - **Kural:** Otomatik ateş kutusuna asla güvenme. Her zaman algılama görseline bak, gerekirse kutuyu yalnızca alevlerin üstüne elle çiz.
- **Pencere kutusu taşıyor:** Masa, minder ya da yastık kutunun içine giriyor.
  - **Kural:** Taşan bölümleri `haric` ile çıkar, öndeki bitkileri ve mobilyayı da.
- **Işık noktaları yanlış nesnelere düşüyor:** Zemin yansımaları, kitap sırtları, metal parlamaları.
  - **Kural:** Işık listesini tek tek gözden geçir.
- **Disk doldu, son birleştirme yarıda kesildi (20, 16 Kasım).**
  - **Kural:** İşe başlamadan boş yere bak. Biriken eski dosyaları temizle.
- **Başlık 100 karakteri aştı (13–20).**
  - **Kural:** Her başlık en fazla 95 karakter olmalı. Python `len()` ile ölç.
- **B küçük resmindeki "3 HOURS" etiketini YouTube'un süre yazısı kapattı.**
  - **Kural:** Sağ alt köşeye yazı ya da etiket koyma.
- **Shorts sade bir kareyle açılıyordu** (koltuk, yorgan).
  - **Kural:** Shorts'un ilk saniyesi en etkileyici manzarayla başlar (`bas` noktası).
- **Ses kaynağı satırları:** Kaynak satırı her zaman `sahne.json` > `ses` içinde gerçekten kullanılan dosyalara göre yazılır. Örneğin 21'de yalnızca Pixabay sesleri vardı, Wikimedia atfı gerekmedi. Klasörde duran ama kullanılmayan dosya atıf gerektirmez. Kaynak satırını yazmadan önce `sahne.json` > `ses` yollarını tek komutla listele; klasördeki dosyalara bakma.

## Kalite çıtası: "en iyisi" ne demek?

- Açılış karesi ve küçük resim, bir telefonda kaydırırken insanı durduracak kadar güzel olmalı.
- Sahnedeki her hareket doğal olmalı: ateş, kar, yağmur, buhar, su. Abartılı ya da yanlış yerde hareket, hiç hareket olmamasından kötüdür.
- Her video kanaldaki diğerlerinden ayırt edilebilmeli: farklı mekân, farklı öykü, farklı kanca.
- Bir şeyden emin değilsen raporunda açıkça yaz. Saklanan bir şüphe, sonradan kullanıcının yakaladığı bir hataya dönüşür.

- **"Sahibi sobayı yakar, çaydanlık üstte" kalıbı yasak (24 tekne evi RET'i).** "Its owner lights the (little iron) stove, sets the kettle on top" ve "When the rain(s) come/arrive, its owner lights…" kanalın klişesi oldu (15, 18, 20, 24, 25'te geçti). Öykü yazmadan önce eski öykülerin ilk iki cümlesini `grep -h -A3 DESCRIPTION dream-window/*/yukleme_3saat.txt` ile karşılaştır; kimsenin bir şey yaktığını/hazırladığını anlatmak yerine sahnedeki sesi ve ışığı (yağmur, çıtırtı, yansıma, buhar) öznesi yap.
- **Shorts'un `son` karesi de yazıdaki öğeyi içermeli (24 tekne evi notu).** shorts 1. saniyede sobayla açılıyordu, ama 24. saniyede soba kadrajdan çıkıyordu ve "Wood Stove" yazısı yalnızca açılışta doğruydu. **Kural:** `bas` ve `son` seçerken iki kadrajı da sahne.png üzerinde hesapla (h = H/yakin, w = h·1080/1920); yazıdaki öğe iki uçta da görünsün. Denetimde 1. ve 24. saniye kareleri birlikte zorunlu.
- **Bir sahnenin iki Shorts'u aynı yolu ters yönde gezmemeli (25 ağaç ev).** shorts 1380→700, shorts2 700→1380 ayarlanmıştı; iki Shorts aynı karelerden oluşuyordu, yalnızca yön farklıydı. Bu "yeniden kullanılmış içerik" izlenimi verir. **Kural:** shorts2 farklı bir yakınlıkla (`yakin` 1.4–1.5) ve farklı bir yolla gezer; iki Shorts'un `bas`/`son` değerlerini yan yana yazıp karşılaştır.
