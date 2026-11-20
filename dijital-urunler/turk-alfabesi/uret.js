// Türk alfabesi kartlarını üretir: yazdırılabilir PDF'ler ve Etsy ilan görselleri.
//   node uret.js            (Playwright gerekir; bu depoda NODE_PATH ile verilir)
// Çıktı: cikti/<dil>/...pdf ve cikti/<dil>/etsy-*.png
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { resim } = require('./resimler');
const { HARFLER, METIN, SESLILER } = require('./kelimeler');

const KOK = __dirname;
// Sayfa önizlemeleri yalnızca kontrol içindir; satılmaz, depoya girmez.
const ONIZLEME = path.join(require('os').tmpdir(), 'turk-alfabesi-onizleme');
const URUNLER = [
  { dil: 'de', kagitlar: ['A4'], ad: 'Turkisches-Alphabet-Bildkarten' },
  { dil: 'en', kagitlar: ['A4', 'Letter'], ad: 'Turkish-Alphabet-Flashcards' },
];
const KAGIT = { A4: { w: 210, h: 297 }, Letter: { w: 215.9, h: 279.4 } };
const ZEMIN = ['#FFF1D6', '#E3F0FB', '#FDE4EC', '#E4F3DF', '#EEE6FA', '#FFE7D6'];
const VURGU = ['#D9731A', '#2F6FB8', '#C9436A', '#3A8452', '#7A47AC', '#CF4F28'];

const GORSEL = {
  de: {
    rozet: ['29 Bildkarten', 'Alphabet-Poster', 'Sofort-Download zum Ausdrucken'],
    tum: 'Alle 29 Buchstaben', tumAlt: 'Türkisches Wort, Bild und deutsche Übersetzung mit Artikel',
    ozel: 'Mit allen türkischen Sonderbuchstaben', ozelAlt: 'Ç, Ğ, I, İ, Ö, Ş und Ü – jeder Buchstabe mit eigener Karte',
    poster: 'Alphabet-Poster', posterAlt: 'A4, lässt sich auch in A3 drucken',
    icerik: 'Das ist enthalten',
    icerikler: ['Deckblatt und Elternseite auf Türkisch und Deutsch', '29 Bildkarten auf 5 Seiten zum Ausschneiden', 'Die 8 türkischen Vokale auf einen Blick', 'Alphabet-Poster für das Kinderzimmer', '4 Spielideen für zu Hause'],
    not: 'Digitales Produkt: Sie erhalten eine PDF-Datei, es wird nichts verschickt.',
    adimlar: ['Herunterladen', 'Ausdrucken', 'Ausschneiden', 'Spielen'],
    sayfa: 'Seiten',
  },
  en: {
    rozet: ['29 picture cards', 'Alphabet poster', 'Digital download · print at home'],
    tum: 'All 29 letters', tumAlt: 'Turkish word, picture and English translation',
    ozel: 'Every special Turkish letter', ozelAlt: 'Ç, Ğ, I, İ, Ö, Ş and Ü – each letter on its own card',
    poster: 'Alphabet poster', posterAlt: 'A4 or US Letter, also prints well larger',
    icerik: 'What’s included',
    icerikler: ['Cover and parents’ page in Turkish and English', '29 picture cards on 5 pages, ready to cut', 'The 8 Turkish vowels at a glance', 'Alphabet poster for the nursery', '4 game ideas to play at home', 'Two files: A4 and US Letter'],
    not: 'Digital download: you receive PDF files, nothing is shipped.',
    adimlar: ['Download', 'Print', 'Cut', 'Play'],
    sayfa: 'pages',
  },
};

/* ---------- Ortak parçalar ---------- */
const kacis = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
function fontCss() {
  const f = (ad) => fs.readFileSync(path.join(KOK, 'fontlar', ad)).toString('base64');
  const LATIN = 'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD';
  const EXT = 'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF';
  const yuz = (aile, agirlik, dosya) => [['latin', LATIN], ['latin-ext', EXT]].map(([k, r]) =>
    `@font-face{font-family:"${aile}";font-weight:${agirlik};font-style:normal;src:url(data:font/woff2;base64,${f(dosya.replace('*', k))}) format("woff2");unicode-range:${r}}`).join('');
  return yuz('Andika', 400, 'andika-*-400-normal.woff2') + yuz('Andika', 700, 'andika-*-700-normal.woff2') +
    yuz('Fredoka', 600, 'fredoka-*-600-normal.woff2') + yuz('Fredoka', 700, 'fredoka-*-700-normal.woff2');
}

const TEMEL_CSS = `
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:Andika,sans-serif;color:#3A2E39;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.kap{width:100%;height:100%;container-type:size}
.kart{position:relative;width:100%;height:100%;background:var(--zemin);border-radius:6cqw;border:.9cqw solid rgba(58,46,57,.12);overflow:hidden}
.kart .harf{position:absolute;left:7cqw;top:3.5cqh;font:700 21cqw/1.22 Fredoka,sans-serif;color:var(--vurgu);letter-spacing:-.02em}
.kart .harf small{font-size:15cqw;margin-left:1cqw}
.kart .resim{position:absolute;left:calc(60cqw - min(30cqw,26cqh));top:5cqh;width:min(60cqw,52cqh);height:min(60cqw,52cqh)}
.kart .resim svg{width:100%;height:100%;display:block}
.kart .kelime{position:absolute;left:0;right:0;bottom:16cqh;text-align:center;font:700 13cqw/1 Andika,sans-serif;letter-spacing:.01em}
.kart .kelime b{color:var(--vurgu)}
.kart .ceviri{position:absolute;left:4cqw;right:4cqw;bottom:6cqh;text-align:center;font:400 6.4cqw/1 Andika,sans-serif;color:#6E6370;white-space:nowrap}
.kap.bilgi>.kart{background:#fff;border-style:dashed;border-color:#D8D0D6}
.kap.bilgi .ic{position:absolute;inset:7cqw;display:flex;flex-direction:column;gap:2.6cqw}
.kap.bilgi h3{margin:0;font:700 11cqw/1 Fredoka,sans-serif;color:#3A8452}
.kap.bilgi p{margin:0;font-size:4.3cqw;line-height:1.3}
.kap.bilgi p.ikinci{color:#6E6370}
.kap.bilgi .sesli{display:flex;flex-wrap:wrap;gap:1.6cqw;margin-top:auto}
.kap.bilgi .sesli span{font:700 6.4cqw/1 Fredoka,sans-serif;background:#E4F3DF;color:#3A8452;border-radius:2cqw;padding:1.6cqw 2.4cqw}
.kap.mini .ceviri{font-size:8cqw}
.kap.yirmidokuz>.kart{background:#fff;border-style:dashed;border-color:#D8D0D6;display:flex;flex-direction:column;align-items:center;justify-content:center}
.kap.yirmidokuz strong{font:700 34cqw/1 Fredoka,sans-serif;color:#3A8452}
.kap.yirmidokuz span{font:700 10cqw/1.1 Andika,sans-serif;text-align:center}
`;

function vurgula(kelime, kucuk) {
  const i = kucuk === 'ğ' ? kelime.indexOf('ğ') : 0;
  return kacis(kelime.slice(0, i)) + '<b>' + kacis(kelime[i]) + '</b>' + kacis(kelime.slice(i + 1));
}
function kart(h, i, dil, sinif = '') {
  return `<div class="kap ${sinif}" style="--zemin:${ZEMIN[i % 6]};--vurgu:${VURGU[i % 6]}"><div class="kart">
    <div class="harf">${kacis(h.b)}<small>${kacis(h.k)}</small></div>
    <div class="resim">${resim(h.resim)}</div>
    <div class="kelime">${vurgula(h.kelime, h.k)}</div>
    <div class="ceviri">${kacis(h[dil])}</div></div></div>`;
}
function bilgiKarti(dil) {
  const t = METIN.tr, d = METIN[dil];
  return `<div class="kap bilgi"><div class="kart"><div class="ic"><h3>${kacis(t.bilgiBaslik)}</h3>
    <p>${kacis(t.bilgi)}</p><p class="ikinci">${kacis(d.bilgi)}</p>
    <div class="sesli">${SESLILER.map((s) => `<span>${s}</span>`).join('')}</div></div></div></div>`;
}

/* ---------- PDF ---------- */
function pdfHtml(dil, kagit) {
  const { w, h } = KAGIT[kagit];
  const t = METIN.tr, d = METIN[dil];
  const kartlar = HARFLER.map((x, i) => kart(x, i, dil)).concat(bilgiKarti(dil));
  const kartSayfalari = [];
  for (let s = 0; s < kartlar.length; s += 6) kartSayfalari.push(kartlar.slice(s, s + 6));
  const kapakSecme = ['Ç', 'Ğ', 'K', 'Ö', 'Ş', 'Ü'].map((b) => HARFLER.findIndex((x) => x.b === b));
  const sutun = (m, baslik, lang) => `<div class="sutun" lang="${lang}"><div class="dil">${baslik}</div>
      <h2>${kacis(m.kullanimBaslik)}</h2><ol>${m.kullanim.map((x) => `<li>${kacis(x)}</li>`).join('')}</ol>
      <h2>${kacis(m.oyunBaslik)}</h2>${m.oyunlar.map(([a, b]) => `<h4>${kacis(a)}</h4><p>${kacis(b)}</p>`).join('')}</div>`;
  const dilAdi = { tr: 'Türkçe', de: 'Deutsch', en: 'English' };

  return `<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>
${fontCss()}${TEMEL_CSS}
@page{size:${w}mm ${h}mm;margin:0}
.sayfa{width:${w}mm;height:${h}mm;position:relative;overflow:hidden;page-break-after:always;break-after:page}
.sayfa:last-child{page-break-after:auto;break-after:auto}
.altbilgi{position:absolute;left:0;right:0;bottom:6mm;text-align:center;font-size:7.5pt;color:#9A8F99}
.kapak{background:#FFF8EC;display:flex;flex-direction:column;align-items:center;padding:26mm 18mm 0}
.kapak h1{margin:0;font:700 40pt/1.05 Fredoka,sans-serif;text-align:center}
.kapak .ust{font:700 13pt/1.2 Andika,sans-serif;color:#3A8452;margin-bottom:5mm;letter-spacing:.06em;text-transform:uppercase}
.kapak .alt{margin:4mm 0 0;font:400 16pt/1.3 Andika,sans-serif;color:#6E6370;text-align:center}
.kapak .ornek{display:grid;grid-template-columns:repeat(3,48mm);grid-auto-rows:48mm;gap:7mm;margin-top:16mm}
.kapak .ornek>div:nth-child(odd){transform:rotate(-3deg)}.kapak .ornek>div:nth-child(even){transform:rotate(2.5deg)}
.kapak .not{margin-top:14mm;font:700 12pt/1.3 Andika,sans-serif;color:#3A2E39;background:#fff;border-radius:20mm;padding:3mm 8mm;border:.4mm solid #E6DCCB}
.rehber{padding:${kagit === 'Letter' ? '14mm 16mm' : '18mm 16mm'}}
.rehber h1{margin:0 0 8mm;font:700 24pt/1.1 Fredoka,sans-serif}
.rehber .iki{display:grid;grid-template-columns:1fr 1fr;gap:10mm}
.rehber .dil{font:700 8.5pt/1 Andika,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:#3A8452;border-bottom:.4mm solid #E4F3DF;padding-bottom:2mm}
.rehber h2{font:700 14pt/1.2 Fredoka,sans-serif;margin:6mm 0 2.5mm;color:#C9436A}
.rehber ol{margin:0;padding-left:5mm;font-size:10pt;line-height:1.45}
.rehber li{margin-bottom:2mm}
.rehber h4{margin:3.5mm 0 1mm;font:700 10.5pt/1.2 Andika,sans-serif}
.rehber p{margin:0;font-size:10pt;line-height:1.45}
.rehber .kucuk{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;margin-top:4mm;padding:0 ${kagit === 'Letter' ? 28 : 14}mm}
.rehber .kucuk>div{aspect-ratio:1}
.kartlar{padding:12mm 12mm 14mm;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:repeat(3,1fr);border-collapse:collapse}
.hucre{border:.3mm dashed #9A8F99;margin:0 -.15mm -.15mm 0;padding:3mm}
.poster{padding:12mm 11mm 12mm;display:flex;flex-direction:column}
.poster h1{margin:0;font:700 26pt/1 Fredoka,sans-serif;text-align:center}
.poster .alt{margin:2mm 0 6mm;text-align:center;font-size:11pt;color:#6E6370}
.poster .izgara{flex:1;display:grid;grid-template-columns:repeat(5,1fr);grid-template-rows:repeat(6,1fr);gap:2.6mm}
</style></head><body>

<section class="sayfa kapak">
  <div class="ust" lang="${dil}">${dil === 'de' ? 'Türkçe · Deutsch' : 'Türkçe · English'}</div>
  <h1>${kacis(t.baslik)}<br><span style="font-size:24pt;color:#6E6370">${kacis(d.baslik)}</span></h1>
  <p class="alt">${kacis(t.altBaslik)}<br>${kacis(d.altBaslik)}</p>
  <div class="ornek">${kapakSecme.map((i) => `<div>${kart(HARFLER[i], i, dil, 'mini')}</div>`).join('')}</div>
  <div class="not">${kacis(d.kapakNot)}</div>
  <div class="altbilgi">${kacis(t.alt)} ${kacis(d.alt)}</div>
</section>

<section class="sayfa rehber">
  <h1>${kacis(t.rehberBaslik)} · ${kacis(d.rehberBaslik)}</h1>
  <div class="iki">${sutun(t, dilAdi.tr, 'tr')}${sutun(d, dilAdi[dil], dil)}</div>
  <div class="dil" style="margin-top:12mm"><span lang="tr">${kacis(t.sesli)}</span> · <span lang="${dil}">${kacis(d.sesli)}</span></div>
  <div class="kucuk">${SESLILER.map((k) => { const i = HARFLER.findIndex((x) => x.k === k); return `<div>${kart(HARFLER[i], i, dil, 'mini')}</div>`; }).join('')}</div>
  <div class="altbilgi">${kacis(t.alt)} ${kacis(d.alt)}</div>
</section>

${kartSayfalari.map((s) => `<section class="sayfa kartlar">${s.map((k) => `<div class="hucre">${k}</div>`).join('')}</section>`).join('\n')}

<section class="sayfa poster">
  <h1>${kacis(t.posterBaslik)}</h1>
  <div class="alt">${kacis(d.posterBaslik)}</div>
  <div class="izgara">${HARFLER.map((x, i) => kart(x, i, dil, 'mini')).join('')}
    <div class="kap yirmidokuz"><div class="kart"><strong>29</strong><span>${kacis(t.bilgiBaslik.replace('29 ', ''))}<br><span style="color:#6E6370;font-weight:400">${kacis(d.bilgiBaslik.replace('29 ', ''))}</span></span></div></div></div>
</section>
</body></html>`;
}

/* ---------- Etsy görselleri (1000×750 css piksel, 2× çözünürlük = 2000×1500) ---------- */
function gorselHtml(dil, tur, pdfSayfalari) {
  const g = GORSEL[dil], t = METIN.tr, d = METIN[dil];
  const ortak = `<!doctype html><html><head><meta charset="utf-8"><style>${fontCss()}${TEMEL_CSS}
  body{width:1000px;height:750px;overflow:hidden;position:relative;background:#FFF8EC}
  h1{font:700 64px/1.02 Fredoka,sans-serif;margin:0}
  .ust{font:700 16px/1 Andika,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#3A8452}
  .alt{font:400 24px/1.3 Andika,sans-serif;color:#6E6370;margin:0}
  .rozetler{display:flex;flex-direction:column;gap:12px}
  .rozet{display:inline-flex;align-self:flex-start;font:700 20px/1 Andika,sans-serif;background:#fff;border:2px solid #E6DCCB;border-radius:40px;padding:12px 20px}
  .golge{box-shadow:0 14px 28px rgba(58,46,57,.16),0 3px 6px rgba(58,46,57,.10);border-radius:6%}
  .golge>.kap>.kart{border-radius:6cqw}
  .baslikbant{position:absolute;left:0;right:0;top:0;padding:36px 48px 0;text-align:center}
  .baslikbant h1{font-size:46px}.baslikbant p{margin:10px 0 0;font-size:20px;color:#6E6370}
  </style></head><body>`;
  const kartBul = (b) => { const i = HARFLER.findIndex((x) => x.b === b); return kart(HARFLER[i], i, dil); };
  const serit = (ust) => `<div style="position:absolute;left:0;right:0;top:${ust}px;display:flex;justify-content:center;align-items:center;gap:14px">
    ${g.adimlar.map((x, i) => `${i ? '<span style="font:700 22px/1 Andika,sans-serif;color:#BDB3BB">→</span>' : ''}<span style="display:inline-flex;align-items:center;gap:10px;font:700 19px/1 Andika,sans-serif;background:#fff;border:2px solid #E6DCCB;border-radius:40px;padding:10px 18px 10px 10px"><span style="display:inline-grid;place-items:center;width:28px;height:28px;border-radius:50%;background:#3A8452;color:#fff;font-size:15px">${i + 1}</span>${kacis(x)}</span>`).join('')}</div>`;

  if (tur === 'kapak') {
    const yer = [['Ç', 575, 64, -7, 186], ['K', 790, 84, 6, 176], ['Ü', 600, 290, 5, 196], ['Ş', 815, 300, -6, 168], ['Ğ', 585, 528, -4, 172], ['Ö', 790, 510, 7, 182]];
    return ortak + `<div style="position:absolute;left:56px;top:110px;width:470px;display:flex;flex-direction:column;gap:22px">
      <div class="ust">${dil === 'de' ? 'Türkçe · Deutsch' : 'Türkçe · English'}</div>
      <h1>${kacis(d.baslik)}</h1><p class="alt">${kacis(d.altBaslik)}</p>
      <div class="rozetler">${g.rozet.map((r) => `<span class="rozet">${kacis(r)}</span>`).join('')}</div></div>
      ${yer.map(([b, x, y, a, s]) => `<div class="golge" style="position:absolute;left:${x}px;top:${y}px;width:${s}px;height:${s}px;transform:rotate(${a}deg)">${kartBul(b)}</div>`).join('')}
    </body></html>`;
  }
  if (tur === 'tum') {
    return ortak + `<div class="baslikbant"><h1>${kacis(g.tum)}</h1><p>${kacis(g.tumAlt)}</p></div>
      <div style="position:absolute;left:0;right:0;top:158px;display:grid;grid-template-columns:repeat(8,106px);grid-auto-rows:106px;gap:14px;justify-content:center">
      ${HARFLER.map((x, i) => `<div class="golge">${kart(x, i, dil)}</div>`).join('')}</div>${serit(668)}</body></html>`;
  }
  if (tur === 'ozel') {
    return ortak + `<div class="baslikbant"><h1>${kacis(g.ozel)}</h1><p>${kacis(g.ozelAlt)}</p></div>
      <div style="position:absolute;left:60px;right:60px;top:186px;display:flex;flex-wrap:wrap;justify-content:center;gap:28px">
      ${['Ç', 'Ğ', 'I', 'İ', 'Ö', 'Ş', 'Ü'].map((b) => `<div class="golge" style="width:180px;height:180px">${kartBul(b)}</div>`).join('')}</div>${serit(640)}</body></html>`;
  }
  if (tur === 'poster') {
    return ortak.replace('background:#FFF8EC', 'background:#EFE7DC') + `
      <div style="position:absolute;left:0;right:0;bottom:0;height:120px;background:#D9C7AE"></div>
      <div style="position:absolute;left:300px;top:40px;width:400px;height:566px;background:#fff;border:16px solid #8C6A4A;box-shadow:0 18px 40px rgba(58,46,57,.28);padding:22px">
        <img src="${pdfSayfalari.poster}" style="width:100%;height:100%;object-fit:contain;display:block"></div>
      <div style="position:absolute;left:56px;top:250px;width:210px"><h1 style="font-size:40px">${kacis(g.poster)}</h1><p class="alt" style="font-size:19px;margin-top:12px">${kacis(g.posterAlt)}</p></div>
      <div class="golge" style="position:absolute;left:752px;top:470px;width:170px;height:170px;transform:rotate(6deg)">${kartBul('Z')}</div>
      <div class="golge" style="position:absolute;left:820px;top:330px;width:150px;height:150px;transform:rotate(-7deg)">${kartBul('A')}</div>
    </body></html>`;
  }
  if (tur === 'icerik') {
    const kucuk = (src, a) => `<img src="${src}" style="width:150px;border-radius:4px;box-shadow:0 10px 22px rgba(58,46,57,.18);transform:rotate(${a}deg);background:#fff">`;
    return ortak + `<div style="position:absolute;left:56px;top:70px;width:440px;display:flex;flex-direction:column;gap:18px">
      <h1 style="font-size:48px">${kacis(g.icerik)}</h1>
      <ul style="margin:6px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:14px">
      ${g.icerikler.map((x) => `<li style="font:400 21px/1.3 Andika,sans-serif;display:flex;gap:12px"><span style="color:#3A8452;font-weight:700">✓</span>${kacis(x)}</li>`).join('')}</ul>
      <p style="margin:18px 0 0;font:400 17px/1.35 Andika,sans-serif;color:#6E6370">${kacis(g.not)}</p></div>
      <div style="position:absolute;left:540px;top:80px;display:grid;grid-template-columns:repeat(2,170px);gap:30px 26px">
        ${kucuk(pdfSayfalari.kapak, -3)}${kucuk(pdfSayfalari.rehber, 2)}${kucuk(pdfSayfalari.kart, 2)}${kucuk(pdfSayfalari.poster, -2)}</div>
      <div style="position:absolute;left:540px;width:366px;top:604px;text-align:center;font:700 18px/1 Andika,sans-serif;color:#6E6370">${pdfSayfalari.sayi} ${kacis(g.sayfa)} · PDF</div>
    </body></html>`;
  }
  throw new Error(tur);
}

/* ---------- Çalıştır ---------- */
(async () => {
  const tarayici = await chromium.launch();
  for (const u of URUNLER) {
    const dizin = path.join(KOK, 'cikti', u.dil);
    fs.mkdirSync(dizin, { recursive: true });
    let sayfaResimleri = null;
    for (const k of u.kagitlar) {
      const sayfa = await tarayici.newPage();
      await sayfa.setContent(pdfHtml(u.dil, k), { waitUntil: 'load' });
      await sayfa.evaluate(() => document.fonts.ready);
      const yol = path.join(dizin, `${u.ad}-${k === 'A4' ? 'A4' : 'US-Letter'}.pdf`);
      await sayfa.pdf({ path: yol, preferCSSPageSize: true, printBackground: true });
      if (!sayfaResimleri) {
        // İlan görselleri için sayfa küçük resimleri (A4)
        const { w, h } = KAGIT[k];
        await sayfa.setViewportSize({ width: Math.round(w * 3.78), height: Math.round(h * 3.78) });
        const bolumler = await sayfa.$$('section.sayfa');
        const resimAl = async (i) => 'data:image/png;base64,' + (await bolumler[i].screenshot({ scale: 'device' })).toString('base64');
        sayfaResimleri = { kapak: await resimAl(0), rehber: await resimAl(1), kart: await resimAl(2), poster: await resimAl(bolumler.length - 1), sayi: bolumler.length };
        fs.mkdirSync(ONIZLEME, { recursive: true });
        for (let i = 0; i < bolumler.length; i++) await bolumler[i].screenshot({ path: path.join(ONIZLEME, `${u.dil}-sayfa-${i + 1}.png`) });
      }
      console.log('PDF', path.relative(KOK, yol), (fs.statSync(yol).size / 1024).toFixed(0) + ' KB');
      await sayfa.close();
    }
    const gorsel = await tarayici.newPage({ viewport: { width: 1000, height: 750 }, deviceScaleFactor: 2 });
    for (const [no, tur] of [[1, 'kapak'], [2, 'tum'], [3, 'ozel'], [4, 'poster'], [5, 'icerik']]) {
      await gorsel.setContent(gorselHtml(u.dil, tur, sayfaResimleri), { waitUntil: 'load' });
      await gorsel.evaluate(() => document.fonts.ready);
      const yol = path.join(dizin, `etsy-${no}-${tur}.png`);
      await gorsel.screenshot({ path: yol });
      console.log('PNG', path.relative(KOK, yol));
    }
    await gorsel.close();
  }
  await tarayici.close();
})().catch((e) => { console.error(e); process.exit(1); });
