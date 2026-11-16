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
| **Strateji (20 hisse, masraflar düşülmüş)** | **%41,8** | **−%32** | **0,57** |
| Havuz sepeti: seçim yapılan tüm hisseler, eşit ağırlık, masrafsız | %35,9 | −%38 | 0,39 |
| BIST 100 endeksi (büyük şirket ağırlıklı, temettüsüz) | %31,8 | −%32 | 0,27 |
| Gecelik faiz (TLREF) | %27,2 | – | – |

\* Sharpe, gecelik TL faizinin üzerindeki getiriyle hesaplanır.

| Yıl | Strateji | Havuz sepeti | BIST 100 | Gecelik faiz |
|---|---:|---:|---:|---:|
| 2017 | +56% | +48% | +48% | +12% |
| 2018 | −14% | −24% | −21% | +20% |
| 2019 | +46% | +60% | +25% | +23% |
| 2020 | +75% | +78% | +29% | +11% |
| 2021 | +43% | +21% | +26% | +20% |
| 2022 | +202% | +237% | +197% | +14% |
| 2023 | +60% | +27% | +36% | +21% |
| 2024 | +27% | +24% | +32% | **+64%** |
| 2025 | +15% | +16% | +15% | **+55%** |
| 2026 (13 Kasım'a kadar) | −9% | −14% | +5% | **+40%** |

**Bu sonuçlar ne kadar güvenilir? Kısaca: umut verici, ama kanıtlanmış değil.**

- Strateji BIST 100 endeksini yılda yaklaşık 10 puan geçti; ancak bunun yaklaşık 4 puanı seçimden değil,
  hisseleri **eşit ağırlıkla** tutmaktan geliyor (havuz sepeti de endeksi geçiyor).
- Hisse **seçiminin** katkısı, havuz sepetine göre yılda yaklaşık **+6 puan**. İstatistiksel olarak sınırda:
  alfa t-istatistiği 1,7 (2'nin altı), bootstrap %90 güven aralığı yılda **−0,9 ile +9,4 puan** arası
  (sıfırı içeriyor), sepeti geçme olasılığı %91.
- Aynı havuzdan rastgele seçilip aynı kurallarla tutulan 200 portföyün **%89'unu** geçti (hepsini değil).
- 27 farklı ayarla denendi (hisse sayısı, sıklık, sütunların tek tek çıkarılması vb.). Rejim filtresi
  dışındaki 23 ayarın 22'si kendi havuz sepetini geçti (biri, yalnız kârlılık sütunu, sepetle aynı kaldı). Kullanılan ayar bu denemelerin en iyisi değil
  (Sharpe'a göre 16.), önceden sabitlenen ayardır; en iyi görüneni seçmek veriye uydurma olurdu.
- Masraflar iki katına çıkınca yıllık getiri %41,8'den %41,1'e iniyor; emirler bir gün geç girilirse değişmiyor.

**Zayıf yanlar — bunları bilerek kullanın:**

- **Son üç yılda gecelik faiz hisseleri geçti.** 2024, 2025 ve 2026'da strateji de endeks de faizin gerisinde
  kaldı; 2026'da strateji ekside. Strateji "hangi hisse" sorusuna yanıt verir; "hisse mi, faiz mi" sorusuna vermez.
- Portföy hep hissededir: piyasa düşünce o da düşer. Geçmişte en büyük düşüş %32; benzer koşullarda %55'e
  kadar düşüş olasılık dışı değil (bootstrap %5'lik dilim).
- Sharpe oranının %90 güven aralığı −0,12 ile 1,27 arasında; yani faizi geçeceği kesin değil.
- Dolar bazında 2025 ve 2026 eksi.
- 10 yıllık veri, bir stratejiyi "kanıtlamak" için kısadır. Gerçek sonuçların geçmiş testin gerisinde kalması
  olağandır. Bu botu "piyasayı kesin yener" diye değil, "BIST 100 içinde disiplinli, dağıtılmış, kurallı
  bir portföy yöneticisi" diye değerlendirin.

Ayrıntılı rapor (27 denemenin tamamı, varsayım duyarlılıkları, grafikler) panelin **Geçmiş testi**
sekmesindedir.

**Bağımsız inceleme ve düzeltmeler.** İlk geçmiş testi üç bağımsız incelemeden geçirildi ve sonuçları
olduğundan iyi gösteren hatalar bulundu; hepsi düzeltildi ve test yeniden çalıştırıldı:
(1) veri kaynağındaki yıl sonu bilanço rakamları sonradan enflasyona göre yeniden düzenlenmiş hâlleriydi,
yani o tarihte bilinmeyen bilgi içeriyordu — artık kullanılmıyor, her mali tablo yalnızca kendi rakamlarıyla
değerlendiriliyor; (2) kıyas sepeti, borsanın Şubat 2023'te yeniden açıldığı günün yükselişini kaçırıyordu;
(3) kıyas her gün yeniden dengeleniyordu, oysa adil kıyas stratejiyle aynı takvimi kullanan sepettir;
(4) rastgele portföy testi rastgele portföylere fazladan masraf yüklüyordu. Bu düzeltmelerden önce seçim
katkısı "+9,7 puan, t = 2,3" görünüyordu; doğrusu yukarıdaki "+6 puan, t = 1,7"dir.

### İsteğe bağlı "temkinli mod"

BIST 100'ün son 12 aylık getirisi gecelik faizin gerisindeyse portföyün yarısını nakitte tutan bir filtre de
var. Geçmiş testte yıllık getiriyi %46,5'e çıkardı ve en büyük düşüşü %24'e indirdi. **Varsayılan değildir**,
çünkü kazancı yalnızca iki döneme (2018-19 ve 2024-26) ve 12 aylık ayara dayanıyor; 6 aylık ayarda fayda
kayboluyor (%40,2), 9 aylıkta azalıyor (%42,2) ve nakdiniz faiz kazanmıyorsa temel stratejiden kötü sonuç
veriyor (%38,0). Açmak isterseniz `ayar.toml` dosyasının sonundaki üç satırın başındaki `#` işaretlerini
silin ve nakit kısmını gecelik repo ya da para piyasası fonunda değerlendirin (para piyasası fonları da
risksiz değildir). Bu ayar yalnızca sonraki kararları etkiler.

## Kurulum (telefondan yapılabilir)

1. **Bot dosyalarını ana dala alın.** Bu klasör `main` dalına birleştirildiğinde zamanlanmış çalışma devreye girer.
2. **Sermayenizi ve komisyonunuzu yazın.** GitHub'da `borsa-bot/ayar.toml` dosyasını açın, kalem simgesine
   dokunun, `capital = 100000` satırına bu stratejiye ayıracağınız tutarı, `commission` satırına aracı
   kurumunuzun komisyon oranını yazıp kaydedin. Emir listesindeki lot adetleri buna göre hesaplanır.
   Sermaye ve masraf ayarları **ilk kararda sabitlenir**; sonradan değiştirmenin etkisi olmaz (geçmiş
   yeniden yazılmasın diye).
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
   için 15-25 dakika sürebilir). Bot ilk emir listesini yalnızca **uygulayabileceğiniz bir zamanda** verir:
   işlem günü akşamı (kapanış verisi yayımlandıktan sonra) ya da sabah 09:30'dan önce. Gün içinde
   çalıştırırsanız "akşam gelecek" der ve bekler.
5. **Panel.** Döviz Kasası sayfanızın adresinin sonuna `borsa-bot/web/` ekleyin
   (örnek: `https://kullanici-adiniz.github.io/Deneme-2/borsa-bot/web/`). Ana ekrana ekleyebilirsiniz.

Bot bundan sonra her işlem günü İstanbul saatiyle 19:17'de (yedekleri 20:47, 22:23 ve ertesi sabah 08:43)
çalışır.

## Günlük kullanım

- Akşam Telegram'a özet gelir. **Akşam 21:00'e kadar mesaj gelmediyse bir sorun vardır:** Actions sekmesine bakın.
- Mesajda **emir varsa**, sonraki seansın açılışından önce (**09:40'tan önce**) aracı kurum uygulamanızdan girin:
  - önce **satışları**, sonra **alışları**;
  - emir türü **limitli**, mesajdaki limit fiyatla (son kapanışın %3 uzağı, tavan/taban içinde);
  - lot adetleri tamdır ve alımların toplamı, limit fiyatlardan bile (nakit + satış gelirine) sığacak
    şekilde hesaplanır; aracı kurumunuz bekleyen satışın parasını kullandırmıyorsa alışları satışlar
    gerçekleştikten hemen sonra girin;
  - bir satış gerçekleşmezse (taban) parası yetmeyen, yani listenin sonundaki alımı azaltın; ertesi
    akşamki mesajdaki "gerçekleşen" listesi kâğıt portföyün ne aldığını gösterir;
  - açılışı tavandan olan hisseyi **almayın** (bot da kâğıt portföyde almaz); tabandan açıldığı için
    satılamayan hisse ertesi günün listesinde "önceki günden kalan" olarak yeniden gelir.
- Emir çoğu ay yalnızca ayın ilk işlem günü akşamı gelir (ayda ortalama 5 işlem).
- Kâğıt portföy yalnızca tam lot alıp satar ve emirlerin açılış fiyatından gerçekleştiğini varsayar; listeyi
  uygularsanız hesabınızdaki lotlar paneldekiyle aynı olur. Gerçekleşme fiyatınız birkaç kuruş farklı olabilir.
- **Temettü** ödendiğinde nakdinize eklenir (bot da öyle sayar). **Bedelsiz/bölünmede** lot adediniz
  kendiliğinden değişir. **Bedelli sermaye artırımında** bot sizi uyarır: rüçhan haklarınızı satmanız ya da
  kullanmanız gerekir; kâğıt portföy hakların kuramsal değerinden satıldığını varsayar.
- Bot bir gün çalışmazsa kararı kaçırmaz; ilk çalıştığı uygun zamanda verir.
- Veri eksik ya da tutarsızsa (ör. bir bülten indirilemediyse, eldeki bir hissenin verisi yoksa) bot **karar
  vermez**, uyarı gönderir ve bir sonraki çalıştırmada yeniden dener. Yanlış emir üretmektense beklemeyi seçer.

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
  resmî "özsermaye hali" bayrağı ve günlük fiyat marjı kullanılarak otomatik yakalanıp onarılır (250 hissenin
  11 yıllık verisinde 6 olay). Onarım, o günün işlem aralığından tahmin edilen yaklaşık bir değerdir; kesin
  değildir, ama onarım sonrası fiyat marjını aşan düzeltilmiş getiri kalmamıştır.
- Mali tablolardan yalnızca ilk yayımlandığı hâliyle duran ara dönem tabloları kullanılır; kaynağın sonradan
  enflasyona göre yeniden düzenlediği yıl sonu rakamları kullanılmaz. Tablolar dönem sonundan 75 gün sonra
  devreye girer.
- Bu kaynaklar kişisel kullanım içindir; veriyi yeniden dağıtmayın.

## Sorun giderme

- **Panel "Bot henüz çalışmadı" diyor:** Actions'tan `gunluk` komutunu bir kez elle çalıştırın.
- **"Yeni karar ertelendi" / "karar bekliyor" uyarısı:** Veri eksik indi ya da karar için uygun zaman değil.
  Bot yanlış işlem yapmamak için bekler; sonraki çalıştırmada kendiliğinden düzelir ve emir listesi o zaman
  ayrıca bildirilir.
- **"Bot çalışamadı: bülten eksik" mesajı:** Bir günün resmî bülteni indirilemedi. Bot eksik günle hesap
  yapmaz; sonraki çalıştırmada yeniden dener.
- **"Daha önce bildirilen kâğıt işlemler yeniden hesaplandı" uyarısı:** Veri kaynağı geçmişe dönük bir
  düzeltme yaptı. Paneldeki lotları hesabınızla karşılaştırın.
- **Zamanlanmış çalışma durdu:** GitHub, 60 gün hiç etkinlik olmayan depolarda zamanlanmış işleri kapatabilir.
  Actions → BIST Bot → **Enable workflow**.
- **Panel eski veri gösteriyor:** Sayfayı yenileyin; panel veriyi hem sayfanın kendi klasöründen hem deponun
  ham dosyasından okur ve yenisini kullanır.

## Geliştiriciler için

```bash
cd borsa-bot
pip install -r requirements-dev.txt
python -m pytest                      # 96 test, ağ erişimi gerektirmez
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
açılışında yapılır; mali tablolar dönem sonundan 75 gün sonra kullanılır ve sonradan yeniden düzenlenen yıl
sonu satırları hiç kullanılmaz; evren ve endeks üyeliği o günkü bültenden alınır. Testler, `t` gününden sonraki
tüm veriler silindiğinde veya değiştirildiğinde `t` günü puanlarının aynı kaldığını doğrular. Canlı kâğıt
portföy, backtest motorunun aynısıyla (tam lot kipinde) ve dondurulmuş kararlarla her gün baştan hesaplanır;
bildirilen işlemler durum dosyasında saklanır ve yeniden hesaplama bunları değiştirirse uyarı verilir.

Günlük çalışma İş Yatırım dosyalarını `.cache/isy-live`, araştırma komutları `.cache/isy` altında tutar;
böylece günlük çalışmanın kısa pencereli dosyaları uzun dönem dosyalarının üzerine yazılmaz.
