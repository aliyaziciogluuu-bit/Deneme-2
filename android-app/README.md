# Gölgekuyu — Android paketi

Bu klasör, `golgekuyu.html` oyununu bir Android uygulamasına saran [Capacitor](https://capacitorjs.com) projesidir.
Oyunun kendisi tek yerde durur (`../golgekuyu.html`); paket her derlemede oradan üretilir.

| Yol | Ne işe yarar |
| --- | --- |
| `capacitor.config.json` | Uygulama kimliği (`appId`) ve adı |
| `scripts/build-web.mjs` | Oyunu `www/` klasörüne hazırlar, yazı tipini pakete gömer |
| `scripts/make-icons.py` | Uygulama simgelerini oyundaki karakterden üretir |
| `fonts/` | Pixelify Sans yazı tipi ve lisansı (SIL OFL 1.1) |
| `android/` | Android Studio / Gradle projesi |
| `store/icon-512.png` | Google Play mağaza simgesi |

## Bilgisayarsız: APK'yı GitHub'da derletmek

Depoda `.github/workflows/android.yml` iş akışı var. `golgekuyu.html` ya da bu klasör her değiştiğinde
GitHub paketi kendisi derler.

1. GitHub'da deponun **Actions** sekmesini açın, **Android paketi** iş akışını seçin.
2. En son başarılı çalıştırmayı açın. Sayfanın altındaki **Artifacts** bölümünden
   `golgekuyu-deneme-apk` dosyasını indirin (zip içinden `app-debug.apk` çıkar).
3. APK'yı Android telefona gönderip açın. Telefon "bilinmeyen kaynak" izni isterse onaylayın.

Bu deneme APK'sı yalnızca kendi telefonunuzda denemek içindir; Google Play'e yüklenemez.
Elle çalıştırmak için iş akışı sayfasındaki **Run workflow** düğmesini kullanabilirsiniz.

## Google Play'e yüklemeden önce

1. **Uygulama kimliğini belirleyin.** Şu an `com.golgekuyu.app`. İlk yüklemeden sonra bir daha
   değiştirilemez. Değiştirecekseniz `capacitor.config.json`, `android/app/build.gradle`
   (`namespace` ve `applicationId`), `android/app/src/main/res/values/strings.xml` dosyalarını ve
   `android/app/src/main/java/` altındaki klasör yolunu birlikte güncelleyin.
2. **İmza anahtarı oluşturun** (bir kez yapılır; Java kurulu bir bilgisayarda):

   ```sh
   keytool -genkeypair -v -keystore yayin.jks -alias golgekuyu -keyalg RSA -keysize 2048 -validity 10000
   ```

   Bu dosyayı ve parolasını güvenli bir yerde saklayın, depoya **eklemeyin**. Kaybederseniz
   uygulamayı güncelleyemezsiniz.
3. **Anahtarı GitHub'a gizli değişken olarak ekleyin** (Settings → Secrets and variables → Actions):

   | Gizli değişken | Değer |
   | --- | --- |
   | `ANDROID_KEYSTORE_BASE64` | `base64 -w0 yayin.jks` komutunun çıktısı |
   | `ANDROID_KEYSTORE_PASSWORD` | Anahtar deposu parolası |
   | `ANDROID_KEY_ALIAS` | `golgekuyu` |
   | `ANDROID_KEY_PASSWORD` | Anahtar parolası |

   Bunlar tanımlıyken iş akışı ayrıca `golgekuyu-yayin-aab` adında imzalı bir `app-release.aab`
   üretir. Google Play Console'a yüklenecek dosya budur.
4. **Her yeni sürümde** `android/app/build.gradle` içindeki `versionCode` değerini bir artırın
   (`versionName` kullanıcıya görünen sürüm adıdır).
5. Play Console ayrıca gizlilik politikası adresi, ekran görüntüleri, içerik derecelendirmesi ve
   mağaza simgesi (`store/icon-512.png`) ister.

## Bilgisayarda derlemek

Node.js 22+, JDK 21 ve Android Studio (Android SDK 36) gerekir.

```sh
cd android-app
npm ci
npm run sync        # oyunu www/ içine hazırlar ve Android projesine kopyalar
npm run open        # projeyi Android Studio'da açar
# ya da komut satırından:
cd android && ./gradlew assembleDebug
```

`golgekuyu.html` değiştikten sonra `npm run sync` komutunu yeniden çalıştırmak yeterlidir.

## Uygulamaya özgü davranışlar

- Ekran dikey kilitlidir.
- Geri tuşu açık pencereyi kapatır, sefer sırasında karakter ekranını açar, ana menüde uygulamayı arka plana alır.
- Oyun ilerlemesi cihazda saklanır; uygulama arka plana geçerken sefer kaydedilir.
- Yazı tipi pakete gömülüdür, oyun internet olmadan çalışır.
