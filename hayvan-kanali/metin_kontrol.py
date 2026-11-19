"""Senaryo ve Shorts metinlerini, ofisin tekrarlanan hatalarına karşı otomatik denetler (para harcamaz, saniyeler sürer).

Kullanım:  python metin_kontrol.py 05-baykus        # senaryo.json + shorts.json
Çıkış kodu: HATA varsa 1 (seslendirmeye geçilmez), yalnızca UYARI varsa 0.

Denetimler (her biri dersler defterindeki bir olaydan doğdu):
  HATA  : "ise" kalıbı · seslendirilen metinde rakam · telefon numarası / "Alo" hattı · Shorts son cümlesi
          "Tam videosu kanalımızda." değil · Shorts'ta uzun videodaki risk grubu uyarısı eksik
  UYARI : 18 kelimeden uzun cümle · art arda aynı kelimeyle başlayan cümle (Ama… Ama…) · art arda iki cümlede aynı
          özel ad ya da içerik kelimesi · ilk soru 10 sn'den geç · ilk 90 sn'de ansiklopedi kalıbı (bilimsel ad,
          santimetre, metre) · Shorts ilk cümlesi soru · küçük resim alt yazısı başlıkta geçiyor · aynı cümlede
          birbirine benzeyen iki özel ad (Athena/Atina) · kaynak künyesinde DOI/bağlantı yok ya da yabancı makalenin
          başlığı Türkçeye çevrilmiş (yarasa, baykuş: uydurma başlık)
Süreler ses/rapor.json'dan alınır; yoksa saniyede 2,3 kelime varsayılır.
"""
import json
import pathlib
import re
import sys

KOK = pathlib.Path(__file__).parent
HIZ = 2.3  # kelime/sn (rapor yoksa)
DURAK = {"bir", "bu", "ve", "da", "de", "ama", "ki", "çok", "daha", "gibi", "için", "o", "en", "ya", "ne", "her",
         "onu", "ona", "sen", "senin", "bile", "kadar", "olan", "olarak", "değil", "var", "yok", "mi", "mı", "mu", "mü",
         "pek", "sonra", "önce", "şu", "hem", "ile", "veya", "çoğu", "zaman", "yani", "hiç", "bazı", "tam", "yaklaşık"}
ANSIKLOPEDI = [r"\bsantimetre", r"\bmetre(ye)? (yüksekliğe|uzunluğ)", r"bilimsel ad", r"bilim dünyasındaki ad",
               r"\b[A-Z][a-z]{3,}(us|is|a|um|on|ops|ix) [a-z]{3,}(us|um|ae|ensis|icus|ica|icum|ii|oides|ata|ina)\b"]
RISK = re.compile(r"(beş yaşından küçük|küçük çocuk|bağışıklığı zayıf|altmış beş)", re.I)

sorunlar = []


def ekle(tur, yer, mesaj):
    sorunlar.append((tur, yer, mesaj))


def kelimeler(m):
    return re.findall(r"[\wçğıöşüÇĞİÖŞÜâîû']+", m.lower())


def cumle_denetle(yer, c, onceki):
    yazi, ses = c["yazi"], c.get("ses", c["yazi"])
    if re.search(r"(?<![\wçğıöşü])ise(?![\wçğıöşü])", ses, re.I):
        ekle("HATA", yer, "\"ise\" kalıbı (seslendirme ve ses tanıma bozuyor)")
    if re.search(r"\d", ses):
        ekle("HATA", yer, "seslendirilen metinde rakam var; sayıyı yazıyla yaz")
    if re.search(r"\b(alo\s*\d|\d{3}[\s-]?\d{3,})", yazi, re.I) or "telefon" in yazi.lower() and re.search(r"\d", yazi):
        ekle("HATA", yer, "telefon numarası ya da hat adı (yasak)")
    k = kelimeler(yazi)
    if len(k) > 18:
        ekle("UYARI", yer, f"{len(k)} kelime (hedef en fazla 18)")
    ozel = re.findall(r"(?<!^)(?<![.!?;:] )\b([A-ZÇĞİÖŞÜ][a-zçğıöşüâî]{3,})", yazi)
    for i, a in enumerate(ozel):
        for b in ozel[i + 1:]:
            if a != b and a[:3].lower() == b[:3].lower():
                ekle("UYARI", yer, f"benzer özel adlar aynı cümlede: {a} / {b} (ses tanıma karıştırıyor)")
    if onceki:
        ok = kelimeler(onceki["yazi"])
        if k and ok and k[0] == ok[0] and k[0] in {"ama", "ve", "yani", "bu", "peki", "oysa", "üstelik"}:
            ekle("UYARI", yer, f"art arda iki cümle \"{k[0].capitalize()}\" ile başlıyor")
        ortak = {w for w in k if len(w) > 4 and w not in DURAK} & {w for w in ok if len(w) > 4 and w not in DURAK}
        ortak = {w for w in ortak if not w.startswith(("kertenk", "baykuş", "kirpi", "yarasa", "yılan", "geko"))}
        if len(ortak) >= 2:
            ekle("UYARI", yer, f"önceki cümleyle tekrar eden kelimeler: {', '.join(sorted(ortak))}")


def uzun_video(klasor, sen):
    rapor = {}
    if (klasor / "ses" / "rapor.json").exists():
        rapor = json.loads((klasor / "ses" / "rapor.json").read_text(encoding="utf-8"))
    t, i, onceki, ilk_soru = 0.7, 0, None, None
    son_soru_t, son_soru_i = 0.0, 0  # izleyiciyi tutan son soru ya da "Peki" anı
    for sh in sen["sahneler"]:
        for c in sh["cumleler"]:
            yer = f"uzun {i:03d} ({int(t) // 60}:{int(t) % 60:02d})"
            cumle_denetle(yer, c, onceki)
            soru = c["yazi"].rstrip().endswith("?")
            if ilk_soru is None and soru:
                ilk_soru = t
            if soru:
                if t < 180 and t - son_soru_t > 40:
                    ekle("UYARI", f"uzun {son_soru_i:03d}–{i:03d} ({int(son_soru_t) // 60}:{int(son_soru_t) % 60:02d}–{int(t) // 60}:{int(t) % 60:02d})",
                         f"{t - son_soru_t:.0f} sn boyunca soru yok (ilk 3 dakikada hedef: en çok 40 sn; yarasa, kirpi ve kargada izleyici kaybı riski)")
                son_soru_t, son_soru_i = t, i
            if t < 90:
                for d in ANSIKLOPEDI:
                    if re.search(d, c["yazi"]):
                        ekle("UYARI", yer, "ilk 90 saniyede ansiklopedi bilgisi (yılan videosunda izleyici burada ayrıldı)")
                        break
            sure = rapor.get(f"{i:03d}", {}).get("sure") or len(kelimeler(c["yazi"])) / HIZ
            t += sure + 0.35
            onceki, i = c, i + 1
    if ilk_soru is None or ilk_soru > 10:
        ekle("UYARI", "uzun giriş", f"ilk soru {'yok' if ilk_soru is None else f'{ilk_soru:.0f}. saniyede'} (hedef ilk 10 sn)")
    for j, kay in enumerate(sen.get("kaynaklar", [])):
        if re.search(r"\(\d{4}\)", kay) and not re.search(r"(doi:|doi\.org|https?://|\b[\w-]+\.(org|gov|com|edu|tr|int|uk|cz)\b)", kay):
            ekle("UYARI", f"kaynak {j + 1}", "makale künyesinde DOI ya da bağlantı yok; özgün başlıkla, DOI'yle yaz")
        if re.search(r"\(\d{4}\)\. [^.]*[çğıöşüÇĞİÖŞÜ]", kay) and re.search(r"(Journal|Biology|PNAS|Science|Zoology|Gerontology|Bioinspiration|Evolution)", kay):
            ekle("UYARI", f"kaynak {j + 1}", "yabancı dergi makalesinin başlığı Türkçe görünüyor; künyeye özgün başlık yazılır (uydurma çeviri olmasın)")
    k = sen.get("kapak", {})
    if k.get("kucuk") and k["kucuk"].lower().strip("!?.") in sen.get("baslik", "").lower():
        ekle("UYARI", "küçük resim", f"alt yazı \"{k['kucuk']}\" başlıkta geçiyor; yeni bir vaat taşımalı")
    return any(RISK.search(c["yazi"]) for sh in sen["sahneler"] for c in sh["cumleler"])


def shorts(klasor, risk_uzunda):
    p = klasor / "shorts.json"
    if not p.exists():
        return
    for sh in json.loads(p.read_text(encoding="utf-8"))["shorts"]:
        cc = sh["cumleler"]
        onceki = None
        for j, c in enumerate(cc):
            cumle_denetle(f"Shorts {sh['ad']} {j}", c, onceki)
            onceki = c
        if cc and cc[0]["yazi"].rstrip().endswith("?"):
            ekle("UYARI", f"Shorts {sh['ad']}", "ilk cümle soru; cevapla ya da şaşırtıcı bir bilgiyle aç")
        if cc and not cc[-1]["yazi"].rstrip().endswith("Tam videosu kanalımızda."):
            ekle("HATA", f"Shorts {sh['ad']}", "son cümle \"Tam videosu kanalımızda.\" ile bitmiyor")
        hijyen = any(re.search(r"(dokun|ellerini yıka|salmonella|kuduz|ısır)", c["yazi"], re.I) for c in cc)
        if risk_uzunda and hijyen and not any(RISK.search(c["yazi"]) for c in cc):
            ekle("HATA", f"Shorts {sh['ad']}", "temas/hijyen anlatılıyor ama uzun videodaki risk grubu uyarısı yok")


def main():
    klasor = KOK / sys.argv[1]
    sen = json.loads((klasor / "senaryo.json").read_text(encoding="utf-8"))
    risk = uzun_video(klasor, sen)
    shorts(klasor, risk)
    hata = [s for s in sorunlar if s[0] == "HATA"]
    for tur, yer, m in sorted(sorunlar, key=lambda s: (s[0] != "HATA", s[1])):
        print(f"[{tur}] {yer}: {m}")
    print(f"\nSONUÇ: {len(hata)} hata, {len(sorunlar) - len(hata)} uyarı." + (" Seslendirmeye geçme." if hata else ""))
    sys.exit(1 if hata else 0)


if __name__ == "__main__":
    main()
