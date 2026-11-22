---
name: dream-window-yeni-sahne
description: Dream Window (uyku/ortam YouTube kanalı) için yeni bir sahneyi baştan sona üretir. Bir ChatGPT görselinden canlandırılmış 3 saatlik video, iki Shorts, A/B/C/D küçük resimler, öykülü yükleme metinleri, 4K paket, 5 dilde çeviriler üretir. Hepsini tekrar testinden ve ofis onay zincirinden (kalite kontrol, metin editörü, kanal yöneticisi) geçirip takvim önerisiyle teslim eder. Kullanıcı yeni bir sahne görseli gönderdiğinde mutlaka bu skill'i kullan. Görsel çoğu zaman yalnızca bir numarayla gelir ("21", "22.png"). "Yeni sahne", "bu görseli canlandır", "bundan video yap", "yeni görseller gönderiyorum" gibi ifadelerde de kullan. Görsel ChatGPT istemi yazmak, toplu görsel üretmek (toplu.py) ya da var olan bir sahneyi yeniden üretmek için de kullan.
---

# Dream Window – yeni sahne üretimi

Dream Window, yüzsüz ve anonim bir uyku/ortam kanalı. Kullanıcının hedefi para kazanmak; kanalın para kazanabilmesi için her videonun özgün, kusursuz ve tekrarsız olması gerekiyor. Kod `dream-window/` klasöründe, Türkçe adlandırılmış Python betikleri olarak duruyor.

**Kullanıcıyla iletişim:** Kullanıcı Türkçe konuşuyor ve teknik değil. Her zaman Türkçe, kısa ve net yaz. Kod, dosya yolu ve terim yığma; ne yaptığını ve ondan ne beklediğini söyle. Kullanıcının adını ve hesap bilgilerini hiçbir dış servise gönderme.

## Neden bu kadar dikkat?

Bir keresinde kuzey ışıkları her 8,5 saniyede bir tekrar ediyordu ve bunu kullanıcı yakaladı. Kullanıcı "Lütfen böyle bir hata daha yapma, sana güveniyorum" dedi. O günden beri şu söz verildi: **her video gönderilmeden önce tekrar testinden geçer.** Bu skill'deki kontroller ve ofis onayı bu sözü tutmak için var. Hiçbirini kısaltma.

## Dersler defteri

Ofisin hafızası `references/dersler.md` dosyasında. İşe başlamadan önce oku; çalışanlara ve denetçilere de okutulur.

Her onay turundan sonra patron deftere yeni dersleri ekler:
- RET nedenleri
- patronun kendi yakaladığı hatalar
- kullanıcının fark ettiği sorunlar
- çalışanların raporlarındaki işe yarar öneriler

Aynı hata iki kez yaşanırsa yalnızca deftere yazmakla kalma. Kontrol listesini ya da betiği düzelt, o hata bir daha olamasın.

## Görsel tarzı (kanal sahibinin kararı, 22 Kasım)

Kanal sahibi, 400 bin+ izlenen rakip kanalı ("Cozy Dream Window") inceledikten sonra "bundan sonraki videoları böyle yapalım" dedi. Yeni sahnelerin ChatGPT istemlerine şu ışık tarzı eklenir:

- **Karanlık, düşük anahtarlı ışık:** tavan ya da ana lamba yok. Oda yalnızca mumlar, küçük peri ışıkları, (varsa) ağaç ışıkları ve ateşle aydınlanır.
- **Tek sıcak renk:** derin kırmızı-amber parıltı, derin gölgeler.
- **Soğuk dışarı:** pencerenin dışı lacivert-mavi gece (kar, yağmur, ay). İçerinin sıcaklığıyla karşıtlık kurar.
- **Az eşya:** sade, sakin kompozisyon; göz dinlensin. Kalabalık masa ve süs yığını yok.
- **Neden:** Uyku izleyicisi videoyu bütün gece açık bırakır; karanlık ekran odayı aydınlatmaz. Atmosfer de daha "güvende ve sıcak" hissettirir.

İsteme eklenecek İngilizce satır:
> Very dark, low-key cinematic lighting: no ceiling lights, the room is lit only by candles, tiny fairy lights and the fire, creating a deep warm red-amber glow with soft deep shadows. Outside the window, a cool deep-blue night for contrast. Calm, minimal, uncluttered composition.

Küçük resimde rakip kanallar yazı kullanmıyor. Her uzun video için `kapak.py` artık yazısız **D** seçeneğini de üretir; YouTube'un "Test et ve karşılaştır" testinde B, C ve D birlikte denenir.

## Ön kontrol (her seferinde)

1. `df -h /`: en az 5 GB boş yer olmalı (bir sahne yaklaşık 1,5 GB kullanır; 10 saatlik videolar için 10 GB). Disk dolunca son birleştirme yarıda kesilir ve bozuk dosya kalır. Yer yoksa önce büyük, gereksiz dosyaları sil (eski `_gecici*` klasörleri, kullanılmayan önbellekler).
2. `pgrep -af "uret.py|shorts.py"`: başka ağır iş çalışıyorsa bekle. Bellek sınırı yaklaşık 8 GB. İki ağır iş birlikte çalışınca biri öldürülür.
3. Sıradaki numarayı bul (`ls -d dream-window/[0-9][0-9]-*`). Klasör adı: `NN-ingilizce-kisa-ad` (örn. `21-snowy-observatory`).

## 1) Taslak

Görselden şunlara karar ver:
- **yağış:** `kar` ya da `yagmur`
- **ateş:** şömine/soba var mı (`--ates var|yok|oto`)
- **Noel:** süs, ağaç ya da yılbaşı ışıkları varsa `--noel`

Ateş klibi para gerektirmez: var olan bir sahnenin klibi yeni ocağa oturtulur (`--ates-klip`).

| Ocak türü | Klibi kullanılabilecek sahneler |
|---|---|
| Açık taş şömine | 03, 05, 07 |
| Camlı döküm soba | 06, 08, 09 |

```bash
cd dream-window
python3 yeni_sahne.py taslak 21-ad gorsel.png --yagis kar --ad "English Name" [--noel] [--ates var] [--ates-klip 05-snowy-library]
```

Sonra `algilama.jpg` ve `onizleme.jpg` dosyalarını Read ile **mutlaka gözünle incele**. Otomatik algılamanın sık yaptığı hatalar:

- **Ateş kutusu yanlış yerde:** lambaya, masaya, koltuğa ya da fenere oturmuş.
- **Pencere kaçırılmış:** çok koyu pencere hiç bulunmamış.
- **Pencere kutusu taşmış:** mobilyayı ya da duvarı içine almış.
- **Pırıltı yanlış yerde:** masadaki nesnelere düşmüş.

Düzeltmeleri `sahne.json`'da elle yap, sonra `taslak <klasor> --yeniden` ile önizlemeyi yenile ve tekrar bak. Hangi anahtarın neyi düzelttiği `references/sahne-ayarlari.md` dosyasında. Kutu ya da maske düzeltmeden önce bu dosyayı oku.

Sahneye göre ekleyebileceğin canlandırmalar:
- **Buhar:** fincan ya da çaydanlık üstüne.
- **Su:** göl ya da gölet.
- **Sallantı ve tren sesi:** tren sahnelerinde.
- **Pırıltı:** yalnızca yılbaşı ışıkları ve havai fişeklerde.

## 2) Metinler (üretim sürerken de yazılabilir)

`yeni_sahne.py uret` metin şablonlarını oluşturur; öyküler `[ÖYKÜ]` ve `[KISA ÖYKÜ]` olarak boş kalır. Onları sen yazarsın.

**Uzun video başlığı:**
- Kalıp: `3 Hours <Ad> <2 emoji> <öğeler> for <kullanım>`.
- **En fazla 95 karakter** (Python `len`). YouTube'un sınırı 100 ve uzun başlık yüklemede hata verir.

**Öykü (açıklamadaki ilk paragraf):**
- 3–4 cümlelik kısa bir sahne öyküsü.
- Hayalî ama somut bir yer adı olsun (Silverfrost Wood, Hartwell Garden gibi).
- Duyulara hitap etsin, sakin ve sıcak olsun.
- Her sahnenin öyküsü farklı olmalı. YouTube'un "seri üretilmiş, özgün olmayan içerik" kuralına karşı kanalın en önemli savunması bu öyküler.

**Açıklamada kalması gereken satırlar:**
- "The scene is an AI-generated illustration animated for this video." satırı açıklamada kalır.
- **Ses kaynakları satırları**, `sahne.json` > `ses` içinde gerçekten kullanılan dosyalarla eşleşmeli:

| Ses dosyası | Kaynak satırı |
|---|---|
| `ses_kaynak/ates.ogg` | "Campfire sound ambience" by Glaneur de sons, CC BY 3.0 (Wikimedia). Atıf zorunlu. |
| yağmur `ses_kaynak/yagmur*` | "Falling Rain SFX 1" by valvalion, CC BY 3.0 (Wikimedia). Atıf zorunlu. |
| `../sesler/*.mp3` | Pixabay. Atıf gerekmez ama "additional ... sounds from Pixabay" yazılabilir. |

Bağlantılar için var olan bir sahnenin `yukleme_3saat.txt` dosyasından kopyala.

**Shorts metinleri (`shorts_yukleme.txt`, `shorts2_yukleme.txt`):**
- İlki sahnenin adıyla.
- İkincisi "POV: ..." kancasıyla.
- Kancalar kanaldaki diğer Shorts'larla aynı olmamalı. Kontrol için: `grep -h -A1 TITLE dream-window/*/shorts*_yukleme.txt`.

**Kanal dosyaları:**
- `kanal/kapak_metinleri.json`: `"21-ad": ["BÜYÜK BAŞLIK", "Alt yazı & Öğe"]`. Sonra `python3 kapak.py 21-ad` B ve C küçük resimlerini üretir.
- `kanal/baslik_4k.json`: 4K başlık. Kalıp `<Ad> 4K <emoji> 3 Hours <öğeler> for <kullanım>`, en fazla 95 karakter.
- `kanal/ceviriler/21-ad.txt`: 5 dil (Deutsch, Español, Português, Français, 日本語). Her dil `=== Dil ===`, `TITLE`, `TITLE_4K`, `DESCRIPTION` bölümlerinden oluşur.
  - Ses kaynakları, bağlantılar, hashtag satırı ve "Dream Window" adı İngilizce kalır.
  - Biçim için var olan bir dosyaya bak.

## 3) Üretim

Üretim saatler sürer ve çalışma ortamı her an yeniden başlayabilir. Bu yüzden:

```bash
cd dream-window
nohup setsid python3 yeni_sahne.py uret 21-ad > _log_21.txt 2>&1 < /dev/null &
```

- Bitmesini bir arka plan bekleme döngüsüyle izle: "RAPOR" ya da "Hata" satırı, işin durması ya da 1,5 GB'ın altına düşen boş yer.
- Tek bekleme en fazla 2 saat sürebilir, süre dolunca yeniden kur.
- Ortam yeniden başlarsa iş ölür. Aynı komutu tekrar çalıştır; biten parçalar (`_gecici_*` içindeki acilis/dongu/kapanis ve hazır mp4'ler) yeniden kullanılır.
- Birden fazla sahne varsa hepsini **tek bir sıralı betikte** art arda çalıştır, asla paralel çalıştırma.

## 4) Yapımcının kendi kontrolü

Ofise göndermeden önce şunları kendin doğrula:

- Rapor satırları: 3 saatlik video, `shorts`, `shorts2` ve 4K paket "TAMAM" olmalı.
  - Uzun videoda döngü 96 saniye civarında ("her 96.0 sn'de bir başa dönüyor (sınır 60 sn)").
  - Shorts'ta "24 sn içinde birebir tekrar yok".
- `ffprobe` ile süreler:
  - Uzun video en az 10800 sn.
  - Shorts 48 sn.
- Dosya boyutları: Video 400 MiB'ı aşarsa sohbetle gönderilemez. Bu durumda sesi `uret.py <sahne> --sesdegistir --cikti video_3saat.mp4 --ses-kbps 72` ile küçült.
- Görsel kontrol:
  - Shorts'lardan 1. ve 24. saniyede kare çıkarıp bak.
  - Yazı okunuyor mu, ateş doğru yerde mi, kadraj güzel bir yerden açılıyor mu?
  - Shorts'ta ilk saniye izleyiciyi tutar; en etkileyici kareyle (genelde karlı/yağmurlu pencere) başlamalı.

## 5) Ofis – kim ne yapar, onay zinciri

Kullanıcı, işin "farklı ajanlar ve yöneticiler birbirinin onayını alarak" teslim edilmesini istedi. **Patron sensin** (ana oturum). Kullanıcıyla yalnızca patron konuşur. Ekibin tanımları `.claude/agents/` klasöründe:

```
                    PATRON (ana Claude oturumu)
        iş dağıtır · son onayı verir · kullanıcıya teslim eder
                               │
                    KANAL YÖNETİCİSİ (kanal-yoneticisi)
       denetçi raporlarını okur · strateji ve takvim · patrona öneri
                               │
       ┌───────────────┬───────┴───────┬───────────────┐
  SAHNE YAPIMCISI  METİN YAZARI   KALİTE KONTROL   METİN EDİTÖRÜ
  (sahne-yapimcisi)(metin-yazari) (kalite-kontrol) (metin-editoru)
  taslak, düzeltme öykü, başlık,  tekrar testi,    başlık, öykü,
  üretim           çeviri         süre, kare, ses  kaynak, çeviri
```

**Akış:**
1. Patron görseli yapımcıya verir (adım 1 ve 3). Aynı anda metin yazarına da görev verir (adım 2). Yazar, sahne adı ve `sahne.json` > `ses` belli olunca başlayabilir.
2. Üretimi patron izler (bekleme döngüsü). Bittiğinde adım 4'ü yapımcıya yaptırır ya da kendisi yapar.
3. Kalite kontrol ve metin editörü **aynı anda** incelemeye başlar.
4. İkisi bitince kanal yöneticisi iki raporu okur ve patrona öneri sunar.
5. Patron son kararı verir. Kararını vermeden kendisi de önizlemelere hızlıca bakar.

**Ajanlar nasıl çalıştırılır:**
- Bu ajan türleri listede görünüyorsa adlarıyla çalıştır.
- Görünmüyorsa (oturum, ajan dosyaları eklenmeden önce başladıysa) `general-purpose` ajana `.claude/agents/<ad>.md` dosyasındaki talimatı aynen ver.
- Her ajana şunları yaz:
  - sahne klasörü (`dream-window/21-ad`)
  - günlük dosyasının yolu
  - neyin teslim edileceği
  - varsa önceki turun RET maddeleri

**Kurallar:**
- Denetçiler son satıra `KARAR: ONAY` ya da `KARAR: RET`, yönetici `ÖNERİ: ONAY` ya da `ÖNERİ: RET` yazar. Denetçiler ve yönetici dosya değiştirmez.
- RET gelirse:
  - Patron düzeltmeyi ilgili çalışana verir: teknik sorun yapımcıya, metin sorunu yazara.
  - Sonra yalnızca RET veren denetçiye ve yöneticiye yeniden gönderir.
- En fazla 2 tur. Hâlâ RET varsa teslim etme. Kullanıcıya durumu açıkça anlat ve kararı ona bırak.
- Onay kayıtlarını `dream-window/kanal/onaylar/21-ad.md` dosyasına kısaca yaz: kim, hangi tur, karar, düzeltilenler.
- Tur bitince `references/dersler.md` dosyasını güncelle: yeni hatalar, yeni kurallar, işe yarar ders önerileri.
- **Öneri kutusu:** Ajanların "yeni fikir"lerini `dream-window/kanal/oneriler.md` dosyasındaki "Bekleyen" bölümüne ekle. Yönetici değerlendirsin.
  - "Sun" kararı alan en iyi 1–3 fikri teslim raporunda kullanıcıya sade bir dille sun: ne, neden, maliyeti.
  - Kullanıcının kararını dosyaya işle. Onaylanan fikri uygula ya da plana al. Reddedileni gerekçesiyle kaydet.
  - Kullanıcıyı fikir yağmuruna boğma. Az ama değerli sun.
  - Ofisin elemek istediği fikirleri de tek satırla ve gerekçesiyle göster. Kesin eleme kullanıcının onayıyla olur.
- **Maliyet:** Her ajan kullanım hakkından yer. Küçük işlerde (tek bir başlık düzeltmesi, bir Shorts'un yeniden üretimi) bütün ofisi çalıştırma. Yalnızca ilgili denetçiyi çalıştır, patron onayı yeterli.

## 6) Teslim

1. `gunluk.py` içindeki `AD` (klasör → dosya adı) ve `TR` (dosya adı → Türkçe ad) sözlüklerine sahneyi ekle.
2. Takvim önerisi:
   - Uzun videolar haftada 2 (genelde salı ve cumartesi) 20:00'de, boşluklara yerleşir.
   - Birinci Shorts uzun videodan 2–3 gün önce çıkar (uzun video günü İlgili video olarak bağlanır).
   - POV Shorts 1–2 gün sonra çıkar (yüklerken bağlanır). Shorts saati 19:30.
   - Noel ve yılbaşı sahnelerini Aralık sonuna denk getir.
   - **Takvime yazmadan önce kullanıcıdan onay al.** Onaylayınca `kanal/takvim.json`'a ekle.
   - Günlük hatırlatma görevinin bitiş tarihi yeni tarihlerden önceyse uzat.
3. Kullanıcıya Türkçe ve kısa bir rapor gönder:
   - Sahne, süre, boyut ve test sonuçlarını içeren bir tablo.
   - Ofis onay özeti ("Kalite kontrol ✅ · Metin editörü ✅ · Yönetici ✅").
   - Küçük resim ve Shorts önizleme sayfası.
   - Tarih önerisi.
4. Commit at ve oturum talimatındaki dala push'la. Commit mesajında model adı geçmesin.

## Hatırlanması gerekenler

- Gerçekten 4K yüklenmeyen videoya "4K" yazma; izleyiciyi yanıltır.
- Bir siteyi korumasını aşarak (Cloudflare vb.) ses ya da görsel indirmeye çalışma. Pixabay sesleri kullanıcı kendisi indirir.
- Kullanıcıdan sohbete şifre ya da API anahtarı yapıştırmasını isteme.
- Toplu görsel üretimi (`toplu.py gorseller`) para harcar. Maliyeti göster ve `--onay` olmadan çalıştırma.
