---
name: avludaki-komsular-yeni-video
description: Avludaki Komşular (evin çevresindeki yanlış tanınan hayvanları anlatan Türkçe YouTube belgesel kanalı) için yeni bir uzun video ve iki Shorts'u baştan sona üretir. Araştırma, senaryo, bağımsız bilgi kontrolü, yapay zekâ görselleri ve klipleri, gerçekçi Türkçe seslendirme, kurgu, son kontrol testleri yapılır. İş, ofis onay zincirinden (bilgi kontrolcüsü, kalite kontrol, metin editörü, kanal yöneticisi) geçirilip takvim önerisiyle teslim edilir. Kullanıcı "yeni video", "sıradaki hayvan", "başla", bir hayvan adı ya da hayvan-kanali klasöründeki bir videonun düzeltilmesini istediğinde kullan. Shorts üretimi, video yeniden sıralama ya da izleyici verisine göre düzeltme için de kullan.
---

# Avludaki Komşular – yeni video üretimi

Avludaki Komşular, evlerin, bahçelerin ve köylerin çevresinde yaşayıp yanlış tanınan hayvanları anlatan, yüzsüz bir Türkçe belgesel kanalı. Görseller yapay zekâ çizimi, anlatım yapay zekâ sesi. Kod `hayvan-kanali/` klasöründe, Türkçe adlı Python betikleri olarak duruyor. Kullanıcının hedefi kanaldan para kazanmak (1.000 abone ve 4.000 saat).

**Kullanıcıyla iletişim:** Kullanıcı Türkçe konuşuyor ve teknik değil. Her zaman Türkçe, kısa ve net yaz. Komut açıklamaları da Türkçe olur ("İngilizce yazma"). Kullanıcının adını, e-postasını ve telefonunu hiçbir dış servise gönderme, tekrar etme.

## Neden bu kadar dikkat?

Kullanıcının istekleri:
- "Hata yapma, kontrol et, masraftan kaçma, izlenmek istiyorum."
- "Fiyat-fayda olarak bak."
- "Seslendirme gerçekçi olsun, yapay olduğu belli olmasın."
- "Testlerden geçir."

Bir keresinde bilgi kontrolcüsünün önerdiği yanlış telefon numarası (Alo 174) videoya girdi. Video yeniden üretildi ve kullanıcıya ilk dosyayı yüklememesi söylendi. O günden beri: **her bilgi bağımsız kontrolden geçer, kontrolcünün önerisi de doğrulanır, her video 14 testten ve ofis onayından geçmeden gönderilmez.**

## Şirket el kitabı

Kanal sahibi "büyük bir şirket gibi yönetin, birlikte büyüyelim" dedi (19 Kasım). Hedefler (OKR), haftalık göstergeler, organizasyon, çalışma ritmi (haftalık yönetim toplantısı, aylık strateji), yetki kuralları, bütçe, içerik stoku hedefi (4 hazır video) ve risk listesi `hayvan-kanali/kanal/sirket.md` dosyasında. Harcamalar `hayvan-kanali/kanal/butce.md` dosyasına video video yazılır. Yorumlar için topluluk sorumlusu (`avlu-topluluk`) çalışır.

## Dersler defteri

Ofisin hafızası `references/dersler.md` dosyasında. İşe başlamadan oku, ajanlara da okut. Her onay turundan sonra yeni dersleri ekle. Aynı hata iki kez olursa betiği ya da kontrol listesini düzelt.

## Ön kontrol (her seferinde)

1. `df -h /`: en az 5 GB boş yer.
2. Python ortamı: Whisper gerektiren adımlar (seslendirme, son kontrol) faster-whisper kurulu bir Python ile çalışır. Oturumda yoksa scratchpad'e venv kur:
   `pip install faster-whisper numpy pillow`
   Çalıştırırken `HF_HUB_DISABLE_XET=1` ver. Model indirme hatası olursa bu değişken çözer.
3. Replicate kredisi: büyük harcamadan önce yeterli mi? Kredi bitince 402 hatası gelir.
4. Sıradaki konu: `hayvan-kanali/kanal/fikirler.json`. Klasör adı `NN-konu` (ör. `06-karga`).

## Fabrika hattı (19 Kasım 2026'dan beri)

Kanal sahibinin isteği: "Şirketi büyütmeni ve geliştirmeni istiyorum, fabrika gibi işlesin, işinde profesyonel çalışanlar al."

Her video aşağıdaki istasyonlardan **sırayla** geçer. Her istasyonun sonunda bir **kalite kapısı** vardır: kapıdan geçmeyen iş bir sonraki istasyona gitmez, hata hattın başında düzeltilir. Durumu her zaman `python3 pano.py` gösterir (`kanal/uretim_panosu.md`).

| # | İstasyon | Yapan | Kalite kapısı (geçmeden ilerlenmez) |
|---|---|---|---|
| 1 | Senaryo | senarist | `metin_kontrol.py` 0 HATA |
| 2 | Kaynak arşivi | **kaynak arşivcisi** (avlu-kaynak-arsivcisi) | her kaynak açılmış ve `kaynaklar/` altında, künye sayfadan, `kaynak_eslesme.md` tam |
| 3 | Bilgi onayı | bilgi kontrolcüsü | KARAR: ONAY (görsele para ancak bundan sonra) |
| 4 | Görsel | yapımcı istem yazar, patron üretir | **görsel denetçi** (avlu-gorsel-denetci): ölçek, tür, anatomi, nesne sayısı, yazı → KABUL |
| 5 | Klip | yapımcı istem yazar, patron üretir | görsel denetçi: 0,3 sn kare taraması → KABUL / kırp / düşür |
| 6 | Ses | **seslendirme yönetmeni** (avlu-seslendirme-yonetmeni) okunuşları hazırlar, patron seslendirir | yönetmen farkları sınıflandırır; HATA kalmaz, dinleme listesi çıkar |
| 7 | Çekim planı | yapımcı; Shorts kadrajı Shorts uzmanı | n toplamı = cümle sayısı, her etiket kendi cümlesinde; bitiş w/y yazılı |
| 8 | Video ve test | patron, **yalnızca `python3 hat.py uret ...`** | son kontrol 14/14 |
| 9 | Shorts | patron, `hat.py uret` | son kontrol geçti, ilk-orta-son kare kontrolü |
| 10 | Denetim | kalite kontrol + metin editörü (paralel) | ikisi de ONAY |
| 11 | Puan | patron, `puan.py ekle` | en az 80 (kırmızı çizgi yok) |
| 12 | Teslim | patron, `teslim.py` | kopyalar cmp ile doğrulandı |


**Otomatik bekçi (`otomatik.py`, 19 Kasım):** Makinenin yakalayabileceği her hata insan denetimine gelmeden yakalanır.
- `hat.py uret` her videodan önce `otomatik.py kontrol <video> --onkontrol` çalıştırır. HATA varsa o video oluşturulmaz.
- `teslim.py` önce `otomatik.py kontrol <video> --teslim` çalıştırır; HATA ya da yapılmamış iş varsa teslim etmez.
- `otomatik.py duzelt <video>`: uygun olmayan sesleri yeniden seslendirir, eski kalmış videoyu ve son kontrolü üretim hattında yeniler.
- Kendiliğinden düzeltilenler: Shorts bitiş w/y, düşürülmüş klibe bağlı çekim, kalmış `_gecici`.
- Yakalanan HATA'lar: metin HATA, yanlış okunuş alanı, çekim toplamı ≠ cümle sayısı, eksik görsel/klip, son kontrol KALDI, disk.
- Her gün 09:43'te (İstanbul) zamanlanmış "Günlük otomatik bekçi turu" bütün videoları denetler, düzeltir, pano ve üretim müdürü raporuyla kanal sahibine kısa özet verir.

**Hat kuralları:**
- **Tek üretim hattı:** `video.py`, önizleme, `--kapak` ve `son_kontrol.py` yalnızca `python3 hat.py uret|onizleme|kapak <klasör...>` ile çalışır. Hat kilitlidir: aynı anda tek iş, diğerleri sırasını bekler; her işten önce boş yer kontrol edilir, sonra `_gecici` silinir. (19 Kasım: iki oluşturma aynı anda çalıştı, disk doldu.)
- **Yarım iş sınırı:** aynı anda en çok 2 video denetim istasyonunda (10).
- **Hata başta düzeltilir:** son denetimde çıkan bir hata türü, giriş kapısındaki uzmanın kontrol listesine eklenir (görsel → görsel denetçi, künye → kaynak arşivcisi, okunuş → seslendirme yönetmeni).
- **Üretim müdürü** (avlu-uretim-muduru) her gün ve her büyük işten sonra panoyu okuyup darboğazı, kırmızı videoları ve sıradaki işleri çıkarır. Haftalık yönetim raporunda pano tablosu yer alır.

## Adımlar ve komutlar (`hayvan-kanali/` içinde)

| Adım | Kim | Komut ya da iş | Maliyet |
|---|---|---|---|
| 1. Araştırma ve senaryo | senarist | `senaryo.json`, `shorts.json` metinleri | yok |
| 2. Bilgi kontrolü | bilgi kontrolcüsü | rapor; patron önerileri doğrular ve uygular | yok |
| 3. Görsel istemleri | yapımcı | `gorseller.json` | yok |
| 3b. Gerçek görüntü (önce) | patron | `python3 gercek_gorsel.py NN inat <ad> "<bilimsel ad>" --turkiye` (iNaturalist, tür doğrulanmış, ücretsiz); yoksa `ara` (Wikimedia Commons). Gerçek fotoğraf bulunamayan sahne için yapay zekâ görseli üretilir. Ölü/ezik hayvan, çıplak elle tutma gibi kanal kurallarına aykırı kareler seçilmez; atıf `kunye` ile açıklamaya eklenir | yok |
| 4. Görsel adayları | patron | `python gorsel.py NN --onay` (≈ 2 $: en çok 20 görsel, hayvansız sahnede `"aday": 1`) | var |
| 5. Aday seçimi | yapımcı önerir, patron seçer | `python gorsel.py NN --sec ad=N ...` | yok |
| 6. Klipler | yapımcı yazar, patron üretir | `python klip.py NN --onay` (4 × 0,35 $: açılış, iki Shorts açılışı, kapanış), arka planda | var |
| 7. Seslendirme | patron | `seslendir_bulut.py NN`, sonra farklar için `--cumle i j` | az |
| 8. Çekim planı | yapımcı | `cekimler.json` ve `video.py NN --onizleme` | yok |
| 9. Video | patron | `python3 hat.py uret NN` (video + son kontrol, tek hat) | yok |
| 10. Shorts | yapımcı kadraj, patron üretir | `shorts_kur.py NN`, sonra her Shorts için seslendir, video, son kontrol | az |
| 1b. Metin denetimi | patron | `python metin_kontrol.py NN` (HATA varsa seslendirmeye geçilmez) | yok |
| 10b. Küçük resim A/B/C | paketleme yazar, patron üretir | `python video.py NN --kapak` (senaryo.json > kapak, kapak_alternatifler) | yok |
| 11. Ofis onayı | denetçiler, yönetici | aşağıda | yok |
| 12. Teslim | patron | `python teslim.py NN` (son kontrolü geçmemiş videoyu teslim etmez, kopyaları cmp ile doğrular, yükleme listesi yazar) | yok |
| 13. Yayın sonrası | analist | kanal sahibinin ekran görüntüleri → dersler, `puan.py gercek` | yok |

Bir videonun toplam maliyeti yaklaşık 5,5–7 $.

**Önemli:**
- Uzun süren işleri (klip, seslendirme, video, son kontrol) her zaman arka planda ve en az 1 saatlik süre sınırıyla başlat.
- Komut süre sınırına takılırsa Replicate'teki son işlere bak (`curl https://api.replicate.com/v1/predictions`). Tahmin oluşmuşsa yeniden ödeme yapma, çıktısını indir.
- Seslendirmede hedef 0 kelime farkı. Testi geçen 1 kelimelik farklar da okunur, anlamı değişenler yeniden seslendirilir.
- Klip bozuksa temiz aralığı kırp (`_ham.mp4` sakla, ileri-geri oynat) ve klipler.json "duzenleme" alanına yaz.
- Kadraj, etiket ve küçük resim her zaman gözle (Read) kontrol edilir.

## Ofis – kim ne yapar, onay zinciri

Kullanıcı, Dream Window kanalındaki gibi işin "farklı ajanlar ve yöneticiler birbirinin onayını alarak" teslim edilmesini istedi. **Patron sensin** (ana oturum). Kullanıcıyla yalnızca patron konuşur. Ekibin tanımları `.claude/agents/avlu-*.md` dosyalarında:

```
                         PATRON (ana Claude oturumu)
        iş dağıtır · para harcayan işleri yapar · son onay · kullanıcıya teslim
                                     │
          KANAL YÖNETİCİSİ (strateji)          ÜRETİM MÜDÜRÜ (avlu-uretim-muduru)
          denetçi raporları · takvim · öneri    pano · darboğaz · sıra · stok
                                     │
   ÜRETİM HATTI                     GİRİŞ KALİTE KAPILARI          SON DENETİM
   SENARİST (avlu-senarist)         KAYNAK ARŞİVCİSİ (künye)      BİLGİ KONTROLCÜSÜ
   YAPIMCI (avlu-yapimci)           GÖRSEL DENETÇİ (görsel, klip)  KALİTE KONTROL
   SHORTS UZMANI                    SESLENDİRME YÖNETMENİ (ses)    METİN EDİTÖRÜ
   PAKETLEME (başlık, küçük resim)
                                     │
             BÜYÜME: VERİ ANALİSTİ (ölçüm) · TOPLULUK SORUMLUSU (yorumlar)
```

**Akış:**
1. **Senaryo.** Patron konuyu senariste verir. Senarist `senaryo.json` ve `kaynak_eslesme.md` dosyalarını yazar.
2. **Otomatik metin denetimi.** Patron `python metin_kontrol.py NN-konu` çalıştırır. HATA varsa senarist düzeltir. Bu ajan çalıştırmaz, para harcamaz, saniyeler sürer.
3. **Bilgi kontrolü.** Bilgi kontrolcüsü inceler ve puanlar. RET ise senarist düzeltir. Bilgi ONAY'ı gelmeden görsele para harcanmaz.
4. **Paralel işler:**
   - Yapımcı görsel ve klip istemlerini yazar.
   - Shorts uzmanı iki Shorts'un metnini ve üst yazısını hazırlar.
   - Paketleme uzmanı başlık seçeneklerini ve A/B/C küçük resim yazılarını hazırlar.
   Shorts metni ve senaryodaki değişiklikler için `metin_kontrol.py` yeniden çalıştırılır.
5. **Üretim.**
   - Patron görselleri ve klipleri üretir. Yapımcı adayları ve klipleri inceler, patron seçer ve kırpar.
   - Patron seslendirir. Yapımcı çekim planını, Shorts uzmanı Shorts kadrajlarını hazırlar.
   - Patron videoyu, Shorts'ları ve küçük resimleri üretir (`video.py`, `--kapak`), ardından son kontrolü çalıştırır.
6. **Denetim.** Kalite kontrol ve metin editörü aynı anda inceler ve puanlar.
7. **Yönetici.** Bütün raporları ve puanları okuyup patrona öneri sunar.
8. **Karar ve teslim.** Patron son kararı verir (bütün denetçilerin ONAY'ı ve en az 80 puan), `python teslim.py NN-konu` ile teslim eder.
9. **Yayından sonra.** Kanal sahibi Studio ekran görüntülerini gönderince veri analisti okur. Patron analistin komutlarıyla `puan.py gercek` ve `ilerleme.md` kayıtlarını işler, önerdiği dersleri deftere ekler.

**Ajanlar nasıl çalıştırılır:**
- `avlu-*` ajan türleri listede görünüyorsa adlarıyla çalıştır.
- Görünmüyorsa (oturum, ajan dosyaları eklenmeden önce başladıysa) `general-purpose` ajana `.claude/agents/<ad>.md` dosyasını okuyup oradaki talimata uymasını söyle.
- Her ajana şunları yaz:
  - video klasörü
  - Whisper'lı Python'un yolu
  - neyin teslim edileceği
  - varsa önceki turun RET maddeleri

**Kurallar:**
- Denetçiler son satıra `KARAR: ONAY` ya da `KARAR: RET`, yönetici `ÖNERİ: ONAY` ya da `ÖNERİ: RET` yazar. Denetçiler ve yönetici dosya değiştirmez.
- RET gelirse:
  - Düzeltmeyi ilgili çalışana ya da kendine ver: metin → senarist, görsel/kadraj → yapımcı, ses/teknik → patron.
  - Sonra yalnızca RET veren denetçiye ve yöneticiye yeniden gönder.
- En fazla 2 tur. Hâlâ RET varsa teslim etme; kullanıcıya durumu açıkça anlat ve kararı ona bırak.
- Onay kaydını `hayvan-kanali/kanal/onaylar/NN-konu.md` dosyasına yaz: tur, kim, karar, not.
- Tur bitince `references/dersler.md` dosyasını güncelle.
- **Öneri kutusu:** Ajanların yeni fikirlerini `hayvan-kanali/kanal/oneriler.md` dosyasındaki "Bekleyen" bölümüne ekle. Yönetici puanlasın.
  - "Sun" kararı alan en iyi 1–3 fikri teslim raporunda kullanıcıya sade bir dille sun: ne, neden, maliyeti.
  - Kullanıcının kararını dosyaya işle. Kullanıcıyı fikir yağmuruna boğma.
- **Maliyet:** Her ajan kullanım hakkından yer. Küçük işlerde (tek bir cümle, tek bir Shorts) bütün ofisi çalıştırma; yalnızca ilgili denetçiyi çalıştır.

## Puanlama sistemi

Kullanıcı ofiste videolar için bir puanlama sistemi istedi. Her video, ONAY/RET'e ek olarak 100 üzerinden bir puan kartı alır.

| Ölçüt | Ağırlık | Puanlayan | Sorumlu çalışan |
|---|---|---|---|
| Doğruluk ve kaynak (`dogruluk`) | 20 | bilgi kontrolcüsü | senarist |
| Güvenlik ve çekinceler (`guvenlik`) | 10 | bilgi kontrolcüsü | senarist |
| Giriş ve izleyici tutma (`kanca`) | 20 | metin editörü | senarist |
| Anlatım ve Türkçe (`anlatim`) | 10 | metin editörü | senarist |
| Başlık, küçük resim, açıklama (`baslik`) | 10 | metin editörü | paketleme uzmanı |
| Shorts kancası (`shorts`) | 5 | metin editörü | Shorts uzmanı |
| Seslendirme ve ses (`ses`) | 10 | kalite kontrol | patron |
| Görsel, anatomi, kadraj (`gorsel`) | 10 | kalite kontrol | yapımcı |
| Testler ve teslim (`teknik`) | 5 | kalite kontrol | patron |

Kurallar:
- Her denetçi raporunda `PUAN:` bloğu yazar (0–10, gerekçeli). Yönetici toplar, patron `python puan.py ekle NN-konu --tur T --dogruluk .. ...` ile tabloya işler. Tablo: `hayvan-kanali/kanal/puan_tablosu.md`, veri: `kanal/puanlar.json`.
- **Eşikler:** 85 ve üzeri çok iyi · 80–84 teslim · 70–79 düzeltme turu · 70 altı RET. (İlk kurulumda teslim eşiği 85'ti. Ölçekte 8 "iyi" demek olduğu için bütün ölçütlerde 8 alan video 80 ediyordu ve geçemiyordu. Kanal sahibi 19 Kasım'da eşiği 80'e indirdi.)
- **Kırmızı çizgi:** doğruluk ya da güvenlik 5 ve altıysa, ya da herhangi bir ölçüt 3 ve altıysa toplam ne olursa olsun RET.
- **Teslim için iki şart birlikte aranır:** bütün denetçilerin ONAY'ı ve toplam puanın 80 ve üzeri olması.
- **Gerçek veriyle karşılaştırma:** Yayından 3 gün sonra kullanıcının gönderdiği verilerle `python puan.py gercek NN-konu --to .. --tutma30 .. --tutma80 .. --ortizleme ..` çalıştırılır. Yönetici, puanların gerçek performansı tahmin edip etmediğini yorumlar. Tahmin etmiyorsa ölçüt ya da ağırlık düzeltilir.
- **Karneler:**
  - Çalışan karnesi: ilk tur puanları, yani çalışanın düzeltmeden önceki işi.
  - Denetçi karnesi: onaydan sonra ortaya çıkan hatalar (`python puan.py kacirilan NN-konu "açıklama"`).
- **Puanlardan ders (kanal sahibinin isteği, 19 Kasım: "Çalışanlar bu puanlamalardan dersler çıkarsın ve en iyisini yapsınlar"):**
  - Denetçiler 10'dan düşük her puan için "9 için:" diye somut bir cümle yazar.
  - Patron her video sonrası bu cümleleri dersler defterindeki **"Puandan dersler: 8'den 9'a nasıl çıkılır?"** bölümüne ölçüt ölçüt işler.
  - Çalışanlar işe başlamadan o bölümü okur, raporlarında öz değerlendirme (tahmini puan ve uyguladıkları maddeler) yazar. Hedef her ölçütte ilk turda 9.
  - Tablodaki "Ölçüt eğilimi" bölümü ilk tur puanlarının videodan videoya yükselip yükselmediğini gösterir. Yerinde sayan ölçütün kuralı sertleştirilir.
  - Aynı kusur iki kez olursa ajan tanımına kesin kural ya da son kontrole otomatik test eklenir.
- Kullanıcıya teslim raporunda puan kartı kısaca gösterilir: toplam, en zayıf ölçüt ve önceki videoyla karşılaştırma.

## Teslim

1. `python teslim.py NN-konu` çalıştır. Dosyalar `hayvan-kanali/teslim/NN-konu/` klasörüne kopyalanır, doğrulanır ve `YUKLEME_LISTESI.txt` yazılır. Bu klasördeki dosyaları kullanıcıya gönder.
2. Takvim önerisi:
   - Uzun videolar salı ve cuma 18:00.
   - Shorts'lar 12:00'de, uzun video yayına girdikten sonraki iki gün. Yüklerken "İlgili video" olarak uzun video bağlanır.
   - Takvime yazmadan önce kullanıcıdan onay al. Onaylayınca `kanal/fikirler.json` ve `kanal/shorts_plani.md` güncellenir.
3. Kullanıcıya Türkçe, kısa rapor:
   - test sonuçları tablosu
   - ofis onay özeti ("Bilgi kontrolü ✅ · Kalite kontrol ✅ · Metin editörü ✅ · Yönetici ✅")
   - sabit yorum metni
   - tarih önerisi
   - varsa öneri kutusundan 1–3 fikir
4. Commit at ve oturum talimatındaki dala push'la. Commit mesajında model adı geçmesin.

## Hatırlanması gerekenler

- Videoda ve görselde İngilizce yazı olmaz. Görselde yazı varsa görsel kullanılmaz.
- Telefon numarası yazılmaz. Kurum: "bölgendeki Doğa Koruma ve Milli Parklar şube müdürlüğü".
- Bir siteyi korumasını aşarak ses ya da görsel indirmeye çalışma. Wikimedia Commons erişilebilir, Freesound erişilemez.
- Kullanıcıdan sohbete şifre ya da API anahtarı yapıştırmasını isteme.
- Para harcayan her komut maliyeti gösterir ve `--onay` olmadan çalışmaz.
