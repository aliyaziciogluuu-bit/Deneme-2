# Öneri kutusu

Ofisteki herkes kanalı büyütecek fikirleri buraya önerir: çalışanlar, denetçiler ve yönetici. Fikirler değerlendirilip kanal sahibine sunulur. Son kararı kanal sahibi verir.

## Nasıl çalışır?

1. **Öneri:** Her ajan raporunun sonunda kendi alanından fikir önerir:
   - görsel, hareket, ses
   - başlık, öykü, SEO
   - kalite, iş akışı
   - strateji, yeni içerik türü
   Patron her fikri aşağıdaki "Bekleyen" bölümüne ekler.
2. **Değerlendirme:** Kanal yöneticisi bekleyen fikirleri puanlar:
   - **Etki:** izlenme, abone ya da gelire katkı (1–5)
   - **Emek:** ne kadar iş (1–5, düşük iyi)
   - **Maliyet:** para harcar mı?
   - **Risk:** kanal kuralları, özgünlük, yanıltıcılık
   Gerekçeli bir öneri yazar: "sun", "beklet" ya da "ele".
3. **Sunum:** Patron en iyi 1–3 fikri kanal sahibine kısa ve anlaşılır bir dille sunar. Bu, teslimlerle birlikte ya da kullanıcı sorduğunda olur.
4. **Karar:** Ofisin elemek istediği fikirler de kanal sahibine tek satırla gösterilir; kesin eleme kanal sahibinin onayıyla olur. Kanal sahibinin kararı "Onaylanan" ya da "Reddedilen" bölümüne yazılır. Reddedilen fikir gerekçesiyle kalır, aynı fikir tekrar önerilmez.

---

## Bekleyen

- **K1 – Uyku sonunda yumuşak iniş: son 20–30 dakikada ses kısılır (kalite kontrol):** etki 2–3. Yönetici kararı BEKLET.
  - Önce K3'ten gelecek tutma verisine bakılacak.

## İç işler (patron uygular, kanal sahibine sunulmaz)

- **E1 – Vaat denetimi betiği (metin editörü, 19 Kasım):** Yükleme metnindeki kelimeleri (waves, wind, thunder, sounds, BGM, lofi, music, sweeps, drifts) `sahne.json` > `ses` ve hareket listesiyle otomatik karşılaştırıp uyarı veren betik. K2 `onay.py` içine katılacak.
- **M1 – Doğrulanabilir öğe listesi (metin yazarı, 19 Kasım):** Her sahne için nesne, konum, hareket var/yok ve ses var/yok listesi. Yapımcı taslaktan sonra çıkarır, metin yazarı ona bakarak yazar.

- **K2 – `onay.py`:** tek komutlu yayın öncesi otomatik kontrol (kalite kontrol). Etki 3.
  - Ek (kalite kontrol, 19 Kasım): `--titreme` seçeneği mum ve fener bölgelerinin parlaklık aralığını ölçüp "flicker" iddiasını rakamla doğrular.
  - Ek (kanal yöneticisi, 19 Kasım): Shorts için `bas` ve `son` kadrajlarının iki küçük kırpım karesini üretsin. Böylece yazıdaki öğenin iki uçta da görünüp görünmediğine bakılır.
- **Y3 – Shorts kancalarını çeşitlendirme ve deneme (metin yazarı):** POV'un yanında soru, talimat ve rakam kalıpları denenecek, sonuçlar `ilerleme.md`'de izlenecek. Ekran yazısıyla uyum kuralı korunacak.
- **P1 – Shorts sonuna "Full 3-hour version on the channel" yazısı (yapımcı):** Yalnızca İlgili video bağlı 2–3 Shorts'ta pilot. Sağ alt köşe kullanılmayacak.

## Sunulan (kanal sahibinin kararı bekleniyor)

_(şu an yok)_

## Onaylanan

- **Y2 – "Christmas Sleep Windows 🎄" oynatma listesi (metin yazarı).** Kanal sahibi 18 Kasım'da onayladı. Liste metni `kanal/noel_listesi.md` dosyasında. Aralık'taki Noel videolarının günlük talimatlarına "listeye ekle" notu kondu.
- **K3 – Haftalık tutma verisi (kalite kontrol).** Kanal sahibi 18 Kasım'da onayladı. Her çarşamba günlük talimatta hatırlatılıyor. Veri `ilerleme.md` dosyasındaki tutma tablosuna işlenir.

- **Başlık ve küçük resimde "4K" etiketi.** Önerisi kanal sahibinden geldi (18 Kasım). Uygulandı.
- **5 dilde başlık ve açıklama çevirisi.** Uygulandı. Etkisi birkaç hafta sonra Analytics > Coğrafya'da ölçülecek.
- **Çeşitli sahneler (21–28).** Önerisi kanal yöneticisinden geldi: Ocak'ta üç yağmur + soba videosu art arda geliyordu. Uygulandı.

- **E2 – Deniz ve fırtına sahnelerine gerçek dalga sesi (metin editörü).** Uygulandı (19 Kasım): 09 ve 23'e ayrı dalga katmanı eklendi; kanal sahibi dinleyip "duyuluyor" dedi.
- **Y4 – Uzun video başlık kalıbını çeşitlendirme (kanal yöneticisi).** Kanal sahibi 19 Kasım'da onayladı. 28 çay evinin başlığı tek kancalı yapıldı ("Spring Rain on the Cherry Blossoms 🌸 3 Hours in a Quiet Japanese Tea House with Irori Embers"). 13 Şubat'ta yayınlanacak; 27 Şubat'ta tıklama oranı öteki videolarla karşılaştırılacak. Eski başlık: "3 Hours Cherry Blossom Tea House 🌸🌧️ Spring Rain, Sakura & Irori Embers for Sleep & Study" (değişiklik 19 Kasım). Karşılaştırırken gösterimin nereden geldiğine de (arama / önerilen) bakılacak; yeni başlıkta "Sleep" yok. Sonuç zayıfsa yedek: "3 Hours Spring Rain on Cherry Blossoms 🌸 Quiet Japanese Tea House & Irori Embers for Sleep".
- **Y5 – Yağmur oynatma listesi.** Kanal sahibi "Rain & Fireplace Sounds for Sleep" listesini zaten açmıştı. 22, 23, 24, 25 ve 28'in yayın günü talimatına "listeye ekle" notu kondu.
- **Y6 – "Japan at Night 🏯" oynatma listesi (kanal yöneticisi).** Kanal sahibi 19 Kasım'da onayladı. Liste metni `kanal/japon_listesi.md` dosyasında. 5 Aralık'ta (Japon bahçesi) açılacak; 22, 26 ve 28'in yayın günlerine "listeye ekle" notu kondu.

- **P2 – 8 saatlik Noel videosu (yapımcı).** Kanal sahibi 22 Kasım'da onayladı (rakip kanalın 8 saatlik videosu 6 günde 262 bin izlendi). Var olan görüntü kullanılmayacak; tamamen yeni bir sahne (Norveç fiyordu kulübesi) yeni karanlık ışık tarzıyla yapılacak. İstem: `kanal/noel_8saat_istemi.md`.
- **Yeni görsel tarzı ve yazısız küçük resim (D).** Kanal sahibi 22 Kasım'da "bundan sonraki videoları böyle yapalım" dedi. Kurallar SKILL.md > Görsel tarzı bölümünde.

## Reddedilen

- **P3 – Aynı görüntüden farklı ses varyantlarıyla ayrı videolar (yapımcı).** Ofis eledi, kanal sahibi de 18 Kasım'da eledi.
  - Neden: YouTube'un yeniden kullanılmış / tekrarlayan içerik kuralı ve İş Ortağı incelemesi için çok yüksek risk. Kazancı küçük, kayıp bütün hedef olabilir.
- **Y1 – Shorts açıklamasına ve yorumuna bağlantı (metin yazarı).** Ofis eledi, kanal sahibi de 18 Kasım'da eledi.
  - Neden: Shorts'taki bağlantılar tıklanamıyor. Tek köprü "İlgili video", o da zaten kullanılıyor. Yararlı kısmı Y3'e katıldı.
