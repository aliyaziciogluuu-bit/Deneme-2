"""Üretim panosu: her videonun hangi istasyonda olduğunu dosyalardan okuyup tek tabloda gösterir.

Kullanım:  python3 pano.py          → ekrana yazar ve kanal/uretim_panosu.md dosyasını günceller

İstasyonlar (fabrika hattı):
  1 Senaryo · 2 Kaynak arşivi · 3 Bilgi onayı · 4 Görsel · 5 Klip · 6 Ses · 7 Çekim planı
  8 Video ve test · 9 Shorts · 10 Denetim (kalite + metin) · 11 Puan ≥ 80 · 12 Teslim
"""
import json
import pathlib
import re
import time

KOK = pathlib.Path(__file__).parent


def oku(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def cumleler(sen):
    return [c for s in sen.get("sahneler", []) for c in s.get("cumleler", [])] if sen else []


def son_karar(onay_metni, kim):
    """Onay kaydında 'kim' denetçisinin en son ONAY/RET kararı (başlık altındaki satırlar dahil)."""
    karar, baslik = None, ""
    for satir in onay_metni.splitlines():
        if satir.startswith("#"):
            baslik = satir.lower()
        if kim in baslik or kim in satir.lower():
            m = re.search(r"\b(ONAY|RET)\b", satir)
            if m:
                karar = m.group(1)
    return karar


def durum(klasor: pathlib.Path):
    sen = oku(klasor / "senaryo.json")
    c = cumleler(sen)
    n = len(c)
    onay = ""
    op = KOK / "kanal" / "onaylar" / f"{klasor.name}.md"
    if op.exists():
        onay = op.read_text(encoding="utf-8")
    g = oku(klasor / "gorseller.json") or {}
    gorsel_ist = len(g.get("gorseller", []))
    gorsel_var = len(list((klasor / "gorseller").glob("*.jpg"))) if (klasor / "gorseller").exists() else 0
    k = oku(klasor / "klipler.json") or {}
    klip_ist = [x for x in k.get("klipler", []) if not x.get("dusuruldu")]
    klip_var = sum(1 for x in klip_ist if (klasor / "klipler" / f"{x['ad']}.mp4").exists())
    rap = oku(klasor / "ses" / "rapor.json") or {}
    ses_ok = sum(1 for i in range(n) if rap.get(f"{i:03d}", {}).get("uygun"))
    cek = oku(klasor / "cekimler.json") or {}
    cek_n = sum(x.get("n", 0) for x in cek.get("cekimler", []))
    video = klasor / "video.mp4"
    sk = klasor / "son_kontrol.txt"
    video_guncel = video.exists() and sen and video.stat().st_mtime >= (klasor / "senaryo.json").stat().st_mtime
    test = "—"
    if sk.exists() and video.exists():
        t = sk.read_text(encoding="utf-8")
        if "[KALDI]" in t:
            test = "KALDI"
        else:
            test = "GEÇTİ" if "[GEÇTİ]" in t and sk.stat().st_mtime >= video.stat().st_mtime else "eski"
    shorts = []
    for s in sorted((klasor / "shorts").glob("*/")) if (klasor / "shorts").exists() else []:
        st = s / "son_kontrol.txt"
        shorts.append(f"{s.name}:{'✓' if st.exists() and '[KALDI]' not in st.read_text(encoding='utf-8') and '[GEÇTİ]' in st.read_text(encoding='utf-8') else '…'}")
    puan = "—"
    pj = oku(KOK / "kanal" / "puanlar.json") or {}
    kayit = (pj.get("videolar") or {}).get(klasor.name) or {}
    turlar = kayit.get("turlar") if isinstance(kayit, dict) else None
    if turlar:
        puan = str(turlar[-1].get("toplam", "—"))
    sen_t = (klasor / "senaryo.json").stat().st_mtime if (klasor / "senaryo.json").exists() else 0
    teslim_dosyalari = list((KOK / "teslim" / klasor.name).glob("*video.mp4")) + [
        f for f in (KOK / "teslim" / "uzun").glob("*video.mp4") if f.name.startswith(f"{int(klasor.name[:2])}-")]
    teslim = any(f.stat().st_mtime >= sen_t for f in teslim_dosyalari) or "YAYINDA" in onay or "TESLİM EDİLDİ" in onay

    adimlar = [
        ("Senaryo", n > 0),
        ("Kaynak arşivi", (klasor / "kaynaklar").exists() or (klasor / "kaynak_eslesme.md").exists()),
        ("Bilgi onayı", son_karar(onay, "bilgi") == "ONAY"),
        ("Görsel", gorsel_ist > 0 and gorsel_var >= gorsel_ist),
        ("Klip", bool(k) and klip_var == len(klip_ist)),
        ("Ses", n > 0 and ses_ok == n),
        ("Çekim planı", n > 0 and cek_n == n),
        ("Video ve test", bool(video_guncel) and test == "GEÇTİ"),
        ("Shorts", bool(shorts) and all(x.endswith("✓") for x in shorts)),
        ("Denetim", son_karar(onay, "kalite") == "ONAY" and son_karar(onay, "metin") == "ONAY"),
        ("Puan ≥ 80", puan != "—" and float(puan) >= 80),
        ("Teslim", teslim),
    ]
    istasyon = "TAMAM (teslim edildi)" if teslim else next((ad for ad, ok in adimlar if not ok), "TAMAM")
    ayrinti = f"ses {ses_ok}/{n} · çekim {cek_n}/{n} · görsel {gorsel_var}/{gorsel_ist} · klip {klip_var}/{len(klip_ist)} · test {test} · {' '.join(shorts) or 'Shorts yok'} · puan {puan}"
    return istasyon, ayrinti


def main():
    satirlar = ["# Üretim panosu – Avludaki Komşular", "",
                f"Güncelleme: {time.strftime('%d.%m.%Y %H:%M')} (`python3 pano.py`)", "",
                "| Video | Bekleyen istasyon | Ayrıntı |", "|---|---|---|"]
    stok = 0
    for klasor in sorted(KOK.glob("[0-9][0-9]-*/")):
        ist, ayr = durum(klasor)
        if ist.startswith("TAMAM"):
            stok += 1
        satirlar.append(f"| {klasor.name} | {ist} | {ayr} |")
    satirlar += ["", f"Teslim edilmiş video: {stok}. Stok hedefi: 4 hazır video (şirket el kitabı)."]
    metin = "\n".join(satirlar) + "\n"
    (KOK / "kanal" / "uretim_panosu.md").write_text(metin, encoding="utf-8")
    print(metin)


if __name__ == "__main__":
    main()
