"""Senaryoyu Gemini TTS (Replicate) ile sahne sahne seslendirir, cümlelere böler ve doğrular.

Kullanım:  python seslendir_bulut.py 01-sagir-yilan          # eksik sahneleri üretir
           python seslendir_bulut.py 01-sagir-yilan 3 7      # 3. ve 7. sahneyi (0'dan sayılır) yeniden üretir
           python seslendir_bulut.py 01-sagir-yilan --cumle 70  # yalnızca 70 numaralı cümleyi tek başına yeniden üretir
                                                     (sahnenin geri kalanı doğruysa bütün sahneyi baştan üretmeye gerek kalmaz)
Çıktı:     <video>/ses/000.wav, 001.wav ... (video.py bunları kullanır), ses/sahne_N.wav, ses/rapor.json

Neden sahne sahne: Her cümleyi ayrı üretmek tonlamayı kopuk yapar; bir sahnenin tamamı tek seferde okunduğunda
anlatım doğal akar. Sonra Whisper'ın kelime zamanlarıyla sahne cümlelere bölünür; her parça yeniden dinlenip
metinle karşılaştırılır. Bir cümlede hata çıkarsa o sahne baştan üretilir (en fazla DENEME kez), en iyisi tutulur.

Ses: google/gemini-3.8-flash-tts, ses "Charon" (kanal sahibi kör karşılaştırmada seçti, 16 Kasım 2026).
API anahtarı ortamın ağ geçidi tarafından eklenir; bu betikte anahtar yoktur.
Gerekenler: ffmpeg, pip install faster-whisper numpy soundfile
"""
import difflib
import json
import pathlib
import re
import subprocess
import sys
import time

import numpy as np
import soundfile as sf

KOK = pathlib.Path(__file__).parent
MODEL = "google/gemini-3.8-flash-tts"
SES = "Charon"
USLUP = "Warm, natural Turkish documentary narrator, calm storytelling pace, native Istanbul Turkish accent"
SR = 24000
DENEME = 4


BIR = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
ON = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]


def sayi_yazi(n: int) -> str:
    """0-999999 arası sayıyı Türkçe sözcüklere çevirir (Whisper rakam yazınca karşılaştırma bozulmasın)."""
    if n == 0:
        return "sıfır"
    parca = []
    if n >= 1000:
        b = n // 1000
        parca.append("bin" if b == 1 else f"{sayi_yazi(b)} bin")
        n %= 1000
    if n >= 100:
        parca.append("yüz" if n // 100 == 1 else f"{BIR[n // 100]} yüz")
        n %= 100
    parca += [ON[n // 10], BIR[n % 10]]
    return " ".join(x for x in parca if x)


def sade(metin: str):
    metin = re.sub(r"(\d)[.,](\d{3})\b", r"\1\2", metin)
    metin = re.sub(r"\d+", lambda m: " " + sayi_yazi(int(m.group())) + " ", metin)
    metin = metin.replace("I", "ı").replace("İ", "i").lower()
    metin = re.sub(r"['’]", "", metin).translate(str.maketrans("âîû", "aiu"))
    metin = re.sub(r"[^a-zçğıöşü0-9 ]", " ", metin)
    kelimeler = re.sub(r"\s+", " ", metin).strip().split()
    birlesik = []  # "adı ise" → "adıysa", "yılanın ise" → "yılanınsa" (konuşmada doğal kısaltma, okuma hatası değil)
    for k in kelimeler:
        if k == "ise" and birlesik:
            onceki = birlesik[-1]
            unluler = [h for h in onceki if h in "aeıioöuü"]
            ek = "sa" if (unluler and unluler[-1] in "aıou") else "se"
            birlesik[-1] = onceki + ("y" + ek if onceki[-1] in "aeıioöuü" else ek)
        else:
            birlesik.append(k)
    return birlesik


def fark(duyulan, beklenen) -> int:
    a, b = sade(duyulan), sade(beklenen)
    if "".join(a) == "".join(b):  # yalnızca yazım farkı (ör. "sağırda" / "sağır da"): okuma doğru
        return 0
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes() if op != "equal")


def curl(*a, cikti=None):
    yeniden = [] if "POST" in a else ["--retry", "3"]
    r = subprocess.run(["curl", "-sS", "-m", "300", *yeniden, *a] + (["-o", str(cikti)] if cikti else []),
                       capture_output=True, text=cikti is None, check=True)
    return None if cikti else json.loads(r.stdout)


def tts(metin: str, hedef: pathlib.Path):
    girdi = {"text": metin, "voice": SES, "style": USLUP, "output_format": "wav"}
    for bekle in (15, 30, 60, 90, 0):
        t = curl("-X", "POST", f"https://api.replicate.com/v1/models/{MODEL}/predictions", "-H", "Content-Type: application/json",
                 "-H", "Prefer: wait=60", "-d", json.dumps({"input": girdi}))
        if "id" in t or not bekle:  # id yoksa istek kabul edilmedi (hız sınırı); tahmin oluşmadığı için yeniden denemek güvenli
            break
        time.sleep(bekle)
    if "id" not in t:
        raise RuntimeError(f"TTS isteği kabul edilmedi: {t}")
    while t["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(3)
        t = curl(f"https://api.replicate.com/v1/predictions/{t['id']}")
    if t["status"] != "succeeded":
        raise RuntimeError(f"TTS başarısız: {t.get('error')}")
    ham = hedef.with_suffix(".indirilen")
    curl(t["output"] if isinstance(t["output"], str) else t["output"][0], cikti=ham)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(ham), "-ac", "1", "-ar", str(SR), str(hedef)], check=True)
    ham.unlink()


def oku(yol, sr=SR) -> np.ndarray:
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(yol), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(ham, dtype=np.float32).copy()


def kirp(ses: np.ndarray) -> np.ndarray:
    """Baştaki ve sondaki sessizliği atar, 60 ms pay bırakır."""
    c = int(SR * 0.02)
    n = len(ses) // c
    if n < 3:
        return ses
    guc = np.sqrt((ses[: n * c].reshape(n, c) ** 2).mean(axis=1))
    sesli = np.where(guc > max(guc.max() * 0.03, 1e-4))[0]
    if len(sesli) == 0:
        return ses
    pay = int(SR * 0.06)
    return ses[max(sesli[0] * c - pay, 0): min((sesli[-1] + 1) * c + pay, len(ses))]


def sessiz_nokta(ses: np.ndarray, t0: float, t1: float) -> float:
    """t0-t1 aralığında enerjisi en düşük 30 ms'lik pencerenin ortası (kesim noktası)."""
    if t1 - t0 < 0.06:
        return (t0 + t1) / 2
    a, b = int(t0 * SR), int(t1 * SR)
    p = int(SR * 0.03)
    enerji = [np.sum(ses[i:i + p] ** 2) for i in range(a, max(b - p, a + 1), int(SR * 0.005))]
    return (a + int(np.argmin(enerji)) * int(SR * 0.005) + p / 2) / SR


def bol(ses: np.ndarray, kelimeler, cumleler):
    """Sahne kaydını cümlelere böler. kelimeler: Whisper (bas, bit, kelime) listesi."""
    beklenen, sahip = [], []
    for i, c in enumerate(cumleler):
        for k in sade(c):
            beklenen.append(k)
            sahip.append(i)
    duyulan = [sade(k[2]) for k in kelimeler]
    duz, dz_kaynak = [], []
    for j, parca in enumerate(duyulan):
        for k in parca:
            duz.append(k)
            dz_kaynak.append(j)
    eslesme = {}  # beklenen kelime indeksi -> Whisper kelime indeksi
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, beklenen, duz, autojunk=False).get_opcodes():
        if op == "equal":
            for d in range(i2 - i1):
                eslesme[i1 + d] = dz_kaynak[j1 + d]
    sinirlar = [0.0]
    for i in range(len(cumleler) - 1):
        onceki = [eslesme[x] for x in range(len(beklenen)) if sahip[x] == i and x in eslesme]
        sonraki = [eslesme[x] for x in range(len(beklenen)) if sahip[x] == i + 1 and x in eslesme]
        if not onceki or not sonraki:
            return None
        t0, t1 = kelimeler[max(onceki)][1], kelimeler[min(sonraki)][0]
        if t1 < t0:
            return None
        sinirlar.append(sessiz_nokta(ses, t0, t1))
    sinirlar.append(len(ses) / SR)
    return [kirp(ses[int(a * SR):int(b * SR)]) for a, b in zip(sinirlar, sinirlar[1:])]


def main():
    klasor = KOK / sys.argv[1]
    senaryo = json.loads((klasor / "senaryo.json").read_text(encoding="utf-8"))
    hedef = klasor / "ses"
    hedef.mkdir(exist_ok=True)
    rapor_yolu = hedef / "rapor.json"
    rapor = json.loads(rapor_yolu.read_text(encoding="utf-8")) if rapor_yolu.exists() else {}
    tek = [int(x) for x in sys.argv[sys.argv.index("--cumle") + 1:]] if "--cumle" in sys.argv else []
    zorla = set() if tek else {int(x) for x in sys.argv[2:]}

    from faster_whisper import WhisperModel
    dinleyici = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4)

    def dinle(ses, kelime=False):
        parcalar, _ = dinleyici.transcribe(ses, language="tr", beam_size=5, word_timestamps=kelime)
        parcalar = list(parcalar)
        if kelime:
            return [(w.start, w.end, w.word) for p in parcalar for w in p.words]
        return " ".join(p.text.strip() for p in parcalar)

    def on16(ses):
        return np.interp(np.arange(0, len(ses), SR / 16000), np.arange(len(ses)), ses).astype(np.float32)

    if tek:
        hepsi = [c for s in senaryo["sahneler"] for c in s["cumleler"]]
        for i in tek:
            c, ad = hepsi[i], f"{i:03d}"
            ok, yz = c.get("ses", c["yazi"]), c["yazi"]
            sinir = 0 if len(sade(yz)) <= 6 else 1
            en_iyi = None
            for deneme in range(1, DENEME + 2):
                kayit = hedef / f"cumle_{ad}.wav"
                tts(ok, kayit)
                p = kirp(oku(kayit))
                kayit.unlink()
                duy = dinle(on16(p))
                h = min(fark(duy, ok), fark(duy, yz))
                r = {"duyulan": duy, "hata": h, "sure": round(len(p) / SR, 2), "uygun": h <= sinir, "tek_basina": True}
                print(f"cümle {ad} deneme {deneme}: fark {h} | {duy}", flush=True)
                if en_iyi is None or h < en_iyi[1]["hata"]:
                    en_iyi = (p, r)
                if r["uygun"]:
                    break
            sf.write(hedef / f"{ad}.wav", en_iyi[0], SR)
            rapor[ad] = {"yazi": yz, **en_iyi[1]}
            rapor_yolu.write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
        return

    no = 0
    for s_i, sahne in enumerate(senaryo["sahneler"]):
        okunan = [c.get("ses", c["yazi"]) for c in sahne["cumleler"]]
        yazilan = [c["yazi"] for c in sahne["cumleler"]]
        adlar = [f"{no + i:03d}" for i in range(len(okunan))]
        no += len(okunan)
        for a, yz, ok in zip(adlar, yazilan, okunan):  # önceki çalıştırmanın sonuçlarını güncel kurallarla yeniden değerlendir
            if a in rapor and (hedef / f"{a}.wav").exists():
                r = rapor[a]
                r["hata"] = min(fark(r["duyulan"], ok), fark(r["duyulan"], yz))
                r["uygun"] = r["hata"] <= (0 if len(sade(yz)) <= 6 else 1)
        hazir = all((hedef / f"{a}.wav").exists() and rapor.get(a, {}).get("uygun") for a in adlar)
        if hazir and s_i not in zorla:
            continue
        en_iyi = None
        for deneme in range(1, DENEME + 1):
            kayit = hedef / f"sahne_{s_i:02d}.wav"
            tts(" ".join(okunan), kayit)
            ses = oku(kayit)
            kelimeler = [(a * 1.0, b * 1.0, k) for a, b, k in dinle(on16(ses), kelime=True)]
            parcalar = bol(ses, kelimeler, okunan)
            if parcalar is None:
                print(f"sahne {s_i} deneme {deneme}: cümle sınırları bulunamadı, yeniden", flush=True)
                continue
            sonuc = []
            for p, ok, yz in zip(parcalar, okunan, yazilan):
                duy = dinle(on16(p))
                h = min(fark(duy, ok), fark(duy, yz))
                sinir = 0 if len(sade(yz)) <= 6 else 1  # kısa cümlede hiç, uzun cümlede en fazla 1 kelime farkı
                sonuc.append({"duyulan": duy, "hata": h, "sure": round(len(p) / SR, 2), "uygun": h <= sinir})
            toplam = sum(r["hata"] for r in sonuc)
            print(f"sahne {s_i} deneme {deneme}: toplam kelime farkı {toplam}, "
                  f"uygun {sum(r['uygun'] for r in sonuc)}/{len(sonuc)}", flush=True)
            if en_iyi is None or (sum(r["uygun"] for r in sonuc), -toplam) > (sum(r["uygun"] for r in en_iyi[1]), -sum(r["hata"] for r in en_iyi[1])):
                en_iyi = (parcalar, sonuc)
            if all(r["uygun"] for r in sonuc):
                break
        if en_iyi is None:
            raise SystemExit(f"sahne {s_i} bölünemedi; metni kontrol et")
        for a, p, r, yz in zip(adlar, en_iyi[0], en_iyi[1], yazilan):
            sf.write(hedef / f"{a}.wav", p, SR)
            rapor[a] = {"yazi": yz, **r}
            if not r["uygun"]:
                print(f"  KONTROL ET {a}: {yz}  |  duyulan: {r['duyulan']}", flush=True)
        rapor_yolu.write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
    sorunlu = [a for a, r in sorted(rapor.items()) if not r["uygun"]]
    print("Bitti." if not sorunlu else f"Kontrol edilecek cümleler: {sorunlu}")


if __name__ == "__main__":
    main()
