# Gölgekuyu — Android paketi

Bu klasör, `golgekuyu.html` oyununu bir Android uygulamasına saran [Capacitor](https://capacitorjs.com) projesidir.
Oyunun kendisi tek yerde durur (`../golgekuyu.html`); paket her derlemede oradan üretilir.

| Yol | Ne işe yarar |
| --- | --- |
| `capacitor.config.json` | Uygulama kimliği (`appId`) ve adı |
| `ads.config.json` | AdMob uygulama kimliği ve ödüllü reklam birimi |
| `scripts/build-web.mjs` | Oyunu `www/` klasörüne hazırlar, yazı tipini pakete gömer |
| `scripts/make-icons.py` | Uygulama simgelerini oyundaki karakterden üretir |
| `fonts/` | Pixelify Sans yazı tipi ve lisansı (SIL OFL 1.1) |
| `android/` | Android Studio / Gradle projesi |
| `store/` | Mağaza görselleri (simge, tanıtım görseli, ekran görüntüleri) ve `listing.md` içinde mağaza metinleri |
| `scripts/make-store-art.cjs` | Mağaza görsellerini oyundan yeniden üretir (Playwright gerekir) |
| `../gizlilik.html` | Gizlilik politikası sayfası (yayınlamadan önce sarı alanları doldurun) |

## Bilgisayarsız: APK'yı GitHub'da derletmek

Depoda `.github/workflows/android.yml` iş akışı var. `golgekuyu.html` ya da bu klasör her değiştiğinde
GitHub paketi kendisi derler.

1. GitHub'da deponun **Actions** sekmesini açın, **Android paketi** iş akışını seçin.
2. En son başarılı çalıştırmayı açın. Sayfanın altındaki **Artifacts** bölümünden
   `golgekuyu-deneme-apk` dosyasını indirin (zip içinden `app-debug.apk` çıkar).
3. APK'yı Android telefona gönderip açın. Telefon "bilinmeyen kaynak" izni isterse onaylayın.

Bu deneme APK'sı yalnızca kendi telefonunuzda denemek içindir; Google Play'e yüklenemez.
Elle çalıştırmak için iş akışı sayfasındaki **Run workflow** düğmesini kullanabilirsiniz.

## Play Store yol haritası

Depoda hazır olanlar: uygulama projesi, otomatik derleme, ödüllü reklam, mağaza görselleri, mağaza metinleri
ve gizlilik politikası taslağı. Geriye kalan adımlar hesap ve kimlik gerektirdiği için sizin yapmanız gerekir:

1. **Google Play geliştirici hesabı** açın (tek seferlik ücretli, kimlik doğrulaması ister).
2. **AdMob hesabı** açın, uygulamayı ekleyin, ödüllü reklam birimi oluşturun; kimlikleri `ads.config.json` dosyasına girin.
3. **Uygulama kimliğine** karar verin ve imza anahtarını oluşturun (aşağıdaki bölüm).
4. **Gizlilik politikasını yayınlayın:** `gizlilik.html` içindeki sarı alanları (ad, e-posta, tarih) doldurun ve
   sayfayı herkese açık bir adreste yayınlayın (örneğin GitHub Pages).
5. **Play Console'da uygulamayı oluşturun:** `store/listing.md` içindeki metinleri ve `store/` görsellerini yükleyin,
   içerik derecelendirmesi, hedef kitle, reklam ve veri güvenliği formlarını doldurun.
6. **Kapalı test:** yeni kişisel hesaplarda Google, yayından önce bir grup test kullanıcısıyla belirli bir süre
   kapalı test yapılmasını ister. Güncel sayı ve süreyi Play Console'da görürsünüz.
7. İmzalı `app-release.aab` dosyasını yükleyin ve incelemeye gönderin.

Ücretler, test şartları ve formlar zamanla değişir; her adımda Play Console'un gösterdiği güncel bilgiyi esas alın.

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

## Ödüllü reklam (AdMob)

Reklam yalnızca Android uygulamasında çalışır; web sürümünde düğmeler hiç görünmez. Oyuncu ölünce
iki seçenek çıkar, ikisi de isteğe bağlıdır:

- **Reklam izle, yarım canla devam et** — sefer başına bir kez. Görünen düşmanlar 2 tur sersemler.
- **Reklam izle, ruhları ikiye katla** — o seferde kazanılan ruhlar iki katına çıkar.

Ödül, reklam sonuna kadar izlenirse verilir. Reklam yüklenemezse oyun normal şekilde devam eder.

`ads.config.json` içindeki kimlikler **Google'ın herkese açık deneme kimlikleridir**: deneme reklamı
gösterir, para kazandırmaz. Yayınlamadan önce:

1. [AdMob](https://admob.google.com) hesabı açın, uygulamayı ekleyin ve bir **ödüllü** reklam birimi oluşturun.
2. `ads.config.json` dosyasında `appId` (içinde `~` olan) ve `rewardedAdUnitId` (içinde `/` olan)
   değerlerini kendi kimliklerinizle değiştirin, `testing` değerini `false` yapın.
3. Kendi telefonunuzda denerken `testing` değerini `true` bırakın. Gerçek reklamlara kendiniz
   tıklamak AdMob hesabının kapatılmasına yol açabilir.
4. Play Console'da uygulamanın **reklam içerdiğini** bildirin ve gizlilik politikanızda reklam
   kimliği kullanımını belirtin. Avrupa'daki kullanıcılara izin penceresi göstermek için AdMob'da
   "Gizlilik ve mesajlaşma" bölümünden bir GDPR mesajı oluşturun; uygulama bunu açılışta kendisi gösterir.

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
