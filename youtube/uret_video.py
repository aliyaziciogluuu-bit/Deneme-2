#!/usr/bin/env python3
"""Tarihte Bugün Shorts üretici.

Bir senaryo dosyasından (youtube/senaryolar/YYYY-AA-GG.json) her dil için 1080x1920 dikey video üretir:
Wikimedia Commons'tan telifsiz görseller, Piper ile yapay seslendirme, Freesound'dan CC0 müzik, altyazı.

    python3 youtube/uret_video.py youtube/senaryolar/2026-11-21.json [--dil tr] [--dil en]

Çıktı: youtube/cikti/<tarih>-<dil>.mp4 ve aynı adla .json (YouTube başlık, açıklama, etiketler).
Gerekenler: ffmpeg, `pip install piper-tts`. Freesound için FREESOUND_TOKEN ortam değişkeni (bu oturumda gerekmez).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

KOK = Path(__file__).resolve().parent
ONBELLEK = Path(os.environ.get('YT_ONBELLEK', KOK / '.onbellek'))
FONT_DIZIN = KOK / 'fontlar'
UA = 'tarihte-bugun-shorts/0.1 (egitim amacli)'
G, Y = 1080, 1920          # video boyutu
FPS = 30
GECIS = 0.4                # sahne geçişi (sn)
DURAK = 0.28               # cümleler arası sessizlik (sn)
ON_BOSLUK = 0.25           # videonun başındaki sessizlik
KUTU = (60, 300, 960, 1060)  # ön plan görselinin kutusu: x, y, genişlik, yükseklik
IZINLI_LISANS = ('public domain', 'cc0', 'pd', 'cc by', 'cc-by', 'no restrictions')


def indir(url, hedef, basliklar=None):
    hedef = Path(hedef)
    if hedef.exists() and hedef.stat().st_size > 0:
        return hedef
    hedef.parent.mkdir(parents=True, exist_ok=True)
    istek = urllib.request.Request(url, headers={'User-Agent': UA, **(basliklar or {})})
    for deneme in range(4):
        try:
            with urllib.request.urlopen(istek, timeout=180) as y, open(hedef, 'wb') as f:
                shutil.copyfileobj(y, f)
            return hedef
        except urllib.error.HTTPError as e:
            # Sunucu "yavaşla" derse istediği kadar bekle; sınırı zorlamadan tekrar dene.
            if e.code != 429 or deneme == 3:
                raise
            bekle = int(e.headers.get('Retry-After') or 0) or 20 * (deneme + 1)
            print(f'  sunucu bekleme istedi, {bekle} sn bekleniyor…', file=sys.stderr)
            time.sleep(min(bekle, 120))


def json_al(url, basliklar=None):
    istek = urllib.request.Request(url, headers={'User-Agent': UA, **(basliklar or {})})
    for deneme in range(5):
        try:
            with urllib.request.urlopen(istek, timeout=60) as y:
                return json.load(y)
        except urllib.error.HTTPError as e:
            if e.code != 429 or deneme == 4:
                raise
            bekle = int(e.headers.get('Retry-After') or 0) or 20 * (deneme + 1)
            print(f'  sunucu bekleme istedi, {bekle} sn bekleniyor…', file=sys.stderr)
            time.sleep(min(bekle, 120))


def calistir(komut):
    s = subprocess.run(komut, capture_output=True, text=True)
    if s.returncode != 0:
        sys.stderr.write(s.stderr[-3000:])
        raise SystemExit('Komut başarısız: ' + ' '.join(map(str, komut[:6])) + ' …')
    return s


# ---------- Kaynaklar ----------
def ses_modeli(ad):
    dil, bolge = ad.split('-')[0], ad.split('-')[0].split('_')[0]
    _, konusmaci, kalite = ad.split('-')
    taban = f'https://huggingface.co/rhasspy/piper-voices/resolve/main/{bolge}/{dil}/{konusmaci}/{kalite}/{ad}'
    m = indir(taban + '.onnx', ONBELLEK / 'sesler' / f'{ad}.onnx')
    indir(taban + '.onnx.json', ONBELLEK / 'sesler' / f'{ad}.onnx.json')
    return m


def gorsel(dosya_adi):
    """Commons dosyasını 960 px genişlikte (Wikimedia'nın standart boyutu) JPEG olarak indirir; lisansı kontrol eder."""
    q = urllib.parse.urlencode({'action': 'query', 'titles': dosya_adi, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata',
                                'iiurlwidth': 960, 'iiextmetadatafilter': 'LicenseShortName|Artist', 'format': 'json'})
    d = json_al('https://commons.wikimedia.org/w/api.php?' + q)
    sayfa = next(iter(d['query']['pages'].values()))
    if 'imageinfo' not in sayfa:
        raise SystemExit('Commons dosyası bulunamadı: ' + dosya_adi)
    bilgi = sayfa['imageinfo'][0]
    lisans = bilgi.get('extmetadata', {}).get('LicenseShortName', {}).get('value', '')
    if not any(k in lisans.lower() for k in IZINLI_LISANS):
        raise SystemExit(f'Lisans uygun değil ({lisans}): {dosya_adi}')
    ad = ONBELLEK / 'gorseller' / (hashlib.md5(dosya_adi.encode('utf-8')).hexdigest() + '.jpg')
    adres = bilgi.get('thumburl') or bilgi['url']
    # Küçük görseller thumb.wikimedia.org'dan da verilir; aynı dosya upload.wikimedia.org altında da durur.
    adres = adres.replace('://thumb.wikimedia.org/', '://upload.wikimedia.org/')
    yol = indir(adres, ad)
    return yol, lisans


def muzik(bilgi):
    """Freesound'dan CC0 müzik. Anahtar yoksa senaryodaki önizleme adresinden indirir (herkese açık)."""
    freesound_id = bilgi['freesound_id']
    hedef = ONBELLEK / 'muzik' / f'{freesound_id}.mp3'
    if hedef.exists():
        return hedef
    if bilgi.get('lisans') != 'CC0':
        raise SystemExit('Müzik CC0 değil: ' + str(freesound_id))
    if not os.environ.get('FREESOUND_TOKEN') and bilgi.get('onizleme'):
        return indir(bilgi['onizleme'], hedef)
    basliklar = {}
    if os.environ.get('FREESOUND_TOKEN'):
        basliklar['Authorization'] = 'Token ' + os.environ['FREESOUND_TOKEN']
    d = json_al(f'https://freesound.org/apiv2/sounds/{freesound_id}/?fields=id,license,previews', basliklar)
    if 'creativecommons.org/publicdomain/zero' not in d.get('license', ''):
        raise SystemExit('Müzik CC0 değil: ' + str(freesound_id))
    return indir(d['previews']['preview-hq-mp3'], hedef, basliklar)


def seslendir(model, metin, hedef):
    s = subprocess.run([sys.executable, '-m', 'piper', '-m', str(model), '-f', str(hedef)], input=metin,
                       capture_output=True, text=True)
    if s.returncode != 0:
        sys.stderr.write(s.stderr[-2000:])
        raise SystemExit('Seslendirme başarısız')
    with wave.open(str(hedef)) as w:
        return w.getnframes() / w.getframerate()


# ---------- Altyazı ----------
def ass_zaman(t):
    s = max(0, t)
    return f'{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}'


def ass_kacis(t):
    return t.replace('\\', '').replace('{', '(').replace('}', ')')


def altyazi(dil_verisi, zamanlar, toplam, hedef):
    ust = ass_kacis(dil_verisi['ust_baslik'])
    tarih = ass_kacis(dil_verisi['tarih_yazisi'])
    satirlar = [
        '[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {G}', f'PlayResY: {Y}', 'WrapStyle: 0', 'ScaledBorderAndShadow: yes', '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Ust,Baloo 2 ExtraBold,74,&H0040D8FF,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,4,0,1,5,0,8,60,60,92,1',
        'Style: Tarih,Baloo 2 ExtraBold,58,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,2,0,1,4,0,8,60,60,182,1',
        'Style: Yazi,Baloo 2 ExtraBold,70,&H00FFFFFF,&H000000FF,&H00101010,&HA0000000,0,0,0,0,100,100,0,0,1,6,2,2,80,80,250,1',
        '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
        f'Dialogue: 0,{ass_zaman(0)},{ass_zaman(toplam)},Ust,,0,0,0,,{ust}',
        f'Dialogue: 0,{ass_zaman(0)},{ass_zaman(toplam)},Tarih,,0,0,0,,{tarih}',
    ]
    for (bas, son), c in zip(zamanlar, dil_verisi['cumleler']):
        satirlar.append(f'Dialogue: 1,{ass_zaman(bas)},{ass_zaman(son)},Yazi,,0,0,0,,{{\\fad(120,80)}}{ass_kacis(c["yazi"])}')
    Path(hedef).write_text('\n'.join(satirlar) + '\n', encoding='utf-8')


# ---------- Görüntü ----------
def sahne_klibi(gorsel_yolu, sure, hedef):
    """Bulanık arka plan + yavaşça yakınlaşan ön plan."""
    kx, ky, kg, kyuk = KUTU
    kare = max(1, round(sure * FPS))
    filtre = (
        f'[0:v]scale={G}:{Y}:force_original_aspect_ratio=increase,crop={G}:{Y},gblur=sigma=38,'
        f'eq=brightness=-0.22:saturation=0.75,setsar=1[bg];'
        f'[0:v]scale={kg}:{kyuk}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,split[o1][o2];'
        f'[o1]scale=iw*2:ih*2,zoompan=z=\'1+0.07*on/{kare}\':x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':d=1:fps={FPS}:s=WxH[zz];'
        f'[o2]null[boyut];'
    )
    # zoompan'ın çıktı boyutu ön planla aynı olmalı; önce boyutu öğren.
    s = calistir(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', str(gorsel_yolu)])
    w0, h0 = map(int, s.stdout.strip().split(',')[:2])
    oran = min(kg / w0, kyuk / h0)
    w, h = int(w0 * oran) // 2 * 2, int(h0 * oran) // 2 * 2
    filtre = (
        f'[0:v]scale={G}:{Y}:force_original_aspect_ratio=increase,crop={G}:{Y},gblur=sigma=38,'
        f'eq=brightness=-0.22:saturation=0.75,setsar=1[bg];'
        f'[0:v]scale={w * 2}:{h * 2},setsar=1,zoompan=z=\'1+0.07*on/{kare}\':x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':d=1:fps={FPS}:s={w}x{h}[fg];'
        f'[bg][fg]overlay=x={kx + (kg - w) // 2}:y={ky + (kyuk - h) // 2}:shortest=1,format=yuv420p[v]'
    )
    calistir(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-framerate', str(FPS), '-t', f'{sure:.3f}', '-i', str(gorsel_yolu),
              '-filter_complex', filtre, '-map', '[v]', '-r', str(FPS), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
              '-t', f'{sure:.3f}', str(hedef)])


def birlestir(klipler, sureler, hedef):
    """Klipleri çapraz geçişle birleştirir. sureler: her sahnenin gerçek süresi (geçiş payı hariç)."""
    if len(klipler) == 1:
        shutil.copy(klipler[0], hedef)
        return
    girisler = sum([['-i', str(k)] for k in klipler], [])
    parcalar, onceki, birikim = [], '[0:v]', 0.0
    for i in range(1, len(klipler)):
        birikim += sureler[i - 1]
        cikis = f'[x{i}]' if i < len(klipler) - 1 else '[v]'
        parcalar.append(f'{onceki}[{i}:v]xfade=transition=fade:duration={GECIS}:offset={birikim:.3f}{cikis}')
        onceki = cikis
    calistir(['ffmpeg', '-y', '-loglevel', 'error', *girisler, '-filter_complex', ';'.join(parcalar), '-map', '[v]',
              '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', str(hedef)])


# ---------- Ana akış ----------
def uret(senaryo_yolu, dil):
    sen = json.loads(Path(senaryo_yolu).read_text(encoding='utf-8'))
    dv = sen['diller'][dil]
    is_dizini = ONBELLEK / 'is' / f'{sen["tarih"]}-{dil}'
    if is_dizini.exists():
        shutil.rmtree(is_dizini)
    is_dizini.mkdir(parents=True)

    model = ses_modeli(dv['ses'])
    gorseller = []
    for s in sen['sahneler']:
        gorseller.append(gorsel(s['gorsel']))
        time.sleep(1)  # Wikimedia'ya arka arkaya yüklenmemek için
    muzik_yolu = muzik(sen['muzik'])

    # Seslendirme ve zamanlama
    zamanlar, ses_parcalari, t = [], [], ON_BOSLUK
    for i, c in enumerate(dv['cumleler']):
        wav = is_dizini / f'c{i:02d}.wav'
        sure = seslendir(model, c['okunus'], wav)
        zamanlar.append((t, t + sure))
        ses_parcalari.append(wav)
        t += sure + DURAK
    toplam = t + 0.6

    # Sahne süreleri: her sahne, kendi ilk cümlesinden bir sonraki sahnenin ilk cümlesine kadar sürer.
    ilk = {}
    for i, c in enumerate(dv['cumleler']):
        ilk.setdefault(c['sahne'], zamanlar[i][0])
    sahne_sirasi = list(ilk)
    if sahne_sirasi != sorted(sahne_sirasi):
        raise SystemExit('Cümlelerin sahne numaraları sırayla artmalı (0, 0, 1, 2, …)')
    sinirlar = [0.0] + [ilk[s] - DURAK / 2 for s in sahne_sirasi[1:]] + [toplam]
    sureler = [sinirlar[i + 1] - sinirlar[i] for i in range(len(sahne_sirasi))]

    klipler = []
    for i, s in enumerate(sahne_sirasi):
        hedef = is_dizini / f'sahne{i}.mp4'
        sahne_klibi(gorseller[s][0], sureler[i] + (GECIS if i < len(sahne_sirasi) - 1 else 0), hedef)
        klipler.append(hedef)
    sessiz = is_dizini / 'goruntu.mp4'
    birlestir(klipler, sureler, sessiz)

    # Ses: anlatım + kısık müzik
    liste = is_dizini / 'liste.txt'
    parcalar = []
    sessizlik = is_dizini / 'sessiz.wav'
    calistir(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=22050:cl=mono', '-t', str(DURAK), str(sessizlik)])
    bas_sessiz = is_dizini / 'bas.wav'
    calistir(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=22050:cl=mono', '-t', str(ON_BOSLUK), str(bas_sessiz)])
    parcalar.append(bas_sessiz)
    for w in ses_parcalari:
        parcalar += [w, sessizlik]
    # Farklı örnekleme hızlarını tek hıza çevir
    duz = []
    for i, p in enumerate(parcalar):
        q = is_dizini / f'd{i:03d}.wav'
        calistir(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(p), '-ar', '44100', '-ac', '1', str(q)])
        duz.append(q)
    liste.write_text(''.join(f"file '{p}'\n" for p in duz))
    anlatim = is_dizini / 'anlatim.wav'
    calistir(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(liste), '-c', 'copy', str(anlatim)])

    ass = is_dizini / 'altyazi.ass'
    altyazi(dv, zamanlar, toplam, ass)

    cikti_dizini = KOK / 'cikti'
    cikti_dizini.mkdir(exist_ok=True)
    cikti = cikti_dizini / f'{sen["tarih"]}-{dil}.mp4'
    ses_filtre = (
        f'[1:a]aresample=44100,apad=whole_dur={toplam:.3f}[anl];'
        f'[2:a]aresample=44100,atrim=0:{toplam:.3f},volume=0.13,afade=t=in:d=1,afade=t=out:st={toplam - 1.5:.3f}:d=1.5[muz];'
        f'[anl][muz]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]'
    )
    vf = f"[0:v]ass='{ass}':fontsdir='{FONT_DIZIN}'[v]"
    calistir(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(sessiz), '-i', str(anlatim), '-stream_loop', '-1', '-i', str(muzik_yolu),
              '-filter_complex', vf + ';' + ses_filtre, '-map', '[v]', '-map', '[a]', '-t', f'{toplam:.3f}',
              '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS),
              '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-movflags', '+faststart', str(cikti)])

    bilgi = dict(dv['youtube'])
    bilgi['sure_sn'] = round(toplam, 1)
    bilgi['gorsel_lisanslari'] = [{'dosya': s['gorsel'], 'lisans': gorseller[i][1]} for i, s in enumerate(sen['sahneler'])]
    (cikti_dizini / f'{sen["tarih"]}-{dil}.json').write_text(json.dumps(bilgi, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{cikti.relative_to(KOK.parent)}  {toplam:.1f} sn')
    return cikti


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('senaryo')
    ap.add_argument('--dil', action='append')
    a = ap.parse_args()
    diller = a.dil or list(json.loads(Path(a.senaryo).read_text(encoding='utf-8'))['diller'])
    for d in diller:
        uret(a.senaryo, d)
