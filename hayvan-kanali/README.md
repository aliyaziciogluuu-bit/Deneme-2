# Hayvan kanalı (ikinci kanal)

Evin, bahçenin ve köyün çevresinde yaşayan ama yanlış tanınan hayvanları anlatan, yüz göstermeyen Türkçe anlatımlı kanal.
Dream Window ve tarih-kanali düzeninden türetildi; kanal kimliği, ad önerileri ve yayın ilkeleri `kanal/kanal_aciklamasi.md` içinde.

## Klasörler

| Yol | İçerik |
|---|---|
| `01-sagir-yilan/` | İlk video: sağır yılan |
| `<video>/senaryo.json` | Metin, başlık, açıklama, kaynaklar, etiketler, kapak yazısı, ambiyans |
| `<video>/gorseller.json` | Görsel istemleri → `gorseller/` (seçilenler), `adaylar/` (tüm adaylar) |
| `<video>/klipler.json` | Animasyonlu çekimler → `klipler/*.mp4` |
| `<video>/cekimler.json` | Her cümlede hangi görsel/klip ve hangi kamera hareketi |
| `<video>/ses/` | Cümle cümle anlatım ve doğrulama raporu |
| `<video>/video.mp4, kapak.jpg, altyazi.srt, yukleme.txt` | Yüklemeye hazır çıktılar |
| `<video>/son_kontrol.txt` | Son testlerin sonucu |
| `sesler/` | Ortak doğa sesi kütüphanesi (lisansları `sesler/KAYNAKLAR.md`) |
| `kanal/` | Kanal kimliği, imza, konu listesi, etkileşim planı, gelir eşiği takibi |

## Yeni video yapmak (sırayla)

1. Klasör aç (ör. `02-ev-kertenkelesi`), `senaryo.json`'u yaz. Sayıları ve Latince adları `ses` alanında okunuşuyla yaz.
2. **Bilgi kontrolü:** senaryoyu bağımsız bir kontrolcüye (ayrı bir Claude ajanı) denetlet, bulguları düzelt.
3. `python gorsel.py 02-... --onay` → `adaylar/secim.jpg`'yi incele. Anatomisi yanlış (ör. bacak çizilmiş) adayı kullanma,
   istemi düzeltip yeniden üret. Sonra `python gorsel.py 02-... --sec ad=N ...`
4. `python klip.py 02-... --onay` (yalnızca açılış ve kilit anlar; kareleri gözle kontrol et)
5. `python seslendir_bulut.py 02-...` (Gemini "Charon" sesi, sahne sahne; her cümle Whisper ile doğrulanır)
6. `cekimler.json`'u yaz, `python video.py 02-... --onizleme` ile kadrajları kontrol et
7. `python video.py 02-...` → video, kapak, altyazı, yükleme metni
8. `python son_kontrol.py 02-...` → **hepsi GEÇTİ demeden yükleme yapma**

`seslendir_bulut.py`, `son_kontrol.py` Whisper kullandığı için faster-whisper kurulu bir Python ortamında çalıştırılır:
`pip install faster-whisper soundfile numpy pillow`.

## Maliyet (video başına, Kasım 2026)

| Kalem | Araç | Yaklaşık |
|---|---|---|
| Görseller (19 × 2 aday + düzeltmeler) | Replicate, Flux 1.1 Pro Ultra | 2,5–3 $ |
| Animasyon (6 × 5 sn) | Replicate, Kling 2.5 Turbo Pro | 2,1 $ |
| Anlatım | Replicate, Gemini 3.8 Flash TTS | < 0,5 $ |
| Doğa sesi, kurgu, kapak, testler | Wikimedia Commons (kamu malı), kendi betiklerimiz | ücretsiz |

Ücretsiz Chatterbox sesi kör testte belirgin aksan ve 43 kelimede 6 okuma hatası verdi; bu yüzden anlatım ücretli modelle yapılıyor.
Replicate hesabında kredi 5 $'ın altına düşünce dakikada 6 istek sınırı uygulanıyor; betikler bu durumda bekleyip yeniden dener.

## Lisans ve beyan
- Görseller ve klipler yapay zekâ ile üretilmiş çizimlerdir (gerçekçi bir kişiyi ya da olayı taklit etmez).
- Anlatım yapay zekâ sesiyle yapılır. YouTube'un "değiştirilmiş veya yapay içerik" beyanı gerçek bir kişiyi/olayı gerçekçi
  biçimde taklit eden içerik için zorunludur; çizim + anlatıcı sesi bu kapsamda değildir. Açıklamadaki beyan satırı
  `senaryo.json` → `beyan` alanından değiştirilebilir.
