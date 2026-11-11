#!/usr/bin/env python3
"""Uygulama simgelerini oyundaki Savaşçı karakterinden üretir.
Kullanım: python3 scripts/make-icons.py   (android-app klasöründen; Pillow gerekir)"""
import os, re
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, '..')
html = open(os.path.join(APP, '..', 'golgekuyu.html'), encoding='utf-8').read()
pal = dict(re.findall(r"(\w): '(#[0-9a-f]{6})'", re.search(r'const PAL = \{(.*?)\};', html, re.S).group(1)))
rows = re.findall(r"'([^']{8})'", re.search(r'warrior: \[(.*?)\]', html, re.S).group(1))
assert len(rows) == 8, rows
BG, RING, OUT = '#241b38', '#43385a', '#120d1c'

def sprite(cell):
    """10x10 hücrelik (1 hücre kenarlıklı) karakter resmi."""
    im = Image.new('RGBA', (10 * cell, 10 * cell), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    box = lambda i, j, w, h, c: d.rectangle([i * cell, j * cell, (i + w) * cell - 1, (j + h) * cell - 1], fill=c)
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != '.': box(i, j + 1, 3, 1, OUT); box(i + 1, j, 1, 3, OUT)
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch != '.': box(i + 1, j + 1, 1, 1, pal[ch])
    return im

def icon(size, shape, frac):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if shape == 'round': d.ellipse([0, 0, size - 1, size - 1], fill=BG, outline=RING, width=max(1, size // 32))
    elif shape == 'square': d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 6, fill=BG, outline=RING, width=max(1, size // 32))
    elif shape == 'full': d.rectangle([0, 0, size, size], fill=BG)
    sp = sprite(max(1, int(size * frac / 10)))
    # karakter 8 hücrelik alanın solunda durduğu için bir hücre sağa kaydırılır
    im.alpha_composite(sp, ((size - sp.width) // 2 + sp.width // 20, (size - sp.height) // 2))
    return im

res = os.path.join(APP, 'android', 'app', 'src', 'main', 'res')
for name, legacy, fg in [('mdpi', 48, 108), ('hdpi', 72, 162), ('xhdpi', 96, 216), ('xxhdpi', 144, 324), ('xxxhdpi', 192, 432)]:
    d = os.path.join(res, 'mipmap-' + name)
    icon(legacy, 'square', .72).save(os.path.join(d, 'ic_launcher.png'))
    icon(legacy, 'round', .6).save(os.path.join(d, 'ic_launcher_round.png'))
    icon(fg, None, .5).save(os.path.join(d, 'ic_launcher_foreground.png'))
os.makedirs(os.path.join(APP, 'store'), exist_ok=True)
icon(512, 'full', .7).save(os.path.join(APP, 'store', 'icon-512.png'))
print('simgeler üretildi')
