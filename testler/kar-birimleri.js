// Döviz Kasası: kârın TL, dolar ve has olarak gösterimi.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const OUT = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'kasa-'));   // ekran görüntüleri
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = {
  tx: [
    { id: '1', seq: 1, date: iso(2), type: 'in', cur: 'TRY', amount: 100000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: iso(2), type: 'in', cur: 'USD', amount: 1000, rate: 40, note: '' },
    { id: '3', seq: 3, date: iso(1), type: 'out', cur: 'USD', amount: 600, rate: 42, note: '' },     // dün: kâr 1200
    { id: '4', seq: 4, date: iso(0), type: 'out', cur: 'USD', amount: 400, rate: 43, note: '' },     // bugün: kâr 1200
    { id: '5', seq: 5, date: iso(0), type: 'out', cur: 'TRY', amount: 150, rate: 1, note: 'Çay', exp: true },
  ],
  rates: { USD: 41, HAS: 2990 }, sell: { USD: 41.5, HAS: 3000 },
  myRates: { USD: { buy: 41, sell: 42 }, HAS: { buy: 2950, sell: 3050 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
  fx: { [iso(1)]: [40, 3000], 'bozuk': [1, 2], [iso(400)]: 'x' },
};

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (name, opts, seed) => {
    const ctx = await b.newContext(opts);
    await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => d.accept());
    await p.addInitScript((seed) => { if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed)); }, seed);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    return { ctx, p, txt };
  };
  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const { ctx, p, txt } = await open(name, opts, SEED);
    // Bugün: net 1050 TL; kur kaydı yok → bugünkü satış kurları (42 ve 3050)
    assert.equal(await txt('#mToday'), '+₺1.050,00');
    assert.equal(await txt('#mTodayAlt'), '≈ $25,00 · 0,34 gr has');
    await p.click('button[data-go="kasa"]');
    assert.ok((await txt('#sTodaySub')).includes('≈ $25,00 · 0,34 gr has'), await txt('#sTodaySub'));
    await p.click('button[data-go="gun"]');
    assert.equal(await txt('#dNet'), '+₺1.050,00');
    assert.equal(await txt('#dNetUsd'), '$25,00'); assert.equal(await txt('#dNetHas'), '0,34 gr');
    await p.screenshot({ path: OUT + '/' + name + '-kar.png' });
    // Dün: net 1200 TL; o günün kayıtlı kurlarıyla (40 ve 3000)
    await p.click('#dayPrev');
    assert.equal(await txt('#dNet'), '+₺1.200,00');
    assert.equal(await txt('#dNetUsd'), '$30,00'); assert.equal(await txt('#dNetHas'), '0,40 gr');
    // İşlem olmayan gün: sıfır yazılır
    await p.click('#dayPrev');
    assert.equal(await txt('#dNetUsd'), '$0,00'); assert.equal(await txt('#dNetHas'), '0,00 gr');
    // Analiz, tüm dönem: 30 + 25 dolar; 0,40 + 0,3443 gr has
    await p.click('#modeAn'); await p.selectOption('#anRange', 'all');
    assert.equal(await txt('#dNet'), '+₺2.250,00');
    assert.equal(await txt('#dNetUsd'), '$55,00'); assert.equal(await txt('#dNetHas'), '0,74 gr');
    assert.ok((await txt('#dayFoot')).includes('Dolar ve has karşılığı'));
    // Has fiyatı değişince bugünün kuru kaydedilir; dünün karşılığı değişmez
    await p.click('button[data-go="hesap"]');
    await p.fill('#hasSell', '3500'); await p.dispatchEvent('#hasSell', 'change');
    const st = await p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    const today = Object.keys(st.fx).sort().pop();
    assert.deepEqual(st.fx[today], [42, 3500]);
    assert.equal(Object.keys(st.fx).length, 2);                                   // bozuk kayıtlar atıldı
    await p.click('button[data-go="gun"]'); await p.click('#modeDay'); await p.click('#dayToday');
    assert.equal(await txt('#dNetUsd'), '$25,00'); assert.equal(await txt('#dNetHas'), '0,30 gr');                 // 1050 / 3500
    await p.click('#dayPrev');
    assert.equal(await txt('#dNetUsd'), '$30,00'); assert.equal(await txt('#dNetHas'), '0,40 gr');
    await ctx.close();
  }
  // Zarar eksiyle; kur hiç yoksa karşılık yazılmaz ve hata olmaz
  const loss = await open('zarar', { viewport: { width: 420, height: 800 } }, { ...SEED, tx: SEED.tx.concat([
    { id: '6', seq: 6, date: iso(0), type: 'out', cur: 'TRY', amount: 3150, rate: 1, note: 'Kira', exp: true }]) });
  assert.equal(await loss.txt('#mToday'), '−₺2.100,00');
  assert.equal(await loss.txt('#mTodayAlt'), '≈ −$50,00 · −0,69 gr has');
  await loss.ctx.close();
  const bare = await open('kursuz', { viewport: { width: 420, height: 800 } }, { tx: [
    { id: '1', seq: 1, date: iso(0), type: 'in', cur: 'TRY', amount: 1000, rate: 1, note: '' },
    { id: '2', seq: 2, date: iso(0), type: 'out', cur: 'TRY', amount: 100, rate: 1, note: 'Çay', exp: true }] });
  assert.equal(await bare.txt('#mToday'), '−₺100,00');
  assert.equal(await bare.txt('#mTodayAlt'), '');
  await bare.p.click('button[data-go="gun"]');
  assert.equal(await bare.txt('#dNetUsd'), '—');                                  // kur yok: çizgi
  assert.equal(await bare.txt('#dNetHas'), '—');
  await bare.ctx.close();
  await b.close();
  assert.deepEqual(errors, []);
  console.log('KÂR GÖSTERİMİ SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('kar-birimleri.js')).slice(0, 2).join(' | ')); process.exit(1); });
