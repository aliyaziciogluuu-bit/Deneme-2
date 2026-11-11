// Oyunun web dosyasını (../golgekuyu.html) Android paketinin www klasörüne hazırlar:
// - yazı tipini çevrimdışı çalışsın diye pakete gömer,
// - Capacitor'ın tarayıcı tarafı betiğini ekler (geri tuşu gibi yerel özellikler için).
import { readFileSync, writeFileSync, mkdirSync, copyFileSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const app = join(dirname(fileURLToPath(import.meta.url)), '..');
const www = join(app, 'www');
let html = readFileSync(join(app, '..', 'golgekuyu.html'), 'utf8');

const fontLink = /<link rel="stylesheet" href="https:\/\/fonts\.googleapis\.com[^>]*>/;
if (!fontLink.test(html)) throw new Error('golgekuyu.html içinde yazı tipi bağlantısı bulunamadı');
const face = (file, range) =>
  `@font-face{font-family:'Pixelify Sans';font-style:normal;font-weight:400 700;font-display:swap;` +
  `src:url(fonts/${file}) format('woff2');unicode-range:${range}}`;
html = html.replace(fontLink, '<style>' +
  face('PixelifySans-latin-ext.woff2', 'U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF') +
  face('PixelifySans-latin.woff2', 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD') +
  '</style>');

const marker = '<div id="app" lang="tr">';
if (!html.includes(marker)) throw new Error('golgekuyu.html içinde oyun kabı bulunamadı');
html = html.replace(marker, '<script src="capacitor.js"></script>\n' + marker);

rmSync(www, { recursive: true, force: true });
mkdirSync(join(www, 'fonts'), { recursive: true });
writeFileSync(join(www, 'index.html'), html);
for (const f of ['PixelifySans-latin.woff2', 'PixelifySans-latin-ext.woff2', 'OFL.txt']) copyFileSync(join(app, 'fonts', f), join(www, 'fonts', f));
copyFileSync(join(app, 'node_modules', '@capacitor', 'core', 'dist', 'capacitor.js'), join(www, 'capacitor.js'));
console.log('www hazır:', join(www, 'index.html'));
