# Ses kaynakları

Videonun sesi iki gerçek kayıttan kurulur. İkisi de CC BY 3.0 lisanslıdır: ticari kullanım ve
düzenleme serbesttir, ancak **video açıklamasında kaynak belirtmek zorunludur** (`yukleme.txt`
içindeki "Sound credits" bölümünü silmeyin).

| Dosya | Kayıt | Sahibi | Lisans | Sayfa |
|---|---|---|---|---|
| `ses_kaynak/yagmur.mp3` | Falling Rain SFX 1 (72 dk) | valvalion | CC BY 3.0 | https://commons.wikimedia.org/wiki/File:Falling_Rain_SFX_1_2016-11-19.oga |
| `ses_kaynak/ates.ogg` | Campfire sound ambience (60 sn) | Glaneur de sons | CC BY 3.0 | https://commons.wikimedia.org/wiki/File:Campfire_sound_ambience.ogg |

Yağmur kaydı 110 MB olduğu için depoya eklenmedi. Yeniden üretmek gerekirse yukarıdaki sayfadan
indirip `ses_kaynak/yagmur.mp3` (ya da `.oga`) adıyla kaydedin.

## Yapılan düzenlemeler

- Yağmur: 100 Hz altı süzüldü, kayıt boyunca değişen ses düzeyi dengelendi, ani yükselmeler bastırıldı.
- Ateş: kısa kayıttan rastgele parçalar yumuşak geçişlerle eklenerek 1 saate uzatıldı, sola yerleştirildi,
  en sert çıtırtılar yumuşatıldı.

`ses_kaynak` klasörü yoksa `uret.py` sesi sıfırdan üretir; ancak üretilen ses dinleyene cızırtı gibi geldi.
