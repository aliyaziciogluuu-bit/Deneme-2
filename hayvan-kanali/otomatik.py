"""Otomatik bekçi: her videoyu baştan sona makinenin yakalayabileceği hatalara karşı denetler ve güvenli olanları kendisi düzeltir.

Kanal sahibinin isteği (19 Kasım 2026): "Videolarda ve başka bir işleyişte sorun çıkmasın; bunu başlangıçta görüp otomatik olarak
düzeltin ve bir otomasyon kurun."

Kullanım (hayvan-kanali/ içinde):
  python3 otomatik.py kontrol 06-karga        # yalnızca denetler ve güvenli düzeltmeleri yapar (para harcamaz)
  python3 otomatik.py kontrol --hepsi         # bütün videolar
  python3 otomatik.py duzelt 06-karga         # + uygun olmayan cümleleri yeniden seslendirir (birkaç kuruş)
                                              #   + eski kalmış videoyu / son kontrolü üretim hattında yeniler
  python3 otomatik.py kontrol 06-karga --kaynak   # + kaynak adreslerinin açılıp açılmadığını da dener

hat.py her oluşturmadan önce ve teslim.py teslimden önce bu denetimi kendiliğinden çalıştırır; HATA varsa durur.

Kendiliğinden düzeltilenler (güvenli, içerik değiştirmez):
  · Shorts çekiminde aw/ay verilip bitiş w/y yazılmamışsa w=aw, y=ay (kamera son saniyede yüzü yazının altına itmesin)
  · düşürülmüş (dusuruldu) klibe bağlı çekimlerden "klip" alanı kaldırılır
  · kalmış _gecici klasörleri silinir
  · (duzelt) seslendirme raporunda uygun olmayan ya da sesi eksik cümleler yeniden seslendirilir
  · (duzelt) senaryodan, çekimden, sesten ya da görselden eski kalmış video ve son kontrol yeniden üretilir

HATA (iş durur, ilgili çalışana gider):
  metin_kontrol HATA · "ses" (okunuş) alanı cümlenin okunuşu değil · çekim toplamı cümle sayısına eşit değil ·
  çekimdeki görsel ya da klip dosyası yok · son kontrol KALDI · disk 7 GB'ın altında
"""
import difflib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

KOK = pathlib.Path(__file__).parent
PYTHON = "/tmp/claude-0/-home-user-Deneme-2/fdddad94-111a-5afb-8da5-24e84d67e505/scratchpad/venv/bin/python"
if not pathlib.Path(PYTHON).exists():
    PYTHON = sys.executable


class Denetim:
    def __init__(self, ad):
        self.ad, self.hata, self.uyari, self.duzeltilen, self.yapilacak = ad, [], [], [], []
        self.teslim_edildi = False

    def satirlar(self):
        s = [f"### {self.ad}"]
        s += [f"- HATA: {m}" for m in self.hata]
        s += [f"- UYARI: {m}" for m in self.uyari]
        s += [f"- DÜZELTİLDİ: {m}" for m in self.duzeltilen]
        s += [f"- YAPILACAK: {m}" for m in self.yapilacak]
        if len(s) == 1:
            s.append("- Temiz.")
        return s


def oku(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def yaz(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def sade(t):
    t = t.lower().replace("â", "a").replace("î", "i").replace("û", "u")
    return re.sub(r"[^\wçğıöşü ]", " ", t).split()


def cumleler(sen):
    return [c for s in sen.get("sahneler", []) for c in s.get("cumleler", [])] if sen else []


def ses_alani(d, yer, cl):
    """'ses' alanı aynı cümlenin okunuşu olmalı (karga 19 Kasım: bölüm adı yazılmıştı, seslendirme onu okudu)."""
    for i, c in enumerate(cl):
        if "ses" not in c:
            continue
        a, b = sade(c["yazi"]), sade(c["ses"])
        oran = difflib.SequenceMatcher(None, a, b).ratio()
        if len(b) < 0.6 * len(a) or oran < 0.45:
            d.hata.append(f"{yer} cümle {i:03d}: 'ses' alanı cümlenin okunuşu değil (\"{c['ses'][:50]}\" ↔ \"{c['yazi'][:50]}\")")


def dosya_denetle(d, klasor, cek, yer):
    k = oku(klasor / "klipler.json") or {}
    if not k and klasor.parent.name == "shorts":
        k = oku(klasor.parent.parent / "klipler.json") or {}
    dusen = {x["ad"] for x in k.get("klipler", []) if x.get("dusuruldu")}
    degisti = False
    for j, c in enumerate(cek):
        if c.get("klip") in dusen:
            d.duzeltilen.append(f"{yer} çekim {j}: düşürülmüş '{c['klip']}' klibi çekimden kaldırıldı")
            c.pop("klip"), c.pop("kx", None)
            degisti = True
        g = c.get("gorsel")
        if g and not (klasor / "gorseller" / f"{g}.jpg").exists():
            d.hata.append(f"{yer} çekim {j}: görsel '{g}' yok")
        if c.get("klip") and not (klasor / "klipler" / f"{c['klip']}.mp4").exists():
            d.hata.append(f"{yer} çekim {j}: klip '{c['klip']}' yok")
    return degisti


def guncellik(d, klasor, yer):
    """Video kaynaklarından eskiyse yeniden üretilmeli; son kontrol videodan eskiyse yeniden çalışmalı."""
    video, sk = klasor / "video.mp4", klasor / "son_kontrol.txt"
    if not video.exists():
        d.yapilacak.append(f"{yer}: video yok → üretim hattı")
        return "uret"
    kaynaklar = [klasor / "senaryo.json", klasor / "cekimler.json"]
    gorsel = list((klasor / "gorseller").glob("*.jpg")) + list((klasor / "klipler").glob("*.mp4"))
    cek = oku(klasor / "cekimler.json")
    if cek:  # Shorts'un gorseller/ klasörü ana videoya bağlı: yalnızca bu videonun kullandığı dosyalar sayılır
        ad = {x for c in cek.get("cekimler", []) for x in (c.get("gorsel"), c.get("klip")) if x}
        gorsel = [g for g in gorsel if g.stem in ad]
    kaynaklar += list((klasor / "ses").glob("*.wav")) + gorsel
    en_yeni = max((p.stat().st_mtime for p in kaynaklar if p.exists()), default=0)
    if en_yeni > video.stat().st_mtime + 1:
        d.yapilacak.append(f"{yer}: video, kaynaklarından eski ({time.strftime('%d.%m %H:%M', time.localtime(video.stat().st_mtime))}) → yeniden üretilmeli")
        return "uret"
    if not sk.exists() or sk.stat().st_mtime < video.stat().st_mtime:
        d.yapilacak.append(f"{yer}: son kontrol videodan eski → yeniden çalışmalı")
        return "uret"
    if "[KALDI]" in sk.read_text(encoding="utf-8"):
        d.hata.append(f"{yer}: son kontrolde KALDI var ({sk})")
    return None


def ses_denetle(d, klasor, n, yer):
    rap = oku(klasor / "ses" / "rapor.json") or {}
    eksik = [i for i in range(n) if not (klasor / "ses" / f"{i:03d}.wav").exists() or not rap.get(f"{i:03d}", {}).get("uygun")]
    if eksik:
        d.yapilacak.append(f"{yer}: {len(eksik)} cümlenin sesi eksik ya da uygun değil → {' '.join(map(str, eksik[:20]))}")
    return eksik


def kaynak_erisim(d, sen):
    """Kaynak adresleri açılıyor mu? Önce www'li, sonra www'siz denenir (ağ izni çoğu sitede www'li adrese verilmiş)."""
    for kay in sen.get("kaynaklar", []):
        m = re.search(r"((?:https?://)?(?:[\w-]+\.)+(?:org|gov|com|edu|tr|int|uk|cz|net)(?:/[^\s,;]*)?)", kay)
        if not m:
            continue
        adres = m.group(1).rstrip(".")
        if adres.count("(") < adres.count(")"):  # künye parantezinin kapanışı adrese karışmasın
            adres = adres[: adres.rfind(")")]
        govde = re.sub(r"^https?://", "", adres)
        adaylar = [f"https://{govde}"] if govde.startswith("www.") else [f"https://www.{govde}", f"https://{govde}"]
        kod = ""
        for a in adaylar:
            kod = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L", "-m", "15", a], capture_output=True, text=True).stdout
            if kod.startswith("2"):
                break
        if not kod.startswith("2"):
            d.uyari.append(f"kaynak açılamıyor (HTTP {kod or 'yok'}): {adaylar[0]} — açılamayan kaynak listede kalmaz")


def kapak_denetle(d, klasor, sen):
    """Kapak seçenekleri gerçekten farklı mı; alt yazı başlık parantezini tekrar ediyor mu (20 Kasım, kırlangıç dersi)."""
    import hashlib
    dosyalar = [klasor / f for f in ("kapak.jpg", "kapak_B.jpg", "kapak_C.jpg") if (klasor / f).exists()]
    ozet = {}
    for f in dosyalar:
        h = hashlib.md5(f.read_bytes()).hexdigest()
        if h in ozet:
            d.hata.append(f"kapak: {f.name} ile {ozet[h]} birebir aynı dosya (A/B testine aynı resim gider); kapak_alternatifler ana kapağı içermemeli")
        ozet[h] = f.name
    kapak = sen.get("kapak") or {}
    for alt in sen.get("kapak_alternatifler", []):
        if alt.get("buyuk") == kapak.get("buyuk") and alt.get("kucuk") == kapak.get("kucuk"):
            d.hata.append("kapak: kapak_alternatifler içinde ana kapağın aynısı var")
    baslik = sen.get("baslik", "")
    if "(" in baslik and kapak.get("kucuk"):
        parantez = set(sade(baslik[baslik.index("("):]).split()) if isinstance(sade(baslik), str) else set(sade(baslik[baslik.index("("):]))
        kucuk = set(sade(kapak["kucuk"]).split()) if isinstance(sade(kapak["kucuk"]), str) else set(sade(kapak["kucuk"]))
        ortak = {k for k in parantez & kucuk if len(k) > 3}
        if ortak:
            d.uyari.append(f"kapak: alt yazı başlık parantezindeki sözcükleri tekrar ediyor ({', '.join(sorted(ortak))}); alt yazı yeni bir vaat taşımalı")


def beyan_denetle(d, klasor):
    """Açıklamadaki yapay zekâ beyanı gerçek fotoğraf kullanımıyla uyumlu mu (22 Kasım, kara kurbağası dersi)."""
    for y in [klasor / "yukleme.txt"] + sorted(klasor.glob("shorts/*/yukleme.txt")):
        if not y.exists():
            continue
        metin = y.read_text(encoding="utf-8")
        yer = "uzun" if y.parent == klasor else f"Shorts {y.parent.name}"
        atif = "Gerçek fotoğraflar:" in metin
        if atif and "\nGörseller yapay zekâ ile üretilmiş" in metin:
            d.hata.append(f"{yer} açıklaması: gerçek fotoğraf atfı var ama beyan 'Görseller yapay zekâ ile üretilmiş' diyor (video.py ile yeniden yaz)")
        if not atif and "Gerçek fotoğraflar yukarıda" in metin:
            d.hata.append(f"{yer} açıklaması: beyan gerçek fotoğraftan söz ediyor ama atıf listesi yok")


def video_denetle(klasor: pathlib.Path, duzelt=False, kaynak=False, onkontrol=False):
    d = Denetim(klasor.name)
    sen = oku(klasor / "senaryo.json")
    if not sen:
        d.hata.append("senaryo.json yok ya da bozuk")
        return d, []
    cl = cumleler(sen)
    n = len(cl)
    onay_yol = KOK / "kanal" / "onaylar" / f"{klasor.name}.md"
    onay = onay_yol.read_text(encoding="utf-8") if onay_yol.exists() else ""
    yayinda = "YAYINDA" in onay or "TESLİM EDİLDİ" in onay
    if not onkontrol and yayinda:
        d.teslim_edildi = True
        if kaynak:
            kaynak_erisim(d, sen)
        d.uyari.append("teslim edildi ya da yayında: dosyalara dokunulmadı (yalnızca kaynak erişimi denendi)")
        return d, []
    # 1. Metin denetimi
    m = subprocess.run([sys.executable, "metin_kontrol.py", klasor.name], cwd=KOK, capture_output=True, text=True)
    for l in m.stdout.splitlines():
        if l.startswith("[HATA]"):
            if yayinda and l[7:].startswith("uzun"):  # yayındaki uzun video yeniden üretilmiyor; yalnız yeni Shorts denetlenir
                d.uyari.append("yayındaki uzun video (engel değil): " + l[7:])
                continue
            d.hata.append("metin: " + l[7:])
    # 2. Okunuş alanları
    if not yayinda:
        ses_alani(d, "uzun", cl)
    sh = oku(klasor / "shorts.json") or {}
    for s in sh.get("shorts", []):
        ses_alani(d, f"Shorts {s.get('ad')}", s.get("cumleler", []))
        metin_s = " ".join(c.get("yazi", "") for c in s.get("cumleler", [])).lower()
        if "yıka" in metin_s and "dokunma" not in metin_s:  # 17 Kasım + 23 Kasım dersi: Shorts kısaltılırken "dokunma" düşüyor
            d.hata.append(f"Shorts {s.get('ad')}: el yıkama uyarısı var ama 'dokunma' uyarısı yok (uzun videodaki güvenlik cümlesini aynen taşı)")
        for c in s.get("cumleler", []):
            y = c.get("yazi", "").lower()
            if ("büyük olasılıkla" in y or "muhtemelen" in y) and not any(k in y for k in ("göre", "sürülüyor", "yazıyor", "aktarıyor", "diyor")):
                d.uyari.append(f"Shorts {s.get('ad')}: '{c.get('yazi','')[:50]}…' kesinlik ifadesi kaynak çekincesi olmadan (bir derlemeye göre / öne sürülüyor)")
        ilk = (s.get("cumleler") or [{}])[0].get("yazi", "").strip()
        if ilk.endswith("?"):  # büyüme kuralı 5: Shorts ilk cümlesi iddia olur (soru %18, iddia %51 izlemeye devam)
            d.hata.append(f"Shorts {s.get('ad')}: ilk cümle soru ('{ilk[:50]}'); şaşırtıcı bir iddiayla aç (buyume_kurallari.md 5)")
    if not yayinda and cl:
        son = " ".join(c.get("yazi", "") for c in cl[-3:]).lower()
        if "abone ol" in son:  # büyüme kuralı 1: kapanış sıradaki videoyu bir soruyla açar
            d.uyari.append("uzun: kapanışta 'abone ol' var; sıradaki videoyu bir soruyla duyur (buyume_kurallari.md 1)")
    # 3. Çekim planı
    cek = None if yayinda else oku(klasor / "cekimler.json")
    if cek:
        top = sum(x.get("n", 0) for x in cek["cekimler"])
        if top != n:
            d.hata.append(f"çekim toplamı {top}, cümle sayısı {n} (yeniden sıralamadan sonra cekimler.json güncellenmeli)")
        if dosya_denetle(d, klasor, cek["cekimler"], "uzun"):
            yaz(klasor / "cekimler.json", cek)
    # 4. Shorts kadrajı: bitiş w/y
    if sh:
        degisti = False
        for s in sh.get("shorts", []):
            for j, c in enumerate(s.get("cumleler", [])):
                if "aw" in c and "w" not in c and not c.get("klip"):
                    c["w"] = c["aw"]; degisti = True
                    d.duzeltilen.append(f"Shorts {s['ad']} cümle {j}: bitiş genişliği w={c['aw']} yazıldı (kamera kaymasın)")
                if "ay" in c and "y" not in c and not c.get("klip"):
                    c["y"] = c["ay"]; degisti = True
                    d.duzeltilen.append(f"Shorts {s['ad']} cümle {j}: bitiş konumu y={c['ay']} yazıldı")
        if degisti:
            yaz(klasor / "shorts.json", sh)
            subprocess.run([sys.executable, "shorts_kur.py", klasor.name], cwd=KOK, capture_output=True)
    # 5. Ses
    yeniden_ses = {}
    eksik = [] if yayinda else ses_denetle(d, klasor, n, "uzun")
    if eksik:
        yeniden_ses[klasor.name] = eksik
    for sd in sorted((klasor / "shorts").glob("*/")) if (klasor / "shorts").exists() else []:
        ss = oku(sd / "senaryo.json")
        if ss:
            e = ses_denetle(d, sd, len(cumleler(ss)), f"Shorts {sd.name}")
            if e:
                yeniden_ses[f"{klasor.name}/shorts/{sd.name}"] = e
            sc = oku(sd / "cekimler.json")
            if sc and dosya_denetle(d, sd, sc["cekimler"], f"Shorts {sd.name}"):
                yaz(sd / "cekimler.json", sc)
    kapak_denetle(d, klasor, sen)
    # 6. Güncellik ve son kontrol
    uretilecek = []
    if onkontrol:  # hat.py oluşturmadan önce: eksik ses oluşturmayı durdurur, eskilik sorulmaz
        for m in [m for m in d.yapilacak if "sesi eksik" in m]:
            d.hata.append(m)
        d.yapilacak = [m for m in d.yapilacak if "sesi eksik" not in m]
        return d, []
    beyan_denetle(d, klasor)  # oluşturma sonrası: yukleme.txt video.py ile yazılır
    if guncellik(d, klasor, "uzun"):
        uretilecek.append(klasor.name)
    for sd in sorted((klasor / "shorts").glob("*/")) if (klasor / "shorts").exists() else []:
        if guncellik(d, sd, f"Shorts {sd.name}"):
            uretilecek.append(f"{klasor.name}/shorts/{sd.name}")
    # 7. Kaynak erişimi (isteğe bağlı, ağ kullanır)
    if kaynak:
        kaynak_erisim(d, sen)
    # Düzeltme: ses → video
    if duzelt:
        for hedef, liste in yeniden_ses.items():
            r = subprocess.run([PYTHON, "seslendir_bulut.py", hedef, "--cumle", *map(str, liste)], cwd=KOK, capture_output=True, text=True,
                               env={**__import__("os").environ, "HF_HUB_DISABLE_XET": "1"})
            rap = oku(KOK / hedef / "ses" / "rapor.json") or {}
            kalan = [i for i in liste if not rap.get(f"{i:03d}", {}).get("uygun")]
            d.duzeltilen.append(f"{hedef}: {len(liste) - len(kalan)}/{len(liste)} cümle yeniden seslendirildi")
            if kalan:
                d.hata.append(f"{hedef}: {kalan} cümleleri 5 denemede uygun çıkmadı → seslendirme yönetmenine (cümle yeniden yazılır ya da eşdeğer yazım eklenir)")
            uretilecek = sorted(set(uretilecek) | {hedef})
    return d, uretilecek


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("kontrol", "duzelt"):
        raise SystemExit(__doc__)
    duzelt = sys.argv[1] == "duzelt"
    onkontrol = "--onkontrol" in sys.argv
    teslim = "--teslim" in sys.argv
    kaynak = "--kaynak" in sys.argv
    adlar = [a for a in sys.argv[2:] if not a.startswith("--")]
    klasorler = sorted(KOK.glob("[0-9][0-9]-*/")) if "--hepsi" in sys.argv else [KOK / a for a in adlar]
    for g in list(KOK.glob("*/_gecici")) + list(KOK.glob("*/shorts/*/_gecici")):
        if not (KOK / "kanal" / ".hat.durum").exists():
            shutil.rmtree(g, ignore_errors=True)
    bos = shutil.disk_usage(KOK).free / 1e9
    rapor = [f"# Otomatik bekçi raporu – {time.strftime('%d.%m.%Y %H:%M')}", "", f"Boş disk: {bos:.1f} GB" + (" (HATA: en az 7 GB)" if bos < 7 else ""), ""]
    hata_var = bos < 7
    hepsi_uret = []
    for k in klasorler:
        d, uret = video_denetle(k, duzelt, kaynak, onkontrol)
        rapor += d.satirlar() + [""]
        hata_var |= bool(d.hata) or (teslim and bool(d.yapilacak))
        hepsi_uret += uret
    if duzelt and hepsi_uret and not hata_var:
        rapor.append(f"Üretim hattına verildi: {' '.join(hepsi_uret)}")
        r = subprocess.run([sys.executable, "hat.py", "uret", *hepsi_uret], cwd=KOK, capture_output=True, text=True)
        rapor += ["```", r.stdout[-3000:], "```"]
    metin = "\n".join(rapor) + "\n"
    if not onkontrol:
        (KOK / "kanal" / "otomatik_rapor.md").write_text(metin, encoding="utf-8")
    print(metin)
    sys.exit(1 if hata_var else 0)


if __name__ == "__main__":
    main()
