# Ortak ses kütüphanesi

| Dosya | Kaynak kayıt | Sahibi | Lisans | Sayfa |
|---|---|---|---|---|
| `gece_cirit.ogg` | Kanal tarafından sentezlendi (`sentez_gece.py`): 5 cırcır + hafif gece havası, ~8 dk | — | Telifsiz (kendi üretimimiz) | — |
| `bahce_kuslar.ogg` | Birdsong mild sunny day (37 sn), 14 kez çapraz geçişle uzatıldı (~8 dk) | stephan | Kamu malı (Public domain) | https://commons.wikimedia.org/wiki/File:Birdsong_mild_sunny_day.ogg |

Kamu malı kayıt için kaynak göstermek zorunlu değildir; yine de açıklamada belirtilir.
Not: Freesound bağlantısı bu ortamda 403 veriyor (16 Kasım 2026); ücretsiz kayıtlar Wikimedia Commons'tan alınıyor.

## Müzik altlıkları (`muzik/`, Shorts için; 27 Kasım 2026)

| Dosya | Kaynak | Lisans | Not |
|---|---|---|---|
| `lyria_merak.ogg` | Google Lyria 2 (Replicate), istem: playful curious documentary underscore, pizzicato + marimba, 100 bpm | Replicate sayfasında "Commercial use" etiketli; çıktıda duyulmayan SynthID filigranı var | 32,8 sn, döngü; bilgi Shorts'ları |
| `lyria_gerilim.ogg` | Google Lyria 2, istem: tense cinematic science underscore, ticking clock, 105 bpm | aynı | "X olursa ne olur?" Shorts'ları |
| `lyria_hayret.ogg` | Google Lyria 2, istem: wonder and discovery, plucked strings + glockenspiel, 95 bpm | aynı | şaşırtıcı yetenek Shorts'ları |
| `merak.ogg`, `gerilim.ogg` | Kanal tarafından sentezlendi (`muzik/sentez_muzik.py`) | Telifsiz (kendi üretimimiz) | yedek |

Hepsi -20 LUFS'a eşitlendi; efekt_ekle.py --muzik ile -21 dB altta çalar, konuşma sırasında sidechain ile ayrıca bastırılır.
Not: Freesound arama API'si 27 Kasım'da çalışıyor ama dosya indirme (cdn.freesound.org ve OAuth gerektiren indirme) kapalı.
