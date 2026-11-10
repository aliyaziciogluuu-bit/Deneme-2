# Tarih kanalı

Yüz göstermeden, seslendirme + tarihî görsel formatında YouTube videoları üreten küçük bir düzenek.

## Klasörler

| Yol | İçerik |
|---|---|
| `01-dans-vebasi/` | İlk video: 1518 Dans Vebası |
| `01-dans-vebasi/video.mp4` | Yüklemeye hazır video (1920x1080) |
| `01-dans-vebasi/kapak.jpg` | Küçük resim (1280x720) |
| `01-dans-vebasi/altyazi.srt` | YouTube'a yüklenebilir altyazı dosyası |
| `01-dans-vebasi/yukleme.txt` | Başlık, açıklama, bölümler ve etiketler |
| `01-dans-vebasi/senaryo.json` | Metin (altyazı ve okunuş) |
| `01-dans-vebasi/cekimler.json` | Hangi cümlede hangi görsel ve kamera hareketi |
| `01-dans-vebasi/KAYNAKLAR.md` | Görsellerin kaynağı ve lisans durumu |
| `seslendir.py` | Senaryoyu seslendirir ve sonucu doğrular |
| `video.py` | Ses + görsel + altyazıdan videoyu üretir |

## Yeni video yapmak

1. `01-dans-vebasi` klasörünü kopyalayın (ör. `02-yeni-konu`).
2. `senaryo.json` içindeki metni yazın. Yabancı adlar ve sayılar için `ses` alanına okunuşunu yazın.
3. Görselleri `gorseller/` klasörüne koyun, `cekimler.json` içinde cümlelere eşleyin.
4. `python video.py 02-yeni-konu --onizleme` ile kadrajları kontrol edin.
5. `python seslendir.py 02-yeni-konu` ile seslendirin (ya da kendi sesinizi kaydedin).
6. `python video.py 02-yeni-konu` ile videoyu üretin.

## Kendi sesinizi kullanmak

`seslendir.py` yerine her cümleyi ayrı ayrı kaydedip `ses/000.wav`, `ses/001.wav` ... adlarıyla
kaydedin (mp3 ve m4a da olur). `video.py` süreleri ve altyazı zamanlamasını kayıtlara göre kendisi ayarlar.

## Lisans notları

- **Görseller:** Yalnızca kamu malı (telif süresi dolmuş) eserler kullanılıyor. Her video klasöründeki
  `KAYNAKLAR.md` dosyasına bakın.
- **Seslendirme:** Chatterbox Multilingual modeliyle üretildi (MIT lisansı, ticari kullanıma açık).
  Model, üretilen sese duyulmayan bir yapay zekâ filigranı ekler.
- **Müzik:** Videoda müzik yok. Eklemek isterseniz YouTube Ses Kitaplığı'ndaki telifsiz parçaları kullanın.
