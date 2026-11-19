// Döviz Kasası: kâr analizi sınaması.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const OUT = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'kasa-'));   // ekran görüntüleri
const URL = 'http://kasa.test/doviz-kasasi.html';
const ym = (back) => { const d = new Date(); const x = new Date(d.getFullYear(), d.getMonth() - back, 1);
  return x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0'); };
const [M0, M1, M2] = [ym(0), ym(1), ym(2)];
const SEED = { tx: [
  { id: '1', seq: 1, date: M2 + '-01', type: 'in', cur: 'TRY', amount: 1000000, rate: 1, note: 'Açılış' },
  { id: '2', seq: 2, date: M2 + '-01', type: 'in', cur: 'USD', amount: 1000, rate: 40, note: '' },
  { id: '3', seq: 3, date: M2 + '-01', type: 'out', cur: 'USD', amount: 600, rate: 41, note: '' },      // kâr 600
  { id: '4', seq: 4, date: M1 + '-01', type: 'in', cur: 'GA', amount: 100, rate: 3000, note: '' },
  { id: '5', seq: 5, date: M1 + '-01', type: 'out', cur: 'GA', amount: 40, rate: 3100, note: '' },       // kâr 4000
  { id: '6', seq: 6, date: M0 + '-01', type: 'out', cur: 'USD', amount: 400, rate: 42, note: '' },       // kâr 800
  { id: '7', seq: 7, date: M0 + '-01', type: 'out', cur: 'TRY', amount: 500, rate: 1, note: 'Çay', exp: true },
  { id: '8', seq: 8, date: M0 + '-01', type: 'out', cur: 'GA', amount: 5, rate: 3000, note: 'Emanet', cari: 'Ali' },   // cari: analize girmez
], rates: { USD: 42, GA: 3100 }, sell: {}, myRates: { USD: { buy: 41, sell: 42 } }, ratesUpdated: new Date().toISOString(), rateSrc: 'tr' };

(async () => {
  const b = await chromium.launch();
  const errors = [];
  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const ctx = await b.newContext(opts);
    await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    await p.addInitScript((seed) => localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed)), SEED);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    await p.click('button[data-go="gun"]');
    await p.click('#modeAn');
    assert.equal(await txt('#dayTitle'), 'Kâr analizi');
    assert.ok(await p.isVisible('#anWrap') && await p.isHidden('#dayWrap') && await p.isHidden('#monthWrap'));
    assert.ok(await p.isHidden('#dayDate') && await p.isHidden('#dayPrev') && await p.isVisible('#anRange'));
    // Son 12 ay: kâr 600 + 4000 + 800 = 5400, masraf 500
    assert.equal(await txt('#dProfit'), '+₺5.400,00');
    assert.equal(await txt('#dExp'), '₺500,00');
    assert.equal(await txt('#dNet'), '+₺4.900,00');
    const rows = await p.locator('#anBody tr').allTextContents();
    assert.equal(rows.length, 2);
    const ga = rows[0].replace(/\s+/g, ' '), usd = rows[1].replace(/\s+/g, ' ');
    assert.ok(ga.includes('Gram Altın') && ga.includes('3.000,00') && ga.includes('3.100,00') && ga.includes('100,00 (+%3,33)') && ga.includes('+₺4.000,00') && ga.includes('%74'), ga);
    assert.ok(usd.includes('USD') && usd.includes('40,0000') && usd.includes('41,4000') && usd.includes('1,4000 (+%3,50)') && usd.includes('+₺1.400,00') && usd.includes('%26'), usd);
    assert.equal(await p.locator('#anChart rect').count(), 3);
    assert.equal((await p.locator('#anChart text').allTextContents()).filter((t) => /^[A-ZŞÇÖÜİ][a-zşçöüğı]{2}$/.test(t)).length, 12);
    await p.screenshot({ path: OUT + '/' + name + '-analiz.png', fullPage: true });
    // Bu ay: yalnız dolar satışı (kâr 800), masraf 500
    await p.selectOption('#anRange', 'm1');
    assert.equal(await txt('#dNet'), '+₺300,00');
    const one = await p.locator('#anBody tr').allTextContents();
    assert.equal(one.length, 1);
    assert.ok(one[0].includes('42,0000') && one[0].includes('+₺800,00'), one[0]);
    // Güne ve aya dönüş çalışıyor
    await p.click('#modeMonth');
    assert.ok(await p.isVisible('#monthWrap') && await p.isHidden('#anWrap') && await p.isVisible('#dayPrev') && await p.isHidden('#anRange'));
    await p.click('#modeDay');
    assert.ok(await p.isVisible('#dayWrap') && await p.isVisible('#dayDate'));
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('ANALİZ SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('analiz.js')).slice(0, 2).join(' | ')); process.exit(1); });
