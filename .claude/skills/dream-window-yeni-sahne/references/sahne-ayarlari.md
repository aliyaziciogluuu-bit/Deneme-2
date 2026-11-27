# sahne.json ayarları ve bilinen düzeltmeler

Bütün koordinatlar **kaynak görselin pikseli** cinsindendir (görseller 1672×941). Kutular `[x0, y0, x1, y1]` biçimindedir. Örnek almak için var olan sahnelere bak; aşağıda hangi sahnede kullanıldığı yazıyor.

## Temel

- `"dongu_sn": 96`: Her sahnede bulunmalı. Görüntü 96 saniyede bir başa döner, 3 saatlik videoda tekrar fark edilmez.
  - 24 saniyelik eski döngü tekrar testinden geçmez (aurora olayı).
- `"gorsel"`, `"gorsel_4k"`: `gorsel_4k` dosyası `buyut4k.py` ile üretilir. Replicate'te görsel başına yaklaşık 0,005 $ tutar ve `uret` adımında kendiliğinden çalışır.
- `"yagis"`: `"kar"` ya da `"yagmur"`.
- `"acilis_yazi"`: Açılıştaki kanal adı ve alt kelimeler. `--noel` ile CHRISTMAS eklenir.

## Pencere (`cam`)

- `kutular`: Kar ya da yağmurun yalnızca göründüğü cam alanları. Koyu pencereler otomatik bulunamayabilir; o zaman elle gir (örnek: 14, 18).
- `haric`: Pencere kutusuna giren mobilya, koltuk, perde gibi alanlar. Çokgen noktaları listesi olarak verilir (örnek: 06, 16, 18). Koltuğun önünde kar yağıyorsa buraya ekle.
- `yesil_haric`: Camın arkasındaki yeşil bitkilere yağmur damlası düşmesin diye (örnek: 18).
- `daire`: Yuvarlak pencere (örnek: 09).
- `esik`, `temizlik`: Cam maskesinin hassasiyeti. Genelde dokunma.

## Ateş (`ates` ve `ates_klip`)

- `ates.kutu`: Alevlerin bulunduğu kutu. Otomatik algılama bazen lambayı, masayı ya da koltuğu ateş sanıyor. Hata 19'da koltukta, 20'de fenerde oldu. **Kutuyu yalnızca alevlerin üstüne elle çiz**, `ates_klip.kutu` da aynı alanı göstermeli.
- `ates_klip.dosya` / `kaynak`: Hangi sahnenin ateş klibinin kullanılacağı (`--ates-klip`).
- `ates_klip.karisik: true`: Klip rastgele noktalardan ileri oynatılan parçalarla, yumuşak geçişle karıştırılır. Ateş hiçbir zaman aynı şekilde tekrar etmez. **Her ateşte açık olmalı.**
- `ates_klip.cubuk_koru: true` (`cubuk_esik`): Sobanın kapağındaki koyu metal çubuklar ateş klibinin önünde kalır. Camlı sobalarda kullan (örnek: 15, 18, 19).
- Kıvılcım (`kivilcim`), ölçek, taban ve tepe genelde otomatik değerlerle iyi çalışır.

## Diğer canlandırmalar

- `buhar`: `{"kutu": [...], "genlik": 0.7}`. Fincan, çaydanlık ya da kase üstünde ince buhar (örnek: 13, 16).
- `su`: `{"kutu": [...], "esik": ...}`. Göl, gölet ya da nehir yüzeyinde hafif dalgalanma (örnek: 10, 20).
- `isiklar`: Mum, lamba ve fener titreşimi. Otomatik bulunur; yanlış nesneye oturduysa listeden çıkar.
- `pirilti`: Yılbaşı ışıkları, süsler ve havai fişekler için ışıltı (örnek: 07, 14). Yalnızca `--noel` sahnelerinde. Aksi hâlde masadaki nesnelere de pırıltı düşebiliyor.
- `sallanti`: `{"genlik": ..., "olcek": ...}`. Tren vagonunda hafif sallanma (örnek: 12, 17). Ses için tren kaydı (`ses.zemin`) gerekir. Frekanslar döngüyle aralarında asal seçilir; elle değiştirme.
- `ek_klipler`: Kuzey ışıkları ve deniz gibi özel klipler (örnek: 09, 11).
  - Kuzey ışıklarında `zaman_bukme` kullanılır: değişken hızda ileri-geri oynatma.
  - Denizde `karisik` kullanılır: 8 sn parçalar, 1,5 sn geçiş. Daha kısa parçalar bulanık görünüyordu.

## Ses (`ses`)

- `ates`: Tek dosya ya da liste. Liste verilirse kayıtlar karıştırılır.
  - Seçenekler: `ses_kaynak/ates.ogg` (Wikimedia, CC BY) ve `../sesler/ates_somine_yumusak.mp3`, `ates_somine_gur.mp3`, `ates_gece.mp3` (Pixabay).
- `zemin`, `zemin_ek`: Yağmur kayıtları, eşit seviyede karıştırılır (`../sesler/yagmur_cam.mp3`, `yagmur_hafif.mp3`).
- `ates_duzey`, `ates_tavan`, `ates_govde`, `ates_denge`: Ateş sesinin yüksekliği ve karakteri. Benzer bir sahneden kopyala.
- Uzun video −24 LUFS'a, Shorts −16 LUFS'a otomatik ayarlanır.

## Shorts

- `shorts` / `shorts2`: `{"bas": x, "son": x, "tur": 2, "baslik": "...", "alt": "...", "ses_kazanc": 1.5}`.
  - Dikey kadraj, `bas` noktasından `son` noktasına kayıp geri döner (x, kaynak pikseli).
  - Kadraj genişliği yaklaşık 529 piksel, bu yüzden merkez 265 ile 1407 arasında olmalı.
  - İlk saniye izleyiciyi tutar: `bas` en etkileyici yerde olsun (genelde karlı/yağmurlu pencere).
- `shorts3` (isteğe bağlı, eski Shorts'lardan farklı bir kadraj için):
  - Ek ayarlar: `"yakin": 1.6`, `"y"` / `"y_son"` (dikey merkez ve dönüş noktası) ve `"ses_tohum": 5`.
  - Komut: `python3 shorts.py <sahne> shorts3 --4k` (net görüntü için sahne 4K görselden çizilir).
- Her Shorts sonrası: `python3 kontrol.py <sahne>/<ad>.mp4 --sure 48 --en-az 48`.

## Bilinen tuzaklar

- **Aynı anda iki ağır iş çalıştırma.** Bellek dolar ve biri öldürülür. 1080p ile 4K aynı geçici klasörü paylaştığında bir keresinde 4,6 GB bozuk dosya çıktı. Artık her işin kendi `_gecici_*` klasörü var, yine de sırayla çalıştır.
- **Disk:** Dolarsa son birleştirme yarıda kesilir. Bozuk `video_3saat.mp4` dosyasını sil ve `uret` komutunu yeniden çalıştır. Hazır parçalar yeniden kullanılır.
- **Süre:** Uzun video en az 10800 sn olmalı. Tur sayısı yukarı yuvarlanır; eski bir dosya 3 sn kısa çıkarsa düzelt.
- **Boyut:** Sohbetle gönderme sınırı 400 MiB. Aşarsa ses bit hızını 72–80 kbps'ye düşür (`--sesdegistir`).
