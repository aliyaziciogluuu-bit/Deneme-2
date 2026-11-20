// Yazıcıoğlu Çilek Döviz: sepet (toplu işlem), sarrafiye stoku (yeni/eski tarihli), ayar dönüştürücü, hurda altın günlüğü,
// ana ekran kısayolları, tema (açık/koyu) ve renk.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const fs = require('fs');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = {
  tx: [
    { id: '1', seq: 1, date: '2020-01-01', type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: '2020-01-01', type: 'in', cur: 'USD', amount: 1000, rate: 40, note: '' },
    { id: '3', seq: 3, date: '2020-01-01', type: 'in', cur: 'CEYREK', amount: 10, rate: 9000, note: '' },
    { id: '4', seq: 4, date: '2020-01-02', type: 'in', cur: 'CEYREK', amount: 4, rate: 8800, note: 'Eski tarihli', old: true },
    { id: '5', seq: 5, date: '2020-01-02', type: 'in', cur: 'A14', amount: 2, rate: 2000, note: '' },
    { id: '6', seq: 6, date: iso(0), type: 'in', cur: 'A14', amount: 10, rate: 2500, note: 'Hesap: bozdurma' },
    { id: '7', seq: 7, date: iso(0), type: 'in', cur: 'B22', amount: 5, rate: 2800, note: '' },
    { id: '8', seq: 8, date: iso(0), type: 'in', cur: 'USD', amount: 1, rate: 50, note: 'kayıt dışı say', old: true },   // dövizde "old" atılır
  ],
  rates: { USD: 50, CEYREK: 10000, GA: 5990 }, sell: { USD: 50.2, CEYREK: 10100, GA: 6000 },
  myRates: { USD: { buy: 49.9, sell: 50.4 }, CEYREK: { buy: 9950, sell: 10150 }, GA: { buy: 5980, sell: 6040 } },
  calc: { old: { CEYREK: 75 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
};

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const cells = (p, sel) => p.locator(sel + ' tr').evaluateAll((trs) => trs.map((tr) => [...tr.children].map((td) => td.textContent.replace(/\s+/g, ' ').trim())));
  const open = async (name, opts, path) => {
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
    await p.goto(URL + (path || ''));
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    return { ctx, p, txt, store, dialogs };
  };

  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const { ctx, p, txt, store, dialogs } = await open(name, opts);
    let st;

    // ================= 1. Sepet =================
    assert.ok(await p.isHidden('#basketBox'));
    await p.click('label[for="tOut"]'); await p.click('#quick button:has-text("USD")');
    await p.fill('#fAmount', '100');
    await p.click('#btnBasket');
    assert.ok(await p.isVisible('#basketBox'));
    assert.equal(await p.inputValue('#fAmount'), '');
    assert.equal(await txt('#btnSave'), 'Sepeti kaydet (1)');
    await p.click('#quick button:has-text("Çeyrek")');
    await p.fill('#fAmount', '2');
    await p.click('#btnBasket');
    await p.click('label[for="tIn"]');
    await p.selectOption('#fCur', 'GA').catch(async () => { await p.click('[data-toggle="txmore"]'); await p.selectOption('#fCur', 'GA'); });
    await p.dispatchEvent('#fCur', 'change');
    await p.fill('#fAmount', '5');                                        // son satır sepete eklenmeden kaydedilir
    assert.equal(await txt('#basketSum'), '2 kalem · Müşteriden alın: ₺25.340,00');   // 5.040 + 20.300
    assert.equal(await txt('#fTotal'), 'Sepet (3 kalem) · Müşteriye ödeyin: ₺4.560,00');   // formdaki satır dahil (alttaki çubukta görünür)
    assert.ok(await p.isHidden('#btnTpl'));
    await p.click('#btnShow');
    assert.equal(await txt('#showTotal'), '₺4.560,00');                   // 25.340 − 29.900: müşteriye ödenecek
    await p.click('#show');
    const n0 = (await store()).tx.length;
    await p.click('#btnSave');
    st = await store();
    const added = st.tx.slice(n0);
    assert.deepEqual(added.map((t) => [t.type, t.cur, t.amount, t.rate]), [['out', 'USD', 100, 50.4], ['out', 'CEYREK', 2, 10150], ['in', 'GA', 5, 5980]]);
    assert.ok(added.every((t) => t.grp && t.grp === added[0].grp));
    assert.ok(!st.tx.find((t) => t.id === '8').old && st.tx.find((t) => t.id === '4').old);   // dövizde "eski tarihli" atılır
    assert.equal(await txt('#toastMsg'), 'Sepet kaydedildi: 3 işlem · müşteriye ödeyin ₺4.560,00.');
    assert.ok(await p.isHidden('#basketBox'));
    assert.equal(await txt('#btnSave'), 'İşlemi kaydet');
    await p.click('#toastUndo');                                          // geri al: üçü birden gider
    assert.equal((await store()).tx.length, n0);
    // Sepetten çıkarma ve TL'nin eklenmemesi
    await p.click('#quick button:has-text("USD")'); await p.fill('#fAmount', '10'); await p.click('#btnBasket');
    await p.click('#basketList li .x');
    assert.ok(await p.isHidden('#basketBox'));
    await p.selectOption('#fCur', 'TRY'); await p.dispatchEvent('#fCur', 'change');
    assert.ok(await p.isHidden('#btnBasket'));
    await p.selectOption('#fCur', 'USD'); await p.dispatchEvent('#fCur', 'change');

    // ================= 2. Sarrafiye stoku =================
    await p.click('button[data-go="kasa"]');
    assert.deepEqual(await cells(p, '#coinBody'), [['Çeyrek Altın', '10', '4', '14 adet', '22,49']]);   // 14 × 1,6065
    // Formdan eski tarihli satış: indirim hesaptaki eski tarih indiriminden gelir
    await p.click('button[data-go="islem"]');
    await p.click('label[for="tOut"]'); await p.click('#quick button:has-text("Çeyrek")');
    assert.equal(await txt('#fWornLbl'), 'Eski tarihli');
    await p.check('#fWorn');
    assert.equal(await p.inputValue('#fWornD'), '75');
    assert.equal(await p.inputValue('#fRate'), '10075');
    await p.fill('#fAmount', '1'); await p.click('#btnSave');
    st = await store();
    let last = st.tx[st.tx.length - 1];
    assert.deepEqual([last.cur, last.type, last.rate, last.note, last.old], ['CEYREK', 'out', 10075, 'Eski tarihli', true]);
    await p.click('button[data-go="kasa"]');
    assert.deepEqual((await cells(p, '#coinBody'))[0].slice(0, 4), ['Çeyrek Altın', '10', '3', '13 adet']);

    // ================= 3. Ayar dönüştürücü =================
    await p.click('button[data-go="hesap"]');
    await p.click('[data-toggle="ayar"]');
    await p.fill('#akGram', '50');
    assert.equal(await p.inputValue('#akFrom'), '14');
    let ak = await txt('#akOut');
    assert.ok(ak.startsWith('50 gr 14 ayar = 29,25 gr has') && ak.includes('22 ayar karşılığı31,932 gr') && ak.includes('8 ayar karşılığı87,838 gr'), ak);
    await p.selectOption('#akFrom', '24');
    assert.ok((await txt('#akOut')).startsWith('50 gr 24 ayar = 50,00 gr has'));

    // ================= 4. Hurda altın günlüğü (Kasa → Vitrin) =================
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="vitrin"]');
    await p.click('[data-toggle="hurda"]');
    const HR = [['22 Ayar Bilezik', '1', '5', '4,58', '₺14.000,00', '₺3.056,77'],    // 14.000 / 4,58
                ['14 Ayar Altın', '1', '10', '5,85', '₺25.000,00', '₺4.273,50'],      // 25.000 / 5,85
                ['Toplam', '2', '15', '10,43', '₺39.000,00', '₺3.739,21']];
    assert.deepEqual(await cells(p, '#hrBody'), HR);
    assert.deepEqual(await cells(p, '#hrStock'), [['22 Ayar Bilezik', '5', '4,58', '₺14.000,00'], ['14 Ayar Altın', '12', '7,02', '₺29.000,00'],
                                                  ['Toplam', '17', '11,60', '₺43.000,00']]);
    await p.selectOption('#hrRange', 'month');
    assert.deepEqual(await cells(p, '#hrBody'), HR);                     // 2020 alışı dönem dışı
    await p.click('#hrShare');
    const sh = await p.evaluate(() => window.__shared);
    assert.ok(sh.startsWith('Yazıcıoğlu Çilek Döviz — Hurda altın\nBu ay alınan') && sh.includes('14 Ayar Altın: 10 gr · has 5,85 gr · ₺25.000,00') &&
              sh.includes('Elde bekleyen:\n22 Ayar Bilezik: 5 gr · has 4,58 gr\n14 Ayar Altın: 12 gr · has 7,02 gr\nToplam: 17 gr · has 11,60 gr'), sh);

    // ================= 5. Görünüm: tema ve renk =================
    await p.click('button[data-go="gun"]'); await p.click('button[data-go="liste"]');
    assert.ok(await p.isChecked('#thAuto'));
    const bg = () => p.evaluate(() => getComputedStyle(document.body).backgroundColor);
    const light = await bg();
    await p.click('label[for="thDark"]');
    assert.equal(await p.getAttribute('html', 'data-theme'), 'dark');
    assert.equal(await bg(), 'rgb(13, 16, 18)');
    await p.click('#accRow button[data-acc="bordo"]');
    assert.equal(await p.getAttribute('html', 'data-accent'), 'bordo');
    assert.equal(await p.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()), '#ff8fa8');
    await p.reload();                                                     // tercih hatırlanır, sayfa ilk çizimde koyu
    assert.equal(await p.getAttribute('html', 'data-theme'), 'dark');
    assert.equal(await bg(), 'rgb(13, 16, 18)');
    await p.click('button[data-go="gun"]'); await p.click('button[data-go="liste"]');
    await p.click('label[for="thLight"]');
    assert.equal(await bg(), light);
    assert.equal(await p.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()), '#8c1d3a');
    // Telefon koyu moddayken "Açık" seçimi koyuya dönmez; "Otomatik" koyu olur
    await p.emulateMedia({ colorScheme: 'dark' });
    assert.equal(await bg(), light);
    await p.click('label[for="thAuto"]');
    assert.equal(await bg(), 'rgb(13, 16, 18)');
    await p.emulateMedia({ colorScheme: 'light' });
    await p.click('#accRow button[data-acc="yesil"]');
    assert.equal(await p.getAttribute('html', 'data-accent'), null);
    const ui = await p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-ui')));
    assert.deepEqual([ui.theme, ui.accent], ['auto', 'yesil']);
    await ctx.close();
  }

  // ================= 6. Ana ekran kısayolları =================
  {
    const { ctx, p } = await open('kisayol', { ...devices['Pixel 7'] }, '?islem=sat&varlik=EUR');
    assert.equal(await p.getAttribute('body', 'data-view'), 'islem');
    assert.ok(await p.isChecked('#tOut'));
    assert.equal(await p.inputValue('#fCur'), 'EUR');
    assert.equal(await p.evaluate(() => location.search), '');           // yenileyince yeniden uygulanmaz
    await p.goto(URL + '?git=hesap');
    assert.equal(await p.getAttribute('body', 'data-view'), 'hesap');
    await p.goto(URL + '?git=yok&islem=x');                              // bilinmeyen değer: ana sayfa
    assert.equal(await p.getAttribute('body', 'data-view'), 'islem');
    await ctx.close();
    const m = JSON.parse(fs.readFileSync(ROOT + '/manifest.webmanifest', 'utf8'));
    assert.deepEqual(m.shortcuts.map((s) => s.url), ['./doviz-kasasi.html?islem=al&varlik=USD', './doviz-kasasi.html?islem=sat&varlik=USD',
      './doviz-kasasi.html?git=hesap', './doviz-kasasi.html?git=kurlar']);
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('PAKET 4 SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('paket4.js')).slice(0, 2).join(' | ')); process.exit(1); });
