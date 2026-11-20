// Döviz Kasası: alım-satım kârının makas kârı ve fiyat farkı olarak ayrılması.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = {
  tx: [
    { id: '1', seq: 1, date: iso(5), type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: iso(4), type: 'in', cur: 'USD', amount: 1000, rate: 50, note: '' },
    { id: '3', seq: 3, date: iso(1), type: 'in', cur: 'USD', amount: 100, rate: 52, note: '' },     // ortalama 55.200 / 1.100
    { id: 'E', seq: 4, date: iso(1), type: 'out', cur: 'USD', amount: 100, rate: 52.4, note: 'eski kayıt' },   // ref yok: son alış 52
  ],
  rates: { USD: 52.1 }, sell: { USD: 52.3 }, myRates: { USD: { buy: 52.2, sell: 52.6 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
};
const tl = (n) => (n < 0 ? '−' : '+') + '₺' + Math.abs(n).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

(async () => {
  const b = await chromium.launch();
  const errors = [];
  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const ctx = await b.newContext(opts);
    await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => d.accept());
    await p.addInitScript((seed) => { if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed)); }, SEED);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    const avg = 55200 / 1100;

    // Dünkü eski satış: kâr 100 × (52,40 − 50,1818) = 221,82; makas 100 × (52,40 − 52,00) = 40; fiyat farkı 181,82
    await p.click('button[data-go="gun"]'); await p.click('#dayPrev');
    assert.equal(await txt('#dProfit'), tl(100 * (52.4 - avg)));
    assert.equal(await txt('#dProfitAlt'), 'makas +₺40,00 · fiyat farkı ' + tl(100 * (52.4 - avg) - 40));

    // Bugün yeni satış: referans o anki alış kurunuz (52,20) yazılır
    await p.click('button[data-go="islem"]');
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tOut"]');
    await p.fill('#fAmount', '200'); await p.fill('#fRate', '52,6');
    await p.click('#btnSave');
    let st = await store();
    const s = st.tx[st.tx.length - 1];
    assert.equal(s.ref, 52.2);
    const p2 = 200 * (52.6 - avg);                                                 // ortalama satışla değişmez
    assert.equal(await txt('#mSplit'), 'Makastan +₺80,00 · fiyat farkından ' + tl(p2 - 80));   // 200 × 0,40
    await p.click('button[data-go="gun"]'); await p.click('#dayToday');
    assert.equal(await txt('#dProfitAlt'), 'makas +₺80,00 · fiyat farkı ' + tl(p2 - 80));
    // Analiz: toplam kâr ve makas
    await p.click('#modeAn'); await p.selectOption('#anRange', 'all');
    assert.equal(await txt('#dProfitAlt'), 'makas +₺120,00 · fiyat farkı ' + tl(100 * (52.4 - avg) + p2 - 120));
    assert.ok((await txt('#anBody')).includes('makas +₺120,00'));
    // Paylaşılan rapor ayrımı içerir
    await p.evaluate(() => { navigator.share = (d) => { window.__s = d.text; return Promise.resolve(); }; });
    await p.click('#btnShareDay');
    assert.ok((await p.evaluate(() => window.__s)).includes('(makas +₺120,00 · fiyat farkı'));
    await p.click('#modeDay');
    // Düzenlemede referans korunur
    await p.click('button[data-go="liste"]');
    const row = p.locator('#txBody tr', { hasText: '52,6000' }).first();
    if (name === 'telefon') await row.locator('td').nth(2).click();
    await row.getByRole('button', { name: 'Düzenle' }).click();
    await p.fill('#fAmount', '150'); await p.click('#btnSave');
    st = await store();
    assert.equal(st.tx.find((t) => t.id === s.id).ref, 52.2);
    // İade makası da geri alır: 50 iade → makas 150 × 0,40 − 50 × 0,40 = 40
    await p.click('button[data-go="gun"]'); await p.click('button[data-go="liste"]');   // düzenleme ana sayfaya götürür
    const row2 = p.locator('#txBody tr', { hasText: '52,6000' }).first();
    if (name === 'telefon') await row2.locator('td').nth(2).click();
    await row2.getByRole('button', { name: 'İade' }).click();
    await p.fill('#dlgInput', '50'); await p.click('#dlgForm button[type="submit"]');
    await p.click('button[data-go="gun"]'); await p.click('#dayToday');
    assert.ok((await txt('#dProfitAlt')).startsWith('makas +₺40,00'), await txt('#dProfitAlt'));
    // Fiyat farkı olmayan günde (yalnız makas) ayrım satırı gizlenir
    await ctx.close();
  }
  // Fiyat farkı yoksa satır görünmez
  const ctx = await b.newContext({ viewport: { width: 420, height: 860 } });
  await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());
  await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
  const p = await ctx.newPage();
  p.on('pageerror', (e) => errors.push('duz: ' + e.message));
  await p.addInitScript(() => localStorage.setItem('doviz-kasasi-v1', JSON.stringify({ tx: [
    { id: '1', seq: 1, date: '2026-01-01', type: 'in', cur: 'TRY', amount: 10000, rate: 1, note: '' },
    { id: '2', seq: 2, date: '2026-01-02', type: 'in', cur: 'USD', amount: 100, rate: 50, note: '' },
    { id: '3', seq: 3, date: '2026-01-02', type: 'out', cur: 'USD', amount: 50, rate: 51, note: '' }] })));
  await p.goto(URL);
  await p.click('button[data-go="gun"]'); await p.fill('#dayDate', '2026-01-02'); await p.dispatchEvent('#dayDate', 'change');
  assert.equal((await p.textContent('#dProfit')).trim(), '+₺50,00');
  assert.equal((await p.textContent('#dProfitAlt')).trim(), '');
  await ctx.close();
  await b.close();
  assert.deepEqual(errors, []);
  console.log('MAKAS SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('makas.js')).slice(0, 2).join(' | ')); process.exit(1); });
