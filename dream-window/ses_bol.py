"""4K paketteki büyük sesi sohbetten gönderilebilir parçalara böler.

8 saatlik ses (~450 MB) tek dosyada sohbet sınırını (400 MiB) aşıyor. Ses, yeniden
kodlanmadan ADTS (.aac) akışına çevrilir ve çerçeve sınırlarından bayt bayt bölünür.
Parçalar ffmpeg'in "concat:" protokolüyle uç uca eklenince özgün akışın aynısı olur
(boşluk, tık ya da kayma yok). BIRLESTIR.bat parçaları bu yolla birleştirir.

Kullanım: python3 ses_bol.py <paket_klasoru> [<paket_klasoru> ...]
"""
import hashlib
import math
import pathlib
import subprocess
import sys

PARCA_SES = 150 * 1024 * 1024        # bir ses parçasının üst sınırı


def bat_yaz(hedef: pathlib.Path, ad: str):
    sesler = sorted(hedef.glob("ses_*.aac"), key=lambda p: int(p.stem.split("_")[1]))
    if sesler:
        giris = '-i "concat:' + "|".join(p.name for p in sesler) + '"'
        ek = " -bsf:a aac_adtstoasc"
        eksik = "".join(f'if not exist "{p.name}" (echo HATA: {p.name} yok. Butun zip parcalarini ayni klasore ac. & pause & exit /b)\r\n'
                        for p in sesler)
    else:
        giris, ek, eksik = "-i ses.m4a", "", ""
    (hedef / "BIRLESTIR.bat").write_text(
        "@echo off\r\ncd /d \"%~dp0\"\r\n" + eksik +
        "echo Video birlestiriliyor, lutfen bekleyin...\r\n"
        f"ffmpeg -v error -y -f concat -safe 0 -i liste.txt {giris} -map 0:v -map 1:a -c copy{ek} -shortest -movflags +faststart \"{ad}.mp4\"\r\n"
        f"if exist \"{ad}.mp4\" (echo HAZIR: {ad}.mp4) else (echo HATA: ffmpeg.exe bu klasorde mi?)\r\npause\r\n", encoding="ascii")


def _cerceveler(veri: bytes):
    """ADTS çerçeve başlangıçlarını döndürür."""
    i, n, bas = 0, len(veri), []
    while i < n:
        if veri[i] != 0xFF or (veri[i + 1] & 0xF6) != 0xF0:
            raise SystemExit(f"ADTS çözümlenemedi (bayt {i})")
        bas.append(i)
        i += ((veri[i + 3] & 0x03) << 11) | (veri[i + 4] << 3) | (veri[i + 5] >> 5)
    return bas


def sure(yol):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(yol)], capture_output=True, text=True)
    return float(r.stdout or 0)


def bol(hedef: pathlib.Path, ad: str | None = None):
    hedef = pathlib.Path(hedef)
    ad = ad or hedef.name.removeprefix("paket_")
    m4a = hedef / "ses.m4a"
    if not m4a.exists():
        if list(hedef.glob("ses_*.aac")):
            bat_yaz(hedef, ad)
            return "zaten bölünmüş"
        raise SystemExit(f"ses yok: {hedef}")
    if m4a.stat().st_size <= PARCA_SES:
        bat_yaz(hedef, ad)
        return "küçük, bölünmedi"
    akis = hedef / "_ses_tam.aac"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(m4a), "-c", "copy", "-f", "adts", str(akis)], check=True)
    veri = akis.read_bytes()
    cer = _cerceveler(veri)
    adet = math.ceil(len(veri) / PARCA_SES)
    sinir = [0]
    for k in range(1, adet):                                  # her sınır, eşit bölme noktasından sonraki ilk çerçeve başı
        hedef_bayt = len(veri) * k // adet
        sinir.append(next(c for c in cer if c >= hedef_bayt))
    sinir.append(len(veri))
    yollar = []
    for k in range(adet):
        y = hedef / f"ses_{k + 1}.aac"
        y.write_bytes(veri[sinir[k]:sinir[k + 1]])
        yollar.append(y)
    # doğrulama: parçalar uç uca özgün akışın aynısı mı, süre özgün sesle aynı mı
    h = hashlib.sha256()
    for y in yollar:
        h.update(y.read_bytes())
    if h.digest() != hashlib.sha256(veri).digest():
        raise SystemExit("parçalar özgün akışla aynı değil")
    sr = (96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350)[(veri[2] >> 2) & 0x0F]
    birlesik = len(cer) * 1024 / sr                          # her ADTS çerçevesi 1024 örnek
    ozgun = sure(m4a)
    if abs(birlesik - ozgun) > 1.0:
        raise SystemExit(f"süre tutmuyor: {birlesik:.1f} / {ozgun:.1f}")
    akis.unlink()
    m4a.unlink()
    bat_yaz(hedef, ad)
    return f"{adet} parça ({', '.join(f'{y.stat().st_size / 1048576:.0f}' for y in yollar)} MiB), {birlesik:.0f} sn"


if __name__ == "__main__":
    for k in sys.argv[1:]:
        print(k, bol(pathlib.Path(k)), flush=True)
