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
1.000 abone ve son 12 ayda 4.000 saat uzun video izlenmesi. Erken aşama: 500 abone ve 3.000 saat.

| Dönem | Hedef |
|---|---|
| **Aralık 2026 sonu** | 100 abone · 250 saat · 10 uzun video yayında |
| **Mart 2027 sonu** | 500 abone · 3.000 saat (erken aşama) |
| **Haziran 2027 sonu** | 1.000 abone · 4.000 saat (para kazanma) |

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
| **Yayın günü** (salı ve cuma, 18:00) | Sabit yorum, Shorts'lara "İlgili video" bağlantısı, ilk 2 saatte yorumlara cevap | kanal sahibi, topluluk sorumlusu hazırlar |
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

- Video başına maliyet: yaklaşık 2,8 $ görsel (23–25 görsel), 2,1–2,5 $ klip (6–7 klip), 0,5–1 $ seslendirme. Toplam **≈ 5,5–7 $**.
- Shorts: mevcut görsellerle yapıldığı için yalnızca seslendirme, birkaç kuruş.
- **Aylık bütçe: 60 $** (kanal sahibi 19 Kasım'da onayladı; haftada 2 video ≈ ayda 8–9 video ve yeniden seslendirmeler).
- Harcamalar `kanal/butce.md` dosyasına video video yazılır.

## 7. İçerik stoku ve üretim planı

- **Hedef:** Her an en az **4 hazır video** (iki haftalık yayın) stokta olsun. Hastalık, kredi bitmesi, düzeltme turu gibi aksilikler yayın ritmini bozmasın.
- Yayın ritmi: uzun video salı ve cuma 18:00; her uzun videonun iki Shorts'u sonraki iki gün 12:00.
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
