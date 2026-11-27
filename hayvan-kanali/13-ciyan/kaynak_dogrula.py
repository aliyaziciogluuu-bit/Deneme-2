# -*- coding: utf-8 -*-
"""kaynak_eslesme.md satırlarını kaynaklar/ arşivinde doğrular.
Kullanım: python3 -I kaynak_dogrula.py   (bu klasörde)"""
import re,os,sys
D=os.path.dirname(os.path.abspath(__file__))
def norm(t): return re.sub(r'[\W_]+','',t.lower())
md=open(os.path.join(D,'kaynak_eslesme.md'),encoding='utf-8').read()
ok=bad=0
for ln in md.splitlines():
    m=re.match(r'- (\d+) → (https?://\S+) → (\S+) → «(.+)» → ',ln)
    if not m: continue
    no,url,dosya,ph=m.groups()
    p=os.path.join(D,'kaynaklar',dosya)
    if not os.path.exists(p): print('DOSYA YOK',no,dosya); bad+=1; continue
    arsiv=norm(open(p,encoding='utf-8',errors='ignore').read())
    if norm(ph) in arsiv: ok+=1
    else: print('BULUNAMADI',no,dosya,ph); bad+=1
sh=__import__('json')
S=sh.load(open(os.path.join(D,'senaryo.json'),encoding='utf-8'))
cum=[c['yazi'] for s in S['sahneler'] for c in s['cumleler']]
SH=sh.load(open(os.path.join(D,'shorts.json'),encoding='utf-8'))['shorts']
for s in SH:
    for c in s['cumleler']:
        if c['yazi']!='Tam videosu kanalımızda.' and c['yazi'] not in cum: print('SHORTS CÜMLESİ UZUNDA YOK',s['ad'],c['yazi']); bad+=1
print(f'cümle sayısı: {len(cum)}; doğrulanan ifade: {ok}; sorun: {bad}')
sys.exit(1 if bad else 0)
