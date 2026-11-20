// Döviz Kasası: okunamayan kayıt ezilmez; kurtarma seçenekleri; kayıt hatası uyarısı.
const { chromium } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const GOOD = [
  { id: '1', seq: 1, date: '2026-11-01', type: 'in', cur: 'TRY', amount: 10000, rate: 1, note: 'Açılış' },
  { id: '2', seq: 2, date: '2026-11-02', type: 'in', cur: 'USD', amount: 100, rate: 50, note: '' },
];
const BROKEN = JSON.stringify({ tx: GOOD.concat([{ id: '3', seq: 3, date: '2026-11-03', type: 'in', cur: 'XYZ', amount: 5, rate: 1 }]),
  myRates: { USD: { buy: 50, sell: 51 } }, ratesUpdated: '2020-01-01T00:00:00Z' });
const MARKET = { USD: { Buying: 50, Selling: 50.2, Change: 0 } };

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (raw) => {
    const ctx = await b.newContext({ viewport: { width: 420, height: 860 }, acceptDownloads: true });
    await ctx.route(/truncgil/, (r) => r.fulfill({ contentType: 'application/json', body: JSON.stringify(MARKET) }));
    await ctx.route(/er-api|frankfurter|gold-api/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    const dialogs = [];
    p.on('pageerror', (e) => errors.push(e.message));
    p.on('dialog', (d) => { dialogs.push(d.message()); d.accept(); });
    await p.addInitScript((raw) => { if (raw && !sessionStorage.getItem('seeded')) { localStorage.setItem('doviz-kasasi-v1', raw); sessionStorage.setItem('seeded', '1'); } }, raw);
    await p.goto(URL);
    return { ctx, p, dialogs };
  };

  // 1) Bozuk kayıt: uyarı çıkar, otomatik fiyat güncellemesi ve işlem denemesi ham kaydı EZMEZ
  let { ctx, p, dialogs } = await open(BROKEN);
  assert.ok(await p.isVisible('#rescueBanner'));
  assert.ok((await p.textContent('#rescueWhy')).includes('Geçersiz işlem kaydı (satır 3)'));
  await p.waitForTimeout(800);                                   // açılıştaki fiyat güncellemesi bitsin
  assert.equal(await p.evaluate(() => localStorage.getItem('doviz-kasasi-v1')), BROKEN);
  assert.equal(await p.evaluate(() => localStorage.getItem('doviz-kasasi-kurtarma')), BROKEN);
  await p.fill('#fAmount', '5'); await p.fill('#fRate', '50'); await p.click('#btnSave');
  assert.equal(await p.evaluate(() => localStorage.getItem('doviz-kasasi-v1')), BROKEN);
  // ham kayıt indirilebilir
  const [dl] = await Promise.all([p.waitForEvent('download'), p.click('#btnRescueDl')]);
  assert.ok(dl.suggestedFilename().startsWith('cilek-doviz-ham-kayit-'));
  assert.equal(require('fs').readFileSync(await dl.path(), 'utf8'), BROKEN);
  // okunabilenlerle devam: bozuk satır atlanır, kayıt düzelir, kurtarma kopyası durur
  await p.click('#btnRescueGo');
  assert.ok(dialogs.some((d) => d.includes('1 bozuk satır atlanacak')), dialogs.join('|'));
  assert.ok(await p.isHidden('#rescueBanner'));
  const st = await p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
  assert.deepEqual(st.tx.map((t) => t.id), ['1', '2']);
  assert.equal(await p.evaluate(() => localStorage.getItem('doviz-kasasi-kurtarma')), BROKEN);
  assert.ok((await p.textContent('#mTL')).includes('5.000'));    // 10.000 − 100 × 50
  await ctx.close();

  // 2) Hiç okunamayan (JSON olmayan) kayıt: devam etme düğmesi açıklama verir, veri durur
  ({ ctx, p, dialogs } = await open('{bozuk'));
  assert.ok(await p.isVisible('#rescueBanner'));
  await p.click('#btnRescueGo');
  assert.ok(dialogs.some((d) => d.includes('hiç okunamıyor')));
  assert.equal(await p.evaluate(() => localStorage.getItem('doviz-kasasi-v1')), '{bozuk');
  await ctx.close();

  // 3) Sağlam kayıtta uyarı yok; depolama doluysa kullanıcı bir kez uyarılır
  ({ ctx, p, dialogs } = await open(JSON.stringify({ tx: GOOD, myRates: { USD: { buy: 50, sell: 51 } } })));
  assert.ok(await p.isHidden('#rescueBanner'));
  await p.evaluate(() => { Storage.prototype.setItem = function () { const e = new Error('dolu'); e.name = 'QuotaExceededError'; throw e; }; });
  await p.fill('#fAmount', '1'); await p.fill('#fRate', '50'); await p.click('#btnSave');
  await p.fill('#fAmount', '1'); await p.fill('#fRate', '50'); await p.click('#btnSave');
  assert.equal(dialogs.filter((d) => d.includes('Kayıt yapılamadı')).length, 1);
  await ctx.close();

  await b.close();
  assert.deepEqual(errors, []);
  console.log('VERİ KORUMA SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('veri-koruma.js')).slice(0, 2).join(' | ')); process.exit(1); });
