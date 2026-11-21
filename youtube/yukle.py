#!/usr/bin/env python3
"""Üretilen videoyu YouTube'a yükler (YouTube Data API v3, kaldığı yerden devam eden yükleme).

    python3 youtube/yukle.py youtube/cikti/2026-11-21-en.mp4

Aynı adlı .json dosyasından başlık, açıklama ve etiketleri alır. Kimlik bilgileri ortam değişkenlerindedir
(GitHub'da "Secrets" olarak saklanır, depoya asla yazılmaz):
    YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN_<DİL>   (ör. YT_REFRESH_TOKEN_EN)
Bilgiler yoksa hiçbir şey yapmadan çıkar.

Not: Google'ın denetiminden geçmemiş projelerin yüklediği videoları YouTube "özel" olarak kilitler.
Denetim onaylanınca aynı kod videoları herkese açık yayınlar.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

KATEGORI_EGITIM = '27'


def erisim_anahtari(dil):
    gerekli = ['YT_CLIENT_ID', 'YT_CLIENT_SECRET', f'YT_REFRESH_TOKEN_{dil.upper()}']
    if not all(os.environ.get(k) for k in gerekli):
        return None
    veri = urllib.parse.urlencode({
        'client_id': os.environ['YT_CLIENT_ID'], 'client_secret': os.environ['YT_CLIENT_SECRET'],
        'refresh_token': os.environ[f'YT_REFRESH_TOKEN_{dil.upper()}'], 'grant_type': 'refresh_token',
    }).encode()
    with urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token', data=veri), timeout=60) as y:
        return json.load(y)['access_token']


def yukle(video):
    video = Path(video)
    dil = video.stem.rsplit('-', 1)[-1]
    anahtar = erisim_anahtari(dil)
    if not anahtar:
        print(f'{video.name}: YouTube izinleri tanımlı değil, yükleme atlandı.')
        return None
    bilgi = json.loads(video.with_suffix('.json').read_text(encoding='utf-8'))
    govde = {
        'snippet': {
            'title': bilgi['baslik'][:100], 'description': bilgi['aciklama'][:5000],
            'tags': bilgi.get('etiketler', [])[:30], 'categoryId': KATEGORI_EGITIM,
            'defaultLanguage': dil, 'defaultAudioLanguage': dil,
        },
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False, 'embeddable': True},
    }
    boyut = video.stat().st_size
    baslat = urllib.request.Request(
        'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
        data=json.dumps(govde).encode(), method='POST',
        headers={'Authorization': f'Bearer {anahtar}', 'Content-Type': 'application/json; charset=UTF-8',
                 'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(boyut)})
    with urllib.request.urlopen(baslat, timeout=60) as y:
        adres = y.headers['Location']
    with open(video, 'rb') as f:
        istek = urllib.request.Request(adres, data=f.read(), method='PUT',
                                       headers={'Content-Type': 'video/mp4', 'Content-Length': str(boyut)})
    with urllib.request.urlopen(istek, timeout=600) as y:
        sonuc = json.load(y)
    durum = sonuc.get('status', {}).get('privacyStatus')
    print(f'{video.name}: yüklendi → https://youtu.be/{sonuc["id"]} (görünürlük: {durum})')
    if durum != 'public':
        print('  Not: YouTube videoyu herkese açık yapmadı. Google denetimi onaylanana kadar bu beklenen bir durum.')
    return sonuc['id']


if __name__ == '__main__':
    hata = 0
    for v in sys.argv[1:]:
        try:
            yukle(v)
        except Exception as e:  # bir dilin hatası ötekini durdurmasın
            hata = 1
            print(f'{v}: yükleme başarısız: {e}', file=sys.stderr)
    sys.exit(hata)
