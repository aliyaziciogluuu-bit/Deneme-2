# BIST Bot

Borsa İstanbul için kurallı bir al-sat botu. Her işlem günü kapanıştan sonra kendiliğinden çalışır,
BIST 100 hisselerini puanlar, bir **kâğıt portföy** tutar ve ertesi sabah vermeniz gereken
**emir listesini** (hisse, lot, limit fiyat) hazırlayıp Telegram'a ve panele yazar.

> **Önemli.** Varsayılan kullanımda bot gerçek hesabınıza emir **göndermez**; emirleri aracı kurumunuzun
> uygulamasından siz girersiniz. İsterseniz, Windows'ta Matriks IQ açıkken emirleri bot gönderir; ama yalnızca
> Telegram'dan o listeye özel kodu yazarak onay verdikten sonra (bkz. [Gerçek emir](#gerçek-emir-matriks-iq-ile-telegram-onayıyla)).
> Buradaki hiçbir şey yatırım tavsiyesi değildir. Geçmiş performans geleceği garanti etmez; kaybetmeyi göze
> alamayacağınız parayla işlem yapmayın.

## Ne yapar?

- **Evren:** O günkü resmî BIST 100 üyeleri (brüt takasta, tek fiyatta veya işlemi durdurulmuş olanlar ile
  bir yıldan kısa geçmişi olanlar hariç).
- **Puanlama (hibrit: temel + teknik analiz, sütunlar eşit ağırlıklı):**
  - **Temel analiz katmanı**
    - *Değer* — özkaynağa ve kâra göre ucuzluk (düşük PD/DD, düşük F/K),
    - *Kârlılık* — özkaynak kârlılığı.
  - **Teknik analiz katmanı**
    - *Momentum* — son 12 ayın getirisi (son ay hariç),
    - *Düşük risk* — az oynak, düşük betalı, "piyango" gibi davranmayan hisseler,
    - *Teknik sütun* (isteğe bağlı, kapalı gelir) — fiyatın 200 günlük ortalamaya uzaklığı, 50/200 günlük
      ortalama oranı ve 52 haftalık zirveye yakınlık.
- **Portföy:** En iyi 20 hisse, eşit ağırlık. Ayda bir (ayın ilk işlem günü) gözden geçirilir; eldeki bir
  hisse sıralamada 40'ın altına düşmedikçe satılmaz (gereksiz al-satı önler).
- **İşlem:** Karar akşam verilir, emirler **ertesi sabah açılış seansında** limitli girilir.

İlk dört sütun, Borsa İstanbul üzerine yayımlanmış akademik çalışmalarda öne çıkan etkenlerdir ve varsayılan
stratejiyi oluşturur: bot bu hâliyle zaten temel ve teknik analizi birlikte kullanır. Ek teknik parçalar
(teknik sütun, teknik onay kapısı) sonradan eklendi ve isteğe bağlıdır; ayrıntısı ve dürüst test sonucu
[Hibrit mod](#hibrit-mod-teknik--temel-analiz) başlığındadır. Eğilim ölçüleri **nakde (gecelik faize) göre**
fiyattan hesaplanır: yüksek enflasyonda TL fiyatların neredeyse hepsi 200 günlük ortalamasının üstündedir;
"yükseliş" ancak hisse faizden fazla kazandırıyorsa anlamlıdır. RSI ve MACD panelde **bilgi olarak**
gösterilir ama puana katılmaz: tek başına al-sat kuralı olarak BIST'te al-tut stratejisini geçemedikleri
görülüyor ve hisse seçiminde işe yaradıklarına dair sağlam kanıt yok.

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

**Bu sonuçlar ne kadar güvenilir? Kısaca: umut verici, ama kanıtlanmış değil.** (Aşağıdaki rakamlar ön
kayıtlı temel strateji içindir; hibrit modun rakamları ayrı başlıktadır.)

- Strateji BIST 100 endeksini yılda yaklaşık 10 puan geçti; ancak bunun yaklaşık 4 puanı seçimden değil,
  hisseleri **eşit ağırlıkla** tutmaktan geliyor (havuz sepeti de endeksi geçiyor).
- Hisse **seçiminin** katkısı, havuz sepetine göre yılda yaklaşık **+6 puan**. İstatistiksel olarak sınırda:
  alfa t-istatistiği 1,7 (2'nin altı), bootstrap %90 güven aralığı yılda **−0,9 ile +9,4 puan** arası
  (sıfırı içeriyor), sepeti geçme olasılığı %91.
- Aynı havuzdan rastgele seçilip aynı kurallarla tutulan 200 portföyün **%89'unu** geçti (hepsini değil).
- 31 farklı ayarla denendi (hisse sayısı, sıklık, sütunların tek tek çıkarılması, rejim filtresi, dört hibrit
  biçim). Rejim filtresi ve hibritler dışındaki 23 ayarın 22'si kendi havuz sepetini geçti (biri, yalnız
  kârlılık sütunu, sepetle aynı kaldı). Temel strateji bu denemelerin en iyisi değil (Sharpe'a göre 20.),
  önceden sabitlenen ayardır; en iyi görüneni seçmek veriye uydurma olurdu.
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

Ayrıntılı rapor (31 denemenin tamamı, hibrit karşılaştırması, varsayım duyarlılıkları, grafikler) panelin
**Geçmiş testi** sekmesindedir.

**Bağımsız inceleme ve düzeltmeler.** İlk geçmiş testi üç bağımsız incelemeden geçirildi ve sonuçları
olduğundan iyi gösteren hatalar bulundu; hepsi düzeltildi ve test yeniden çalıştırıldı:
(1) veri kaynağındaki yıl sonu bilanço rakamları sonradan enflasyona göre yeniden düzenlenmiş hâlleriydi,
yani o tarihte bilinmeyen bilgi içeriyordu — artık kullanılmıyor, her mali tablo yalnızca kendi rakamlarıyla
değerlendiriliyor; (2) kıyas sepeti, borsanın Şubat 2023'te yeniden açıldığı günün yükselişini kaçırıyordu;
(3) kıyas her gün yeniden dengeleniyordu, oysa adil kıyas stratejiyle aynı takvimi kullanan sepettir;
(4) rastgele portföy testi rastgele portföylere fazladan masraf yüklüyordu. Bu düzeltmelerden önce seçim
katkısı "+9,7 puan, t = 2,3" görünüyordu; doğrusu yukarıdaki "+6 puan, t = 1,7"dir.

### Hibrit mod (teknik + temel analiz)

Bot her zaman iki katmanla puanlar: **temel** (değer, kârlılık) ve **teknik** (momentum, düşük risk). Buna
eklenebilecek dört **ek teknik parça** denendi. Biçimler, sonuçlar görülmeden **önce** beyan edildi ve geçme
ölçütleri önceden yazıldı: (1) tam dönemde hem getiri hem Sharpe temel stratejiden yüksek, (2) üç alt dönemin
en az ikisinde daha iyi, (3) masraflar iki katına çıkınca da Sharpe daha yüksek.

| Biçim | Yıllık getiri | Sharpe | En büyük düşüş | 2017-19 | 2020-22 | 2023-26 | Nakde faiz yokken | Ölçütler |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| **Temel strateji (varsayılan)** | **%41,8** | **0,57** | −%32 | %25 | %96 | %21 | %41,4 | – |
| Teknik sütun (5. sütun) | %44,2 | 0,63 | −%35 | %27 | %99 | %23 | %43,6 | ✓ ✓ ✓ |
| Onay kapısı, yalnız alımda | %42,5 | 0,58 | −%35 | %24 | %95 | %24 | %41,7 | ✓ ✗ ✓ |
| Onay kapısı, alım + çıkış (ön kayıtlı aday) | %47,4 | 0,77 | −%33 | %21 | %89 | %41 | %39,7 | ✓ ✗ ✓ |
| Teknik sütun + onay kapısı | %49,7 | 0,81 | −%32 | %26 | %99 | %37 | %43,8 | ✓ ✓ ✓ |

**Sonuç: ek teknik parçaların hiçbiri varsayılan değil; ikisi de `ayar.toml` ile açılabilen seçenek.** Nedenleri:

- Önceden "aday" ilan ettiğim biçim **onay kapısıydı** (hisse ancak yükseliş eğilimindeyse alınır, eğilim
  bozulunca satılır, uygun hisse yoksa para nakitte bekler). Toplamda iyi görünse de **kendi koyduğum ikinci
  ölçütü geçemedi**: kazancının neredeyse tamamı 2023-2026'dan (faizin hisseleri geçtiği dönemden) geliyor,
  diğer iki dönemde temel stratejinin gerisinde ve nakdiniz faiz kazanmıyorsa daha kötü (%39,7'ye karşı %41,4).
  Kural açıktı: aday geçemezse varsayılan değişmez.
- **Teknik sütun** tabloda üç ölçütü de sağlıyor ve dokuz komşu ayarın (farklı karar günleri, hisse sayıları,
  haftalık dengeleme, bant genişlikleri) **yedisinde** temel stratejiden önde; önde olmadığı iki ayar, kararın
  ayın 6. işlem gününde verilmesi (%42,6'ya karşı %42,5: fark yok) ve 10 hisseli portföy (%49,7'ye karşı
  %50,2). Yani katkısı büyük olasılıkla tümüyle rastlantı değil; ama küçük (yılda yaklaşık +2,3 puan), en
  büyük düşüşü derinleştiriyor (−%35) ve dört biçim denendikten **sonra** öne çıktı (şans payı). Ön kayıtlı
  aday olmadığı için kuralı sonradan esnetmedim. **Ek teknik parçalardan birini açmak isterseniz en
  savunulabilir olanı budur.**
- "Teknik sütun + kapı" en parlak rakamı veriyor (%49,7); onu seçmek, veriye uydurmanın ta kendisi olurdu.

**Bir hata ve düzeltmesi (şeffaflık için).** İlk hibrit testte teknik sütun çok daha iyi görünüyordu (%46,3,
Sharpe 0,69) ve bir süre açık bırakılmıştı. Bağımsız inceleme nedenini buldu: teknik sütun açıkken **mali
tablosu hiç olmayan** hisseler yalnızca fiyat ölçütleriyle puanlanıp listeye girebiliyordu ve görünen
üstünlüğün yaklaşık yarısı böyle tek bir hisseden geliyordu. Bu, "temel + teknik" fikrine aykırıydı;
düzeltildi (hibritte en az bir temel ölçütün verisi aranır) ve test yeniden çalıştırıldı. Yukarıdaki tablo
düzeltilmiş hâlidir.

Teknik sütunu denemek için `ayar.toml` içindeki `[signal]` ve `w_technical = 1.0` satırlarını, onay kapısı
için `[portfolio]` ve `trend_gate = "entry_exit"` satırlarını açın (başlarındaki `#` işaretini silin). Bu
ayarlar yalnızca sonraki kararları etkiler; geçmiş kâğıt işlemler değişmez. Panelin **Sıralama** sekmesi her
hisse için temel ve teknik katman puanını, eğilimini ve RSI değerini her durumda gösterir.

### İsteğe bağlı "temkinli mod"

BIST 100'ün son 12 aylık getirisi gecelik faizin gerisindeyse portföyün yarısını nakitte tutan bir filtre de
var. Geçmiş testte yıllık getiriyi %46,5'e çıkardı ve en büyük düşüşü %24'e indirdi. **Varsayılan değildir**,
çünkü kazancı yalnızca iki döneme (2018-19 ve 2024-26) ve 12 aylık ayara dayanıyor; 6 aylık ayarda fayda
kayboluyor (%40,2), 9 aylıkta azalıyor (%42,2) ve nakdiniz faiz kazanmıyorsa temel stratejiden kötü sonuç
veriyor (%38,0). Açmak isterseniz `ayar.toml` dosyasının sonundaki `[portfolio]`, `regime` ve
`regime_off_exposure` satırlarının başındaki `#` işaretlerini silin ve nakit kısmını gecelik repo ya da para
piyasası fonunda değerlendirin (para piyasası fonları da risksiz değildir). Bu ayar yalnızca sonraki kararları
etkiler.

## Halka arz keşfi (sonuç: işe yarar bir kural çıkmadı)

Soru: yeni halka arz olan bir hisseyi **piyasadan sonradan alan** biri için tekrarlanan, kazandıran bir kalıp
var mı? Kurallar, yöntem ve geçme ölçütleri sonuçlar görülmeden önce yazılıp depoya işlendi (bkz.
`bistbot/ipo.py` başındaki ön kayıt). Veri: resmî günlük bültenler, Haziran 2016 – Kasım 2026, **261 halka arz**.

Sınanan 6 sinyal × 3 elde tutma süresi (5, 20, 60 seans) = 18 kural: tavan serisi bozulduğu gün alım; bozulduğu
gün artıda / ekside kapatanlar; hiç tavan yapmayanlar; uzun seri yapanlar; zirveden %30 düşünce alım. Alım hep
ertesi sabah açılıştan, masraflar düşülerek; kıyas, aynı günlerde bütün hisselerin eşit ağırlıklı getirisi.

**Sonuç: keşif yok.** 2024 öncesi 173 halka arzda 18 kuralın hiçbiri önceden konan eşiği (t ≥ 3,0) geçemedi;
en yükseği 2,4'te kaldı. Kural gereği ayrılan 2024–2026 verisi (88 halka arz) yalnızca bilgi için incelendi ve
tablo daha da kötü çıktı. Kıyas, yeni halka arzlar dışarıda tutularak yeniden hesaplandığında sonuç değişmedi.

**Bir düzeltme (şeffaflık için).** İlk hesapta bültendeki "önceki kapanış" alanını bedelsiz/bedelli/temettüye göre
düzeltilmiş sanmıştım; değilmiş. Getiriler İş Yatırım düzeltme katsayılarıyla yeniden hesaplandı. Halka arzdan
sonraki ilk aylarda bu tür olaylar ender olduğu için 20 seanslık 251 işlemin yalnızca 1'i, 60 seanslık 248 işlemin
9'u değişti; sonuç aynı kaldı. Aşağıdaki rakamlar düzeltilmiş hâlidir.

Tavan serisi bozulduktan sonraki sabah alan biri için (bütün dönem):

| Elde tutma | İşlem | Zarar eden | Faizin altında kalan | Ortanca net getiri | Ortalama net getiri |
|---|---:|---:|---:|---:|---:|
| 5 seans | 251 | %65 | %65 | −%4,9 | −%0,7 |
| 20 seans | 251 | %59 | %62 | −%5,0 | +%4,5 |
| 60 seans | 248 | %48 | %54 | +%1,3 | +%20,9 |

- **Piyango gibi davranıyor.** Ortalama artı görünse de tipik (ortanca) sonuç zarar: 60 seanslık ortalama
  anormal getirinin (%12,2) neredeyse tamamı en iyi 10 işlemden geliyor; onlar çıkarılınca %0,7 kalıyor.
- **Son yıllarda daha kötü.** 2024'ten beri 20 seans tutanların %73'ü zarar etti; ortanca sonuç piyasanın
  13 puan altında.
- **Hiç tavan yapmayan halka arzlar ilk hafta düşmeye devam ediyor** (5 seansta piyasanın ortalama 3 puan
  altında; 2024 sonrasında 5 puan). Bu bir "alma" bulgusudur, alım kuralı değil.
- Tek zayıf ipucu: seri bozulduğu gün artıda kapatanlar sonraki 5 seansta piyasayı ortalama 6 puan geçti
  (iki dönemde de). Eşiği geçemediği ve mutlak getiride işlemlerin yarısı zararda olduğu için **işlem kuralı
  olarak sunulmuyor.**

Bu çalışma halka arza **katılmayı** (dağıtımdan pay almayı) ölçmez; bültenlerde halka arz fiyatı ve kişi başına
dağıtılan lot yoktur. Yeniden üretmek için: `python -m bistbot halka-arz`.

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

## Gerçek emir (Matriks IQ ile, Telegram onayıyla)

Bot, emir listesini aracı kurumunuza kendisi de gönderebilir. Bunun için **Windows bilgisayarda Matriks IQ
masaüstü programı** gerekir: program açıkken aynı bilgisayarda bir "Dışarıdan Emir Kabulü" kapısı açar
(`127.0.0.1:18890`) ve bot emirleri bu kapıdan iletir. **Telefondaki Matriks Mobil IQ uygulaması bu kapıyı
açmaz;** yalnızca telefonunuz varsa emirleri listeden elle girmeye devam edersiniz. Onay, rapor ve panel
her durumda telefondan kullanılır.

**Nasıl çalışır?**

1. Bulut tarafı her akşam emir listesini (fişi) üretir (`web/data/latest.json`).
2. Emir günü sabahı bilgisayarınızdaki bot fişi okur ve güvenlik kontrollerinden geçirir: fiş bugünün seansı
   için mi, tek emir ve günlük toplam sınırlarının içinde mi, fiyatlar son kapanışa yakın mı, satılacak lot
   hesabınızda var mı (elinizde olandan fazlası asla satılmaz). Bir ihlal varsa **hiçbir emir gitmez**.
3. Telegram'a emir listesi ve dört haneli bir **kod** gelir. Kodu yazarsanız emirler gönderilir; `RED`
   yazarsanız ya da 17:30'a kadar yanıt vermezseniz gönderilmez. Kod o listeye özeldir ve yalnızca sizin
   Telegram hesabınızdan kabul edilir. Son söz geçerlidir: koddan sonra `RED`, `İPTAL` ya da `DUR` yazarsanız
   emirler gitmez.
4. Emirler limitli ve günlük olarak, önce satışlar sonra alışlar gönderilir: 09:40-09:55 arasındaysa açılış
   seansına, daha geç onaylarsanız sürekli işleme. Parası yetmediği için reddedilen alışlar, satışlar
   gerçekleşince bir kez daha denenir.
5. Sonuç (gerçekleşen, bekleyen, reddedilen) Telegram'a yazılır. Onaydan sonra `DUR` (ya da `RED`, `İPTAL`)
   yazarsanız sıradaki emirler durur; `bistbot emir --iptal` botun o gün gönderdiği bekleyen emirleri iptal
   eder. Reddedilen ya da gönderilemeyen emir kaldıysa programı yeniden çalıştırabilirsiniz: yalnızca kalanlar
   için yeniden onay istenir, gönderilmiş olanlar bir daha gönderilmez.

**Kurulum (Windows):**

1. [Python 3.11+](https://www.python.org/downloads/) kurun ("Add to PATH" işaretli olsun) ve bu depoyu
   bilgisayara indirin (`git clone` ya da ZIP).
2. `borsa-bot\windows\kur.bat` dosyasını çalıştırın; `emir-ayar.toml` oluşur. İçine Telegram bot anahtarınızı
   ve sohbet numaranızı yazın (bu dosya depoya gönderilmez).
3. Matriks IQ'da aracı kurumunuza giriş yapın. **Dışarıdan Emir Kabulü** ayrı bir lisansla çalışır: Matriks'in
   belgesine göre kapı ancak "ilgili lisans aktif edildiğinde" açılır; lisans için Matriks'e (ya da aracı
   kurumunuza) başvurun. Belge: "MatriksIQ Dışarıdan Emir Kabulü API Dokümanı" (matriksdata.com).
4. Bağlantıyı sınayın (yalnızca okur). Komut satırında `borsa-bot` klasöründe:
   `.venv\Scripts\activate` ve ardından `python -m bistbot emir --hesap`. Hesaplarınız, pozisyonlarınız ve
   bakiye satırları listelenir; gerekiyorsa `emir-ayar.toml` içindeki `[matriks]` ayarlarını buna göre doldurun.
5. Birkaç gün **deneme** kipinde bırakın (`mod = "deneme"` ya da `"salt-okunur"`): onay mesajı gelir, siz
   onaylarsınız, ama emir gönderilmez.
6. **Yön testi** (zorunlu, seans içinde): `python -m bistbot emir --yon-testi SEMBOL --fiyat FİYAT`. Elinizde
   olmayan bir hisse için piyasanın %5 altında **1 lotluk** alış emri gönderilir, size Matriks IQ'da "ALIŞ"
   olarak görünüp görünmediği sorulur ve emir iptal edilir. Bu test geçmeden gerçek kip açılmaz.
7. `emir-ayar.toml` içinde `mod = "gercek"` yapın ve `windows\gorev-kur.bat` ile hafta içi her sabah 09:25'e
   görev ekleyin. O saatte bilgisayar açık, Matriks IQ çalışıyor ve aracı kurum girişi yapılmış olmalıdır.

**Bilmeniz gerekenler (dürüstçe):**

- Bu bölüm **gerçek Matriks IQ programıyla denenemedi** (program Windows'ta, lisansla ve aracı kurum
  girişiyle çalışır; geliştirme ortamında yoktu). Protokol, Matriks'in resmî API belgesinden (sürüm 1.6) ve
  kendi yayımladığı örnek istemcilerden (github.com/MatriksIQ) çıkarıldı; belgedeki örnek iletileri taklit
  eden sahte bir sunucuya karşı test edildi. İlk kullanımda küçük sorunlar çıkması beklenir; o yüzden sıra
  şudur: `--hesap` → deneme kipi → yön testi → küçük sınırlarla gerçek kip.
- Belgeye göre yeni emirde **alış 1, satış 2**'dir (Matriks'in örnek kodunda 2022'ye kadar 0/1 idi). Yanlış
  kod, alış yerine satış demektir; **yön testi** bunu kendi hesabınızda, 1 lotla doğrulamak içindir. Ayrıca
  her emrin yanıtındaki yön, testte görülen değerle karşılaştırılır; uyuşmazsa emir iptal edilir ve gönderim
  durur. (Matriks IQ yanıtlarda yön alanını doldurmuyorsa bu denetim satışlarda yanlış alarm verebilir; o
  zaman Telegram'daki uyarıda yazdığı gibi `yon_yanit_denetimi = false` yapılır.)
- Bot her emri göndermeden **önce** günlüğe yazar ve aynı emri ikinci kez göndermez (program yeniden
  başlatılsa, aynı karar ertesi gün için yeniden yayımlansa ya da alış ikinci turda gönderilmiş olsa bile).
  Bir emrin yanıtı alınamazsa ("belirsiz") gönderim durur ve bot o emri kendiliğinden yeniden göndermez;
  Matriks IQ'dan kontrol etmeniz istenir.
- Emirler gönderilmeden hemen önce bağlantı, hesaptaki lotlar ve (okunabiliyorsa) bakiye **yeniden** okunur:
  onaydan sonra bir hisseyi elle sattıysanız bot olmayan lotu satmaya çalışmaz. Matriks IQ bağlantısı ya da
  aracı kurum oturumu düşerse rapor "emir durumları izlenemedi" der; eski durumu güncelmiş gibi göstermez.
- Telegram grubunda kullanıyorsanız botun gizlilik kipini kapatın (BotFather → `/setprivacy` → Disable);
  aksi hâlde bot düz yazılmış `DUR` mesajını göremez (`/dur` ya da mesaja yanıt olarak yazmak çalışır).
  En güvenlisi botla **özel sohbet** kullanmaktır.
- Resmî tatilleri bot tam bilemez (dinî bayramları `emir-ayar.toml` içindeki `tatiller` listesine yazın);
  tatil ya da yarım gün ise onay mesajına `RED` yazın.
- Gerçek gerçekleşme fiyatları ve miktarları kâğıt portföyden farklı olabilir (kâğıt portföy açılış fiyatını
  varsayar). Onay mesajı, kâğıt portföy ile hesabınız arasındaki lot farklarını gösterir.
- Sınırlar (`[sinirlar]`) 100.000 TL'lik portföye göre ayarlıdır; sermayeniz farklıysa güncelleyin.
- Otomatik emir, hatalı çalıştığında gerçek para kaybettirebilir. Küçük tutarla başlayın.

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
python -m pytest                      # ağ erişimi gerektirmez (emir katmanı sahte Matriks sunucusuyla sınanır)
python -m bistbot doktor              # veri kaynaklarına erişim testi
python -m bistbot gunluk --deneme     # bugünün sinyalleri; hiçbir şey kaydetmez
python -m bistbot veri                # 2015'ten bugüne veriyi indir (≈1 saat)
python -m bistbot backtest            # geçmiş testi + sağlamlık raporu → web/data/backtest.json
python -m bistbot halka-arz           # halka arz keşfi: ön kayıtlı 18 kuralı resmî bültenlerle sınar
python -m bistbot emir --mod deneme   # günün fişini deneme kipinde işle (emir göndermez)
```

| Modül | Görev |
|---|---|
| `bistbot/data/bulletin.py` | Resmî günlük bültenleri indirir ve ayrıştırır |
| `bistbot/data/panel.py` | Tarih × hisse tabloları; kod değişikliklerini (ör. KOZAL → TRALT) birleştirir |
| `bistbot/data/adjust.py` | Düzeltme katsayıları ve eksik sermaye olaylarının onarımı |
| `bistbot/data/isyatirim.py`, `isystore.py`, `macro.py` | İş Yatırım ve TLREF verileri, önbellek |
| `bistbot/data/dataset.py` | Hepsini tek veri nesnesinde birleştirir; mali tablolar gecikmeli devreye girer |
| `bistbot/ipo.py` | Halka arz keşfi: ön kayıt, olay saptama, 18 kuralın sınanması |
| `bistbot/signals.py` | Evren filtresi, özellikler, temel/teknik sütunlar, bileşik puan |
| `bistbot/technical.py` | Teknik göstergeler: eğilim (nakde göre), RSI, MACD, ATR |
| `bistbot/portfolio.py` | Seçim bandı, teknik onay kapısı, ağırlıklar, takvim, rejim filtresi |
| `bistbot/backtest/` | Motor, ölçüler, aşırı uyum istatistikleri, kıyaslar |
| `bistbot/research.py` | Ön kayıtlı deneme seti ve sağlamlık raporu |
| `bistbot/live/` | Günlük çalıştırıcı, durum dosyası, bildirim |
| `bistbot/exec/` | Gerçek emir katmanı: fiş doğrulama, sınırlar, Telegram onayı, Matriks IQ bağlantısı, emir günlüğü |
| `web/` | Panel (tek sayfa, bağımlılıksız) |

**İleriye bakma (look-ahead) güvenceleri:** kararlar `t` günü kapanış verisiyle verilir, işlemler `t+1`
açılışında yapılır; mali tablolar dönem sonundan 75 gün sonra kullanılır ve sonradan yeniden düzenlenen yıl
sonu satırları hiç kullanılmaz; evren ve endeks üyeliği o günkü bültenden alınır. Testler, `t` gününden sonraki
tüm veriler silindiğinde veya değiştirildiğinde `t` günü puanlarının aynı kaldığını doğrular. Canlı kâğıt
portföy, backtest motorunun aynısıyla (tam lot kipinde) ve dondurulmuş kararlarla her gün baştan hesaplanır;
bildirilen işlemler durum dosyasında saklanır ve yeniden hesaplama bunları değiştirirse uyarı verilir.

Günlük çalışma İş Yatırım dosyalarını `.cache/isy-live`, araştırma komutları `.cache/isy` altında tutar;
böylece günlük çalışmanın kısa pencereli dosyaları uzun dönem dosyalarının üzerine yazılmaz.
