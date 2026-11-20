// Döviz Kasası: gün sonu sihirbazı (sayım → özet → kapat ve yedek) ve müşteriye göster ekranı.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const fmt = (d) => d.slice(8) + '.' + d.slice(5, 7) + '.' + d.slice(0, 4);
const SEED = {
  tx: [
    { id: '1', seq: 1, date: iso(2), type: 'in', cur: 'TRY', amount: 100000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: iso(1), type: 'in', cur: 'USD', amount: 1000, rate: 50, note: '' },
    { id: '3', seq: 3, date: iso(0), type: 'out', cur: 'USD', amount: 100, rate: 51, note: '', ref: 50.5 },
  ],
  rates: { USD: 50.4, HAS: 6000 }, sell: { USD: 50.6, HAS: 6010 }, myRates: { USD: { buy: 50.5, sell: 51 }, HAS: { buy: 5990, sell: 6050 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
  calc: { mil: { sell: {}, buy: {} }, labor: { 22: { v: 100, unit: 'gr' } } },
};
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
    await p.addInitScript((seed) => {
      if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed));
      window.__shared = 0; navigator.canShare = () => true; navigator.share = () => { window.__shared++; return Promise.resolve(); };
    }, SEED);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));

    // ================= Müşteriye göster =================
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tIn"]');
    assert.ok(await p.isHidden('#btnShow'));                                       // tutar yokken gizli
    await p.fill('#fAmount', '200');
    await p.click('#btnShow');
    assert.ok(await p.isVisible('#show'));
    assert.equal(await txt('#showK'), 'Size ödenecek');
    assert.equal(await txt('#showTotal'), '₺10.100,00');                            // 200 × 50,50
    assert.equal(await txt('#showCalc'), '200,00 USD × 50,5000');
    assert.equal(await txt('#showShop'), 'Yazıcıoğlu Çilek Döviz');
    if (name === 'telefon') await p.screenshot({ path: require('os').tmpdir() + '/kasa-goster.png' });
    await p.click('#show');                                                        // dokununca kapanır
    assert.ok(await p.isHidden('#show'));
    await p.click('label[for="tOut"]'); await p.click('#btnShow');
    assert.equal(await txt('#showK'), 'Ödenecek tutar');
    await p.keyboard.press('Escape');
    assert.ok(await p.isHidden('#show'));
    await p.click('#quick button:has-text("TL")');
    assert.ok(await p.isHidden('#btnShow'));                                       // TL'de yok
    // kuyum hesabından
    await p.click('button[data-go="hesap"]');
    await p.fill('#kGram', '10');
    await p.click('#kShow');
    assert.equal(await txt('#showK'), 'Ödenecek tutar');
    assert.equal(await txt('#showTotal'), '₺56.418,00');                            // 10 × 0,916 × 6050 + 10 × 100
    assert.equal(await txt('#showCalc'), '22 ayar · 10 gr · işçilik dahil');
    await p.click('#showClose');

    // ================= Gün sonu sihirbazı (bugün) =================
    await p.click('button[data-go="gun"]');
    await p.click('#btnCloseDay');
    assert.ok(await p.isVisible('#wiz'));
    assert.equal(await txt('#wizTitle'), 'Kasayı sayın');
    assert.ok(await p.isHidden('#wizBack'));
    // TL kayıtlı: 100.000 − 50.000 + 5.100 = 55.100 ; USD 900
    await p.fill('#wz-TRY', '55.000');
    assert.equal(await txt('#wizBody .wiz-count:first-of-type .wiz-diff'), 'eksik ₺100,00');
    await p.fill('#wz-USD', '900');
    await p.click('#wizNext');
    assert.equal(await txt('#wizTitle'), fmt(iso(0)) + ' özeti');
    const sum = await txt('#wizBody');
    assert.ok(sum.includes('Net kâr+₺100,00') && sum.includes('Makastan +₺50,00') && sum.includes('TL kasası₺55.000,00'), sum);
    assert.ok(sum.includes('Sayım farkı: TL eksik ₺100,00') && !sum.includes('USD eksik'), sum);
    assert.ok(await p.isChecked('#wzPost'));
    await p.click('#wizBack');                                                     // geri dönünce yazılanlar durur
    assert.equal(await p.inputValue('#wz-TRY'), '55000');
    await p.click('#wizNext'); await p.click('#wizNext');
    assert.equal(await txt('#wizTitle'), fmt(iso(0)) + ' kapatılsın mı?');
    assert.equal(await txt('#wizNext'), 'Günü kapat');
    const n0 = (await store()).tx.length;
    await p.click('#wizNext');
    assert.ok(await p.isHidden('#wiz'));
    let st = await store();
    assert.equal(st.closed.slice(-1)[0].d, iso(0));
    const adj = st.tx[st.tx.length - 1];
    assert.equal(st.tx.length, n0 + 1);
    assert.deepEqual([adj.type, adj.cur, adj.amount, adj.adj, adj.note], ['out', 'TRY', 100, true, 'Gün sonu sayımı']);
    await p.waitForFunction(() => window.__shared === 1);                          // yedek gönderildi
    assert.ok((await txt('#closeBar')).includes('Bu gün kapatıldı.'));
    // Vazgeç: hiçbir şey değişmez
    await p.click('#btnReopen');
    await p.click('#btnCloseDay');
    await p.click('#wizCancel');
    assert.ok(await p.isHidden('#wiz'));
    assert.equal((await store()).closed.length, 0);
    // Sayım farkını işlememeyi seçmek
    await p.click('#btnCloseDay');
    await p.fill('#wz-USD', '899');
    await p.click('#wizNext');
    await p.uncheck('#wzPost');
    await p.click('#wizNext'); await p.uncheck('#wzBackup'); await p.click('#wizNext');
    st = await store();
    assert.equal(st.tx.length, n0 + 1);                                            // yeni sayım farkı yazılmadı
    assert.equal(st.closed.length, 1);
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('SİHİRBAZ VE GÖSTER SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('sihirbaz.js')).slice(0, 2).join(' | ')); process.exit(1); });
