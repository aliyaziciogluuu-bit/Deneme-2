# Avludaki Komşular – şirket el kitabı

Kanal sahibinin isteği (19 Kasım 2026): "Büyük bir şirket gibi yönetin, birlikte büyüyelim."

Bu belge şirketin anayasasıdır. Hedefler, göstergeler, organizasyon, çalışma ritmi, yetkiler, bütçe ve riskler burada yazılıdır. Patron (ana Claude oturumu) her ay başında günceller. Ajanlar strateji kararı verirken buna bakar.

---

## 1. Misyon ve vizyon

- **Misyon:** Evin, bahçenin ve köyün çevresinde yaşayan, yanlış tanınan hayvanları doğru, kaynaklı ve merak uyandırıcı biçimde anlatmak. İnsanlar korkudan öldürmek yerine tanıyıp korusun.
- **Vizyon:** Türkiye'nin "doğru bilinen doğa" kanalı olmak. İnsanlar bahçede bir hayvan görünce önce Avludaki Komşular'a baksın.
- **Değerler:**
  1. **Doğruluk izlenmeden önce gelir.** Yanlış bilgiyle büyümeyiz.
  2. **İzleyicinin vakti değerlidir.** Cevap ilk 30 saniyede verilir, dolgu olmaz.
  3. **Her hata bir kurala dönüşür.**

## 2. Hedefler ve göstergeler (OKR)

### Ana hedef: YouTube İş Ortağı Programı
1.000 abone ve son 365 günde 8.000 geçerli saat (1 Şubat 2027 sonrası yeni başvurular; YouTube Yardım 12843009). Erken aşama: 500 abone ve 3.000 saat (hayran desteği, Creator Partnerships, Shopping; şart değişmiyor). **Bütün saat hedefleri organiktir: reklam/tanıtım izlenmesi sayılmaz** (kanal sahibi onayı, 23 Kasım).

| Dönem | Hedef |
|---|---|
| **Aralık 2026 sonu** | 40–50 abone · 50 organik uzun video saati · ortalama izleme (organik) ≥ %25 · 15 uzun video yayında |
| **Mart 2027 sonu** | 500 abone · 3.000 organik saat (erken aşama) |
| **12–24 ay** | 1.000 abone · 8.000 organik saat (para kazanma) |

### Haftalık takip edilen göstergeler

| Gösterge | Şu an | Hedef | Sorumlu |
|---|---|---|---|
| Tıklama oranı (uzun video) | %2,7 (yılan) | %4 | paketleme uzmanı |
| İzleyici tutma, 0:30 | %59 (yılan) | %65 | senarist |
| İzleyici tutma, 1:20 | ~%25 (yılan) | %40 | senarist |
| Ortalama izleme yüzdesi | %20 (yılan) | %35 | senarist, yapımcı |
| Shorts izlemeye devam oranı | %50,5 | %60 | Shorts uzmanı |
| Ofis puanı (son tur) | 80–84 | 85+ | herkes |
| Ofis puanı (ilk tur) | 66–68 | 80+ | çalışanlar |
| İlk turda kapıdan geçme oranı | ölçülmeye başlandı | %80 | üretim müdürü |
| Video başına maliyet | ~5,5–7 $ | ≤ 6 $ | patron |
| Hazır video stoku | 1 (baykuş) | 4 | patron, kanal yöneticisi |

## 3. Organizasyon

```
                    KANAL SAHİBİ (yönetim kurulu)
           son söz · bütçe · takvim onayı · yayınlama · "insan kulağı"
                               │
                    PATRON (genel müdür: ana Claude oturumu)
        iş dağıtır · para harcayan işleri yapar · son onay · kanal sahibine rapor
                               │
        KANAL YÖNETİCİSİ (strateji)        ÜRETİM MÜDÜRÜ (hat, pano, stok)
                               │
   ÜRETİM HATTI          GİRİŞ KALİTE KAPILARI        SON DENETİM          BÜYÜME
   Senarist              Kaynak arşivcisi             Bilgi kontrolcüsü    Paketleme uzmanı
   Yapımcı               Görsel denetçi               Kalite kontrol       Shorts uzmanı
                         Seslendirme yönetmeni        Metin editörü        Veri analisti
                                                                           Topluluk sorumlusu
```

Ajan tanımları `.claude/agents/avlu-*.md`, iş akışı `.claude/skills/avludaki-komsular-yeni-video/SKILL.md`.


### Fabrika düzeni (19 Kasım 2026)

Kanal sahibinin isteği: "Fabrika gibi işlesin, işinde profesyonel çalışanlar al."

- **12 istasyonlu üretim hattı**, her istasyonda bir kalite kapısı (ayrıntı: SKILL.md → "Fabrika hattı"). Durum panosu: `python3 pano.py` → `kanal/uretim_panosu.md`.
- **Tek üretim hattı:** bütün video oluşturma ve testler `python3 hat.py` ile sırayla çalışır (disk ve işlemci çakışması olmaz).
- **Yeni çalışanlar (19 Kasım):**
  - Üretim müdürü: hattı akıtır, darboğaz ve stok.
  - Kaynak arşivcisi: her kaynak açılır, arşivlenir; künye sayfadan.
  - Görsel denetçi: ölçek, tür, anatomi ve klip bozulmaları hattın başında yakalanır.
  - Seslendirme yönetmeni: okunuşlar seslendirmeden önce, dinleme listesi seslendirmeden sonra.
  Neden: 19 Kasım'daki RET'lerin çoğu (dev karga ve kirpi ölçeği, kanat bozulması, çevrilmiş künye, yanlış okunuş alanı) en son denetimde yakalandı ve videoların yeniden oluşturulmasına yol açtı. Hatayı başta yakalamak hem zaman hem para kazandırır.
- **Fabrika göstergesi: ilk turda kapıdan geçme oranı.** Her istasyonda ilk denemede KABUL/ONAY alan iş oranı; hedef %80. Puan tablosundaki "ilk tur" puanı bunun özetidir.

## 4. Çalışma ritmi

| Ne zaman | Ne yapılır | Kim |
|---|---|---|
| **Her gün 09:43: otomatik bekçi turu** (zamanlanmış görev; kanal sahibi 19 Kasım'da istedi) | `otomatik.py kontrol --hepsi --kaynak`, güvenli düzeltmeler, eski video ve eksik seslerin yenilenmesi, pano ve üretim müdürü raporu; kanal sahibine yalnızca yapması gerekenler | patron, üretim müdürü |
| **Her video** | Üretim → otomatik metin denetimi → bilgi kontrolü → üretim → denetim ve puan → yönetici → teslim | bütün ofis |
| **Yayın günü** (20 Kasım'dan beri: uzun video salı, perşembe, cumartesi 18:00; Shorts her gün 12:00) | Sabit yorum, Shorts'lara "İlgili video" bağlantısı, ilk 2 saatte yorumlara cevap | kanal sahibi, topluluk sorumlusu hazırlar |
| **Yayından 3 gün sonra** | İzleyici tutma, tıklama oranı ve Shorts verisinin ekran görüntüleri → analist → ders ve puan kalibrasyonu | kanal sahibi gönderir, analist okur |
| **Her pazartesi 08:39: haftalık yönetim toplantısı** (zamanlanmış görev; kanal sahibi 19 Kasım'da istedi) | Göstergeler tablosu, geçen haftanın dersleri, bu haftanın üretim ve yayın planı, bütçe durumu, öneri kutusundan en fazla 3 fikir | patron hazırlar, kanal sahibi karar verir |
| **Her ay başı: aylık strateji** | Hedeflere göre neredeyiz, konu sırası, yeni içerik biçimi denemeleri, şirket el kitabının güncellenmesi | patron, kanal yöneticisi, analist |

## 5. Yetki kuralları (kim neye karar verir?)

| Karar | Kim karar verir |
|---|---|
| Para harcamak (görsel, klip, seslendirme) | Patron, **onaylı aylık bütçe içinde**. Bütçeyi aşacaksa kanal sahibine sorulur |
| Yayın takvimi, YouTube'a yükleme, silme | Kanal sahibi (patron önerir) |
| Bilgi doğruluğu | Bilgi kontrolcüsü RET verirse kimse aşamaz |
| Teslim | Bütün denetçilerin ONAY'ı ve en az 80 puan. Patron son kararı verir |
| Kural ve eşik değişikliği | Kanal sahibi (ör. 19 Kasım: teslim eşiği 85 → 80) |
| Ortam ve ağ izinleri | Kanal sahibi (onay ekranıyla) |
| Yeni çalışan ve araç | Patron önerir, kanal sahibi onaylar |

## 6. Bütçe

- Kasım'a kadar video başına maliyet: 2,8–4,9 $ görsel (23–25 görsel, 2–3 aday + yeniden üretimler), 2,1–2,5 $ klip (6–7 klip), 0,3–1 $ seslendirme. Toplam **≈ 5,5–7,5 $**.
- **Aralık'tan itibaren tasarruflu üretim (kanal sahibi, 20 Kasım: "haftada 3 video 60 $'a"): video başına tavan 5 $, hedef ≈ 4,5 $.**
  - Görsel: en çok 20 görsel. Hayvanın göründüğü sahnede 2 aday, hayvansız sahnede (insan, manzara, nesne) 1 aday (`"aday": 1`). ≈ 2 $.
  - Zor tür özelliği (yuva biçimi, renk deseni, halka gibi) olan görsel önce TEK aday denenir; tutmazsa istem düzeltilir. İki turda tutmayan görsel düşürülür, cümle mevcut görsellerle anlatılır (üçüncü tur yok).
  - Küçük hatalar yeniden üretim yerine düzenleme modeliyle düzeltilir (0,04 $).
  - Klip: 4 klip (açılış, iki Shorts açılışı, kapanış) ≈ 1,4 $.
  - Seslendirme ve düzeltme payı ≈ 0,6 $.
  - Bir videoda 5 $ aşılacaksa patron durur, yeniden üretim yerine mevcut görselle devam eder.
- Shorts: mevcut görsellerle yapıldığı için yalnızca seslendirme, birkaç kuruş.
- **Aylık bütçe: 60 $** (kanal sahibi 19 Kasım'da onayladı; 20 Kasım'da haftada 3 video da bu bütçeyle istendi). Aralık: 14 yayın günü, 2'si hazır (karga, kırlangıç), 12 yeni video × ≈ 4,5 $ ≈ 54 $ + 6 $ yedek.
- **Karar (20 Kasım, kanal sahibi kararı patrona bıraktı):** Aralık 60 $ tasarruflu düzenle başlar. Ölçüt izlenme: Aralık'ın ilk 4 videosu (kara kurbağası dahil) yayına girip 7 gün dolunca, ilk 30 sn tutma ve ortalama izleme süresi Kasım videolarının ortalamasıyla karşılaştırılır. Tutma 5 puandan fazla düşmüşse klipler 6'ya çıkar (≈ 70 $); kanal sahibine haber verilir. Düşmemişse 60 $ düzeni sürer.
- Ayın ortasında harcama planın önündeyse (15'inde 30 $'ı geçtiyse) patron kanal sahibine haber verir; gerekirse ayın kalanında haftada 2 videoya inilir.
- Harcamalar `kanal/butce.md` dosyasına video video yazılır.

## 7. İçerik stoku ve üretim planı

- **Hedef:** Her an en az **4 hazır video** (iki haftalık yayın) stokta olsun. Hastalık, kredi bitmesi, düzeltme turu gibi aksilikler yayın ritmini bozmasın.
- Yayın ritmi (kanal sahibi, 22 Kasım; 20 Kasım kararının yerine): **uzun video haftada 2 (salı ve cumartesi 18:00)**, Shorts her gün 12:00 (her uzun videodan 3 Shorts, uzun videonun en güçlü bölümlerinden). Gerekçe: büyük kanallar analizi (`reports/Büyük hayvan kanalları analizi.md`) — darboğaz tutma; boşalan zaman senaryo ve paketlemeye. İzleme oranı sürekli %25'i geçerse haftada 3'e dönüş önerilir. Kurallar: `.claude/skills/avludaki-komsular-yeni-video/references/buyume_kurallari.md`.
- Sıradaki üretim: karga → kırlangıç → kara kurbağası → yılan ve süt efsanesi (konu sırası her ay analistin önerisiyle gözden geçirilir; mevsim ve arama ilgisi dikkate alınır).

## 8. Risk listesi

| Risk | Olasılık | Etki | Önlem |
|---|---|---|---|
| Yanlış bilgi (kirpi Alo 174 olayı gibi) | Orta | Çok yüksek | Bağımsız bilgi kontrolü, kontrolcünün önerisi de doğrulanır, kaynak eşleme dosyası, kaynak sitelerine ağ izni |
| Düşük izleyici tutma, YouTube göstermeyi bırakır | Yüksek | Yüksek | Cevap ilk 30 sn'de, otomatik metin denetimi, analist |
| "Seri üretilmiş içerik" sayılıp para kazanmanın reddedilmesi | Orta | Çok yüksek | Her video özgün araştırma ve senaryo; yapay zekâ beyanı; aynı kalıbı tekrar etmeme kontrolü |
| Replicate kredisinin bitmesi, yayın aksar | Orta | Orta | Aylık bütçe, 4 videoluk stok |
| Yapay ses ya da görselin fark edilmesi | Düşük | Orta | Kanal sahibinin dinlemesi, anatomi kontrolü |
| Tek hesaba ve tek telefona bağımlılık | Düşük | Yüksek | İki adımlı doğrulama, kanal sahibinin hesabı güvende tutması |

## 9. Büyüme yol haritası

1. **0–100 abone (şimdi):** ritmi kur, girişi ve Shorts'u veriyle düzelt, her video bir öncekinden iyi olsun.
2. **100–500 abone:**
   - İlk seriler: "Köy efsaneleri" (yılan süt emer mi, kurbağa siğil yapar mı), "Kışın neredeler?".
   - Topluluk gönderileri (500 abonede açılır).
   - Küçük resim A/B testleri.
3. **500–1.000 abone:**
   - En çok izlenen konuların derin ikinci bölümleri.
   - İzleyicinin sorduğu hayvanlar (yorumlardan konu).
   - Uzun derleme videolar ("Evin çevresindeki 5 zararsız hayvan").
4. **1.000+ abone:** para kazanma, sonra bütçe artışıyla haftada üç video.

## Karar (22 Kasım): haftada 2 uzun video, bütçe kalitede
- Aralık: kara kurbağasından sonra 7 yeni uzun video (8, 12, 15, 19, 22, 26, 29 Aralık) × ≈ 5 $ ≈ 35 $. Aylık 60 $ bütçeden artan ≈ 20 $ kaliteye gider: video başı tavan 5 $ → 7 $ (daha çok görsel adayı, 4 → 6 klip, gerçek fotoğraf önceliği sürer), küçük resim için ayrı görsel turu.
- Para kazanma hedefi: 1.000 abone + 8.000 saat (1 Şubat 2027 sonrası yeni başvurular; YouTube Yardım sayfası 12843009 ile doğrulandı, 23 Kasım), takvim 12–24 ay. Ara hedef: 500 abone + 3.000 saat → hayran desteği, Creator Partnerships ve Shopping açılır (bu şart değişmiyor).
- Ücretli tanıtım: "Görüntüleme sayısı" hedefi yok (geko: ₺966 → 0 abone; izlenmeleri şarta sayılmıyor). **Tanıtımla gelen aboneler ve izlenme saatleri para kazanma şartına SAYILMAZ; yalnızca organik aboneler sayılır. İstisna: Kitle büyütme tanıtımının "follow-on" (reklamdan sonra kanalda yapılan organik) görüntülemeleri sayılır. Tanıtım organik erişimi etkilemez.** (YouTube Yardım 12199105 ve 72851, arama özetiyle doğrulandı 25 Kas; sayfa açılamadı.) "Kitle büyütme" hedefi test ediliyor (sağır yılan, 24–27 Kas): 25 Kas ara sonuç ₺51,62 → 13 abone, kanal toplamı 8 → 47. Abone başına < ₺20 sürerse Aralık'ta her yeni uzun videoya küçük bütçe (karar 27 Kas).

## Karar (24 Kasım, kanal sahibi: "hepsini yapalım")
1. **Mevsimlik Shorts:** kış sorularını (kışın kirpi, kışın yarasa vb.) mevcut doğrulanmış içerikten Shorts'a çevirmek.
2. **Öğretmen/veli kitlesi:** açıklamalara "Derste kullanabilirsiniz" notu; kanal sahibine öğretmen tanıdıkları için WhatsApp metni.
3. **Yoruma Shorts ile yanıt:** izleyici sorusu gelince "yoruma video ile yanıt" Shorts'u (bilgi kontrolünden geçmiş bilgiyle).
4. **Konu yelpazesi genişledi:** evde/bahçede görülüp "zehirli mi?" diye aranan böcek ve eklembacaklılar da kanala girer (ev örümceği, çıyan, kırkayak, akrep sanılanlar vb.; "Zehirli Sanılanlar" serisi). Güvenlik kritik konularda (akrep, karadul gibi gerçekten tehlikeli türler) resmi sağlık/kurum kaynağı şart.
5. **Kış derlemesi:** Aralık sonunda "Kışın bahçendeki komşular nerede?" (8–10 dk, mevcut görseller, tamamen yeni anlatım; tekrar eden içerik kuralına dikkat).

## Karar (26 Kasım, kanal sahibi: "ekle") – küçük kanal analizinden Aralık planı
Kaynak: kanal/kucuk_kanallar_2026-11-26.md (vidIQ).
1. **Shorts önce:** "… değildir!" serisi sürer (haftada en fazla 2, ters durum kontrolüyle). Aralık'ta en az 4 Shorts 25 sn altında denenir; izlemeye devam oranı 30–40 sn'lik Shorts'larla karşılaştırılır.
2. **Aylık uzun derleme:** ayda bir 20–40 dk derleme. İlki 26 Aralık: "Kışın Bahçendeki Komşular Nerede?" (mevcut videoların kış bölümleri + yeni bağlantı anlatımı; düşük maliyet). Amaç izlenme saati.
3. **Tanıtım yerine üretim:** Aralık'ta ücretli tanıtım bütçesi derleme ve Shorts'a gider (27 Kas test sonucu farklı bir şey göstermezse).
4. **Para kazanma için iki yol izlenir:** (a) 1.000 organik abone + 8.000 saat; (b) 1.000 organik abone + 90 günde Shorts izlenme eşiği. Haftalık raporda ikisi de gösterilir.

## Karar (27 Kasım, kanal sahibi: "1") – ilk 3D uzun video: semender
- Semender (12 Ara) 3D belgesel animasyonu tarzında üretilir; tür tanıtımında 3–4 gerçek fotoğraf kalır. Tahmini maliyet 10–20 $.
- Ölçüt: ortalama izleme yüzdesi ve tıklama oranı önceki uzun videolarla karşılaştırılır (kirpi %25–33, TO %5,8; yarasa TO %6,7). İyiyse sonraki uzun videolar 3D; değilse eski tarza dönülür.
- Shorts tarafında 3D kararı 4 Ara verisine bağlı (ayrı deneme).

## Karar (27 Kasım, kanal sahibi: "Ben tamamen 3D istiyorum, karışık olsun uzun ve Shorts")
- Kanal tamamen 3D'ye geçiyor: uzun videolar ve Shorts 3D animasyon (semender ilk örnek). Gerçek fotoğraflar yalnızca tür tanıtımı/kanıt için kullanılabilir.
- Karışık yayın sürüyor: uzun videolar (izlenme saati, gelir) + Türler Alemi kısalığında 3D Shorts serisi (18–25 sn, "sen" hitabı, herkesin gördüğü bir şeyle açılış, tek benzetme, 2 bilgi, çağrısız döngü bitişi, 2 günde bir 19:00). Konu kimliği korunur: ev çevresindeki hayvanlar, kaynaklı bilgi, güvenlik çekinceleri.
- 4 Aralık 3D değerlendirmesi artık "3D'ye geçilsin mi" değil, "hangi 3D kalıp daha iyi" sorusunu ölçer.
- Bütçe etkisi (tahmin): 3D uzun ≈ 13–15 $/video, 3D Shorts ≈ 3–4 $/adet. Haftada 2 uzun + 2 günde bir Shorts ≈ ayda 150–180 $ (Aralık planı 60 $'ın üstünde; kanal sahibi "para sorun değil" demişti, Replicate bakiyesi izlenecek).
- Ders: semender/kurbağa gibi küt parmaklı hayvanlarda ayak kuralları (dersler.md 27 Kasım) her 3D işte geçerli.
