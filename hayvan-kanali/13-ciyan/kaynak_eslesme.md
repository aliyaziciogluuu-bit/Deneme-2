# Kaynak eşleme – 13-ciyan (70 cümle, 1 tabanlı)

Biçim: `cümle no → kaynak bağlantısı → arşiv dosyası → «kaynakta geçen ifade (özgün dilde)» → durum`. Her ifade `kaynaklar/` altındaki arşiv dosyasında boşluk, noktalama ve büyük-küçük harf yok sayılarak aranır: `python3 kaynak_dogrula.py` (bu klasörde) bu dosyayı okuyup her satırı arşivde doğrular; son sonuç en altta. Bütün sayfalar 27 Kasım 2026'da curl ile açılıp kaydedildi; "açıldı" = tam metin arşivde.

Bu ortamdan açılabilen siteler: dergipark.org.tr, en/tr.wikipedia.org. Açılamayan (403, reCAPTCHA ya da çözülemedi; hiç kullanılmadı): pmc.ncbi.nlm.nih.gov (bugün reCAPTCHA; çıyan ısırığı vaka makaleleri), ncbi.nlm.nih.gov/books (StatPearls), medlineplus.gov, ufhealth.org, statpearls.com, scielo.br, hkmj.org, mdedge.com, gbif.org, memorial.com.tr, tandfonline.com, archive.org, escholarship.org. DergiPark'ta çıyan ısırığı olgu makalesi bulunamadı. Zehir Danışma Merkezi anılmadı; telefon numarası yok.

## Kaynaklar (arşiv dosyası, durum)

- E_CEN: https://en.wikipedia.org/wiki/Centipede → `en_vikipedi_centipede.txt` — açıldı (2026-11-27)
- E_MIL: https://en.wikipedia.org/wiki/Millipede → `en_vikipedi_millipede.txt` — açıldı (2026-11-27)
- E_FORC: https://en.wikipedia.org/wiki/Forcipule → `en_vikipedi_forcipule.txt` — açıldı (2026-11-27)
- E_SCU: https://en.wikipedia.org/wiki/Scutigera_coleoptrata → `en_vikipedi_scutigera_coleoptrata.txt` — açıldı (2026-11-27)
- E_SCOLC: https://en.wikipedia.org/wiki/Scolopendra_cingulata → `en_vikipedi_scolopendra_cingulata.txt` — açıldı (2026-11-27)
- E_BITE: https://en.wikipedia.org/wiki/Centipede_bite → `en_vikipedi_centipede_bite.txt` — açıldı (2026-11-27)
- T_CIY: https://tr.wikipedia.org/wiki/Çıyan → `tr_vikipedi_ciyan.txt` — açıldı (2026-11-27)
- T_KIR: https://tr.wikipedia.org/wiki/Kırkayak → `tr_vikipedi_kirkayak.txt` — açıldı (2026-11-27)
- T_SCOL: https://tr.wikipedia.org/wiki/Scolopendra → `tr_vikipedi_scolopendra.txt` — açıldı (2026-11-27)
- T_SCU: https://tr.wikipedia.org/wiki/Scutigera_coleoptrata → `tr_vikipedi_scutigera_coleoptrata.txt` — açıldı (2026-11-27)
- Y: https://dergipark.org.tr/en/download/article-file/1346124 → `yuksel2020_ethabd.txt` — açıldı (2026-11-27) (12-ev-orumcegi arşivinden kopya; ilk açılış 2026-11-27)

## Cümleler

**1.** Bahçede bir taşı kaldırıyorsun ve altından upuzun, çok bacaklı bir hayvan fırlıyor.
- 1 → kaynak gerekmiyor → — → sahne kurulumu; bilgi iddiası yok
**2.** Çıyan ısırır mı?
- 2 → kaynak gerekmiyor → — → başlık sorusu
**3.** Isırabilir; hem de ağzıyla değil, bacağının dönüştüğü bir kıskaçla.
- 3 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Forcipules are not oral mouthparts» → açıldı
- 3 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «The forcipules are modifications of the first pair of legs» → açıldı
- 3 → https://tr.wikipedia.org/wiki/Çıyan → tr_vikipedi_ciyan.txt → «tehdit esnasında ısırabilmesine karşın» → açıldı
**4.** Ama taşın altında yavaşça kıvrılan çok bacaklı hayvan, çıyan değil kırkayak olabilir.
- 4 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «which move rapidly, are venomous, carnivorous, and have only a single pair of legs on each body segment» → açıldı
- 4 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Other millipedes commonly curl into a spiral when attacked or disturbed» → açıldı
- 4 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Most millipedes are slow-moving detritivores» → açıldı
**5.** Kırkayak ısırmaz da sokmaz da.
- 5 → https://tr.wikipedia.org/wiki/Çıyan → tr_vikipedi_ciyan.txt → «kırkayaklar ise genel kanının aksine sokmaz ve ısırmaz» → açıldı
- 5 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Millipedes do not bite» → açıldı
**6.** Evlerde yaşayabilen bir çıyan türü var; yediği şeyler arasında örümcek bile bulunuyor.
- 6 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «it frequently lives in and around human homes» → açıldı
- 6 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «House centipedes feed on spiders» → açıldı
**7.** Peki çıyan ısırığı kimler için ciddi olabilir?
- 7 → kaynak gerekmiyor → — → giriş sonu merak sorusu; cevabı 'Isırırsa ne olur' bölümünde
**8.** Çıyan ve kırkayak benzer görünür ama yalnızca uzak akrabadır.
- 8 → https://tr.wikipedia.org/wiki/Kırkayak → tr_vikipedi_kirkayak.txt → «benzeseler de sadece kuzenlerdir» → açıldı
- 8 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «only distantly related centipedes» → açıldı
**9.** Çıyanda her bölümde bir çift bacak var; kırkayakta çoğu bölümde iki çift.
- 9 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Centipedes have one pair of legs per segment, while millipedes have two» → açıldı
- 9 → https://tr.wikipedia.org/wiki/Kırkayak → tr_vikipedi_kirkayak.txt → «segmentinde ikişer çift bacağı olması» → açıldı
- 9 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Two pairs on most body segments» → açıldı
  - not: kapak B ile aynı bilgi
**10.** Böyle bir yanlışı her hafta düzeltiyoruz; sıradakini kaçırmamak için abone ol.
- 10 → kaynak gerekmiyor → — → kanal vaadi (buyume_kurallari 13), bilgi iddiası yok
**11.** Salı ve cumartesi akşamı yeni komşu geliyor.
- 11 → kaynak gerekmiyor → — → kanal vaadi
**12.** Çıyanlar genellikle hızlı koşar ve çoğunlukla etçildir; kırkayakların çoğu yavaş, çürüyen yaprakla beslenir.
- 12 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «kırkayaklara göre daha hızlı hareket etmeleri» → açıldı
- 12 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Generally adapted for running» → açıldı
- 12 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Centipedes are predominantly generalist carnivores» → açıldı
- 12 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Most millipedes are slow-moving detritivores, eating decaying leaves» → açıldı
**13.** Çıyanın ön bacakları zehir kıskacına dönüşmüş; kırkayakta zehir kıskacı yok.
- 13 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Primarily carnivores with front legs modified into venomous fangs» → açıldı
- 13 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «centipedes have long threadlike antennae, a pair of small mandibles, two pairs of maxillae and a pair of large venom claws» → açıldı
  - not: kırkayakta 'no venom' ifadesi E_CEN tablosunda: 'no venom' (enjekte edilen zehir); savunma salgısı ayrı anlatılıyor (cümle 'Kırkayak gerçekten zararsız mı' bölümü)
**14.** Çıyan utangaçtır ama tehdit anında ısırabilir; kırkayak kıvrılır.
- 14 → https://tr.wikipedia.org/wiki/Çıyan → tr_vikipedi_ciyan.txt → «Etçil beslenen çıyanlar utangaç olsa da» → açıldı
- 14 → https://tr.wikipedia.org/wiki/Çıyan → tr_vikipedi_ciyan.txt → «tehdit esnasında ısırabilmesine karşın» → açıldı
- 14 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Other millipedes commonly curl into a spiral when attacked or disturbed» → açıldı
**15.** Hangisi olduğundan emin değilsen elle tutma.
- 15 → kaynak gerekmiyor → — → Bize göre güvenlik önerisi (türü ayırt edememe riski); kaynak iddiası yok
**16.** Çıyanın zehri nereden geliyor?
- 16 → kaynak gerekmiyor → — → bölüm sorusu
**17.** Zehir bezleri kafanın içinden başlıyor; bir tüp zehri kıskacın ucuna taşıyor, kıskaç avı da tutuyor.
- 17 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Venom glands run through a tube, from inside the head to the tip of each forcipule» → açıldı
- 17 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «they are used to subdue prey by injecting venom and gripping the prey animal» → açıldı
**18.** Vikipedi'ye göre, ön bacağı zehir enjektörü olan bilinen tek örnek çıyanlar.
- 18 → https://en.wikipedia.org/wiki/Forcipule → en_vikipedi_forcipule.txt → «They are the only known examples of front legs acting as venom injectors» → açıldı
**19.** Çıyanlar nemli yer arıyor; güneşten örtü altında saklanıyor ya da geceleri etkin oluyor.
- 19 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «centipedes require a moist microhabitat» → açıldı
- 19 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «avoid direct sunlight by staying under cover or by being active at night» → açıldı
**20.** Dişi çıyanlar yumurtalarının ve yavrularının çevresine kıvrılarak bakım veriyor.
- 20 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Females provide parental care, both by curling their bodies around eggs and young» → açıldı
**21.** Peki evde yaşayabilen çıyan nasıl biri?
- 21 → kaynak gerekmiyor → — → bölüm sorusu
**22.** Ev çıyanı denen bu tür, gövdesi kısa ama bacakları upuzun bir hayvan.
- 22 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «it frequently lives in and around human homes» → açıldı
- 22 → https://tr.wikipedia.org/wiki/Scutigera_coleoptrata → tr_vikipedi_scutigera_coleoptrata.txt → «ev çıyanı» → açıldı
- 22 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Up to 15 pairs of long legs are attached to the rigid body» → açıldı
  - not: bacak sayısı verilmedi
**23.** Yerde, duvarda, hatta tavanda koşuyor; bacak ve antenleriyle olduğundan büyük görünüyor.
- 23 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «running across floors, up walls and along ceilings» → açıldı
- 23 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «give the centipede an appearance of being» → açıldı
**24.** Ev çıyanının arka bacakları anten gibi görünüyor; dinlenirken baş mı kuyruk mu anlamak zor.
- 24 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «its tail-like hind legs present the appearance of antennae» → açıldı
- 24 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «it is not easy to tell its cranial end from its caudal end» → açıldı
**25.** Ev çıyanı örümcek, tahtakurusu, hamamböceği ve karınca gibi evdeki eklembacaklıları yiyor.
- 25 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «House centipedes feed on spiders, bed bugs, termites, cockroaches, silverfish, ants» → açıldı
**26.** Avını nasıl yakalıyor?
- 26 → kaynak gerekmiyor → — → bölüm içi soru
**27.** Avının üstüne atlıyor ya da bacaklarıyla kement atar gibi sarıyor.
- 27 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «they either jump onto it or use their legs in a technique described as lassoing» → açıldı
**28.** Ev çıyanı yakalanırsa sıkışan bacağını koparıp kaçabiliyor.
- 28 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «it can detach any legs that have become trapped» → açıldı
**29.** Evin içinde çoğunlukla bodrum ve garaj gibi karanlık yerlerde, banyo ve mutfakta da görülüyor.
- 29 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «they are usually encountered in dark or dimly lit areas such as basements and garages» → açıldı
- 29 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «they can be found in bathrooms, lavatories and kitchens» → açıldı
**30.** Çoğu evin dışında, özellikle büyük taşların, odun ve yaprak yığınlarının altında yaşıyor.
- 30 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Most live outside, primarily under large rocks, woodpiles, barkdust and especially under piles of leaves or compost» → açıldı
  - not: ev çıyanı için; hikâyedeki 'taşı kaldırıyorsun' sahnesine bağ
**31.** Akdeniz çevresinde ortaya çıkıp dünyaya yayılmış; bilimsel adı Skutigera koleoptrata.
- 31 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Scutigera coleoptrata, also known as the house centipede» → açıldı
- 31 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Originating in the Mediterranean region, it has spread to other parts of the world» → açıldı
  - not: Türkiye'de görüldüğüne dair açılan kaynakta ifade yok; cümlede Türkiye iddiası yok
**32.** Ev çıyanı ısırırsa ne olur?
- 32 → kaynak gerekmiyor → — → bölüm sorusu
**33.** Ev çıyanı insana saldırgan değil; rahatsız edilince genellikle kaçıyor.
- 33 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «not aggressive towards people and usually flee when disturbed» → açıldı
**34.** Isırık genellikle ancak çıyan sıkışırsa ya da sertçe tutulursa oluyor.
- 34 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «usually resulting only when the centipede is cornered or aggressively handled» → açıldı
**35.** Başarılı bir ısırık genellikle hafif, bölgesel ağrı ve şişlik yapıyor; arı sokmasına benzetiliyor.
- 35 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Successful stings typically produce only mild, localized pain and swelling, similar to bee sting» → açıldı
**36.** Alerjik tepki bildirilmiş ama nadir.
- 36 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Allergic reactions to centipede stings have been reported, but these are rare» → açıldı
**37.** Küçük çıyanlar genellikle insan derisini zaten delemiyor.
- 37 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Smaller centipedes are generally incapable of piercing human skin» → açıldı
**38.** Türkiye'de bulunan çıyan türlerinden biri Skolopendra kingulata; Akdeniz çevresinde kendi takımının en yaygın türü.
- 38 → https://tr.wikipedia.org/wiki/Scolopendra → tr_vikipedi_scolopendra.txt → «Cinsin Türkiye'de 5 türü bulunur» → açıldı
- 38 → https://tr.wikipedia.org/wiki/Scolopendra → tr_vikipedi_scolopendra.txt → «Scolopendra cingulata - Latreille, 1829» → açıldı
- 38 → https://en.wikipedia.org/wiki/Scolopendra_cingulata → en_vikipedi_scolopendra_cingulata.txt → «the most common scolopendromorph species in the Mediterranean area» → açıldı
  - not: Türkiye kaydı Vikipedi (Türkçe) Scolopendra sayfasındaki tür listesine dayanır; sayfa Zapparoli 1999'a atıf yapıyor, o makale açılamadı. 'Beş tür' sayısı söylenmedi
**39.** Bu çıyanın bantları siyah ve sarı-altın renkli; karanlık, nemli yerde, kütük ve yaprak altında yaşıyor.
- 39 → https://en.wikipedia.org/wiki/Scolopendra_cingulata → en_vikipedi_scolopendra_cingulata.txt → «alternating bands of black and yellow-gold» → açıldı
- 39 → https://en.wikipedia.org/wiki/Scolopendra_cingulata → en_vikipedi_scolopendra_cingulata.txt → «preferring dark, damp environments such as beneath logs and in leaf litter» → açıldı
**40.** Kendinden büyük olmayan hemen her hayvana saldırıyor; böcek ve küçük kertenkele de yiyor.
- 40 → https://en.wikipedia.org/wiki/Scolopendra_cingulata → en_vikipedi_scolopendra_cingulata.txt → «will attack and consume almost any animal that is not larger than itself; this includes insects and small lizards» → açıldı
**41.** Türkçe bir derleme, çıyanlar arasında en zehirli türlerin Skolopendra cinsinde olduğunu yazıyor.
- 41 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «Scolpopendra cinsi en zehirli türleri içermektedir» → açıldı
  - not: kaynakta yazım 'Scolpopendra' (yazım hatası, kaynakta aynen)
**42.** Skolopendra cinsinin zehrine maruz kalanlarda şişme ve kızarıklığın yanında baş ağrısı, kalp çarpıntısı, bulantı ve kusma görülmüş.
- 42 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «Bu türlerin zehrine maruz kalanlarda sokulan bölge ve etrafında şişme, kızarıklık, baş ağrısı, kalp çarpıntısı, bulantı ve kusma gibi semptomlar görülmektedir» → açıldı
**43.** Bazı çıyan türlerinin ısırığı yetişkin biri için genellikle çok acı verici; şiddetli şişlik, titreme, ateş ve halsizlik yapabiliyor.
- 43 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «While a bite to an adult human is usually very painful and may cause severe swelling, chills, fever, and weakness» → açıldı
**44.** Çıyan ısırıkları acı verse de insanda nadiren ağır sağlık sorunu yapıyor.
- 44 → https://en.wikipedia.org/wiki/Centipede_bite → en_vikipedi_centipede_bite.txt → «Centipede bites, while painful, rarely cause severe health complications in people» → açıldı
**45.** Çocuklar ve arı alerjisi olanlar için tehlikeli olabilir; büyük çıyan ısırığı ağır alerjik tepki yapabilir.
- 45 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «centiped bites can be dangerous to small children and those with allergies to bee stings» → açıldı
- 45 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «The venomous bite of larger centipedes can induce anaphylactic shock in such people» → açıldı
  - not: E_CEN'de yazım 'centiped bites' (kaynakta aynen)
**46.** Peki kırkayak gerçekten zararsız mı?
- 46 → kaynak gerekmiyor → — → bölüm sorusu
**47.** Kırkayak ısırmaz; tehlikede sıkı bir spiral olup bacaklarını zırhlı gövdesinin içine saklıyor.
- 47 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Due to their lack of speed and their inability to bite or sting, millipedes' primary defence mechanism is to curl into a tight coil» → açıldı
- 47 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «curl into a tight coil, thus protecting their delicate legs inside an armoured exoskeleton» → açıldı
**48.** Birçok kırkayak, yanlardaki gözeneklerden kötü kokulu, tahriş edici bir sıvı salgılıyor.
- 48 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Many species also emit various foul-smelling liquid secretions through microscopic holes called ozopores» → açıldı
- 48 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Among the many irritant and toxic chemicals found in these secretions» → açıldı
**49.** Türkçe derleme, tutulan ya da sıkılan kırkayakta deride yanma ve koyu lezyon görülebildiğini yazıyor.
- 49 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «tutulduklarında ya da sıkıldıklarında» → açıldı
- 49 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «Etkilenen bölgede yanmalara, iltihaplanmalara ve siyah-kahverengi lezyonlara neden olurlar» → açıldı
  - not: Y 'her segmentinde bulunan lateral salgı bezlerinden zehirli cyanide ve quinone toksinlerini dışarıya salarlar' diyor
**50.** Vikipedi daha hafif anlatıyor: salgılar çoğunlukla zararsız, genellikle yalnızca hafif renk değişimi yapıyor.
- 50 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «their defensive secretions are mostly harmless to humans, usually causing only minor discolouration on the skin» → açıldı
  - not: iki kaynak (Y ve E_MIL) şiddet konusunda tam aynı fikirde değil; ikisi de aktarıldı
**51.** Ağrı ve kabarcık gibi daha ağır etkiler bazı tropikal türlerde bildirilmiş.
- 51 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «the secretions of some tropical species may cause pain, itching, local erythema, edema, blisters» → açıldı
**52.** Göze kaçarsa tahriş ve göz iltihabı gibi daha ciddi sorunlar çıkabilir.
- 52 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Eye exposures to these secretions causes general irritation and potentially more severe effects such as conjunctivitis and keratitis» → açıldı
  - not: conjunctivitis = göz zarı iltihabı
**53.** Göze ya da deriye değerse bol suyla iyice yıka; gözde şikâyet sürerse sağlık kuruluşuna başvur.
- 53 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «First aid consists of flushing the area thoroughly with water» → açıldı
  - not: ikinci yarı (sağlık kuruluşu) Bize göre güvenlik önerisi
**54.** Karşılaşırsan ne yapmalısın?
- 54 → kaynak gerekmiyor → — → bölüm sorusu
**55.** Taş ya da odun yığınını kaldırırken eldiven giy.
- 55 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «primarily under large rocks, woodpiles» → açıldı
  - not: Bize göre öneri; dayanak: ev çıyanının taş ve odun yığını altında yaşaması
**56.** Elle tutma, sıkıştırma; çıyan genellikle ancak sıkışınca ya da sertçe tutulunca ısırıyor.
- 56 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «usually resulting only when the centipede is cornered or aggressively handled» → açıldı
  - not: Bize göre öneri; dayanak cümle 34 (genellikle ancak sıkışırsa ya da sertçe tutulursa)
**57.** Ev çıyanı karşına çıkarsa geri çekil; rahatsız edilince genellikle kaçıyor.
- 57 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «usually flee when disturbed» → açıldı
**58.** Bize göre yakalamak istersen kabı üstüne kapat, altına sert kâğıt kaydır; bacaklarını sıkıştırma.
- 58 → kaynak gerekmiyor → — → Bize göre öneri; kaynak iddiası yok
**59.** Isırıldığını düşünüyorsan yarayı sabunlu suyla yıka; buzu bezle sararak uygulayabilirsin.
- 59 → https://en.wikipedia.org/wiki/Centipede_bite → en_vikipedi_centipede_bite.txt → «Icing also helps» → açıldı
  - not: sabunlu su Bize göre; buz Vikipedi 'Icing also helps'; 'bezle sararak' güvenlik önerisi
**60.** Şiddetli ağrı, şişlik, ateş, kalp çarpıntısı, bulantı ya da kusma varsa vakit kaybetmeden bir sağlık kuruluşuna git.
- 60 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «şişme, kızarıklık, baş ağrısı, kalp çarpıntısı, bulantı ve kusma» → açıldı
- 60 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «severe swelling, chills, fever, and weakness» → açıldı
  - not: güvenlik cümlesi; Shorts'a kelimesi kelimesine taşınır
**61.** Isırık yeri günler içinde kötüleşiyor, morarıyor ya da ateş çıkıyorsa da bir hekime başvur.
- 61 → kaynak gerekmiyor → — → güvenlik cümlesi (12-ev-orumcegi ile aynı kalıp); Shorts'a kelimesi kelimesine
**62.** Belirti gösteren çocuk, hamile, arı alerjili ya da kalp veya tansiyon hastası yaşlı varsa beklemeden sağlık kuruluşuna git.
- 62 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «dangerous to small children and those with allergies to bee stings» → açıldı
  - not: güvenlik cümlesi; çocuk ve arı alerjisi kaynaklı, hamile/kalp/tansiyon genel ihtiyat
**63.** Nefes darlığı gibi ağır bir belirti olursa hemen acil servise git.
- 63 → kaynak gerekmiyor → — → güvenlik cümlesi (anafilaksi çekincesi)
**64.** Hangi hayvandan olduğuna ve nasıl tedavi edileceğine karar vermek sana değil, hekime düşer.
- 64 → kaynak gerekmiyor → — → güvenlik cümlesi; tıbbi karar hekime bırakılıyor
**65.** Özetle çıyan ısırabilir, ama evdeki çıyan genellikle kaçar; kırkayak ısırmaz, salgısı tahriş edebilir.
- 65 → kaynak gerekmiyor → — → özet; ilgili cümleler: 3, 5, 33, 37, 47-52
**66.** Senin yörende çıyana ne derler, taşın altında en çok hangisini gördün?
- 66 → kaynak gerekmiyor → — → yorum sorusu
**67.** Avludaki Komşular'da, evinin çevresindeki yanlış tanınan komşuları anlatmaya devam edeceğiz.
- 67 → kaynak gerekmiyor → — → kanal kapanışı
**68.** Soğuk bastırınca bu komşular ne yapıyor?
- 68 → kaynak gerekmiyor → — → kış derlemesine genel bağ (soru)
**69.** Kış derlememizde evinin çevresindeki komşuların hepsini bir arada göreceksin.
- 69 → kaynak gerekmiyor → — → kış derlemesine genel bağ (26 Aralık); içerik iddiası yok; patron onayı bekler
**70.** Komşunu tanı.
- 70 → kaynak gerekmiyor → — → kanal vaadi

## Shorts cümleleri

Shorts cümlelerinin hepsi uzun videodaki cümlelerin kelimesi kelimesine kopyasıdır (`shorts.json` ile `senaryo.json` betikle karşılaştırıldı); eşleme uzun video numaralarıyla:

- **s1-ev-ciyani-isirir**: 33, 34, 35, 45, 60, 61, 'Tam videosu kanalımızda.' (köprü cümlesi)
- **s2-kirkayak-isirmaz**: 5, 9, 48, 53, 14, 60, 61, 'Tam videosu kanalımızda.' (köprü cümlesi)
- **s3-ev-ciyani-ne-yer**: 25, 27, 24, 60, 61, 62, 'Tam videosu kanalımızda.' (köprü cümlesi)

## Doğrulama sonucu (27 Kasım 2026)

`python3 -I kaynak_dogrula.py` → cümle sayısı: 70; doğrulanan ifade: 79; sorun: 0. Shorts cümleleri uzun videoda aynen var.

Ek: açılıp arşive kaydedilen ama cümlede doğrudan kullanılmayan sayfalar: en_vikipedi_millipede_burn.txt, en_vikipedi_scolopendra.txt, tr_vikipedi_diplopoda.txt, tr_vikipedi_scolopendra_cingulata.txt (içerik zayıf ya da tekrar).
