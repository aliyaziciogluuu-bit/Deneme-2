# Kaynak eşleme – 07-kirlangic (kaynak arşivcisi sürümü, 20 Kasım 2026)

Her alıntı `kaynaklar/` altındaki arşiv dosyasında birebir arandı (boşluk ve satır sonu tireleri yok sayıldı). Dosyalar: ilk satırlar adres, açılma tarihi, sayfa başlığı.

## Kaynaklar (9 açıldı, 0 açılamadı)

| Kod | Adres | Arşiv dosyası | Sayfa başlığı |
|---|---|---|---|
| K1 | https://en.wikipedia.org/wiki/Barn_swallow | barn_swallow_wiki.txt | Barn swallow - Wikipedia |
| K2 | https://en.wikipedia.org/wiki/Common_house_martin (sayfa "Western house martin" adına yönleniyor) | house_martin_wiki.txt | Western house martin - Wikipedia |
| K3 | https://tr.wikipedia.org/wiki/Kırlangıç | kirlangic_trwiki.txt | Kırlangıç - Vikipedi |
| K4 | https://tr.wikipedia.org/wiki/Kır_kırlangıcı | kir_kirlangici_trwiki.txt | Kır kırlangıcı - Vikipedi |
| K5 | https://tr.wikipedia.org/wiki/Ev_kırlangıcı | ev_kirlangici_trwiki.txt | Ev kırlangıcı - Vikipedi |
| K6 | https://dergipark.org.tr/tr/pub/trkjnat/article/267844 | per2016_dergipark.txt | The Distribution, Migration Phenology and Spatial and Temporal Status of Hirundinidae Species in Turkey - Trakya University Journal of Natural Sciences |
| K7 | https://dergipark.org.tr/tr/pub/dosder/article/830899 (künye) + PDF https://dergipark.org.tr/en/download/article-file/1413803 (metin) | umurhan2020_sayfa.txt, umurhan2020_pdf.txt | KIR KIRLANGIÇLARI (Hirundo rustica) İLE UYGULAMALI ÇEVRE EĞİTİMİ - Doğanın Sesi |
| K8 | https://www.rspca.org.uk/adviceandwelfare/wildlife/birds/baby/swifts | rspca_swifts.txt | Found a Grounded Swift, Swallow or House Martin? - RSPCA |
| K9 | https://www.rspca.org.uk/adviceandwelfare/wildlife/birds/baby | rspca_baby.txt | Found a Baby Bird Out of a Nest? - RSPCA |

Künye (sayfanın citation_* alanları): K6 = Esra Per, Kiraz Erciyas-yavuz, Nizamettin Yavuz; 2016; Trakya University Journal of Natural Sciences 17(1): 7-15. K7 = Betül Umurhan, Hakan Karaardıç; 2020; Doğanın Sesi 5: 37-47. İki sayfada da DOI alanı yok.

Kaynak çelişkisi: K4 (tr.wikipedia Kır kırlangıcı) "Yılda 3-4 defa kuluçkaya yatarlar. Kuluçka dönemi 3 haftadır." diyor; K1 ise "14–19 days" ve "two broods". Video K1'e dayanıyor. Çekince: K4'ün kuluçka bilgisi videoda kullanılmasın.

Genel çekince: K1, K2, K8, K9 Türkiye'ye özgü değildir (dünya / Avrupa / İngiltere).

## Eşleme tablosu

Soru, kurgu, kanal kalıbı ve bilgi iddiası taşımayan cümleler "–" ile gösterildi.

| No | Cümle | Kaynak | Sayfadaki alıntı | Durum |
|---|---|---|---|---|
| 000 | Nisan geliyor; saçağa bakıyorsun… | – | Kurgu, iddia yok | – |
| 001 | Kırlangıç gerçekten her yıl aynı eve mi dönüyor? | – | Soru | – |
| 002 | Dünyadaki çalışmalara göre evet: aynı kuşlar sık sık yıllarca aynı yerde üreyebiliyor. | K1 | "The same individuals often breed at the same site year after year" | TAMAM (kaynak "aynı yer" diyor, "aynı ev" demiyor; cümle "aynı yerde" diyor, uygun) |
| 003 | Birazdan kışı nerede geçirdiğini… göreceksin. | – | Vaat | – |
| 004 | Peki kırlangıç kışın nereye gidiyor? | – | Soru | – |
| 005 | Gilbert White, 1789 yılında yayımlanan kitabında bu konuda emin değildi. | K1 | "Gilbert White studied the barn swallow in detail in his pioneering work The Natural History of Selborne, but even this careful observer was uncertain whether it migrated or hibernated in winter." ve "The Natural History of Selborne, originally published in 1789" | TAMAM |
| 006 | Göç mü, kış uykusu mu? | – | Soru | – |
| 007 | Bugün biliyoruz: göç ediyor. | K3 | "yavru ve erginler göç ederek kışı Afrika'da geçirir" | TAMAM |
| 008 | İngiltere'de halkalanan kırlangıç, 1912 aralığında Güney Afrika'da bulundu. | K1 | "Migration of barn swallows between Britain and South Africa was first established on 23 December 1912 when a bird that had been ringed by James Masefield at a nest in Staffordshire, was found in Natal." | TAMAM |
| 009 | Avrupa'da ürüyen kır kırlangıçları kışı Afrika'da, Arabistan'da ya da Hindistan yarımadasında geçiriyor. | K1 | "H. r. rustica, the nominate European subspecies, breeds in Europe and Asia, as far north as the Arctic Circle, south to North Africa, the Middle East and Sikkim, and east to the Yenisei River. It migrates on a broad front to winter in Africa, Arabia, and the Indian subcontinent." | KISMEN. Kaynak yalnızca "nominate European subspecies" (H. r. rustica) için söylüyor; bu alt tür Asya'da da ürüyor. Cümle "Avrupa'da ürüyen kır kırlangıçları" diyerek bütün Avrupa üreyenlerine genelliyor. Öneri: "Kır kırlangıcının Avrupa alt türü kışı…" ya da "Avrupa'dan göç eden kır kırlangıçlarının büyük bölümü" (büyük bölümü kaynakta yok, kullanma) → en güvenlisi "Kır kırlangıcının Avrupa alt türü kışı Afrika'da, Arabistan'da ya da Hindistan yarımadasında geçiriyor." |
| 010 | Güney Afrika'da kışlayan bazı kuşların yıllık yolculuğu, 11.660 km'ye kadar kaydedilmiş. | K1 | "The barn swallows wintering in southern Africa are from across Eurasia to at least 91°E,[22] and have been recorded as covering up to 11,660 km (7,250 mi) on their annual migration." | TAMAM (sayı birebir: 11,660 km) |
| 011 | Türkiye'nin güneyinden İsrail'e kadar ürüyen bir alt tür kısmen yerleşik; bazıları Doğu Afrika'da kışlıyor. | K1 | "H. r. transitiva was described by Ernst Hartert in 1910. It breeds in the Middle East from southern Turkey to Israel and is partially resident, though some birds winter in East Africa." | TAMAM (alt tür adı H. r. transitiva; cümlede "bir alt tür" denmesi doğru) |
| 012 | Peki bu kuşlar neden gidiyor? | – | Soru | – |
| 013 | Yaz sonunda günler kısalıp böcekler azalınca yavrular ve yetişkinler göç ediyor. | K3 | "Yaz sonunda, günler kısalıp, böcekler azalınca yavru ve erginler göç ederek kışı Afrika'da geçirir." | TAMAM (kaynak Kırlangıçgiller düzeyinde) |
| 014 | Gündüz uçarak yol alıyorlar; fırtınalar binlercesinin ölümüne yol açabiliyor. | K3 | "Diğer göçmen kuşların aksine gündüz göç yollarına devam eder. Göç sırasında bazen şiddetli yağmur ve fırtınalar binlercesinin ölümüne sebep olur." | TAMAM |
| 015 | Peki Türkiye'ye ne zaman dönüyorlar? | – | Soru | – |
| 016 | Bir araştırmaya göre kır kırlangıcı ve ev kırlangıcı, mart sonuna kadar önce Akdeniz ve Ege kıyılarında görülüyor. | K6 | "R. riparia, H. rustica and D. urbicum distributed along Mediterranean and Aegean coasts in spring until the end of March" | TAMAM (kum kırlangıcı da aynı grupta; cümle iki türü anıyor, çelişki yok) |
| 017 | Sonra Orta Anadolu'ya, ardından daha kuzeye yayılıyorlar; sonbaharda bu sıra tersine dönüyor. | K6 | "spread later first to Central Anatolia and then to northern areas in Turkey and this pattern reversed in autumn period" | TAMAM |
| 018 | Araştırmacılar bunu enleme göre değişen böcek bolluğuyla ilişkilendiriyor. | K6 | "The latitudinal climatic differences and the resulting food availability are thought to be the reasons for such a distribution difference." | KISMEN. Kaynak "iklim farkları ve besin bulunabilirliği" diyor, "böcek" demiyor; "düşünülüyor" kipi de kaynakta var. Öneri: "Araştırmacılar bunu enleme göre değişen iklim ve besin bolluğuyla ilişkilendiriyor." |
| 019 | Peki yuva neden bu kadar değerli? | – | Soru | – |
| 020 | Kır kırlangıcı yuvayı gagasında taşıdığı çamur topaklarıyla yapıyor. | K1 | "constructed by both sexes, although more often by the female, with mud pellets collected in their beaks" | TAMAM |
| 021 | İçini ot ve tüy gibi yumuşak şeylerle döşüyor. | K1 | "lined with grasses, feathers, algae[69] or other soft materials" | TAMAM (sayfada köşeli dipnot numarası araya giriyor) |
| 022 | Kaynaklara göre bir çift, yuvayı yaklaşık iki haftada tamamlıyor. | K1 | "Because it takes around 2 weeks for a pair to build a nest from mud, hair, and other materials, old nests are highly prized." | TAMAM |
| 023 | Bu yüzden eski yuvalar kuşlar için çok değerli sayılıyor. | K1 | "old nests are highly prized" | TAMAM |
| 024 | Erkek kuş dişilerden önce gelip yuva yerini seçiyor. | K1 | "The male barn swallow returns to the breeding grounds before the females and selects a nest site" | TAMAM |
| 025 | Bir deneyde kuşların nereye yerleşeceği, eşin özelliklerinden çok boş yuva bulunmasıyla tahmin edilebilmiş. | K1 | "settlement choices have been experimentally shown to be predicted by nest availability rather than any characteristics of available mates" | TAMAM |
| 026 | Her yıl onarılan kırlangıç yuvalarının on, on beş yıl kullanılması olağan sayılıyor. | K1 | "Survival, with suitable annual refurbishment, for 10–15 years is regular" | TAMAM (sayı birebir: 10–15 years) |
| 027 | Bir yuvanın kırk sekiz yıl boyunca kullanıldığı bile bildirilmiş. | K1 | "one nest was reported to have been occupied for 48 years" | TAMAM (sayı birebir: 48 years) |
| 028 | Peki yuvayı bozarsan ne olur? | – | Soru | – |
| 029 | Kaynağa göre geçmişte yuvaya zarar vermenin ineğin kanlı süt vermesine ya da tavukların yumurtlamayı bırakmasına yol açacağı düşünülmüş. | K1 | "superstitions regarding damage to the barn swallow's nest. Such an act might lead to cows giving bloody milk, or no milk at all, or to hens ceasing to lay." | TAMAM (kaynak yer belirtmiyor; cümle de yer söylemiyor. "ya da süt hiç vermemesine" kısmı atlanmış, anlam bozulmuyor) |
| 030 | Kaynak buna batıl inanç diyor; yine de insanların kırlangıçlara hoşgörüsünü artırmış. | K1 | "In the past, the tolerance for this beneficial insectivore was reinforced by superstitions regarding damage to the barn swallow's nest." | KISMEN. Kaynakta fiil "reinforced" (pekiştirmiş); "artırmış" biraz daha güçlü. "yine de" bağlacı da mantığı zayıflatıyor. Öneri: "Kaynak buna batıl inanç diyor; bu inançların insanların kırlangıca hoşgörüsünü pekiştirdiği belirtiliyor." |
| 031 | Asıl neden daha sade: yuvanın içinde yumurta ya da yavru olabilir. | K1 | 032'deki "The incubation period is normally 14–19 days, with another 18–23 days before the altricial chicks fledge." çıkarımı | TAMAM (çıkarım; "asıl neden" ifadesi bir yorum, kaynaklı bir sav değil) |
| 032 | Kuluçka on dört ile on dokuz gün, yavruların yuvada kalışı on sekiz ile yirmi üç gün sürüyor. | K1 | "The incubation period is normally 14–19 days, with another 18–23 days before the altricial chicks fledge." | TAMAM (sayılar birebir: 14–19, 18–23). Dikkat: K4 farklı söylüyor ("Kuluçka dönemi 3 haftadır"), K1 kullanıldı |
| 033 | Kaynaklara göre kırlangıç normalde yılda iki kez yavru yetiştiriyor ve ilk yuvayı ikinci kuluçkada da kullanıyor. | K1 | "Barn swallows will normally raise two broods, with the original nest being reused for the second brood and being repaired and reused in subsequent years." | TAMAM. Dikkat: K4 "Yılda 3-4 defa" diyor, çelişki; video K1'i izliyor |
| 034 | Yani yuvanın içi, iki kuluçka boyunca dolu olabilir. | K1 | 033'ten çıkarım | TAMAM |
| 035 | Yasal kuralları doğrulayamadık; şube müdürlüğüne danışabilirsin. | – | Hukuki iddia yok; resmî karar metni açılmadı, cümle bunu dürüstçe söylüyor | TAMAM (kaynak gerektirmiyor) |
| 036 | Yuva sahipleri sonbaharda zaten göç ediyor; yuvaya dokunmadan beklemek en az zarar veren yol. | K3 | "Yaz sonunda, günler kısalıp, böcekler azalınca yavru ve erginler göç ederek kışı Afrika'da geçirir." | KISMEN. Birinci yarı (göç) kaynaklı ama kaynak "yaz sonunda" diyor, "sonbaharda" demiyor; ikinci yarı ("en az zarar veren yol") kaynaksız bir öneri. Öneri: "Yuva sahipleri yaz sonunda göç ediyor; yuvaya dokunmadan beklemek en güvenli seçenek gibi görünüyor." ya da ikinci yarıyı "bu yüzden beklemek bir seçenek" diye yumuşat. |
| 037 | Peki yuvanın altı pislenirse ne yapacaksın? | – | Soru | – |
| 038 | Ev kırlangıcı yuvalarının altında kuş pisliği sorun olabiliyor; bu yüzden yuvalar bazen yıkılıyor. | K5, K2 | K5: "Yuvaların altında kuş pislikleri sorun yaratabilmektedir." K2: "the accumulation of droppings below breeding birds can be a nuisance leading to some destruction of nests" | TAMAM |
| 039 | Yuvaya dokunmadan altını sık sık silmek, kuşlara zarar vermeyen bir çözüm olabilir. | – | Arşivlenen 9 sayfada altı silme / temizleme önerisi yok | YOK. Öneri: cümleyi çıkar ya da "Bu konuda doğrulanmış bir öneri bulamadık; şube müdürlüğüne danış" de. Kaynaklı hâle getirmek için açık bir kurum ya da üniversite sayfası (ör. Kuş Koruma derneği) ayrıca açılmalı. |
| 040 | Kırlangıçlar, uçarken sinek ve sivrisinek gibi küçük böcekleri yakalıyor. | K3 | "Üçgen şeklindeki gagaları geniş yırtmaçlı olup ağızları açık uçarken sinek, sivrisinek gibi küçük böcekleri avlar." (kısaltılmış: "ağızları açık uçarken sinek, sivrisinek gibi küçük böcekleri avlar") | TAMAM |
| 041 | Kaynaklara göre kır kırlangıcının üreme bölgelerindeki menüsünün yaklaşık yüzde yetmişini iri sinekler oluşturuyor. | K1 | "In the breeding areas, large flies make up around 70% of the diet, with aphids also a significant component." | TAMAM (sayı birebir: 70%) |
| 042 | Bunun Türkiye'de ölçülüp ölçülmediğini bulamadık. | – | Dürüstlük cümlesi | – |
| 043 | Bir Türkçe makale, yavrulara getirilen böceklerin tarım ilacı nedeniyle zehirli olma ihtimalini sorunlar arasında sayıyor. | K7 | "bu süreçte karşılaştıkları sorunlar (getirdikleri besin-lerin zirai ilaç kullanımı nedeniyle zehirli olma ihtimalleri, yuva materyali olarak taşıdıkları çöpler vb)" (PDF'te satır sonu tiresi var) | TAMAM. Not: makale bir çevre eğitimi derlemesi; bulgu değil, öğrencilerin gözlediği sorunlar listesi. Cümle "ihtimal" diyerek doğru çekinceli. "Böcek" sözcüğü makalede yok ("besin"); "böcek" yerine "besin" demek daha birebir olur |
| 044 | Avrupa ve Asya'nın bazı yerlerinde tarımın yoğunlaşması, böcek yiyeceğini azaltarak kırlangıç sayısını düşürmüş. | K1 | "an ongoing gradual decline in numbers in parts of Europe and Asia due to agricultural intensification, reducing the availability of insect food." | TAMAM |
| 045 | Peki saçağındaki kırlangıç hangisi? | – | Soru | – |
| 046 | Bir araştırma, Türkiye'deki yaz göçmeni beş kırlangıç türünü incelemiş: kum, kaya, kır, kızıl ve ev kırlangıcı. | K6, K3 | K6: "5 summer migrant Hirundinidae species (Riparia riparia, Ptyonoprogne rupestris, Hirundo rustica, Cecropis daurica, Delichon urbicum) in Turkey were evaluated". K3 tür tablosu: "Kum kırlangıcı, Riparia riparia"; "Kızıl kırlangıç, Cecropis daurica" | TAMAM (Türkçe adlar K3'ten; "kızıl kırlangıç" tr.wikipedia adı) |
| 047 | Binalara yuva yapan iki tanıdık tür kır kırlangıcı ve ev kırlangıcı. | K4, K5 | K4: "Yuvaladıkları yerler: eski harabeler, balkonlar, ahırlar." K5: "Binaların saçakları altında kapalı kap şeklinde çamurdan yuvalar yapar" | TAMAM ("tanıdık" yorum) |
| 048 | Kır kırlangıcının sırtı koyu mavi, kuyruğu uzun ve çatallı; alnı ve boğazı pas rengi. | K4, K1 | K4: "Uzun, çatallı bir kuyruğu vardır." K1: "It has steel blue upperparts and a rufous forehead, chin and throat" | TAMAM (renk ve alın/boğaz K1'den; "koyu mavi" K4'te de var) |
| 049 | Yuvası üstü açık bir çanak gibi; ahırlarda, balkonlarda, eski harabelerde bulunabiliyor. | K1, K4 | K1: "The neat cup-shaped nest is placed on a beam or against a suitable vertical projection." K4: "Yuvaladıkları yerler: eski harabeler, balkonlar, ahırlar." | TAMAM |
| 050 | Türkiye'de kır kırlangıçları çoğunlukla kırsal yerleşimlerde, ama şehir ve beldelerde de üreyebiliyor. | K7 | "Kır kırlangıçları, yoğun olarak kırsal bölgelerde yer alan yerleşim yerlerinde kuluçkaya yatsalar da, şehir ve" (PDF'te satır devam ediyor: "…beldelerde de üremektedir") | TAMAM ("Türkiye'de": makale Türkçe, çalışma yeri Türkiye'dir; makale bölge belirtmiyorsa "bir Türkçe makaleye göre" demek daha güvenli) |
| 051 | Ev kırlangıcının başı ve sırtı mavi, kıç tarafı ve karnı bembeyaz. | K5 | "Başı ve üst tüyleri mavidir, kuyruksokumu ve alt tüyleri ise beyazdır." | KISMEN. Kaynak "beyaz" diyor; "bembeyaz" abartı. Öneri: "kıç tarafı ve karnı beyaz." |
| 052 | Yuvasını saçak altına, üstü kapalı bir kap gibi, çamurdan yapıyor. | K5, K2 | K5: "Binaların saçakları altında kapalı kap şeklinde çamurdan yuvalar yapar" K2: "closed convex cup fixed below a suitable ledge, with a narrow opening at the top" | TAMAM |
| 053 | Serçeler yuva yapılırken sık sık araya girip yuvayı ele geçirmeye çalışıyor. | K2 | "House sparrows frequently attempt to take over the nest during construction" | TAMAM (ev kırlangıcı için; cümle "Serçeler" diyor, kaynak "ev serçeleri"; "Ev serçeleri" daha birebir) |
| 054 | Kırlangıçlar yuvaya yaklaşan kedi gibi tehditlere çok yakından uçarak karşı koyuyor. | K1 | "The barn swallow will mob intruders such as cats or accipiters that venture too close to their nest, often flying very close to the threat." | KISMEN. Kaynak yalnızca kır kırlangıcı için (cümle "Kırlangıçlar" diye bütün gruba genelliyor, dersler defteri: tür genellemesi). "karşı koyuyor" yerine kaynakta "mob" (sürü hâlinde rahatsız etmek/kovalamak) var ve "often flying very close" = "çoğu zaman çok yakından". Öneri: "Kır kırlangıçları yuvaya fazla yaklaşan kedi gibi tehditlerin çevresinde çoğu zaman çok yakından uçarak onları rahatsız ediyor." |
| 055 | Suyu da uçarken içiyor: alçaktan süzülüp gagasıyla yüzeyden alıyor. | K1 | "The barn swallow drinks by skimming low over lakes or rivers and scooping up water with its open mouth." | TAMAM (yine kır kırlangıcı; cümlede özne yok, 054 ile birlikte "Kır kırlangıcı" diye başlatılırsa tutarlı olur) |
| 056 | Peki yuvadan bir yavru yere düşerse ne yapmalısın? | – | Soru | – |
| 057 | İngiltere'deki bir hayvan koruma derneğine göre, kırlangıç yavruları yuvayı erken terk edip yere çakılabiliyor. | K8 | "Young swifts, swallows and house martins that leave their nests too soon may not be able to fly properly and can crash-land." | TAMAM |
| 058 | Yere inen yavru, oradan tekrar havalanamayabiliyor. | K8 | "They'll then be unable to take off again from the ground." | TAMAM |
| 059 | Dernek, böyle bir kuşu bir uzmana göstermeyi öneriyor. | K8 | "you should get them looked at by a professional to find out the cause." | TAMAM |
| 060 | Yavruyu havalandırma delikleri olan sağlam bir kartona koy; içine havlu ya da gazete ser. | K8 | "Place them in a secure cardboard box with ventilation holes and line them with a towel or newspaper." | TAMAM |
| 061 | Kedi ve köpeğini yavrudan uzak tut. | K9 | "if you find a baby bird, keep your pets away" | TAMAM (genel yavru kuş sayfası; kırlangıca özgü değil, kırlangıç için de geçerli) |
| 062 | Kuş gribi nedeniyle tutarken eldiven, gözlük ve maske takman, sonra ellerini yıkaman öneriliyor. | K8 | "Always wear gloves, eye protection and a mask when handling birds due to Avian Flu, and be sure to wash hands afterwards." | KISMEN. Öneri İngiltere kuş gribi bağlamında; cümle "İngiltere'deki dernek" çekincesini 057'den taşımıyor. Öneri: "İngiltere'deki dernek, kuş gribi nedeniyle…" |
| 063 | Hasta ya da ölü bir kuşa mümkünse hiç dokunma. | K8 | "don't touch or handle sick or dead birds. If you have to, thoroughly wash your hands immediately afterwards" | KISMEN. Kaynak "Avian Influenza Prevention Zone currently in place across the UK" bağlamında. Öneri: "İngiltere'de kuş gribi nedeniyle…" ya da "mümkünse" çekincesi korunarak "Dernek, hasta ya da ölü kuşa dokunmamayı öneriyor." |
| 064 | Kime başvuracaksın? Şube müdürlüğüne ya da bir veterinere. | K8 | "call a wildlife rehabilitator"; "take it to a vet" | TAMAM (veteriner kaynaklı; "şube müdürlüğü" kanal kuralı, kaynak değil; telefon yazılmıyor) |
| 065 | Kırlangıç sık sık aynı yuvaya dönebiliyor; yuva iki haftalık emek ve yıllarca süren bir ev. | K1 | 002 "often breed at the same site year after year"; 022 "around 2 weeks"; 033 "repaired and reused in subsequent years" | TAMAM ("aynı yuva" için 033 dayanak) |
| 066 | Yorum sorusu. | – | – | – |
| 067 | Sıradaki komşu: kara kurbağası… | – | Kanal planı (kanal/fikirler.json), iddia yok | – |
| 068 | Kanal kapanışı. | – | – | – |

## Shorts (shorts.json)

| Shorts cümlesi | Dayanak | Durum |
|---|---|---|
| s1-1 (1912 halkalı kuş) | 008 | TAMAM |
| s1-2 (Avrupa'da ürüyen kır kırlangıçları kışı…) | 009 | KISMEN (009'daki gibi alt tür çekincesi) |
| s1-3 (11.660 km) | 010 | TAMAM |
| s1-4 (Gilbert White) | 005 | TAMAM |
| s1-5 (alt tür kısmen yerleşik) | 011 | TAMAM |
| s2-1 (48 yıl) | 027 | TAMAM |
| s2-2 (iki hafta) | 020, 022 | TAMAM |
| s2-3 (eski yuvalar değerli; onarılıp kullanılıyor) | 023, 033 | TAMAM |
| s2-4 (kuluçka 14–19 gün) | 032 | TAMAM |
| s2-5 (yasal kurallar doğrulanamadı) | 035 | TAMAM |

## Senaristin emin olmadığı cümleler

- 009: KISMEN (alt tür). 011: TAMAM. 029: TAMAM. 030: KISMEN ("artırmış" → "pekiştirmiş"). 035: TAMAM (iddia yok). 039: YOK. 054: KISMEN (tür genellemesi).
