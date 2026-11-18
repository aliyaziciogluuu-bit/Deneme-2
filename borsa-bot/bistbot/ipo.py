"""Halka arz keşfi: yeni halka arz olan paylarda, piyasadan sonradan alan biri için
tekrarlanan ve kazandıran bir kalıp var mı?

ÖN KAYIT (18.11.2026) — bu metin, halka arz sonrası getirilere HİÇ bakılmadan önce yazıldı
----------------------------------------------------------------------------------------
Aşağıdaki tanımlar, kural ailesi, yöntem ve geçme ölçütleri sonuçlar görülmeden sabitlendi.
Sonradan yapılan her değişiklik "keşif sonrası" sayılır ve raporda öyle etiketlenir.
Tek serbestlik: halka arzların *saptanması* (hangi yeni kod gerçek bir halka arzdır) ilk işlem
günü verisine ve bilinen yıllık halka arz sayılarına bakılarak ayarlanabilir; sonraki
getirilere bakılarak ayarlanamaz.

Veri: Borsa İstanbul resmî Pay Piyasası günlük bültenleri (30.11.2015'ten beri). Günlük getiri
``kapanış / önceki kapanış`` ile hesaplanır; bültendeki "önceki kapanış" özsermaye olaylarına
göre düzeltilmiş baz fiyat olduğundan bedelli, bedelsiz ve temettü getiriyi bozmaz.

Tanımlar
* Halka arz: 01.06.2016'dan sonra bültende ilk kez görünen, kod değişikliği / birleşme /
  pazar geçişi olmayan, ana pazarlarda işlem gören pay.
* Kilitli gün: bütün işlemlerin tavan fiyatından geçtiği gün (en düşük = en yüksek = tavan).
  O gün dışarıdan biri gerçekçi olarak alım yapamaz.
* Açılma günü (T): payın tavanın altında işlem gördüğü ilk gün; yani dışarıdan birinin
  alabileceği ilk gün. S: T'den önceki kilitli gün sayısı (tavan serisinin uzunluğu).
* Giriş: sinyal gününü izleyen seansın açılış fiyatı (karar kapanıştan sonra verilir).
  Giriş günü pay tavanda kilitliyse işlem yapılmamış sayılır.
* Çıkış: girişten H seans sonra kapanış fiyatı; o gün pay tabanda kilitliyse satılabildiği
  ilk seansın kapanışı.
* Ölçü: anormal getiri = payın getirisi − aynı günlerde ana pazarlardaki bütün payların eşit
  ağırlıklı getirisi. "Net" rakamlar komisyon (binde 2 + BSMV) ve kaymayı (binde 1) iki
  yönde düşer.

Kural ailesi: 6 sinyal × 3 elde tutma süresi (5, 20, 60 seans) = 18 deneme
  A  Her halka arz, açılma günü T'de.
  B  Tavan serisi yapmış (S ≥ 1) ve T günü önceki kapanışının üstünde ya da aynı kapatmış.
  C  Tavan serisi yapmış (S ≥ 1) ve T günü önceki kapanışının altında kapatmış.
  D  Hiç tavan serisi yapmamış (S = 0).
  E  Uzun tavan serisi yapmış (S ≥ 4).
  F  Dipten alım: T'den sonraki 60 seans içinde kapanışın, işlem görmeye başladığından beri
     görülen en yüksek kapanışın %30 altına ilk kez indiği gün.

Yöntem
1. Keşif örneklemi: ilk işlem günü 01.01.2024'ten önce olan halka arzlar. Doğrulama
   örneklemi: 01.01.2024 ve sonrası. Doğrulama örneklemine 3. adıma kadar bakılmaz.
2. Keşif örnekleminde 18 denemenin her biri için ortalama anormal getiri ve giriş ayına göre
   kümelenmiş t-istatistiği hesaplanır. Aday olmak için: en az 30 işlem, kümelenmiş t ≥ 3,0
   (18 deneme için düzeltilmiş eşik) ve masraflar düşüldükten sonra artı ortalama getiri.
   Aday çıkmazsa sonuç "keşif yok"tur; doğrulama örneklemi yalnızca bilgi için raporlanır.
3. Aday varsa t-istatistiği en yüksek olan tek kural seçilir ve doğrulama örnekleminde BİR KEZ
   sınanır. Geçme ölçütleri: ortalama anormal getiri artı ve kümelenmiş t ≥ 2,0; net ortalama
   getiri aynı günlerdeki gecelik faizden yüksek; medyan anormal getiri artı (sonuç birkaç
   uç değere dayanmıyor).
4. Yalnızca geçen kural bot uyarısına dönüştürülür. Geri kalan her şey "keşif amaçlı" diye
   raporlanır ve işlem kuralı olarak sunulmaz.
"""
from __future__ import annotations

#: İlk işlem günü bu tarihten önce olan kodlar halka arz sayılmaz (veri başlangıcı payı).
FIRST_EVENT_DATE = "2016-06-01"
#: Keşif / doğrulama ayrımı.
HOLDOUT_START = "2024-01-01"
#: Elde tutma süreleri (seans).
HORIZONS = (5, 20, 60)
#: Sinyaller (ön kayıtlı aile).
SIGNALS = ("A", "B", "C", "D", "E", "F")
#: F sinyali: zirveden düşüş eşiği ve T'den sonra aranacak seans sayısı.
DIP_DRAWDOWN = 0.30
DIP_WINDOW = 60
#: Aday ve geçme eşikleri.
MIN_TRADES = 30
DISCOVERY_T = 3.0
HOLDOUT_T = 2.0
