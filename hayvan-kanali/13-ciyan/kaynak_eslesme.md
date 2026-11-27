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
- INAT: https://www.inaturalist.org/observations/253992882 → `inat_253992882.txt` — açıldı (2026-11-27)
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
**12.** Başka hangi farklar var?
- 12 → kaynak gerekmiyor → — → bölüm içi soru
**13.** Çıyanlar genellikle hızlı koşar ve çoğunlukla etçildir; kırkayakların çoğu yavaş, çürüyen yaprakla beslenir.
- 13 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «kırkayaklara göre daha hızlı hareket etmeleri» → açıldı
- 13 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Generally adapted for running» → açıldı
- 13 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Centipedes are predominantly generalist carnivores» → açıldı
- 13 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Most millipedes are slow-moving detritivores, eating decaying leaves» → açıldı
**14.** Çıyanın ön bacakları zehir kıskacına dönüşmüş; kırkayakta zehir kıskacı yok.
- 14 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Primarily carnivores with front legs modified into venomous fangs» → açıldı
- 14 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «centipedes have long threadlike antennae, a pair of small mandibles, two pairs of maxillae and a pair of large venom claws» → açıldı
  - not: kırkayakta 'no venom' ifadesi E_CEN tablosunda: 'no venom' (enjekte edilen zehir); savunma salgısı ayrı anlatılıyor (cümle 'Kırkayak gerçekten zararsız mı' bölümü)
**15.** Çıyan utangaçtır ama tehdit anında ısırabilir; kırkayak çoğu zaman kıvrılır.
- 15 → https://tr.wikipedia.org/wiki/Çıyan → tr_vikipedi_ciyan.txt → «Etçil beslenen çıyanlar utangaç olsa da» → açıldı
- 15 → https://tr.wikipedia.org/wiki/Çıyan → tr_vikipedi_ciyan.txt → «tehdit esnasında ısırabilmesine karşın» → açıldı
- 15 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Other millipedes commonly curl into a spiral when attacked or disturbed» → açıldı
  - not: E_MIL: 'commonly' = çoğu zaman
**16.** Hangisi olduğundan emin değilsen elle tutma.
- 16 → kaynak gerekmiyor → — → Bize göre güvenlik önerisi (türü ayırt edememe riski); kaynak iddiası yok
**17.** Çıyanın zehri nereden geliyor?
- 17 → kaynak gerekmiyor → — → bölüm sorusu
**18.** Zehir bezleri kafanın içinden başlıyor; bir tüp zehri kıskacın ucuna taşıyor, kıskaç avı da tutuyor.
- 18 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Venom glands run through a tube, from inside the head to the tip of each forcipule» → açıldı
- 18 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «they are used to subdue prey by injecting venom and gripping the prey animal» → açıldı
**19.** Vikipedi'ye göre, ön bacağı zehir enjektörü olan bilinen tek örnek çıyanlar.
- 19 → https://en.wikipedia.org/wiki/Forcipule → en_vikipedi_forcipule.txt → «They are the only known examples of front legs acting as venom injectors» → açıldı
**20.** Peki evde yaşayabilen çıyan nasıl biri?
- 20 → kaynak gerekmiyor → — → bölüm sorusu
**21.** Ev çıyanı denen bu tür, gövdesine göre bacakları upuzun bir hayvan.
- 21 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «it frequently lives in and around human homes» → açıldı
- 21 → https://tr.wikipedia.org/wiki/Scutigera_coleoptrata → tr_vikipedi_scutigera_coleoptrata.txt → «ev çıyanı» → açıldı
- 21 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Up to 15 pairs of long legs are attached to the rigid body» → açıldı
  - not: bacak sayısı verilmedi
**22.** Yerde, duvarda, hatta tavanda koşuyor; bacak ve antenleriyle olduğundan büyük görünüyor.
- 22 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «running across floors, up walls and along ceilings» → açıldı
- 22 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «give the centipede an appearance of being» → açıldı
**23.** Ev çıyanının arka bacakları anten gibi görünüyor; dinlenirken baş mı kuyruk mu anlamak zor.
- 23 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «its tail-like hind legs present the appearance of antennae» → açıldı
- 23 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «it is not easy to tell its cranial end from its caudal end» → açıldı
**24.** Ev çıyanı örümcek, tahtakurusu, hamamböceği ve karınca gibi evdeki eklembacaklıları yiyor.
- 24 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «House centipedes feed on spiders, bed bugs, termites, cockroaches, silverfish, ants» → açıldı
**25.** Avını nasıl yakalıyor?
- 25 → kaynak gerekmiyor → — → bölüm içi soru
**26.** Avının üstüne atlıyor ya da bacaklarıyla kement atar gibi sarıyor.
- 26 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «they either jump onto it or use their legs in a technique described as lassoing» → açıldı
**27.** Ev çıyanı yakalanırsa sıkışan bacağını koparıp kaçabiliyor.
- 27 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «it can detach any legs that have become trapped» → açıldı
**28.** Evin içinde çoğunlukla bodrum ve garaj gibi karanlık yerlerde, banyo ve mutfakta da görülüyor.
- 28 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «they are usually encountered in dark or dimly lit areas such as basements and garages» → açıldı
- 28 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «they can be found in bathrooms, lavatories and kitchens» → açıldı
**29.** Çoğu evin dışında, özellikle büyük taşların, odun ve yaprak yığınlarının altında yaşıyor.
- 29 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Most live outside, primarily under large rocks, woodpiles, barkdust and especially under piles of leaves or compost» → açıldı
  - not: ev çıyanı için; hikâyedeki 'taşı kaldırıyorsun' sahnesine bağ
**30.** Akdeniz çevresinde ortaya çıkıp dünyaya yayılmış; bilimsel adı Skutigera koleoptrata.
- 30 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Scutigera coleoptrata, also known as the house centipede» → açıldı
- 30 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Originating in the Mediterranean region, it has spread to other parts of the world» → açıldı
  - not: Türkiye'de görüldüğüne dair açılan kaynakta ifade yok; cümlede Türkiye iddiası yok
**31.** Ev çıyanı Türkiye'de de gözlemlenmiş.
- 31 → https://www.inaturalist.org/observations/253992882 → inat_253992882.txt → «quality_grade: research; takson: Scutigera coleoptrata» → açıldı
- 31 → https://www.inaturalist.org/observations/253992882 → inat_253992882.txt → «İzmir, Türkiye» → açıldı
  - not: iNaturalist araştırma sınıfı gözlem (İzmir, 2024); API ile açıldı, arşivde
**32.** Ev çıyanı ısırırsa ne olur?
- 32 → kaynak gerekmiyor → — → bölüm sorusu
**33.** Ev çıyanı ısırabilir ama saldırgan değil; rahatsız edilince genellikle kaçıyor.
- 33 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «not aggressive towards people and usually flee when disturbed» → açıldı
**34.** Başarılı bir ısırık genellikle hafif, bölgesel ağrı ve şişlik yapıyor; arı sokmasına benzetiliyor.
- 34 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Successful stings typically produce only mild, localized pain and swelling, similar to bee sting» → açıldı
**35.** Alerjik tepki bildirilmiş ama nadir.
- 35 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «Allergic reactions to centipede stings have been reported, but these are rare» → açıldı
**36.** Küçük çıyanlar genellikle insan derisini zaten delemiyor.
- 36 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «Smaller centipedes are generally incapable of piercing human skin» → açıldı
**37.** Türkiye'de bulunan çıyan türlerinden biri Skolopendra kingulata; Akdeniz çevresinde kendi takımının en yaygın türü.
- 37 → https://tr.wikipedia.org/wiki/Scolopendra → tr_vikipedi_scolopendra.txt → «Cinsin Türkiye'de 5 türü bulunur» → açıldı
- 37 → https://tr.wikipedia.org/wiki/Scolopendra → tr_vikipedi_scolopendra.txt → «Scolopendra cingulata - Latreille, 1829» → açıldı
- 37 → https://en.wikipedia.org/wiki/Scolopendra_cingulata → en_vikipedi_scolopendra_cingulata.txt → «the most common scolopendromorph species in the Mediterranean area» → açıldı
  - not: Türkiye kaydı Vikipedi (Türkçe) Scolopendra sayfasındaki tür listesine dayanır; sayfa Zapparoli 1999'a atıf yapıyor, o makale açılamadı. 'Beş tür' sayısı söylenmedi
**38.** Bu çıyanın bantları siyah ve sarı-altın renkli; karanlık, nemli yerde, kütük ve yaprak altında yaşıyor.
- 38 → https://en.wikipedia.org/wiki/Scolopendra_cingulata → en_vikipedi_scolopendra_cingulata.txt → «alternating bands of black and yellow-gold» → açıldı
- 38 → https://en.wikipedia.org/wiki/Scolopendra_cingulata → en_vikipedi_scolopendra_cingulata.txt → «preferring dark, damp environments such as beneath logs and in leaf litter» → açıldı
**39.** Kendinden büyük olmayan hemen her hayvana saldırıyor; böcek ve küçük kertenkele de yiyor.
- 39 → https://en.wikipedia.org/wiki/Scolopendra_cingulata → en_vikipedi_scolopendra_cingulata.txt → «will attack and consume almost any animal that is not larger than itself; this includes insects and small lizards» → açıldı
**40.** Türkçe bir derleme, çıyanlar arasında en zehirli türlerin Skolopendra cinsinde olduğunu yazıyor.
- 40 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «Scolpopendra cinsi en zehirli türleri içermektedir» → açıldı
  - not: kaynakta yazım 'Scolpopendra' (yazım hatası, kaynakta aynen)
**41.** Skolopendra cinsinin zehrine maruz kalanlarda şişme ve kızarıklığın yanında baş ağrısı, kalp çarpıntısı, bulantı ve kusma görülmüş.
- 41 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «Bu türlerin zehrine maruz kalanlarda sokulan bölge ve etrafında şişme, kızarıklık, baş ağrısı, kalp çarpıntısı, bulantı ve kusma gibi semptomlar görülmektedir» → açıldı
**42.** Bazı çıyan türlerinin ısırığı yetişkin biri için genellikle çok acı verici; şiddetli şişlik, titreme, ateş ve halsizlik yapabiliyor.
- 42 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «While a bite to an adult human is usually very painful and may cause severe swelling, chills, fever, and weakness» → açıldı
**43.** Çıyan ısırıkları acı verse de insanda nadiren ağır sağlık sorunu yapıyor.
- 43 → https://en.wikipedia.org/wiki/Centipede_bite → en_vikipedi_centipede_bite.txt → «Centipede bites, while painful, rarely cause severe health complications in people» → açıldı
**44.** Küçük çocuklar ve arı alerjisi olanlar için tehlikeli olabilir; büyük çıyanların ısırığı bu kişilerde ağır alerjik tepki yapabilir.
- 44 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «centiped bites can be dangerous to small children and those with allergies to bee stings» → açıldı
- 44 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «The venomous bite of larger centipedes can induce anaphylactic shock in such people» → açıldı
  - not: E_CEN'de yazım 'centiped bites' (kaynakta aynen)
**45.** Peki kırkayak gerçekten zararsız mı?
- 45 → kaynak gerekmiyor → — → bölüm sorusu
**46.** Kırkayak ısırmaz; tehlikede çoğu zaman sıkı bir spiral olup bacaklarını zırhlı gövdesinin içine saklıyor.
- 46 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Due to their lack of speed and their inability to bite or sting, millipedes' primary defence mechanism is to curl into a tight coil» → açıldı
- 46 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «curl into a tight coil, thus protecting their delicate legs inside an armoured exoskeleton» → açıldı
**47.** Birçok kırkayak, yanlardaki gözeneklerden kötü kokulu, tahriş edici bir sıvı salgılıyor.
- 47 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Many species also emit various foul-smelling liquid secretions through microscopic holes called ozopores» → açıldı
- 47 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Among the many irritant and toxic chemicals found in these secretions» → açıldı
**48.** Türkçe derleme, tutulan ya da sıkılan kırkayakta etkilenen bölgede yanma ve koyu lezyon görülebildiğini yazıyor.
- 48 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «tutulduklarında ya da sıkıldıklarında» → açıldı
- 48 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «Etkilenen bölgede yanmalara, iltihaplanmalara ve siyah-kahverengi lezyonlara neden olurlar» → açıldı
  - not: Y 'her segmentinde bulunan lateral salgı bezlerinden zehirli cyanide ve quinone toksinlerini dışarıya salarlar' diyor
**49.** Vikipedi daha hafif anlatıyor: salgılar çoğunlukla zararsız, genellikle yalnızca hafif renk değişimi yapıyor.
- 49 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «their defensive secretions are mostly harmless to humans, usually causing only minor discolouration on the skin» → açıldı
  - not: iki kaynak (Y ve E_MIL) şiddet konusunda tam aynı fikirde değil; ikisi de aktarıldı
**50.** Ağrı ve kabarcık gibi daha ağır etkiler bazı tropikal türlerde bildirilmiş.
- 50 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «the secretions of some tropical species may cause pain, itching, local erythema, edema, blisters» → açıldı
**51.** Göze kaçarsa tahriş ve göz iltihabı gibi daha ciddi sorunlar çıkabilir.
- 51 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «Eye exposures to these secretions causes general irritation and potentially more severe effects such as conjunctivitis and keratitis» → açıldı
  - not: conjunctivitis = göz zarı iltihabı
**52.** Göze ya da deriye değerse bol suyla iyice yıka; gözde şikâyet sürerse sağlık kuruluşuna başvur.
- 52 → https://en.wikipedia.org/wiki/Millipede → en_vikipedi_millipede.txt → «First aid consists of flushing the area thoroughly with water» → açıldı
  - not: ikinci yarı (sağlık kuruluşu) Bize göre güvenlik önerisi
**53.** Karşılaşırsan ne yapmalısın?
- 53 → kaynak gerekmiyor → — → bölüm sorusu
**54.** Taş ya da odun yığınını kaldırırken eldiven giy.
- 54 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «primarily under large rocks, woodpiles» → açıldı
  - not: Bize göre öneri; dayanak: ev çıyanının taş ve odun yığını altında yaşaması
**55.** Bize göre hangi çıyan olursa olsun elle tutma, sıkıştırma.
- 55 → kaynak gerekmiyor → — → Bize göre güvenlik önerisi; kaynak iddiası yok
**56.** Ev çıyanı genellikle ancak sıkışınca ya da sertçe tutulunca ısırıyor.
- 56 → https://en.wikipedia.org/wiki/Scutigera_coleoptrata → en_vikipedi_scutigera_coleoptrata.txt → «usually resulting only when the centipede is cornered or aggressively handled» → açıldı
  - not: E_SCU: 'usually' = genellikle
**57.** Bize göre yakalamak istersen kabı üstüne kapat, altına sert kâğıt kaydır; bacaklarını sıkıştırma.
- 57 → kaynak gerekmiyor → — → Bize göre öneri; kaynak iddiası yok
**58.** Bize göre ısırılan yeri sabunlu suyla yıkamak iyi olur.
- 58 → kaynak gerekmiyor → — → Bize göre güvenlik önerisi; kaynak iddiası yok
**59.** Vikipedi'ye göre buz da yardımcı oluyor, ama bize göre buzu doğrudan deriye değil, bezle sararak koy.
- 59 → https://en.wikipedia.org/wiki/Centipede_bite → en_vikipedi_centipede_bite.txt → «Icing also helps» → açıldı
  - not: buz: Vikipedi 'Icing also helps'; bezle sarma Bize göre güvenlik önerisi
**60.** Şiddetli ağrı, şişlik, ateş, kalp çarpıntısı, bulantı ya da kusma varsa vakit kaybetmeden bir sağlık kuruluşuna git.
- 60 → https://dergipark.org.tr/en/download/article-file/1346124 → yuksel2020_ethabd.txt → «şişme, kızarıklık, baş ağrısı, kalp çarpıntısı, bulantı ve kusma» → açıldı
- 60 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «severe swelling, chills, fever, and weakness» → açıldı
  - not: güvenlik cümlesi; Shorts'a kelimesi kelimesine taşınır
**61.** Isırık yeri günler içinde kötüleşiyor, morarıyor ya da ateş çıkıyorsa da bir hekime başvur.
- 61 → kaynak gerekmiyor → — → güvenlik cümlesi (12-ev-orumcegi ile aynı kalıp); Shorts'a kelimesi kelimesine
**62.** Belirti gösteren çocuk, hamile ya da arı alerjili biri varsa beklemeden sağlık kuruluşuna git.
- 62 → https://en.wikipedia.org/wiki/Centipede → en_vikipedi_centipede.txt → «dangerous to small children and those with allergies to bee stings» → açıldı
  - not: çocuk ve arı alerjisi kaynaklı; hamile genel ihtiyat; Shorts'a kelimesi kelimesine
**63.** Bize göre kalp veya tansiyon hastası yaşlılar belirti gösterirse de vakit kaybetmeden hekime başvursun.
- 63 → kaynak gerekmiyor → — → Bize göre ihtiyat (kalp/tansiyon hastası yaşlı kaynakta yok)
**64.** Nefes darlığı gibi ağır bir belirti olursa hemen acil servise git.
- 64 → kaynak gerekmiyor → — → güvenlik cümlesi (anafilaksi çekincesi)
**65.** Hangi hayvandan olduğuna ve nasıl tedavi edileceğine karar vermek sana değil, hekime düşer.
- 65 → kaynak gerekmiyor → — → güvenlik cümlesi; tıbbi karar hekime bırakılıyor
**66.** Özetle çıyan ısırabilir, ama ev çıyanı genellikle kaçar; kırkayak ısırmaz, salgısı tahriş edebilir.
- 66 → kaynak gerekmiyor → — → özet; ilgili cümleler: 3, 5, 31, 35, 43-48
**67.** Senin yörende çıyana ne derler, taşın altında en çok hangisini gördün?
- 67 → kaynak gerekmiyor → — → yorum sorusu
**68.** Avludaki Komşular'da, evinin çevresindeki yanlış tanınan komşuları anlatmaya devam edeceğiz.
- 68 → kaynak gerekmiyor → — → kanal kapanışı
**69.** Soğuk bastırınca bu komşular ne yapıyor?
- 69 → kaynak gerekmiyor → — → kış derlemesine genel bağ (soru)
**70.** Kış derlememizde evinin çevresindeki komşuların hepsini bir arada göreceksin.
- 70 → kaynak gerekmiyor → — → kış derlemesine genel bağ (26 Aralık); içerik iddiası yok; patron onayı bekler
**71.** Komşunu tanı.
- 71 → kaynak gerekmiyor → — → kanal vaadi

## Shorts cümleleri

Shorts cümlelerinin hepsi uzun videodaki cümlelerin kelimesi kelimesine kopyasıdır (`shorts.json` ile `senaryo.json` betikle karşılaştırıldı); eşleme uzun video numaralarıyla:

- **s1-ev-ciyani-isirir**: 33, 34, 16, 44, 60, 61, 64, 'Tam videosu kanalımızda.' (köprü cümlesi)
- **s2-kirkayak-isirmaz**: 5, 47, 52, 15, 44, 64, 60, 61, 'Tam videosu kanalımızda.' (köprü cümlesi)
- **s3-ev-ciyani-ne-yer**: 24, 60, 61, 44, 63, 64, 'Tam videosu kanalımızda.' (köprü cümlesi)

## Doğrulama sonucu (27 Kasım 2026)

`python3 -I kaynak_dogrula.py` → cümle sayısı: 71; doğrulanan ifade: 76; sorun: 0. Shorts cümleleri uzun videoda aynen var.

Ek: açılıp arşive kaydedilen ama cümlede doğrudan kullanılmayan sayfalar: en_vikipedi_millipede_burn.txt, en_vikipedi_scolopendra.txt, tr_vikipedi_diplopoda.txt, tr_vikipedi_scolopendra_cingulata.txt. iNaturalist tarayıcı sayfası 403 verdi; aynı gözlem resmî API'den (api.inaturalist.org/v1/observations/253992882) açıldı: özet inat_253992882.txt, ham yanıt inat_253992882_api.json.
