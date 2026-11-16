# BIST Bot

Borsa İstanbul için kurallı bir al-sat botu. Her işlem günü kapanıştan sonra kendiliğinden çalışır,
BIST 100 hisselerini puanlar, bir **kâğıt portföy** tutar ve ertesi sabah vermeniz gereken
**emir listesini** (hisse, lot, limit fiyat) hazırlayıp Telegram'a ve panele yazar.

> **Önemli.** Bot gerçek hesabınıza emir **göndermez**; emirleri aracı kurumunuzun uygulamasından siz
> girersiniz. Buradaki hiçbir şey yatırım tavsiyesi değildir. Geçmiş performans geleceği garanti etmez;
> kaybetmeyi göze alamayacağınız parayla işlem yapmayın.

## Ne yapar?

- **Evren:** O günkü resmî BIST 100 üyeleri (brüt takasta, tek fiyatta veya işlemi durdurulmuş olanlar ile
  bir yıldan kısa geçmişi olanlar hariç).
- **Puanlama (dört sütun, eşit ağırlık):**
  - *Değer* — özkaynağa ve kâra göre ucuzluk (düşük PD/DD, düşük F/K),
  - *Kârlılık* — özkaynak kârlılığı,
  - *Düşük risk* — az oynak, düşük betalı, "piyango" gibi davranmayan hisseler,
  - *Momentum* — son 12 ayın getirisi (son ay hariç).
- **Portföy:** En iyi 20 hisse, eşit ağırlık. Ayda bir (ayın ilk işlem günü) gözden geçirilir; eldeki bir
  hisse sıralamada 40'ın altına düşmedikçe satılmaz (gereksiz al-satı önler).
- **İşlem:** Karar akşam verilir, emirler **ertesi sabah açılış seansında** limitli girilir.

Bu sütunlar, Borsa İstanbul üzerine yayımlanmış akademik çalışmalarda öne çıkan etkenlerdir. Hareketli
ortalama, RSI, MACD gibi göstergelere dayalı kurallar bilerek kullanılmadı: BIST üzerindeki çalışmalarda
al-tut stratejisini geçemedikleri görülüyor.

## Geçmiş testi (dürüst hâliyle)

Kurallar, veriyle hiçbir test çalıştırılmadan **önce** sabitlendi. Test; komisyon (binde 2 + BSMV), kayma
(binde 1), temettü stopajı, tavan/taban kilidi ve "karardan bir gün sonra açılıştan işlem" varsayımlarıyla,
Borsa İstanbul'un resmî günlük bültenleri üzerinde yapıldı (kottan çıkan hisseler ve o günkü endeks üyeliği
dahil; yani "bugünün kazananlarını geçmişe taşıma" hatası yok).

**02.01.2017 – 13.11.2026 (9,9 yıl):**

| | Yıllık getiri | En büyük düşüş | Sharpe* |
|---|---:|---:|---:|
| **Strateji (masraflar düşülmüş)** | **%42,7** | **−%36** | **0,59** |
| Eşit ağırlıklı BIST 100 (masrafsız) | %33,0 | −%43 | 0,30 |
| BIST 100 endeksi (temettüsüz) | %31,8 | −%32 | 0,27 |
| Gecelik faiz (TLREF) | %27,2 | – | – |

\* Sharpe, gecelik TL faizinin üzerindeki getiriyle hesaplanır.

| Yıl | Strateji | Eşit ağ. BIST 100 | BIST 100 | Gecelik faiz |
|---|---:|---:|---:|---:|
| 2017 | +70% | +48% | +48% | +12% |
| 2018 | −20% | −24% | −21% | +20% |
| 2019 | +42% | +61% | +25% | +23% |
| 2020 | +71% | +76% | +29% | +11% |
| 2021 | +36% | +21% | +26% | +20% |
| 2022 | +215% | +229% | +197% | +14% |
| 2023 | +57% | +15% | +36% | +21% |
| 2024 | +36% | +22% | +32% | **+64%** |
| 2025 | +9% | +16% | +15% | **+55%** |
| 2026 (13 Kasım'a kadar) | +1% | −19% | +5% | **+40%** |

**Bu sonuçlar ne kadar güvenilir?**

- Hisse seçiminin katkısı BIST 100 ortalamasına göre yılda yaklaşık **+9,7 puan**; istatistiksel anlamlılığı
  orta düzeyde (alfa t-istatistiği 2,3). Bootstrap ile %90 güven aralığı yılda **+1 ile +13 puan** arası.
- Aynı havuzdan aynı kurallarla **rastgele** seçilen 200 portföyün hepsinden iyi sonuç verdi.
- 27 farklı ayarla denendi (hisse sayısı, sıklık, sütunların tek tek çıkarılması vb.); rejim filtresi
  dışındaki 23 komşu ayarın **hepsi** ortalamayı geçti. Kullanılan ayar bu denemelerin en iyisi değil (Sharpe'a
  göre 13.), önceden sabitlenen ayardır. Denemelerin sayısını hesaba katan "sönümlenmiş Sharpe" %87.
- Masraflar iki katına çıkınca yıllık getiri %42,7'den %41,9'a, emirler bir gün geç girilince %42,2'ye iniyor.

**Zayıf yanlar — bunları bilerek kullanın:**

- **Son üç yılda gecelik faiz hisseleri geçti.** 2024, 2025 ve 2026'da strateji de endeks de faizin gerisinde
  kaldı. Strateji "hangi hisse" sorusuna yanıt verir; "hisse mi, faiz mi" sorusuna vermez.
- Portföy hep hissededir: piyasa düşünce o da düşer. Geçmişte en büyük düşüş %36; benzer koşullarda %55'e
  kadar düşüş olasılık dışı değil (bootstrap %5'lik dilim).
- Sharpe oranının %90 güven aralığı −0,08 ile 1,30 arasında; yani faizi geçeceği kesin değil.
- Dolar bazında 2025 ve 2026 eksi.
- 10 yıllık veri, bir stratejiyi "kanıtlamak" için kısadır. Gerçek sonuçların geçmiş testin gerisinde kalması
  olağandır; beklentinizi geçmiş testteki katkının yarısına göre kurun.

Ayrıntılı rapor (27 denemenin tamamı, varsayım duyarlılıkları, grafikler) panelin **Geçmiş testi**
sekmesindedir.

### İsteğe bağlı "temkinli mod"

BIST 100'ün son 12 aylık getirisi gecelik faizin gerisindeyse portföyün yarısını nakitte tutan bir filtre de
var. Geçmiş testte yıllık getiriyi %48'e çıkardı ve en büyük düşüşü %25'e indirdi. **Varsayılan değildir**,
çünkü kazancı yalnızca iki döneme (2018-19 ve 2024-26) ve 12 aylık ayara dayanıyor; 6-9 aylık ayarda fayda
kayboluyor ve nakdiniz faiz kazanmıyorsa temel stratejiden kötü sonuç veriyor. Açmak isterseniz `ayar.toml`
dosyasının sonundaki üç satırın başındaki `#` işaretlerini silin ve nakit kısmını gecelik repo ya da para
piyasası fonunda değerlendirin (para piyasası fonları da risksiz değildir).

## Kurulum (telefondan yapılabilir)

1. **Bot dosyalarını ana dala alın.** Bu klasör `main` dalına birleştirildiğinde zamanlanmış çalışma devreye girer.
2. **Sermayenizi yazın.** GitHub'da `borsa-bot/ayar.toml` dosyasını açın, kalem simgesine dokunun,
   `capital = 100000` satırına bu stratejiye ayıracağınız tutarı yazıp kaydedin. Emir listesindeki lot
   adetleri buna göre hesaplanır. (İlk çalıştırmadan sonra değiştirmenin etkisi olmaz.)
3. **Telegram bildirimi (isteğe bağlı ama önerilir).**
   - Telegram'da **@BotFather**'a `/newbot` yazın, bir ad ve `bot` ile biten bir kullanıcı adı verin; size bir
     **anahtar (token)** verir.
   - Yeni botunuzu açıp **Başlat**'a dokunun ve bir mesaj yazın.
   - Tarayıcıda `https://api.telegram.org/bot<ANAHTAR>/getUpdates` adresini açın; `"chat":{"id":` yazısından
     sonraki sayı sizin **sohbet numaranızdır**.
   - GitHub'da deponuzda **Settings → Secrets and variables → Actions → New repository secret** ile iki gizli
     değer ekleyin: `TELEGRAM_BOT_TOKEN` (anahtar) ve `TELEGRAM_CHAT_ID` (sohbet numarası).
     Anahtarı başka hiçbir yere yazmayın.
4. **İlk çalıştırma.** Deponuzda **Actions → BIST Bot → Run workflow**. Önce komut olarak `doktor` seçip
   veri kaynaklarına erişimi sınayın; sonra `gunluk` ile ilk çalıştırmayı yapın (ilk seferde veri indirdiği
   için 15-25 dakika sürebilir).
5. **Panel.** Döviz Kasası sayfanızın adresinin sonuna `borsa-bot/web/` ekleyin
   (örnek: `https://kullanici-adiniz.github.io/Deneme-2/borsa-bot/web/`). Ana ekrana ekleyebilirsiniz.

Bot bundan sonra her işlem günü İstanbul saatiyle 19:17'de (yedekleri 20:47, 22:23 ve ertesi sabah 08:43)
çalışır.

## Günlük kullanım

- Akşam Telegram'a özet gelir. **Akşam 21:00'e kadar mesaj gelmediyse bir sorun vardır:** Actions sekmesine bakın.
- Mesajda **emir varsa**, ertesi sabah **09:40'tan önce** aracı kurum uygulamanızdan girin:
  - önce **satışları**, sonra **alışları**;
  - emir türü **limitli**, mesajdaki limit fiyatla (son kapanışın %3 uzağı, tavan/taban içinde);
  - açılışı tavandan olan hisseyi **almayın** (bot da kâğıt portföyde almaz).
- Emir çoğu ay yalnızca ayın ilk işlem günü akşamı gelir (ayda ortalama 4-5 işlem).
- Kâğıt portföy, emirlerin açılış fiyatından gerçekleştiğini varsayar. Sizin gerçekleşmeleriniz birkaç kuruş
  farklı olabilir; önemli olan aynı hisseleri aynı ağırlıkta tutmanızdır.
- Bot bir gün çalışmazsa kararı kaçırmaz; ilk çalıştığı gün verir ve "ertelenmiş" olarak işaretler.

**Vergi notu (2026 itibarıyla, bilgi amaçlı):** BIST hisselerinin alım-satım kazancında stopaj %0'dır;
nakit temettüde %15 stopaj kesilir (geçmiş testte düşülmüştür). Kendi durumunuz için mali müşavirinize danışın.

## Neden gerçek emir göndermiyor?

Türkiye'de bireysel yatırımcıya açık, ücretsiz ve güvenilir bir emir API'si şu an yok: en yaygın olanı
(Deniz Yatırım AlgoLab) 31.12.2025'te kapatıldı; kalan seçenekler SMS onayı, ücretli masaüstü programı veya
sık değişen sunucu adresleri gerektiriyor. Bu yüzden bot, her aracı kurumda çalışan en sağlam yolu izler:
**emir listesi + sizin onayınız.** Ayda bir kaç emir girmek birkaç dakikanızı alır.

## Veri kaynakları

| Veri | Kaynak |
|---|---|
| Günlük fiyatlar, BIST 100 üyeliği, brüt takas / durdurma bayrakları | Borsa İstanbul resmî Pay Piyasası günlük bülteni |
| Temettü / bedelli / bedelsiz düzeltme katsayıları, piyasa değeri, mali tablolar | İş Yatırım (kamuya açık sayfalar) |
| Gecelik faiz (TLREF) | Borsa İstanbul |

- Piyasa verisi **depoya konmaz**; her çalıştırmada kaynağından indirilir ve yalnızca geçici önbellekte tutulur.
- İş Yatırım'ın düzeltilmiş fiyat serisindeki eksikler (ör. atlanmış bedelli sermaye artırımları), bültenin
  resmî "özsermaye hali" bayrağı ve günlük fiyat marjı kullanılarak otomatik yakalanıp onarılır. 251 hissenin
  11 yıllık verisinde onarım sonrası fiyat marjını aşan tek bir düzeltilmiş getiri kalmamıştır.
- Bu kaynaklar kişisel kullanım içindir; veriyi yeniden dağıtmayın.

## Sorun giderme

- **Panel "Bot henüz çalışmadı" diyor:** Actions'tan `gunluk` komutunu bir kez elle çalıştırın.
- **"Yeni karar ertelendi" uyarısı:** Veri eksik indi (ör. kaynak geçici olarak yanıt vermedi). Bot yanlış
  işlem yapmamak için bekler; sonraki çalıştırmada kendiliğinden düzelir.
- **Zamanlanmış çalışma durdu:** GitHub, 60 gün hiç etkinlik olmayan depolarda zamanlanmış işleri kapatabilir.
  Actions → BIST Bot → **Enable workflow**.
- **Panel eski veri gösteriyor:** Sayfayı yenileyin; panel veriyi hem sayfanın kendi klasöründen hem deponun
  ham dosyasından okur ve yenisini kullanır.

## Geliştiriciler için

```bash
cd borsa-bot
pip install -r requirements-dev.txt
python -m pytest                      # 70 test, ağ erişimi gerektirmez
python -m bistbot doktor              # veri kaynaklarına erişim testi
python -m bistbot gunluk --deneme     # bugünün sinyalleri; hiçbir şey kaydetmez
python -m bistbot veri                # 2015'ten bugüne veriyi indir (≈1 saat)
python -m bistbot backtest            # geçmiş testi + sağlamlık raporu → web/data/backtest.json
```

| Modül | Görev |
|---|---|
| `bistbot/data/bulletin.py` | Resmî günlük bültenleri indirir ve ayrıştırır |
| `bistbot/data/panel.py` | Tarih × hisse tabloları; kod değişikliklerini (ör. KOZAL → TRALT) birleştirir |
| `bistbot/data/adjust.py` | Düzeltme katsayıları ve eksik sermaye olaylarının onarımı |
| `bistbot/data/isyatirim.py`, `isystore.py`, `macro.py` | İş Yatırım ve TLREF verileri, önbellek |
| `bistbot/data/dataset.py` | Hepsini tek veri nesnesinde birleştirir; mali tablolar gecikmeli devreye girer |
| `bistbot/signals.py` | Evren filtresi, özellikler, bileşik puan |
| `bistbot/portfolio.py` | Seçim bandı, ağırlıklar, takvim, rejim filtresi |
| `bistbot/backtest/` | Motor, ölçüler, aşırı uyum istatistikleri, kıyaslar |
| `bistbot/research.py` | Ön kayıtlı deneme seti ve sağlamlık raporu |
| `bistbot/live/` | Günlük çalıştırıcı, durum dosyası, bildirim |
| `web/` | Panel (tek sayfa, bağımlılıksız) |

**İleriye bakma (look-ahead) güvenceleri:** kararlar `t` günü kapanış verisiyle verilir, işlemler `t+1`
açılışında yapılır; mali tablolar dönem sonundan 75 gün (yıllıklar 145 gün) sonra kullanılır; evren ve endeks
üyeliği o günkü bültenden alınır. Testler, `t` gününden sonraki tüm veriler silindiğinde veya değiştirildiğinde
`t` günü puanlarının aynı kaldığını doğrular. Canlı kâğıt portföy, backtest motorunun birebir aynısıyla ve
dondurulmuş kararlarla her gün baştan hesaplanır; böylece geçmiş testi ile canlı davranış ayrışamaz.
