// Yazıcıoğlu Çilek Döviz: makas uyarısı, pozisyon sınırları, envanter listesi, vitrin ekranında yön okları.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const Y = new Date().getFullYear() - 1;
const SEED = {
  tx: [
    { id: '1', seq: 1, date: Y + '-12-01', type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: Y + '-12-10', type: 'in', cur: 'USD', amount: 1000, rate: 40, note: '' },
    { id: '3', seq: 3, date: Y + '-12-20', type: 'in', cur: 'USD', amount: 1000, rate: 42, note: '' },     // ort. 41
    { id: '4', seq: 4, date: Y + '-12-28', type: 'in', cur: 'CEYREK', amount: 10, rate: 9000, note: '' },
    { id: '5', seq: 5, date: Y + '-12-31', type: 'out', cur: 'USD', amount: 500, rate: 43, note: '' },
    { id: '6', seq: 6, date: iso(0) > Y + 1 + '-01-01' ? Y + 1 + '-01-01' : iso(0), type: 'in', cur: 'USD', amount: 500, rate: 44, note: 'yeni yıl' },
  ],
  rates: { USD: 50, CEYREK: 10000 }, sell: { USD: 50.2, CEYREK: 10100 },
  myRates: { USD: { buy: 49.9, sell: 50.4 }, CEYREK: { buy: 9950, sell: 10150 } },
  items: [
    { id: 'i1', seq: 1, date: Y + '-11-01', name: 'Bilezik', karat: 22, gram: 10, cost: 30000, sold: null, txIn: 'x' },
    { id: 'i2', seq: 2, date: Y + '-11-02', name: 'Kolye', karat: 14, gram: 5, cost: null, sold: Y + '-12-15' },
  ],
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
};

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (name, opts) => {
    const ctx = await b.newContext({ ...opts, acceptDownloads: true });
    await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    const dialogs = [];
    let answer = true;
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => { dialogs.push(d.message()); answer ? d.accept() : d.dismiss(); });
    await p.addInitScript((seed) => {
      if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed));
      navigator.share = (d) => { window.__shared = d.text; return Promise.resolve(); };
    }, SEED);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    return { ctx, p, txt, store, dialogs, setAnswer: (v) => { answer = v; } };
  };

  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const { ctx, p, txt, store, dialogs, setAnswer } = await open(name, opts);

    // ================= 1. Makas uyarısı =================
    assert.ok(await p.isHidden('#spreadBanner'));
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="kurlar"]');
    await p.fill('#mr-sell-USD', '49,8'); await p.dispatchEvent('#mr-sell-USD', 'change');              // satış < alış
    assert.equal(await txt('#spreadText'), 'Kur tablonuzu kontrol edin: USD — satış kurunuz alış kurunuzdan düşük.');
    assert.ok((await txt('#myRates')).includes('⚠ Satış kurunuz alış kurunuzdan düşük'));
    await p.fill('#mr-sell-USD', '50,1'); await p.dispatchEvent('#mr-sell-USD', 'change');              // piyasa alışının (50) üstünde, sorun yok
    assert.ok(await p.isHidden('#spreadBanner'));
    await p.fill('#mr-buy-CEYREK', '10200'); await p.dispatchEvent('#mr-buy-CEYREK', 'change');         // alış > satış
    await p.fill('#mr-sell-CEYREK', '10300'); await p.dispatchEvent('#mr-sell-CEYREK', 'change');       // alış piyasa satışının (10100) üstünde
    assert.equal(await txt('#spreadText'), 'Kur tablonuzu kontrol edin: Çeyrek Altın — alış kurunuz piyasa satış fiyatının (10.100,00) üstünde.');
    await p.fill('#mr-sell-USD', '49,9'); await p.dispatchEvent('#mr-sell-USD', 'change');
    assert.equal(await txt('#spreadText'), 'Kur tablonuzda 2 kur hatalı görünüyor: USD, Çeyrek Altın.');
    await p.fill('#mr-sell-USD', '50,4'); await p.dispatchEvent('#mr-sell-USD', 'change');
    await p.fill('#mr-buy-CEYREK', '9950'); await p.dispatchEvent('#mr-buy-CEYREK', 'change');
    assert.ok(await p.isHidden('#spreadBanner'));
    // Formda: alışı satış kurundan yükseğe yazınca uyarı (kaydı engellemez)
    await p.click('button[data-go="islem"]');
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tIn"]');
    assert.ok(await p.isHidden('#fRateWarn'));
    await p.fill('#fRate', '50,5');
    assert.equal(await txt('#fRateWarn'), 'Dikkat: bu alış kuru satış kurunuzdan (50,4000) yüksek.');
    await p.click('label[for="tOut"]'); await p.fill('#fRate', '49,5');
    assert.equal(await txt('#fRateWarn'), 'Dikkat: bu satış kuru alış kurunuzdan (49,9000) düşük.');
    await p.fill('#fRate', '50,3');
    assert.ok(await p.isHidden('#fRateWarn'));
    // Fiyatlar 24 saatten eskiyse piyasayla karşılaştırma yapılmaz
    await p.evaluate(() => { const k = JSON.parse(localStorage.getItem('doviz-kasasi-v1')); k.ratesUpdated = '2020-01-01T00:00:00Z';
      k.myRates.CEYREK.buy = 10200; localStorage.setItem('doviz-kasasi-v1', JSON.stringify(k)); });
    await p.reload();
    assert.ok(await p.isHidden('#spreadBanner'));

    // ================= 2. Pozisyon sınırları =================
    await p.click('button[data-go="kasa"]');
    await p.click('[data-toggle="sinir"]');
    await p.selectOption('#limCur', 'USD');
    assert.equal(await txt('#limMaxLbl'), 'En fazla (USD)');
    await p.fill('#limMax', '2000'); await p.click('#limForm button[type="submit"]');
    assert.ok((await txt('#limList')).includes('USD en fazla 2.000,00Şu an 2.000,00 · %100'), await txt('#limList'));
    assert.ok(await p.isHidden('#limitBanner'));
    assert.ok((await txt('#balBody')).includes('sınır 2.000,00'));
    // Sınırı aşan alış sorulur; "Vazgeç" kaydetmez
    await p.click('button[data-go="islem"]');
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tIn"]');
    await p.fill('#fAmount', '100'); await p.fill('#fRate', '49,9');
    const n0 = (await store()).tx.length;
    setAnswer(false); dialogs.length = 0;
    await p.click('#btnSave');
    assert.ok(dialogs[0].startsWith('Bu işlemle sınırınız aşılıyor:\n• USD sınırı aşıldı: 2.100,00 (en fazla 2.000,00)'), dialogs[0]);
    assert.equal((await store()).tx.length, n0);
    setAnswer(true);
    await p.click('#btnSave');
    assert.equal((await store()).tx.length, n0 + 1);
    assert.equal(await txt('#limitText'), 'USD sınırı aşıldı: 2.100,00 (en fazla 2.000,00).');
    // Satış sınırı düzeltir; sormaz
    dialogs.length = 0;
    await p.click('label[for="tOut"]'); await p.fill('#fAmount', '200'); await p.fill('#fRate', '50,4');
    await p.click('#btnSave');
    assert.equal(dialogs.length, 0, dialogs.join('|'));
    assert.ok(await p.isHidden('#limitBanner'));
    // TL kasası alt sınırı
    await p.click('button[data-go="kasa"]');
    await p.fill('#limTL', '600000'); await p.click('#limForm button[type="submit"]');
    assert.ok((await txt('#limitText')).startsWith('TL kasası sınırın altında: ₺'));
    await p.click('#btnLimitGo');
    assert.ok((await txt('#limList')).includes('TL kasası en az ₺600.000,00'));
    await p.locator('#limList li', { hasText: 'TL kasası' }).getByRole('button').click();
    assert.ok(await p.isHidden('#limitBanner'));
    assert.deepEqual((await store()).limits, { max: { USD: 2000 }, minTL: null });

    // ================= 3. Envanter listesi =================
    await p.click('button[data-go="gun"]');
    await p.click('[data-toggle="envanter"]');
    await p.click('#invYear');
    assert.equal(await p.inputValue('#invDate'), Y + '-12-31');
    const inv = await txt('#invBody');
    // USD: 1.500 kalan, ort. 41 → 61.500; çeyrek 10 adet × 9.000
    assert.ok(inv.includes('1.500,00') && inv.includes('41,0000') && inv.includes('₺61.500,00'), inv);
    assert.ok(inv.includes('10 adet') && inv.includes('16,07') && inv.includes('₺90.000,00'), inv);
    const sum = await txt('#invSum');
    assert.ok(sum.includes('Stok maliyeti toplamı₺151.500,00') && sum.includes('TL kasası₺349.500,00') &&
              sum.includes('Genel toplam (TL + stok maliyeti)₺501.000,00'), sum);          // 500.000 − 82.000 − 90.000 + 21.500
    assert.ok((await txt('#invNote')).startsWith('Vitrin defteri: 1 parça · 10 gr (has 9,16 gr) · kayıtlı maliyet ₺30.000,00. Bunlardan 1 parça kasaya'));
    await p.click('#invShare');
    const shared = await p.evaluate(() => window.__shared);
    assert.ok(shared.startsWith('Yazıcıoğlu Çilek Döviz — Envanter listesi\n31.12.' + Y + ' akşamı itibarıyla'), shared);
    assert.ok(shared.includes('USD: 1.500,00 · ort. maliyet 41,0000 · toplam ₺61.500,00'), shared);
    const [dl] = await Promise.all([p.waitForEvent('download'), p.click('#invCsv')]);
    assert.equal(dl.suggestedFilename(), 'cilek-doviz-envanter-' + Y + '-12-31.csv');
    const csv = require('fs').readFileSync(await dl.path(), 'utf8');
    assert.ok(csv.includes('"USD";1500;USD;;41;61500') && csv.includes('"Genel toplam";;;;;501000'), csv);
    // Daha önceki gün: 31 Aralık satışı ve çeyrek yok
    await p.fill('#invDate', Y + '-12-20'); await p.dispatchEvent('#invDate', 'change');
    assert.ok((await txt('#invSum')).includes('Stok maliyeti toplamı₺82.000,00'));
    await ctx.close();
  }

  // ================= 4. Vitrin ekranında yön okları =================
  {
    const ctx = await b.newContext({ viewport: { width: 1280, height: 720 } });
    await ctx.route(/truncgil/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push('vitrin: ' + e.message));
    await p.addInitScript((seed) => { if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed)); }, SEED);
    await p.goto('http://kasa.test/vitrin.html');
    const rows = async () => (await p.locator('#body tr').allTextContents()).map((t) => t.replace(/\s+/g, ' ').trim());
    const setRate = (c, side, v) => p.evaluate(([c, side, v]) => { const k = JSON.parse(localStorage.getItem('doviz-kasasi-v1')); k.myRates[c][side] = v;
      localStorage.setItem('doviz-kasasi-v1', JSON.stringify(k)); window.dispatchEvent(new StorageEvent('storage', { key: 'doviz-kasasi-v1' })); }, [c, side, v]);
    assert.deepEqual(await rows(), ['DolarUSD49,900050,4000', 'Çeyrek Altın9.950,0010.150,00']);
    assert.equal(await p.textContent('#legend'), '');
    await setRate('USD', 'buy', 49.7); await setRate('CEYREK', 'sell', 10200);
    assert.deepEqual(await rows(), ['DolarUSD▼49,700050,4000', 'Çeyrek Altın9.950,00▲10.200,00']);
    assert.equal(await p.textContent('#legend'), ' ▲ ▼ günün ilk fiyatına göre.');
    assert.equal(await p.locator('.dir.down').count(), 1);
    // Fiyat günün ilk fiyatına dönünce ok kalkar; yenileyince günün ilk fiyatı hatırlanır
    await setRate('USD', 'buy', 49.9);
    await p.reload();
    assert.deepEqual(await rows(), ['DolarUSD49,900050,4000', 'Çeyrek Altın9.950,00▲10.200,00']);
    // Ertesi gün sıfırlanır
    await p.evaluate(() => { const o = JSON.parse(localStorage.getItem('vitrin-acilis')); o.d = '2000-1-1'; localStorage.setItem('vitrin-acilis', JSON.stringify(o)); });
    await p.reload();
    assert.deepEqual(await rows(), ['DolarUSD49,900050,4000', 'Çeyrek Altın9.950,0010.200,00']);
    // Ayarlardan kapatılabilir
    await setRate('USD', 'sell', 50.9);
    assert.ok((await rows())[0].includes('▲'));
    await p.click('#btnSet');
    assert.ok(await p.isChecked('#fArrows'));
    await p.uncheck('#fArrows'); await p.click('#form button[type="submit"]');
    await setRate('USD', 'sell', 51.2);
    assert.deepEqual(await rows(), ['DolarUSD49,900051,2000', 'Çeyrek Altın9.950,0010.200,00']);
    assert.equal(JSON.parse(await p.evaluate(() => localStorage.getItem('vitrin-v1'))).arrows, false);
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('PAKET 3 SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('paket3.js')).slice(0, 2).join(' | ')); process.exit(1); });
