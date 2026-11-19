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

- **E2 – Deniz ve fırtına sahnelerine gerçek dalga sesi (metin editörü, 19 Kasım):** 09 ve 23'te görüntüde dalga var, seste yok. Kanal sahibi Pixabay'den bir "ocean waves / sea storm" kaydı indirirse sesler yeniden kurulur. Görüntü yeniden üretilmez, ses kısa bir işle değişir. Böylece "waves sounds" etiketleri dürüst olur.
  - Değerlendirme: etki 3, emek 2, maliyet yok, risk yok.

- **P2 – Noel'e özel 8–10 saatlik "sleep marathon" (yapımcı):** etki 4, emek 4. Yönetici kararı BEKLET.
  - Neden: Mevcut Noel videolarının görüntüsü yeniden kullanılırsa "yeniden kullanılmış içerik" riski doğar.
  - Ocak'ta, özgün parçalarla bir "winter marathon" olarak yeniden değerlendirilecek.
- **K1 – Uyku sonunda yumuşak iniş: son 20–30 dakikada ses kısılır (kalite kontrol):** etki 2–3. Yönetici kararı BEKLET.
  - Önce K3'ten gelecek tutma verisine bakılacak.

- **Y4 – Uzun video başlık kalıbını çeşitlendirme (kanal yöneticisi, 19 Kasım):** 21–28'in sekiz başlığından altısı aynı kalıpta ("3 Hours [Sıfat] [Mekân] [emoji] [3 öğe] for Sleep"). Bir sahnede, örneğin 28'de, tek kancalı farklı bir başlık denenir ve Analytics'te tıklama oranı karşılaştırılır.
  - Değerlendirme: etki 2–3, emek 1, maliyet yok.

- **Y5 – (YAPILDI: kanal sahibi "Rain & Fireplace Sounds for Sleep" listesini zaten açmış; yeni yağmur sahneleri buna eklenecek) "Rain Around the World" oynatma listesi (kanal yöneticisi, 19 Kasım):** Yağmur sahneleri tek listede toplanır (06 kafe, 22 Tokyo, 24 kanal, 25 orman, 28 kiraz çiçeği). Tek bir sahneyi bulan izleyici art arda başkasını izler ve izlenme saati artar. Y2 Noel listesinin yağmur karşılığı.
  - Değerlendirme: etki 2–3, emek 1, maliyet yok.

- **Y6 – "Japan at Night 🏯" oynatma listesi (kanal yöneticisi, 19 Kasım):** 10 Japon bahçesi, 22 Tokyo, 26 dağ tapınağı ve 28 kiraz çiçeği tek listede toplanır. Bir Japon sahnesini bulan izleyici ötekileri de izler.
  - Değerlendirme: etki 2, emek 1, maliyet yok.

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

## Reddedilen

- **P3 – Aynı görüntüden farklı ses varyantlarıyla ayrı videolar (yapımcı).** Ofis eledi, kanal sahibi de 18 Kasım'da eledi.
  - Neden: YouTube'un yeniden kullanılmış / tekrarlayan içerik kuralı ve İş Ortağı incelemesi için çok yüksek risk. Kazancı küçük, kayıp bütün hedef olabilir.
- **Y1 – Shorts açıklamasına ve yorumuna bağlantı (metin yazarı).** Ofis eledi, kanal sahibi de 18 Kasım'da eledi.
  - Neden: Shorts'taki bağlantılar tıklanamıyor. Tek köprü "İlgili video", o da zaten kullanılıyor. Yararlı kısmı Y3'e katıldı.
