# Medya Bölümü: Tarihte Bugün ağı

Şirketin ikinci iş kolu. Patron kararıyla açıldı (21.11.2026): fikir puanı 54'tü, eşik 75; Patron bu işi
istediği için kural bu iş kolu için delindi. Bu karar puan tablosunda kayıtlıdır.

## 1. Model

**Tek doğrulanmış senaryo, birçok dil, her gün.** Her gün tarihte o gün olmuş bir olay seçilir, bir dakikalık senaryosu
yazılır, bağımsız doğrulamadan geçer, sonra her dilde ayrı kanal için otomatik videoya dönüşür.

Neden böyle: bir senaryoyu doğrulamak işin en pahalı kısmıdır; bir kez yapılıp her dile dağıtılınca maliyet bölünür.
İngilizce kanalın kitlesi ve reklam geliri Türkçeden kat kat büyüktür; Türkçe kanal yerel kitleyi tutar.

| Sıra | Dil | Durum | Açılma koşulu |
|---|---|---|---|
| 1 | İngilizce | Kuruluyor | Başlangıç |
| 2 | Türkçe | Kuruluyor | Başlangıç |
| 3 | İspanyolca | Bekliyor | İlk iki kanalın 30 günlük ortalaması video başına 1.000 izlenmeyi geçerse |
| 4 | Portekizce (Brezilya) | Bekliyor | Aynı koşul |
| 5 | Almanca | Bekliyor | Aynı koşul |

Yeni dil açmak tek bir senaryo alanı ve bir ses modeli eklemek demektir; üretim düzeni değişmez.

## 2. Görev dağılımı

| Görev | Kim | Ne yapar |
|---|---|---|
| **Patron** | Siz | Kanalları açar, yükleme iznini bir kez verir, para ve marka kararlarını verir. |
| **Yayın Yönetmeni** | Claude | Haftalık yayın takvimini çıkarır, konuları seçer, kanalları yönetir. |
| **Araştırma ve Senaryo** | Claude | Olayı kaynaklardan çalışır, senaryoyu ve her dildeki metni yazar. |
| **Doğrulama Masası** | Bağımsız denetçi (ayrı Claude ajanı) | Senaryodaki her bilgiyi kaynağa karşı kontrol eder, görsel ve müzik lisanslarına bakar, **Video Puanı** verir. |
| **Prodüksiyon** | Otomatik (GitHub sunucusu) | Görselleri indirir, seslendirir, kurgular, altyazı ekler. |
| **Yayın ve Dağıtım** | Otomatik | Videoyu belirlenen saatte kanala yükler. YouTube denetimi onaylanana kadar bu adımı Patron yapar. |
| **Analiz** | Claude | İzlenme verilerine göre hangi konuların tuttuğunu çıkarır, takvimi buna göre ayarlar. |

## 3. Yayın akışı

```
Konu seçimi → Senaryo → Doğrulama (Video Puanı) → Üretim → Yayın → Analiz
```

- Senaryolar **haftalık topluca** yazılır (7 gün), doğrulanır ve `youtube/senaryolar/` klasörüne konur.
- GitHub her gün belirlenen saatte o günün videolarını üretir ve yükler.
- Doğrulamadan geçmeyen senaryo yayına girmez; yerine yedek senaryo kullanılır.

## 4. Puanlama

### Video Puanı (100): yayından önce, her senaryo için

| Ölçüt | Puan |
|---|---|
| Doğruluk (her rakam, tarih ve isim kaynakla uyumlu) | 35 |
| Kanca (ilk 3 saniye merak uyandırıyor mu) | 15 |
| Görsel (olayla ilgili, net, telifsiz) | 15 |
| Ses ve altyazı (doğru okunuş, okunur altyazı) | 15 |
| Başlık, açıklama, etiketler | 10 |
| Kurallar (lisanslar, kaynak gösterme, yapay zekâ beyanı) | 10 |

**Eşik: 80 ve hiç kritik hata yok.** Kritik hata: yanlış bilgi, lisansı belirsiz görsel ya da müzik, kaynaksız iddia,
yanıltıcı başlık.

### Kanal Puanı (100): her ay

| Ölçüt | 0 | 10 | 20 | 30 | 40 |
|---|---|---|---|---|---|
| Video başına ortalama izlenme | 100'den az | 100–499 | 500–1.999 | 2.000–9.999 | 10.000+ |
| Ortalama izlenme oranı | %50'den az | %50–69 | %70–89 | %90+ | |
| Aylık abone artışı | 10'dan az | 10–99 | 100–999 | 1.000+ | |

**Karar:** 70+ ise yeni dil kanalı açılır ya da günde ikinci video denenir. 40–69 arası başlık, kanca ve konu seçimi
iyileştirilir. 40 altında 2 ay kalırsa format değiştirilir.

## 5. Yayın ilkeleri

- **Doğruluk her şeyden önce gelir.** Emin olunmayan bilgi kullanılmaz; rakamlar kaynakla birebir uyuşmalı.
- **Tık tuzağı yok.** Başlık merak uyandırır ama videoda olmayan bir şey vaat etmez.
- **Hassas konular:** felaket ve ölüm içeren olaylar saygılı anlatılır, gerilim malzemesi yapılmaz. Siyasi ve dinî
  tartışma yaratacak konular seçilmez. Türkiye'de yasal sorun doğurabilecek içerikten (ör. 5816 sayılı Kanun kapsamı)
  özellikle kaçınılır.
- **Telif:** yalnızca kamu malı ya da açık lisanslı görseller (Wikimedia Commons) ve CC0 müzik. Her videonun
  açıklamasında kaynaklar ve lisanslar yazar.
- **Yapay zekâ beyanı:** açıklamada seslendirme ve kurgunun yapay zekâ yardımıyla yapıldığı yazar. YouTube gerçekçi
  sentetik içerik isterse "değiştirilmiş içerik" kutusu işaretlenir.
- **Seri üretim tuzağı:** YouTube birbirinin aynısı videoları reklamdan çıkarabilir. Her video gerçek bir bilgi taşımalı,
  konu ve anlatım çeşitlenmeli.

## 6. Hedefler

Bunlar tahmin değil hedeftir.

| Zaman | Hedef |
|---|---|
| 1. ay | İngilizce ve Türkçe kanal açık; her birinde 30 video |
| 3. ay | İngilizce kanalda 1.000 abone |
| 6. ay | İngilizce kanal YouTube ortaklık şartlarını karşılıyor; üçüncü dil açılmış |

## 7. Teknik notlar

- Üretim: `youtube/uret_video.py`, iş akışı `.github/workflows/tarihte-bugun.yml`.
- Ses: Piper (ücretsiz, açık kaynak). Türkçe için tek ses var (orta kalite); İngilizce için daha kaliteli sesler var.
- Görseller GitHub sunucusundan Wikimedia Commons'a, kurallarına uyarak (standart boyut, bekleme isteğine uyma) indirilir.
- Otomatik yükleme: YouTube, denetlenmemiş otomatik yükleme sistemlerinin videolarını "özel" olarak kilitler. Tam otomasyon
  için Google'a denetim başvurusu yapılır. Onaylanana kadar videolar hazır olur, yüklemeyi Patron yapar.
