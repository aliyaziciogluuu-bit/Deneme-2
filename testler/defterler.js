// Döviz Kasası: toptancı has hesabı ve vitrin defteri sınaması.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const OUT = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'kasa-'));   // ekran görüntüleri
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = {
  tx: [{ id: 'a', seq: 1, date: iso(30), type: 'in', cur: 'TRY', amount: 100000, rate: 1, note: 'Açılış' }],
  rates: { HAS: 2990 }, sell: { HAS: 3000 }, myRates: { HAS: { buy: 2950, sell: 3050 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
  items: [
    { id: 'old', seq: 1, date: iso(100), name: 'Kolye', karat: 18, gram: 8, cost: null, note: 'taşlı', sold: null },
    { name: '', karat: 22, gram: 5, date: iso(1) }, { name: 'Bozuk', karat: 23, gram: 5, date: iso(1) }, 'çöp',
  ],
  whole: [{ who: 'X', date: 'dün', dir: 'in', has: 5, tl: 0 }, null],
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
    await p.addInitScript((seed) => { if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed)); }, SEED);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));

    // ================= Toptancı has hesabı =================
    await p.click('button[data-go="cari"]'); await p.click('button[data-go="toptanci"]');
    assert.ok(await p.isVisible('#wEmpty') && await p.isHidden('#wSum'));          // bozuk kayıtlar atıldı
    assert.ok(await p.isHidden('#wForm'));                                        // form kapalı gelir
    await p.click('[data-toggle="toptanci"]');
    await p.fill('#wWho', 'Altın Toptan');
    await p.fill('#wGram', '100');
    assert.equal(await p.inputValue('#wMil'), '916');
    assert.equal(await txt('#wHint'), 'Has karşılığı: 91,60 gr');
    await p.fill('#wLabor', '5000');
    await p.click('#wForm button[type="submit"]');
    let row = await txt('#wList .person');
    assert.ok(row.includes('91,60 gr has borç') && row.includes('₺5.000,00 işçilik borcu'), row);
    assert.equal(await txt('#wDebt'), '91,60 gr');
    assert.equal(await txt('#wDebtTL'), '≈ ₺279.380,00');                          // 91,6 × 3050
    assert.equal(await txt('#wLaborSum'), '₺5.000,00');
    // ödeme: doğrudan has 41,6 gr + 2000 TL işçilik; ad küçük harfle yazılsa da aynı toptancı
    await p.click('label[for="wOut"]');
    await p.fill('#wWho', 'altın toptan');
    await p.selectOption('#wKarat', 'has');
    assert.ok(await p.isHidden('#wMilF'));
    await p.fill('#wGram', '41,6'); await p.fill('#wLabor', '2000');
    await p.click('#wForm button[type="submit"]');
    assert.equal(await p.locator('#wList .person').count(), 1);
    row = await txt('#wList .person');
    assert.ok(row.includes('50,00 gr has borç') && row.includes('₺3.000,00 işçilik borcu'), row);
    assert.equal(await p.locator('#wList ul.sub li').count(), 2);                  // hareketler açık
    // hurda ile fazla ödeme → alacak
    await p.selectOption('#wKarat', '14');
    assert.equal(await p.inputValue('#wMil'), '585');
    await p.fill('#wGram', '100'); await p.fill('#wLabor', '');
    await p.click('#wForm button[type="submit"]');
    row = await txt('#wList .person');
    assert.ok(row.includes('8,50 gr has alacak'), row);                             // 50 − 58,5
    assert.equal(await txt('#wDebt'), '0,00 gr');
    // hata: boş hareket
    await p.fill('#wGram', ''); await p.fill('#wLabor', '');
    await p.click('#wForm button[type="submit"]');
    assert.equal(await txt('#wMsg'), 'Ağırlık ya da işçilik tutarı yazın.');
    // son hareketi sil → yeniden 50 gr borç
    await p.click('#wList ul.sub li:first-child .x');
    row = await txt('#wList .person');
    assert.ok(row.includes('50,00 gr has borç'), row);
    await p.screenshot({ path: OUT + '/' + name + '-toptanci.png', fullPage: true });
    let st = await store();
    assert.equal(st.whole.length, 2);
    assert.equal(st.tx.length, 1);                                                  // kasa etkilenmez

    // ================= Vitrin defteri =================
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="vitrin"]');
    assert.equal(await txt('#iCount'), '1');                                        // yalnız geçerli tohum ürün
    assert.ok((await txt('#iList li:first-child')).includes('100 gündür vitrinde'));
    assert.ok(await p.locator('#iList li:first-child small.neg').count() === 1);    // 90 günü geçen işaretlenir
    await p.click('[data-toggle="vitrin"]');
    await p.fill('#iName', 'Bilezik'); await p.selectOption('#iKarat', '22'); await p.fill('#iGramIn', '12,5'); await p.fill('#iCost', '35000');
    await p.click('#iForm button[type="submit"]');
    await p.fill('#iName', 'Yüzük'); await p.selectOption('#iKarat', '14'); await p.fill('#iGramIn', '3,2'); await p.fill('#iCost', '');
    await p.click('#iForm button[type="submit"]');
    assert.equal(await txt('#iCount'), '3');
    assert.equal(await txt('#iGram'), '23,7 gr');                                   // 8 + 12,5 + 3,2
    assert.equal(await txt('#iPure'), '19,32 gr');                                  // 6 + 11,45 + 1,872
    const info = await txt('#iInfo');
    assert.ok(info.includes('22 ayar: 1 parça, 12,5 gr') && info.includes('≈ ₺56.999,90'), info);   // 19,322 × 2950
    assert.ok((await txt('#iList li:nth-child(2)')).includes('bugün eklendi · maliyet ₺35.000,00'));
    await p.screenshot({ path: OUT + '/' + name + '-vitrin.png', fullPage: true });
    // Hesapla: hesap bölümüne ayar ve gramla geçer
    await p.click('#iList li:nth-child(2) button:has-text("Hesapla")');
    assert.ok(await p.isVisible('#kForm'));
    assert.equal(await p.inputValue('#kGram'), '12,5');
    assert.equal(await p.inputValue('#kMil'), '916');
    assert.ok((await txt('#kOut')).includes('₺34.922,50'));                         // 12,5 × 0,916 × 3050
    // Satıldı, göster, geri al, sil
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="vitrin"]');
    await p.click('#iList li:nth-child(2) button:has-text("Sat")');
    assert.ok((await txt('#dlgText')).includes('Hesaplanan satış fiyatı: ₺34.922,50'));
    await p.click('#dlgForm button[type="submit"]');                              // tutar boş: yalnızca defterde işaretlenir
    assert.equal(await txt('#iCount'), '2');
    assert.equal(await txt('#iSold'), 'Satılanları göster (1)');
    await p.click('#iSold');
    assert.ok((await txt('#iList')).includes('satıldı: ') && !(await txt('#iList')).includes('kasaya işlendi'));
    await p.click('#iList li:last-child button:has-text("Geri al")');
    assert.equal(await txt('#iCount'), '3');
    await p.click('#iList li:first-child .x');
    assert.equal(await txt('#iCount'), '2');
    // kalıcılık
    await p.reload();
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="vitrin"]');
    assert.equal(await txt('#iCount'), '2');
    st = await store();
    assert.deepEqual(st.items.map((x) => [x.name, x.karat, x.gram, x.cost]), [['Bilezik', 22, 12.5, 35000], ['Yüzük', 14, 3.2, null]]);
    await p.click('button[data-go="cari"]'); await p.click('button[data-go="toptanci"]');
    assert.ok((await txt('#wList .person')).includes('50,00 gr has borç'));
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('DEFTER SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('defterler.js')).slice(0, 2).join(' | ')); process.exit(1); });
