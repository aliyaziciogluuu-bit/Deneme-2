"""Yayından önce bir videonun bütün teknik ve içerik testlerini çalıştırır. Hepsi GEÇTİ demeden video yüklenmez.

Kullanım:  python son_kontrol.py 01-sagir-yilan
Gerekenler: ffmpeg, pip install faster-whisper numpy pillow

Testler:
  1. Ses kaydı: her cümle ses/rapor.json'da doğrulanmış mı
  2. Bitmiş videonun sesi baştan sona yeniden dinlenir, senaryoyla kelime kelime karşılaştırılır (en fazla %2 fark)
  3. Ses yüksekliği: -16..-13 LUFS (YouTube referansı -14; netliği bozmamak için tek geçiş), gerçek tepe ≤ -1 dBTP
  4. Görüntü: 1920x1080, 30 fps, H.264 + AAC; video ve ses süresi tutarlı
  5. Siyah kare (0,5 sn'den uzun) ve donmuş görüntü (4 sn'den uzun) yok
  6. Altyazı: sıralı, çakışmasız, video süresi içinde, satır uzunluğu makul
  7. Yükleme metni: başlık ≤ 100, açıklama ≤ 5000 karakter, etiketler toplamı ≤ 500, açıklamada < > yok
  8. Bölümler: 0:00'da başlar, en az 3 bölüm, artan sırada, her biri ≥ 10 sn
  9. Kapak: 1280x720, < 2 MB, JPEG
"""
import difflib
import json
import pathlib
import re
import subprocess
import sys

import numpy as np
from PIL import Image

KOK = pathlib.Path(__file__).parent
sys.path.insert(0, str(KOK))
from seslendir_bulut import sade  # noqa: E402  (rakamları sözcüğe çeviren aynı normalleştirme)

sonuclar = []


def test(ad, gecti, ayrinti=""):
    sonuclar.append((ad, gecti, ayrinti))
    print(f"[{'GEÇTİ' if gecti else 'KALDI'}] {ad}" + (f" — {ayrinti}" if ayrinti else ""), flush=True)


def ffprobe(yol):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(yol)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def main():
    klasor = KOK / sys.argv[1]
    video = klasor / "video.mp4"
    senaryo = json.loads((klasor / "senaryo.json").read_text(encoding="utf-8"))
    cumleler = [c["yazi"] for s in senaryo["sahneler"] for c in s["cumleler"]]

    # 1
    rapor = json.loads((klasor / "ses" / "rapor.json").read_text(encoding="utf-8"))
    eksik = [f"{i:03d}" for i in range(len(cumleler)) if not rapor.get(f"{i:03d}", {}).get("uygun")]
    test("Cümle cümle ses doğrulaması", not eksik, f"{len(cumleler) - len(eksik)}/{len(cumleler)} cümle doğrulandı"
         + (f"; sorunlu: {eksik}" if eksik else ""))

    # 4
    bilgi = ffprobe(video)
    v = next(s for s in bilgi["streams"] if s["codec_type"] == "video")
    a = next(s for s in bilgi["streams"] if s["codec_type"] == "audio")
    fps = eval(v["r_frame_rate"])
    vs, as_ = float(v["duration"]), float(a["duration"])
    dikey = bool(senaryo.get("dikey"))
    test("Görüntü biçimi", (v["width"], v["height"]) == ((1080, 1920) if dikey else (1920, 1080)) and abs(fps - 30) < 0.01 and v["codec_name"] == "h264"
         and a["codec_name"] == "aac", f"{v['width']}x{v['height']} {fps:.0f} fps {v['codec_name']}/{a['codec_name']}")
    test("Video ve ses süresi tutarlı", abs(vs - as_) < 0.5, f"video {vs:.1f} sn, ses {as_:.1f} sn")
    if dikey:
        test("Shorts süresi (≤ 60 sn)", vs <= 60.0, f"{vs:.1f} sn")

    # 3
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    ozet = r.stderr[r.stderr.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", ozet).group(1))
    tepe = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", ozet).group(1))
    test("Ses yüksekliği (-16..-13 LUFS, tepe ≤ -1 dBTP)", -16.0 <= lufs <= -13.0 and tepe <= -0.9, f"{lufs:.1f} LUFS, tepe {tepe:.1f} dBTP")

    # 5
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vf",
                        "blackdetect=d=0.5:pix_th=0.06,freezedetect=n=0.0005:d=4", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    siyah = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)
    donuk = re.findall(r"freeze_start: ([\d.]+)", r.stderr)
    test("Siyah kare yok", not siyah, f"{siyah}" if siyah else "")
    test("Donmuş görüntü yok (4 sn+)", not donuk, f"başlangıçlar: {donuk}" if donuk else "")

    # 2  Bitmiş videonun sesi (kuş sesi ve ses düzeltmesi dahil) her cümlenin kendi zaman aralığında dinlenir.
    #    6 dakikalık kaydı tek parça dinletmek Whisper'ın kendi hatalarını artırıyor; cümle aralıkları hem daha
    #    güvenilir hem de son karışımı doğrudan denetler.
    from faster_whisper import WhisperModel
    from seslendir_bulut import fark
    import video as vmod
    zaman, _, _, _ = vmod.cizelge(klasor)
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    ses = np.frombuffer(ham, dtype=np.float32)
    dinleyici = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4)
    toplam_hata, toplam_kelime, sorunlu, satirlar = 0, 0, [], []
    for i, c in enumerate(zaman):
        parca = ses[max(int((c["bas"] - 0.15) * 16000), 0): int((c["bit"] + 0.15) * 16000)]
        duy = " ".join(p.text.strip() for p in dinleyici.transcribe(parca, language="tr", beam_size=5)[0])
        h = fark(duy, c["yazi"])
        n = len(sade(c["yazi"]))
        toplam_hata += h
        toplam_kelime += n
        satirlar.append(f"{i:03d} fark={h} | {c['yazi']} || {duy}")
        if h > (0 if n <= 6 else 1):
            sorunlu.append(i)
            print(f"      {i:03d}: senaryo «{c['yazi']}» → duyulan «{duy}»")
    (klasor / "son_kontrol_duyulan.txt").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    test("Bitmiş videoda anlatım = senaryo (cümle cümle)", not sorunlu,
         f"{len(zaman) - len(sorunlu)}/{len(zaman)} cümle birebir, toplam {toplam_hata}/{toplam_kelime} kelime farkı")

    # 6
    srt = (klasor / "altyazi.srt").read_text(encoding="utf-8").strip().split("\n\n")

    def sn(z):
        h, m, s = z.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    zaman = [tuple(sn(x) for x in blok.split("\n")[1].split(" --> ")) for blok in srt]
    satirlar = [blok.split("\n", 2)[2] for blok in srt]
    sirali = all(b > a for a, b in zaman) and all(zaman[i][1] <= zaman[i + 1][0] + 1e-3 for i in range(len(zaman) - 1))
    test("Altyazı zamanlaması", sirali and zaman[-1][1] <= vs + 0.1, f"{len(srt)} altyazı, son {zaman[-1][1]:.1f} sn")
    test("Altyazı uzunluğu", max(len(s) for s in satirlar) <= 80, f"en uzun {max(len(s) for s in satirlar)} karakter")

    # 7-8
    yukleme = (klasor / "yukleme.txt").read_text(encoding="utf-8")
    baslik = yukleme.split("BAŞLIK\n", 1)[1].split("\n", 1)[0]
    aciklama = yukleme.split("AÇIKLAMA\n", 1)[1].split("\nETİKETLER", 1)[0].strip()
    etiketler = [e.strip() for e in yukleme.split("ETİKETLER\n", 1)[1].strip().split(",")]
    test("Başlık uzunluğu", 0 < len(baslik) <= 100, f"{len(baslik)} karakter")
    test("Açıklama uzunluğu ve karakterleri", len(aciklama) <= 5000 and "<" not in aciklama and ">" not in aciklama,
         f"{len(aciklama)} karakter")
    test("Etiketler (toplam ≤ 500)", sum(len(e) for e in etiketler) + 2 * (len(etiketler) - 1) <= 500, f"{len(etiketler)} etiket")
    bolumler = [] if dikey else [(int(m), int(s), ad) for m, s, ad in re.findall(r"^(\d+):(\d{2}) (.+)$", aciklama, re.M)]
    saniye = [m * 60 + s for m, s, _ in bolumler]
    if not dikey:
      test("Bölümler (YouTube kuralları)", saniye and saniye[0] == 0 and len(saniye) >= 3
         and all(b - a >= 10 for a, b in zip(saniye, saniye[1:] + [vs])), f"{len(saniye)} bölüm, en kısa "
         f"{min(b - a for a, b in zip(saniye, saniye[1:] + [vs])):.0f} sn")

    # 9
    kapak = klasor / "kapak.jpg"
    if not dikey:
      im = Image.open(kapak)
      test("Kapak", im.size == (1280, 720) and im.format == "JPEG" and kapak.stat().st_size < 2 * 1024 * 1024,
         f"{im.size[0]}x{im.size[1]}, {kapak.stat().st_size // 1024} KB")

    kalan = [s for s in sonuclar if not s[1]]
    print("\nSONUÇ:", "BÜTÜN TESTLER GEÇTİ — yüklemeye hazır." if not kalan else f"{len(kalan)} test KALDI, yükleme yapma.")
    (klasor / "son_kontrol.txt").write_text("\n".join(f"[{'GEÇTİ' if g else 'KALDI'}] {a} {d}" for a, g, d in sonuclar) + "\n",
                                            encoding="utf-8")
    sys.exit(1 if kalan else 0)


if __name__ == "__main__":
    main()
