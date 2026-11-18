// Döviz Kasası: vitrin defteri ↔ kasa bağlantısı ve rapor paylaşımı.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const OUT = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'kasa-'));   // ekran görüntüleri
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = {
  tx: [{ id: 'a', seq: 1, date: iso(3), type: 'in', cur: 'TRY', amount: 200000, rate: 1, note: 'Açılış' }],
  rates: { HAS: 2990, USD: 41 }, sell: { HAS: 3000, USD: 41.5 }, myRates: { HAS: { buy: 2950, sell: 3050 }, USD: { buy: 41, sell: 42 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr', calc: { mil: { sell: {}, buy: {} }, labor: { 22: { v: 100, unit: 'gr' } } },
};
(async () => {
  const b = await chromium.launch();
  const errors = [];
  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const ctx = await b.newContext(opts);
    await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    const dialogs = [];
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => { dialogs.push(d.message()); d.accept(); });
    await p.addInitScript((seed) => {
      if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed));
      navigator.share = (d) => { window.__shared = d.text; return Promise.resolve(); };
    }, SEED);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    const add = async (n, karat, gram, cost, post) => {
      await p.fill('#iName', n); await p.selectOption('#iKarat', String(karat)); await p.fill('#iGramIn', gram); await p.fill('#iCost', cost);
      await p.setChecked('#iPost', post);
      await p.click('#iForm button[type="submit"]');
    };
    await p.click('button[data-go="kasa"]');
    // --- Alışı kasaya işleyerek ürün ekleme
    await add('Bilezik', 22, '10', '', true);
    assert.equal(await txt('#iMsg'), 'Alışı kasaya işlemek için maliyeti yazın.');
    await add('Bilezik', 22, '10', '28000', true);
    let st = await store();
    assert.equal(st.tx.length, 2);
    assert.deepEqual([st.tx[1].type, st.tx[1].cur, st.tx[1].amount, st.tx[1].rate], ['in', 'B22', 10, 2800]);
    assert.equal(st.items[0].txIn, st.tx[1].id);
    assert.equal(await txt('#sTL'), '₺172.000,00');
    // geri al: ürün de işlem de gider
    await p.click('#toastUndo');
    st = await store();
    assert.equal(st.tx.length, 1); assert.equal(st.items.length, 0);
    await add('Bilezik', 22, '10', '28000', true);
    // --- Sat: hesaplanan fiyat gösterilir, satış kasaya işlenir
    await p.click('#iList li:first-child button:has-text("Sat")');
    assert.ok((await txt('#dlgText')).includes('Hesaplanan satış fiyatı: ₺28.938,00'), await txt('#dlgText'));   // 10×3050×0,916 + 10×100
    await p.fill('#dlgInput', 'abc'); await p.click('#dlgForm button[type="submit"]');
    assert.equal(await txt('#dlgMsg'), 'Geçerli bir tutar yazın.');
    await p.fill('#dlgInput', '29000'); await p.click('#dlgForm button[type="submit"]');
    st = await store();
    assert.equal(st.tx.length, 3);
    assert.deepEqual([st.tx[2].type, st.tx[2].cur, st.tx[2].amount, st.tx[2].rate, st.tx[2].note], ['out', 'B22', 10, 2900, 'Vitrin: Bilezik']);
    assert.equal(st.items[0].price, 29000); assert.equal(st.items[0].txOut, st.tx[2].id);
    assert.equal(await txt('#iCount'), '0');
    assert.equal(await txt('#sTL'), '₺201.000,00');
    await p.click('#iSold');
    const soldRow = await txt('#iList li:first-child');
    assert.ok(soldRow.includes('₺29.000,00') && soldRow.includes('maliyete göre kâr +₺1.000,00') && soldRow.includes('kasaya işlendi'), soldRow);
    await p.screenshot({ path: OUT + '/' + name + '-vitrin-sat.png', fullPage: true });
    // --- Rapor paylaşımı (gün, ay, analiz)
    await p.click('button[data-go="gun"]');
    assert.equal(await txt('#dProfit'), '+₺1.000,00');
    await p.click('#btnShareDay');
    let shared = await p.evaluate(() => window.__shared);
    assert.ok(shared.startsWith('Yazıcıoğlu Çilek Döviz — Gün sonu ') && shared.includes('Net kâr: +₺1.000,00 (≈ $23,81 · 0,33 gr has)') &&
              shared.includes('TL kasası: ₺201.000,00') && shared.includes('İşlem: 2'), shared);
    assert.ok(!shared.includes('Stok:'));                                           // stok kalmadı
    await p.click('#modeMonth'); await p.click('#btnShareDay');
    shared = await p.evaluate(() => window.__shared);
    assert.ok(/— Aylık rapor \d\d\.\d{4}\n/.test(shared) && shared.includes('Alım-satım kârı: +₺1.000,00'), shared);
    await p.click('#modeAn'); await p.click('#btnShareDay');
    shared = await p.evaluate(() => window.__shared);
    assert.ok(shared.includes('Kâr analizi (Son 12 ay)') && shared.includes('22 Ayar Bilezik: kâr +₺1.000,00, makas 100,00 (+%3,57)'), shared);
    await p.click('#modeDay');
    // --- Satışı geri al: kasadaki satış da silinir
    await p.click('button[data-go="kasa"]');
    await p.click('#iList li:first-child button:has-text("Geri al")');
    st = await store();
    assert.equal(st.tx.length, 2); assert.equal(st.items[0].sold, null); assert.equal(st.items[0].txOut, null);
    assert.equal(await txt('#iCount'), '1');
    assert.equal(await txt('#sTL'), '₺172.000,00');
    // günün raporunda artık stok görünür
    await p.click('button[data-go="gun"]'); await p.click('#btnShareDay');
    assert.ok((await p.evaluate(() => window.__shared)).includes('Stok: 22 Ayar Bilezik 10 gr'));
    // --- Kasada stoğu olmayan ürün: sorulur, yalnızca defterde işaretlenir
    await p.click('button[data-go="kasa"]');
    await add('Yüzük', 14, '3', '', false);
    assert.equal((await store()).tx.length, 2);
    await p.click('#iList li:nth-child(2) button:has-text("Sat")');
    await p.fill('#dlgInput', '9000'); await p.click('#dlgForm button[type="submit"]');
    assert.ok(dialogs.some((d) => d.includes('Kasada yeterli 14 Ayar Altın stoku yok')), dialogs.join('|'));
    st = await store();
    assert.equal(st.tx.length, 2);
    const ring = st.items.find((x) => x.name === 'Yüzük');
    assert.ok(ring.sold && ring.price === 9000 && ring.txOut === null);
    const ringRow = await txt('#iList li:last-child');                             // satılanlar zaten açık
    assert.ok(ringRow.includes('₺9.000,00') && !ringRow.includes('kasaya işlendi'), ringRow);
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('VİTRİN–KASA VE PAYLAŞIM SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('vitrin-kasa-paylasim.js')).slice(0, 2).join(' | ')); process.exit(1); });
