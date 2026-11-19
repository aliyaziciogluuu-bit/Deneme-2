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

## Dersler defteri

Ofisin hafızası `references/dersler.md` dosyasında. İşe başlamadan oku, ajanlara da okut. Her onay turundan sonra yeni dersleri ekle. Aynı hata iki kez olursa betiği ya da kontrol listesini düzelt.

## Ön kontrol (her seferinde)

1. `df -h /`: en az 5 GB boş yer.
2. Python ortamı: Whisper gerektiren adımlar (seslendirme, son kontrol) faster-whisper kurulu bir Python ile çalışır. Oturumda yoksa scratchpad'e venv kur:
   `pip install faster-whisper numpy pillow`
   Çalıştırırken `HF_HUB_DISABLE_XET=1` ver. Model indirme hatası olursa bu değişken çözer.
3. Replicate kredisi: büyük harcamadan önce yeterli mi? Kredi bitince 402 hatası gelir.
4. Sıradaki konu: `hayvan-kanali/kanal/fikirler.json`. Klasör adı `NN-konu` (ör. `06-karga`).

## Adımlar ve komutlar (`hayvan-kanali/` içinde)

| Adım | Kim | Komut ya da iş | Maliyet |
|---|---|---|---|
| 1. Araştırma ve senaryo | senarist | `senaryo.json`, `shorts.json` metinleri | yok |
| 2. Bilgi kontrolü | bilgi kontrolcüsü | rapor; patron önerileri doğrular ve uygular | yok |
| 3. Görsel istemleri | yapımcı | `gorseller.json` | yok |
| 4. Görsel adayları | patron | `python gorsel.py NN --onay` (~2,8 $) | var |
| 5. Aday seçimi | yapımcı önerir, patron seçer | `python gorsel.py NN --sec ad=N ...` | yok |
| 6. Klipler | yapımcı yazar, patron üretir | `python klip.py NN --onay` (7 × 0,35 $), arka planda | var |
| 7. Seslendirme | patron | `seslendir_bulut.py NN`, sonra farklar için `--cumle i j` | az |
| 8. Çekim planı | yapımcı | `cekimler.json` ve `video.py NN --onizleme` | yok |
| 9. Video | patron | `video.py NN` ve `son_kontrol.py NN` | yok |
| 10. Shorts | yapımcı kadraj, patron üretir | `shorts_kur.py NN`, sonra her Shorts için seslendir, video, son kontrol | az |
| 11. Ofis onayı | denetçiler, yönetici | aşağıda | yok |
| 12. Teslim | patron | aşağıda | yok |

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
                       KANAL YÖNETİCİSİ (avlu-kanal-yoneticisi)
          denetçi raporları · veriler · takvim · öneri kutusu · patrona öneri
                                     │
      ┌──────────────┬───────────────┼───────────────┬──────────────────┐
  SENARİST       YAPIMCI      BİLGİ KONTROLCÜSÜ  KALİTE KONTROL     METİN EDİTÖRÜ
  (avlu-senarist)(avlu-yapimci)(avlu-bilgi-kontrol)(avlu-kalite-kontrol)(avlu-metin-editoru)
  araştırma,     görsel, klip, her iddia, sayı,   14 test, kare,     kanca, tempo, Türkçe,
  senaryo,       çekim planı,  güvenlik, kaynak   anatomi, ses,      başlık, açıklama,
  Shorts metni   kadraj                           küçük resim        Shorts metni
```

**Akış:**
1. Patron konuyu senariste verir. Senaryo gelince **bilgi kontrolcüsü** inceler. RET ise senarist düzeltir. Bilgi ONAY'ı gelmeden görsel üretimine para harcanmaz (görsel istemleri paralel hazırlanabilir).
2. Yapımcı görsel ve klip istemlerini yazar. Patron üretir, yapımcı adayları ve klipleri inceler, patron seçer ve kırpar.
3. Patron seslendirir. Yapımcı çekim planını ve kadrajları hazırlar. Patron videoyu ve Shorts'ları üretir, son kontrolü çalıştırır.
4. **Kalite kontrol** ve **metin editörü** aynı anda inceler.
5. İkisi bitince **kanal yöneticisi** bütün raporları okuyup patrona öneri sunar.
6. Patron son kararı verir. Vermeden önce önizlemelere ve küçük resme kendisi de bakar.

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
| Başlık, küçük resim, açıklama (`baslik`) | 10 | metin editörü | senarist |
| Shorts kancası (`shorts`) | 5 | metin editörü | senarist |
| Seslendirme ve ses (`ses`) | 10 | kalite kontrol | patron |
| Görsel, anatomi, kadraj (`gorsel`) | 10 | kalite kontrol | yapımcı |
| Testler ve teslim (`teknik`) | 5 | kalite kontrol | patron |

Kurallar:
- Her denetçi raporunda `PUAN:` bloğu yazar (0–10, gerekçeli). Yönetici toplar, patron `python puan.py ekle NN-konu --tur T --dogruluk .. ...` ile tabloya işler. Tablo: `hayvan-kanali/kanal/puan_tablosu.md`, veri: `kanal/puanlar.json`.
- **Eşikler:** 85 ve üzeri teslim · 70–84 düzeltme turu · 70 altı RET.
- **Kırmızı çizgi:** doğruluk ya da güvenlik 5 ve altıysa, ya da herhangi bir ölçüt 3 ve altıysa toplam ne olursa olsun RET.
- **Teslim için iki şart birlikte aranır:** bütün denetçilerin ONAY'ı ve toplam puanın 85 ve üzeri olması.
- **Gerçek veriyle karşılaştırma:** Yayından 3 gün sonra kullanıcının gönderdiği verilerle `python puan.py gercek NN-konu --to .. --tutma30 .. --tutma80 .. --ortizleme ..` çalıştırılır. Yönetici, puanların gerçek performansı tahmin edip etmediğini yorumlar. Tahmin etmiyorsa ölçüt ya da ağırlık düzeltilir.
- **Karneler:**
  - Çalışan karnesi: ilk tur puanları, yani çalışanın düzeltmeden önceki işi.
  - Denetçi karnesi: onaydan sonra ortaya çıkan hatalar (`python puan.py kacirilan NN-konu "açıklama"`).
- Kullanıcıya teslim raporunda puan kartı kısaca gösterilir: toplam, en zayıf ölçüt ve önceki videoyla karşılaştırma.

## Teslim

1. Dosyaları `hayvan-kanali/teslim/uzun/` ve `teslim/shorts/` klasörlerine anlaşılır adlarla kopyala (ör. `6-karga-video.mp4`, `11-karga-...mp4`) ve kullanıcıya gönder.
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
