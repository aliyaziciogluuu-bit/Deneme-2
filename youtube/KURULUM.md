# Bir kerelik kurulum (Patron)

Bu adımlar yalnızca bir kez yapılır; sonrasında videolar her gün kendiliğinden üretilip yüklenir.
Şifrenizi, doğrulama kodlarınızı ve aşağıdaki gizli anahtarları **kimseyle paylaşmayın, sohbete de yazmayın.**
Hepsi yalnızca GitHub'ın "Secrets" bölümüne girilir.

Toplam süre: yaklaşık 30–40 dakika. Bilgisayardan yapın.

## 1. İki YouTube kanalı açın (10 dk)

1. youtube.com'a Google hesabınızla girin.
2. Profil resmi › **Ayarlar** › **Kanal ekleyin veya yönetin** › **Kanal oluştur**.
   Bu bir "marka hesabı" olur; kişisel adınız görünmez.
3. İki kanal açın:
   - **İngilizce kanal** · ad önerileri: *Today in History · 60s*, *One Minute Back*, *Daily Time Capsule*
   - **Türkçe kanal** · ad önerileri: *Tarihte Bugün · 1 Dakika*, *Bir Dakikada Tarih*
   Ad başka bir kanalda kullanılıyorsa farklı bir ad seçin.
4. Kanal açıklaması, profil resmi ve kapak görseli için bana kanal adlarını söyleyin; ben hazırlarım.

## 2. Google'da yükleme izni (15 dk)

1. **console.cloud.google.com** › üstte proje seçici › **Yeni proje** › ad: `tarihte-bugun` › Oluştur.
2. Sol menü › **API'ler ve Hizmetler** › **Kitaplık** › "YouTube Data API v3" › **Etkinleştir**.
3. Sol menü › **OAuth izin ekranı** (bazı hesaplarda "Google Auth Platform"):
   - Kullanıcı türü: **Harici (External)**
   - Uygulama adı: `Tarihte Bugün Yükleyici`, destek e-postası: kendi e-postanız
   - Kitle (Audience) bölümünde **Uygulamayı yayınla (Publish app)** düğmesine basın.
     *Önemli: "Test" durumunda kalırsa Google izni 7 günde bir siler ve yükleme durur.*
4. Sol menü › **Kimlik bilgileri** › **Kimlik bilgisi oluştur** › **OAuth istemci kimliği**:
   - Uygulama türü: **Web uygulaması**
   - Yetkilendirilmiş yönlendirme URI'si: `https://developers.google.com/oauthplayground`
   - Oluştur › çıkan **İstemci kimliği** ve **İstemci gizli anahtarı**nı bir kenara not edin.

## 3. Her kanal için izin anahtarı alın (5 dk)

1. **developers.google.com/oauthplayground** adresini açın.
2. Sağ üstteki dişli simgesi › **Use your own OAuth credentials** › 2. adımdaki iki bilgiyi yapıştırın.
3. Soldaki kutuya şunu yazın: `https://www.googleapis.com/auth/youtube.upload` › **Authorize APIs**.
4. Google hesabınızı seçin, ardından **İngilizce kanalı** seçin.
   "Google bu uygulamayı doğrulamadı" uyarısı çıkarsa: **Gelişmiş** › **Tarihte Bugün Yükleyici'ye git** › İzin ver.
   (Uygulama sizin; uyarı Google'ın inceleme yapmadığını söyler.)
5. **Exchange authorization code for tokens** düğmesine basın. Çıkan **Refresh token** değerini not edin (İngilizce kanal).
6. 3–5. adımları **Türkçe kanalı** seçerek tekrarlayın (Türkçe kanal için ikinci refresh token).

## 4. Anahtarları GitHub'a girin (5 dk)

GitHub'da depo › **Settings** › **Secrets and variables** › **Actions** › **New repository secret**. Dört kayıt:

| Name | Değer |
|---|---|
| `YT_CLIENT_ID` | İstemci kimliği |
| `YT_CLIENT_SECRET` | İstemci gizli anahtarı |
| `YT_REFRESH_TOKEN_EN` | İngilizce kanalın refresh token'ı |
| `YT_REFRESH_TOKEN_TR` | Türkçe kanalın refresh token'ı |

Bu andan sonra yükleme her gün 15:41'de (İstanbul) kendiliğinden yapılır.

## 5. Google denetim başvurusu (10 dk, sonra beklemek)

Denetimden geçmemiş projelerin yüklediği videolar YouTube'da **"özel" olarak kilitlenir**; izleyici göremez.
Herkese açık yayın için başvuru gerekir:

- Form: **support.google.com/youtube/contact/yt_api_form**
- Başvuru metnini ben hazırlarım; siz forma yapıştırıp gönderirsiniz.
- Onay süresi birkaç gün ile birkaç hafta arasında değişebilir; ret de mümkündür.

**Onay gelene kadar:** videolar her gün yine üretilir. GitHub'da depo › **Actions** › "Tarihte Bugün video" › son çalışma ›
**videolar** dosyası indirilip YouTube Studio'dan yüklenir (haftada bir, 7 video, yaklaşık 10 dakika).
