// Vitrin fiyat ekranı sınaması.
const { chromium } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const OUT = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'kasa-'));   // ekran görüntüleri
const URL = 'http://kasa.test/vitrin.html';
const MARKET = { Update_Date: 'x',
  USD: { Buying: 41, Selling: 41.5 }, EUR: { Buying: 45, Selling: 45.6 }, GBP: { Buying: 52, Selling: 53 },
  HAS: { Buying: 2990, Selling: 3000 }, YIA: { Buying: 2740, Selling: 2800 }, CEYREKALTIN: { Buying: 9900, Selling: 10000 } };
const KASA = { tx: [], rates: { USD: 41, HAS: 2990, GBP: 52 }, sell: { USD: 41.5, HAS: 3000, GBP: 53 },
  myRates: { USD: { buy: 41.2, sell: 41.9 }, HAS: { buy: 2950, sell: 3050 }, GBP: { buy: null, sell: null } },
  calc: { mil: { sell: { 22: 930 }, buy: { 22: 912 } }, labor: {} } };

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (name, kasa, marketOk) => {
    const ctx = await b.newContext({ viewport: { width: 1280, height: 720 } });
    await ctx.route(/truncgil/, (r) => marketOk ? r.fulfill({ contentType: 'application/json', body: JSON.stringify(MARKET) }) : r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    await p.addInitScript((kasa) => { if (kasa && !localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(kasa)); }, kasa);
    await p.goto(URL);
    const rows = async () => (await p.locator('#body tr').allTextContents()).map((t) => t.replace(/\s+/g, ' ').trim());
    return { ctx, p, rows };
  };

  // --- Döviz Kasası olan cihaz: kur tablosu gösterilir
  let { ctx, p, rows } = await open('kasa', KASA, true);
  await p.waitForFunction(() => document.querySelectorAll('#body tr').length === 3);
  let r = await rows();
  assert.deepEqual(r, ['DolarUSD41,200041,9000', 'SterlinGBP52,000053,0000', 'Has Altıngram2.950,003.050,00'], JSON.stringify(r));   // GBP: kendi kur yok → piyasa
  assert.equal(await p.textContent('#shop'), 'Yazıcıoğlu Çilek Döviz');
  assert.ok((await p.textContent('#src')).includes('uygulamadaki kur tablosu'));
  // Ayarlar: 22 ayarı has fiyatından hesapla, dükkân adını değiştir
  await p.click('#btnSet');
  assert.equal(await p.inputValue('#fSource'), 'kasa');
  await p.check('#karats input[data-k="22"]');
  await p.fill('#fName', 'Deneme Kuyumculuk');
  await p.click('#form button[type="submit"]');
  r = await rows();
  assert.equal(r[3], '22 Ayargram2.690,402.836,50', r[3]);                       // 2950 × 0,912 ve 3050 × 0,930
  assert.equal(await p.textContent('#shop'), 'Deneme Kuyumculuk');
  await p.screenshot({ path: OUT + '/vitrin-kasa.png' });
  // Döviz Kasası'nda fiyat değişince ekran güncellenir ve hücre parlar
  await p.evaluate(() => { const k = JSON.parse(localStorage.getItem('doviz-kasasi-v1')); k.myRates.USD.sell = 42.5;
    localStorage.setItem('doviz-kasasi-v1', JSON.stringify(k)); window.dispatchEvent(new StorageEvent('storage', { key: 'doviz-kasasi-v1' })); });
  r = await rows();
  assert.equal(r[0], 'DolarUSD41,200042,5000');
  assert.equal(await p.locator('#body td.flash').count(), 1);
  // Ayarlar kalıcı
  await p.reload();
  await p.waitForFunction(() => document.querySelectorAll('#body tr').length === 4);
  assert.equal(await p.textContent('#shop'), 'Deneme Kuyumculuk');
  await ctx.close();

  // --- Ayrı cihaz (Döviz Kasası verisi yok): piyasa + fark
  ({ ctx, p, rows } = await open('tv', null, true));
  await p.waitForFunction(() => document.querySelectorAll('#body tr').length === 4);
  r = await rows();
  assert.deepEqual(r, ['DolarUSD41,000041,5000', 'EuroEUR45,000045,6000', 'Has Altıngram2.990,003.000,00', 'Çeyrek Altın9.900,0010.000,00'], JSON.stringify(r));
  assert.ok((await p.textContent('#src')).includes('Piyasa verisi'));
  await p.click('#btnSet');
  assert.equal(await p.inputValue('#fSource'), 'piyasa');
  assert.ok(await p.isVisible('#piyasaBox') && await p.isHidden('#kasaBox'));
  await p.fill('#rows input[data-b="USD"]', '-0,5'); await p.fill('#rows input[data-s="USD"]', '0,5');
  await p.fill('#rows input[data-b="HAS"]', '−40'); await p.fill('#rows input[data-s="HAS"]', '50');
  await p.uncheck('#rows input[data-c="EUR"]'); await p.check('#rows input[data-c="B22"]');
  await p.click('#form button[type="submit"]');
  r = await rows();
  assert.deepEqual(r, ['DolarUSD40,500042,0000', 'Has Altıngram2.950,003.050,00', '22 Ayar Bilezikgram2.740,002.800,00', 'Çeyrek Altın9.900,0010.000,00'], JSON.stringify(r));
  await p.screenshot({ path: OUT + '/vitrin-tv.png' });
  await ctx.close();

  // --- Piyasa verisi alınamazsa açıklama gösterilir, hata olmaz
  ({ ctx, p, rows } = await open('kesik', null, false));
  await p.waitForFunction(() => !document.getElementById('empty').hidden);
  assert.ok((await p.textContent('#empty')).includes('Piyasa fiyatı alınamadı'));
  await ctx.close();

  // --- Piyasa verisi eskiyse vitrinde kırmızı uyarı; güncelse yok
  ({ ctx, p, rows } = await open('eski', null, false));
  await p.evaluate(() => {
    localStorage.setItem('vitrin-fiyat', JSON.stringify({ at: new Date(Date.now() - 3600e3).toISOString(), buy: { USD: 41 }, sell: { USD: 41.5 } }));
    localStorage.setItem('vitrin-v1', JSON.stringify({ source: 'piyasa', rows: { USD: { on: true, b: 0, s: 0 } } }));
  });
  await p.reload();
  await p.waitForSelector('#stale:not([hidden])');
  assert.ok((await p.textContent('#stale')).includes('Fiyatlar güncel olmayabilir'));
  await ctx.close();
  ({ ctx, p, rows } = await open('taze', null, true));
  await p.waitForFunction(() => document.querySelectorAll('#body tr').length > 0);
  assert.ok(await p.isHidden('#stale'));
  await ctx.close();

  // --- Uygulamadaki bağlantı
  ({ ctx, p } = await open('link', KASA, true));
  await p.goto('http://kasa.test/doviz-kasasi.html');
  await p.click('button[data-go="kasa"]'); await p.click('button[data-go="kurlar"]');
  assert.equal(await p.getAttribute('#lnkVitrin', 'href'), 'vitrin.html');
  await ctx.close();

  await b.close();
  assert.deepEqual(errors, []);
  console.log('VİTRİN SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('vitrin-ekrani.js')).slice(0, 2).join(' | ')); process.exit(1); });
