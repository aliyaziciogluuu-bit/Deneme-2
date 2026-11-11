"""Senaryodaki her cümleyi seslendirir ve sonucu konuşma tanıma ile doğrular.

Kullanım:  python seslendir.py 01-dans-vebasi
Çıktı:     <video klasörü>/ses/000.wav, 001.wav ... ve ses/rapor.json

Ses modeli: Chatterbox Multilingual (MIT lisansı, ticari kullanıma açık).
Gerekenler: pip install chatterbox-tts faster-whisper soundfile "setuptools<81"

Kendi sesinizi kullanmak isterseniz bu betiği çalıştırmayın; her cümleyi
ses/000.wav, ses/001.wav ... adıyla kaydedin, video.py gerisini halleder.
"""
import difflib
import json
import pathlib
import re
import sys

import numpy as np
import soundfile as sf
import torch

CFG = (0.0, 0.0, 0.4, 0.0, 0.4)  # her denemede kullanılacak cfg_weight; deneme sayısı = uzunluk
ESIK = 0.975        # metinle benzerlik bu değerin altındaysa yeniden üret
HIZ = (9.0, 18.0)   # kabul edilen konuşma hızı (karakter/saniye)


def sade(metin: str) -> str:
    metin = metin.replace("I", "ı").replace("İ", "i").lower()
    metin = re.sub(r"['’]", "", metin).translate(str.maketrans("âîû", "aiu"))
    metin = re.sub(r"[^a-zçğıöşü0-9 ]", " ", metin)
    return re.sub(r"\s+", " ", metin).strip()


def benzerlik(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, sade(a), sade(b)).ratio()


def kirp(ses: np.ndarray, sr: int) -> np.ndarray:
    """Baştaki ve sondaki sessizliği atar, 60 ms pay bırakır."""
    cerceve = int(sr * 0.02)
    n = len(ses) // cerceve
    if n < 3:
        return ses
    guc = np.sqrt((ses[: n * cerceve].reshape(n, cerceve) ** 2).mean(axis=1))
    sesli = np.where(guc > max(guc.max() * 0.03, 1e-4))[0]
    if len(sesli) == 0:
        return ses
    pay = int(sr * 0.06)
    return ses[max(sesli[0] * cerceve - pay, 0): min((sesli[-1] + 1) * cerceve + pay, len(ses))]


def main() -> None:
    klasor = pathlib.Path(__file__).parent / sys.argv[1]
    senaryo = json.loads((klasor / "senaryo.json").read_text(encoding="utf-8"))
    cumleler = [c for s in senaryo["sahneler"] for c in s["cumleler"]]
    hedef = klasor / "ses"
    hedef.mkdir(exist_ok=True)
    rapor_yolu = hedef / "rapor.json"
    rapor = json.loads(rapor_yolu.read_text(encoding="utf-8")) if rapor_yolu.exists() else {}

    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    from faster_whisper import WhisperModel

    torch.set_num_threads(4)
    tts = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    dinleyici = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4)

    def degerlendir(ses, c, okunan, deneme):
        gecici = hedef / "_gecici.wav"
        sf.write(gecici, ses, tts.sr)
        parcalar, _ = dinleyici.transcribe(str(gecici), language="tr", beam_size=5)
        gecici.unlink()
        duyulan = " ".join(p.text.strip() for p in parcalar)
        puan = max(benzerlik(duyulan, okunan), benzerlik(duyulan, c["yazi"]))
        sure = len(ses) / tts.sr
        hiz = len(okunan) / sure
        return {"puan": round(puan, 3), "sure": round(sure, 2), "hiz": round(hiz, 1), "deneme": deneme,
                "duyulan": duyulan, "uygun": bool(puan >= ESIK and HIZ[0] <= hiz <= HIZ[1])}

    for i, c in enumerate(cumleler):
        ad = f"{i:03d}"
        okunan = c.get("ses", c["yazi"])
        en_iyi, onceki = None, 0
        if (hedef / f"{ad}.wav").exists() and ad in rapor:  # önceki çalıştırmanın sonucunu yeniden değerlendir
            eski = rapor[ad]
            puan = max(benzerlik(eski["duyulan"], okunan), benzerlik(eski["duyulan"], c["yazi"]))
            eski.update(puan=round(puan, 3), uygun=bool(puan >= ESIK and HIZ[0] <= eski["hiz"] <= HIZ[1]))
            if eski["uygun"]:
                continue
            onceki = eski["deneme"]
            en_iyi = ({k: v for k, v in eski.items() if k != "yazi"}, sf.read(hedef / f"{ad}.wav", dtype="float32")[0])
        for deneme, cfg in enumerate(CFG):
            torch.manual_seed(7919 * (deneme + 1 + onceki) + i)
            dalga = tts.generate(okunan, language_id="tr", cfg_weight=cfg, temperature=0.7)
            ses = kirp(dalga.squeeze().cpu().numpy().astype(np.float32), tts.sr)
            aday = degerlendir(ses, c, okunan, onceki + deneme + 1)
            if en_iyi is None or (aday["uygun"], aday["puan"]) > (en_iyi[0]["uygun"], en_iyi[0]["puan"]):
                en_iyi = (aday, ses)
            if aday["uygun"]:
                break
        sf.write(hedef / f"{ad}.wav", en_iyi[1], tts.sr)
        rapor[ad] = {"yazi": c["yazi"], **en_iyi[0]}
        rapor_yolu.write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")
        print(ad, en_iyi[0]["puan"], en_iyi[0]["sure"], "OK" if en_iyi[0]["uygun"] else "KONTROL ET",
              "|", en_iyi[0]["duyulan"], flush=True)

if __name__ == "__main__":
    main()
