# Kirpi (03-kirpi) kaynak eşleşmesi (Tur 4, 19 Kasım 2026)

Cümle no: yeni senaryo.json sırası, 0'dan başlar (seslendirme dosya adlarıyla aynı). Eski numara karşılığı için yeniden_sira.json'a bak.
Durum: "açıldı" = bu turda `curl -sSL` ile sayfayı kendim açıp ifadeyi okudum. "açılmadı, özetten" = sayfa bu ortamda açılamadı, ifade arama özetinden. "kaynak bulunamadı" = çekinceli ya da kontrolcüye bırakıldı.
Güncelleme notu: hedgehogstreet.org sayfaları önceki turlarda 403 vermişti; bu turda hepsi HTTP 200 ile açıldı (feed-hedgehogs, hedgehog-biology, hibernation, hedgehogs-history, link-your-garden, ayrıca where-do-they-live, helpful-garden-features, hibernation-faqs).

| Cümle | Bağlantı | Kaynakta geçen ifade | Durum |
|---|---|---|---|
| 3 (laktoz sindiremez) | hedgehogstreet.org/help-hedgehogs/feed-hedgehogs/ | "Hedgehogs are lactose intolerant, so please do not give them milk." | açıldı |
| 4 (enzim yok denecek kadar az) | HS sayfalarında yok; wildlifeonline.me.uk/animals/article/european-hedgehog-interaction-with-humans-supplemental-feeding | Arama özeti: kirpiler laktaz enzimi eksik, yavrularda ölçülebilir laktaz aktivitesi yok (1995 tezi). "yok denecek kadar az" bu özetten | açılmadı, özetten (403 proxy) |
| 5, 7 (ishal, susuz kalma) | aynı wildlifeonline sayfası | Arama özeti: "milk can cause diarrhoea... dehydration". HS sayfasında ishal geçmiyor | açılmadı, özetten; çekinceli ("başlayabiliyor") |
| 8 (aç/zayıf/yavru için ağır sağlık sorunu OLABİLİR) | aynı | Arama özeti: dehydration "life-threatening or fatal in juvenile or elderly and sicker animals". Hayat tehlikesi ifadesi bilerek yumuşatıldı; "hayat/ölüm" geçen cümle kalmadı | açılmadı, özetten |
| 6 (ekmek yanlış), 9 | hedgehogstreet.org/help-hedgehogs/feed-hedgehogs/ | "Bread is low in energy and is fairly worthless to them." ("karnını doyurur" iddiası kaynaksızdı, çıkarıldı) | açıldı |
| 11 (su) | feed-hedgehogs; hedgehogs-history | "Don't forget to offer water bowls too!"; "it is important to only ever leave them water to drink" | açıldı |
| 12 (sıcak/kurak günlerde su) | feed-hedgehogs | "During cold or dry periods, these creepy-crawlies become much scarcer in gardens, so hedgehogs will hugely benefit from a shallow dish of water and supplementary feeding at these times." (HS "cold or dry" diyor; "sıcak" kaynakta yok, kontrolcü kararına bırakıldı) | açıldı; "sıcak" ifadesi kısmen |
| 13 (et bazlı mama; balıklı değil) | feed-hedgehogs | "meat-based wet dog or cat foods, or dry cat/kitten food ... Those resembling pet food with a high meat cont[ent] are most suitable." "Balıklı olanlar değil" ifadesi bu sayfada geçmiyor | açıldı; "balıklı" kaynak bulunamadı |
| 15 (mama destek) | feed-hedgehogs | "this food is only supplementary"; "they will be getting most of their food from insects and worms in the wild" | açıldı |
| 16 (kap temizliği) | feed-hedgehogs | "regularly clean your feeding bowls and do not wash them with your own plates and bowls" | açıldı |
| 14 (evcil değil) | yaban hayvanı genel bilgi; HS "wild hedgehogs" | doğrudan ifade yok | kaynak bulunamadı, güvenlik tavsiyesi |
| 18–21 (elma efsanesi, kanıt yok) | hedgehogstreet.org/about-hedgehogs/hedgehogs-history/ ; en.wikipedia.org/wiki/Hedgehogs_in_culture | HS: "this myth is almost certainly untrue"; Wikipedia: "the Roman author Pliny the Elder mentions hedgehogs gathering grapes by this method in his Naturalis Historia." "iki bin yıl önce" Plinius MS 23-79 | HS açıldı; Wikipedia önceki turda açıldı |
| 22 (böcekçil) | en.wikipedia.org/wiki/Hedgehog | "insectivorous"; gece hayvanı: HS biology "well adapted for nocturnal life" | açıldı (HS), Wikipedia önceki tur |
| 23–25 (üç tür, Trakya Balkan kirpisi, Güneydoğu uzun kulaklı) | dergipark.org.tr/tr/pub/ksudobil/issue/22831/243746 ; dergipark.org.tr/en/pub/dpufbed/article/408590 ; en.wikipedia.org/wiki/Long-eared_hedgehog | Diyarbakır'da Hemiechinus auritus ve Erinaceus concolor; E. concolor için Kütahya, Konya, Kastamonu örnekleri; Trakya Balkan kirpisi (E. roumanicus) için acikerisim.omu.edu.tr arama alıntısı, listeye yazılmadı | önceki tur AÇILDI; Trakya satırı özetten |
| 26 (üçünün de sırtı dikenli) | genel | tür bilgisi | genel bilgi |
| 27 (beş bin–yedi bin diken, Avrupa kirpisi) | hedgehogstreet.org/about-hedgehogs/hedgehog-biology/ | "An adult hedgehog has between 5,000 and 7,000 spines on it's body." (Wikipedia "up to 6000" diyor; "sayılmış" çekincesi) | açıldı |
| 28 (keratin) | aynı HS sayfası | "The spines are made up of keratin; the same material as human hair and nails." | açıldı |
| 29 (zehirli değil, fırlatamaz) | en.wikipedia.org/wiki/Hedgehog | "Their spines are not poisonous or barbed" ("ok gibi fırlatamaz" için doğrudan ifade yok) | Wikipedia önceki tur açıldı; fırlatma kısmı kaynak bulunamadı |
| 30 (kas ile topa dönme) | hedgehog-biology | "The hedgehog has a muscle around it's body which contracts to allow the hedgehog to curl up" ; "curl up into a tight, spiky ball" | açıldı |
| 31 (araba karşısında işe yaramaz) | en.wikipedia.org/wiki/Hedgehog | "many are run over as they attempt to cross roadways" | Wikipedia önceki tur açıldı |
| 32, 33 (menü) | en.wikipedia.org/wiki/European_hedgehog ; hedgehogstreet.org/help-hedgehogs/feed-hedgehogs/ | HS: "Hedgehogs' natural diet mainly consists of earthworms, ground beetles, caterpillars, earwigs and millipedes." Wikipedia: "largely of earthworms, as well as snails and slugs, beetles ... caterpillars"; "Plant matter ... only a negligible part" | HS açıldı; Wikipedia ek açıldı (bu tur) |
| 34 (sert kabuklu böcekler önemli bölüm) | European hedgehog / HS feed | "ground beetles"/"beetles" sayılıyor; "önemli bölüm" nitelemesi kaynakta aynen yok | kısmen; kontrolcü karar versin |
| 35 (yumurta, leş) | en.wikipedia.org/wiki/European_hedgehog | "Eggs of ground-nesting birds are also taken and carcasses may be foraged on." | açıldı (bu tur) |
| 36 ("zararlıları yiyerek doğal denge") | kaynak bulunamadı | Çıkarılabilir; eski cümle, değiştirmedim | kaynak bulunamadı |
| 37, 38 (yılan zehrine kısmi direnç; ısırık ağır hasta eder) | hedgehogstreet.org/about-hedgehogs/hedgehogs-history/ | "Research shows hedgehogs have a partial resistance to snake venom. But, a bite to the face or leg would still make a hedgehog very ill, and could even kill it." | açıldı |
| 39 | aynı | "Immune to snakebites ... It has been suggested" ; menü: Wikipedia | açıldı |
| 40–43 (köpük) | en.wikipedia.org/wiki/Hedgehog | "it will lick and bite the source, then form a scented froth in its mouth and paste it on its spines with its tongue." "Some experts believe..." (nedeni kesin değil) | Wikipedia önceki tur açıldı |
| 44 (kış uykusu, yaprak ve ot yığını) | hedgehogstreet.org/about-hedgehogs/hibernation/ ; hibernation-faqs/ | "Hedgehogs usually hibernate from October/November through to March/April"; "Log piles, leaf piles, compost heaps, under your shed". "Özellikle soğuk bölgelerde" Wikipedia: Avrupa kirpisi hibernate edebilir | açıldı |
| 45 (vücut işlevleri yavaşlar) | hibernation | "...enter a state of torpor. This allows them to save a lot of energy but slows down all other bodily functions making normal activity impossible." (Eski "kalp atışı" cümlesi, HS'de kalp geçmediği için bu ifadeyle değiştirildi) | açıldı |
| 46 (sıcaklık çevreye yaklaşır) | hibernation | "they drop their body temperature to match their surroundings" | açıldı |
| 47, 48 (yaprak yığınına dikkat, rahatsız etme) | hibernation ; hibernation-faqs ; helpful-garden-features | "Any disturbance during this period can be extremely dangerous"; "it's best not to add or remove any nesting materials"; "Please be careful when tidying leaf piles as there may be a hog in residence!" ("yakmadan" için bonfire ayrı SSS sayfası, açılmadı; yaprakları "eski hâline getir" tavsiyesi Gardeners' World özetinden) | açıldı; "yakmadan" ve "eski hâline getir" özetten |
| 49 (gece hayvanı) | hedgehog-biology | "well adapted for nocturnal life" | açıldı |
| 50 (gündüz dolaşan sorunlu olabilir) | kaynak bulunamadı | "çoğu zaman" iddiası kaynaksızdı; "olabilir"e yumuşatıldı | çekinceli |
| 51, 52 (yaz anne; güneşte yatan yardım ister) | kaynak bulunamadı (HS "found-a-hedgehog" sayfası 404) | Kontrolcü doğrulasın; çekinceli ifade | kaynak bulunamadı |
| 53–58 (süt verme, kutu, şişe, el yıkama, kime haber) | feed-hedgehogs (süt); kurum: kullanıcı kuralı | "Eldiven/kutu/şişe/yıka" adımları HS sayfalarında bu turda bulunamadı; kontrolcü doğrulasın. Kurum yalnızca "bölgendeki Doğa Koruma ve Milli Parklar şube müdürlüğü" | kısmen; kontrolcüye bırakıldı |
| 59 (arabalar) | en.wikipedia.org/wiki/Hedgehog | "many are run over as they attempt to cross roadways. In Ireland, hedgehogs are one of the most common mammalian road fatalities." | Wikipedia önceki tur açıldı |
| 60 (çim biçme, ilaç, file ağ) | hedgehogstreet.org/help-hedgehogs/faqs/ (başlıklar: "What garden hazards are there for hedgehogs?", "Do slug pellets harm hedgehogs?") | Soru başlıkları açıldı; yanıt metinleri açılmadı | kısmen |
| 61 (bir gecede kilometrelerce) | hedgehogstreet.org/about-hedgehogs/where-do-they-live/ | "Hedgehogs can roam an average distance of 2km on a single night." | açıldı |
| 62, 63 (delik, on üç santimetre) | hedgehogstreet.org/help-hedgehogs/link-your-garden/ | "DIY 'Hedgehog Highways' 13cm by 13cm square is sufficient for any hedgehog to pass through." "Yola doğru açma" bir öneridir, kaynağa dayalı iddia değil | açıldı |
| 64 (yaprak yığını yuva) | hedgehogstreet.org/help-hedgehogs/helpful-garden-features/ | "Log piles, leaf piles ... " (hibernation-faqs) ve "Overgrown 'wild' corner ... leaf piles as there may be a hog in residence" | açıldı |
| 65 (havuz rampası) | helpful-garden-features | "Hedgehogs are excellent swimmers, just make sure there is a gently sloping edge for them to escape from" | açıldı |
| 66, 67 (yaban hayvanı, yetkililere ulaştırmak) | güvenlik tavsiyesi; MAK Kararı (tarimorman.gov.tr) kirpi satırı bulunamadı, "koruma altında" denmedi | genel öneri | kaynak bulunamadı (hukuki iddia yok) |
| 68–72 | özet ve kapanış | | iddia yok |

## Güncelleme (Tur 4b, bilgi kontrolcüsü önerileri; yeni numaralar için senaryo.json sırasına bak)

Açıldı (curl, HTTP 200): rspca.org.uk/adviceandwelfare/wildlife/hedgehogs/garden (başlık "Attracting Hedgehogs to Your Garden - RSPCA") ve hedgehogstreet.org/sick-or-injured-hedgehog/ (başlık "Found a sick or injured hedgehog? - Hedgehog Street").

| Cümle (yeni metin) | Bağlantı | Kaynakta geçen ifade | Durum |
|---|---|---|---|
| "enzim yok denecek kadar az" | silindi | kaynak açılamadığı için | çıkarıldı |
| "İshal ... sıvı kaybı riski demek." | RSPCA garden | "Never feed hedgehogs milk or bread – they're lactose intolerant, so milk and bread can disrupt their digestive system and cause diarrhoea." (sıvı kaybı kısmı kontrolcü özeti) | açıldı |
| "et bazlı konserve kedi ya da köpek maması" | RSPCA garden | "Try tinned meaty cat or dog food" | açıldı |
| "akgöğüslü kirpi" (Trakya/Balkan çıktı) | dergipark ksudobil 243746 | önceki satır | önceki tur açıldı |
| "Zehirli değiller; ucu kancalı da değiller." | en.wikipedia.org/wiki/Hedgehog | "not poisonous or barbed" | önceki tur açıldı |
| "Solucanlar ve böcekler besinin en önemli kısmını" | RSPCA garden | "Hedgehogs mostly eat caterpillars, beetles and earthworms" ("en önemli" kontrolcü önerisi; RSPCA "mostly") | açıldı, nitelik kısmen |
| "bahçıvanların dostu" | RSPCA garden | "Hedgehogs are also a gardener's friend, as they eat beetles, caterpillars, worms..." | açıldı |
| "yığına daha fazla dokunma" | hedgehogstreet.org/hibernation-faqs | "it's best not to add or remove any nesting materials" | açıldı |
| "Yavruları varsa ... anne" | Hedgehog Street sick-or-injured | "Those hedgehogs will generally be moving quickly, appear well and only out for short periods of time." (anne yuva yaparken ya da yavrular uyurken beslenirken) | açıldı |
| "ince sesle bağıran ... sinekler dolaşan yavru" | aynı | "they may be squeaking and there may be flies around them. These hoglets need rescuing as soon as possible" | açıldı |
| "kaynamamış sıcak su dolu şişe ... suyu değiştir ... boşluk" | aynı | "Fill the bottle with hot tap water (not boiling)"; "change the water frequently and make sure there is room in the box for the hedgehog to get off the bottle" | açıldı |
