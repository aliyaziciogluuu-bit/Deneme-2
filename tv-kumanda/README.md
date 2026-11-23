# 📺 Philips TV Kumandası

Philips **Android TV / Google TV** için telefondan kullanılan kumanda ve Ambilight paneli.

## Neler yapar?

- **Kumanda:** güç, ana ekran, kaynak, yön tuşları, OK, geri, ses (basılı tutunca hızlı), sessiz, kanal,
  oynat/duraklat, rakamlar, renkli tuşlar, altyazı
- **Ses kaydıracı:** sesi tek hareketle istediğin seviyeye getirir
- **Ambilight:** aç/kapat; videoyu takip et, rahat (göz dostu), canlı, oyun, müziğe göre, ekolayzır, lav, okyanus
- **Sabit Ambilight rengi:** sinema, gece, sıcak beyaz gibi hazır renkler ya da istediğin renk, ayarlanabilir parlaklıkla
  (TV'nin kendi kumandasında bu yok)
- **Uygulamalar:** TV'deki tüm uygulamalar (YouTube, Netflix, tabii…) tek dokunuşla açılır
- **Uyku zamanlayıcısı:** 15 dk – 1,5 saat sonra Ambilight'ı ve TV'yi kapatır

## Gerekenler

- TV ile **aynı Wi-Fi ağına** bağlı bir cihaz. İkisinden biri olabilir:
  - **Bilgisayar** (Windows, Mac ya da Linux), Python 3 kurulu olmalı. Windows'ta Microsoft Store'dan "Python 3" kurun.
  - **Android telefon**, Termux uygulamasıyla (F-Droid'den). Bilgisayar gerekmez.
- Ek bir kütüphane gerekmez.

## Kurulum

### Bilgisayarda

1. `philips_kumanda.py` dosyasını bilgisayara indirin.
2. Dosyanın olduğu klasörde terminal (Windows'ta Komut İstemi) açıp çalıştırın:

   ```
   python3 philips_kumanda.py
   ```

   Windows'ta komut `python philips_kumanda.py` olabilir.
3. Ekranda yazan adresi (ör. `http://192.168.1.20:8000`) **telefonun tarayıcısında** açın.

### Yalnızca Android telefonla (Termux)

```
pkg install python
python philips_kumanda.py
```

Sonra telefonun tarayıcısında `http://localhost:8000` adresini açın.

### İlk eşleştirme (bir kez)

1. TV açık olsun.
2. Sayfada **"Ağda TV ara"**ya basın ve çıkan TV'yi seçin.
   Bulamazsa IP adresini elle girin. TV'de bulmak için: *Ayarlar → Kablosuz ve ağlar → Kablolu veya Wi-Fi → Ağ ayarlarını göster*.
3. TV ekranında 4 haneli bir kod çıkar. Kodu sayfaya yazıp **Eşleştir**'e basın.

Eşleşme `philips_ayar.json` dosyasına kaydedilir; program her açıldığında yeniden eşleştirmek gerekmez.

**İpucu:** Sayfayı tarayıcının menüsünden **"Ana ekrana ekle"** ile telefona uygulama gibi ekleyebilirsiniz.

## Sorun giderme

| Sorun | Çözüm |
|---|---|
| TV bulunamıyor | TV ile cihaz aynı Wi-Fi'da mı? Misafir ağı ya da 5 GHz / 2,4 GHz ayrımı engel olabilir. IP'yi elle girin. |
| TV kapalıyken açılmıyor | TV'de *Ayarlar → Kablosuz ve ağlar → Wi-Fi ile aç (WoWLAN)* seçeneğini açın. |
| "TV bu kumandayı tanımıyor" | ⚙️ Ayarlar → *Başka TV ile eşleştir* ile yeniden eşleştirin. |
| Bir Ambilight stili çalışmıyor | Bazı modellerde her stil bulunmaz; başka bir stil deneyin. |
| Uyku zamanlayıcısı çalışmadı | Programın (bilgisayarda ya da Termux'ta) açık kalması gerekir. |

## Güvenlik notu

Panel yalnızca ev ağınızdan açılır ve şifre sormaz: aynı Wi-Fi'daki herkes TV'yi kontrol edebilir.
TV kendi imzaladığı bir sertifika kullandığı için, program yalnızca TV bağlantısında sertifika doğrulaması yapmaz.

Saphi ya da Titan OS çalışan (Play Store olmayan) Philips TV'lerde test edilmedi.
