// Döviz Kasası: zararına satış uyarısı, satış kârı bildirimi, hızlı tutar düğmeleri, başparmakla kaydet, büyük yazı, titreşim.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = {
  tx: [
    { id: '1', seq: 1, date: iso(3), type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: iso(2), type: 'in', cur: 'USD', amount: 1000, rate: 50, note: '' },
    { id: '3', seq: 3, date: iso(1), type: 'in', cur: 'USD', amount: 1000, rate: 51, note: '' },        // ortalama 50,50
    { id: '4', seq: 4, date: iso(2), type: 'in', cur: 'CEYREK', amount: 10, rate: 10000, note: '' },
  ],
  rates: { USD: 50.4, CEYREK: 9950 }, sell: { USD: 50.5, CEYREK: 10050 },
  myRates: { USD: { buy: 50.2, sell: 50.6 }, CEYREK: { buy: 9900, sell: 10100 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
  tpl: [{ id: 't1', type: 'out', cur: 'USD', amount: 100 }],
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
    let answer = true;
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => { dialogs.push(d.message()); answer ? d.accept() : d.dismiss(); });
    await p.addInitScript((seed) => {
      if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed));
      window.__vib = []; navigator.vibrate = (ms) => { window.__vib.push(ms); return true; };
    }, SEED);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    const n0 = (await store()).tx.length;

    // ================= Hızlı tutar düğmeleri =================
    await p.click('#quick button:has-text("USD")');
    assert.deepEqual(await p.locator('#amtQuick button').allTextContents(), ['100', '500', '1.000', '5.000']);
    await p.click('#amtQuick button:has-text("500")');
    assert.equal(await p.inputValue('#fAmount'), '500');
    assert.equal(await p.getAttribute('#amtQuick button:has-text("500")', 'aria-pressed'), 'true');
    assert.ok((await txt('#fTotal')).includes('25.100'));                          // 500 × 50,20
    await p.fill('#fAmount', '1000');
    assert.equal(await p.getAttribute('#amtQuick button:has-text("1.000")', 'aria-pressed'), 'true');
    await p.click('#quick button:has-text("Çeyrek")');
    assert.deepEqual(await p.locator('#amtQuick button').allTextContents(), ['1 adet', '2 adet', '5 adet', '10 adet']);
    await p.click('#quick button:has-text("TL")');
    assert.deepEqual(await p.locator('#amtQuick button').allTextContents(), ['1.000 ₺', '5.000 ₺', '10.000 ₺', '50.000 ₺']);

    // ================= Zararına satış uyarısı =================
    // ortalama maliyet 50,50; 50,20'den 100 USD satmak 30 TL zarar
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tOut"]');
    await p.fill('#fAmount', '100'); await p.fill('#fRate', '50,2');
    answer = false;
    await p.click('#btnSave');
    const warn = dialogs.find((d) => d.includes('ortalama maliyetinizin altında'));
    assert.ok(warn && warn.includes('Ortalama maliyet: 50,5000') && warn.includes('Tahmini zarar: ₺30,00'), dialogs.join('|'));
    assert.equal((await store()).tx.length, n0);                                     // vazgeçildi: kaydedilmedi
    assert.deepEqual(await p.evaluate(() => window.__vib), []);                      // kayıt yoksa titreşim yok
    answer = true;
    await p.click('#btnSave');
    assert.equal((await store()).tx.length, n0 + 1);                                 // onaylandı: kaydedildi
    assert.deepEqual(await p.evaluate(() => window.__vib), [30]);                    // kayıtta kısa titreşim
    // kârlı satışta uyarı yok
    dialogs.length = 0;
    await p.click('label[for="tOut"]');
    await p.fill('#fAmount', '100'); await p.fill('#fRate', '50,8');
    await p.click('#btnSave');
    assert.ok(!dialogs.some((d) => d.includes('ortalama maliyetinizin altında')), dialogs.join('|'));
    assert.equal(await txt('#toastMsg'), 'İşlem kaydedildi · bu satıştan +\u2060₺30,00 kâr.');      // 100 × (50,80 − 50,50)
    assert.equal((await store()).tx.length, n0 + 2);
    // hızlı işlemde de çalışır (şablon kuru 50,60 > 50,50: uyarı yok; kur 50,30'a inince uyarı)
    await p.click('#tplRow button:has-text("100,00 USD sat")');
    assert.equal((await store()).tx.length, n0 + 3);
    assert.ok((await txt('#toastMsg')).endsWith('kaydedildi · bu satıştan +\u2060₺10,00 kâr.'), await txt('#toastMsg'));
    await p.evaluate(() => { const k = JSON.parse(localStorage.getItem('doviz-kasasi-v1')); k.myRates.USD.sell = 50.3; localStorage.setItem('doviz-kasasi-v1', JSON.stringify(k)); });
    await p.reload();
    answer = false; dialogs.length = 0;
    await p.click('#tplRow button:has-text("100,00 USD sat")');
    assert.ok(dialogs.some((d) => d.includes('Tahmini zarar: ₺20,00')), dialogs.join('|'));
    assert.equal((await store()).tx.length, n0 + 3);
    answer = true;
    // alışta uyarı yok
    dialogs.length = 0;
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tIn"]');
    await p.fill('#fAmount', '10'); await p.fill('#fRate', '60');
    await p.click('#btnSave');
    assert.ok(!dialogs.some((d) => d.includes('ortalama maliyetinizin altında')));
    assert.equal(await txt('#toastMsg'), 'İşlem kaydedildi.');                        // alışta kâr yazmaz

    // ================= Başparmakla kaydet (telefon) =================
    if (name === 'telefon') {
      await p.evaluate(() => window.scrollTo(0, 0));
      const pos = await p.evaluate(() => {
        const r = document.getElementById('btnSave').getBoundingClientRect(), n = document.getElementById('tabs').getBoundingClientRect();
        return { saveBottom: r.bottom, navTop: n.top, h: window.innerHeight };
      });
      assert.ok(pos.saveBottom <= pos.navTop + 1 && pos.saveBottom > pos.navTop - 90, 'kaydet düğmesi altta değil: ' + JSON.stringify(pos));
      await p.fill('#fAmount', '5'); await p.click('#btnSave');                       // kaydırmadan dokunulabilir
      assert.equal(await txt('#toastMsg'), 'İşlem kaydedildi.');
      const ov = await p.evaluate(() => [document.getElementById('toast').getBoundingClientRect().bottom, document.getElementById('btnSave').getBoundingClientRect().top]);
      assert.ok(ov[0] <= ov[1] + 1, 'bildirim kaydet düğmesinin üstüne biniyor: ' + ov.join(','));
    }

    // ================= Büyük yazı modu =================
    const before = await p.evaluate(() => document.getElementById('mToday').getBoundingClientRect().height);
    assert.equal(await p.getByRole('button', { name: 'Büyük yazı' }).count(), 1);
    await p.click('#btnBig');
    assert.equal(await p.getAttribute('#btnBig', 'aria-pressed'), 'true');
    const after = await p.evaluate(() => document.getElementById('mToday').getBoundingClientRect().height);
    assert.ok(after > before * 1.1, 'yazı büyümedi: ' + before + ' → ' + after);
    // telefonda yatay kaydırma olmaz, alt çubuk ekranın içinde kalır
    const fit = await p.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth, document.getElementById('tabs').getBoundingClientRect().bottom, window.innerHeight]);
    assert.ok(fit[0] <= fit[1] + 1, 'yatay taşma: ' + fit.join(','));
    if (name === 'telefon') assert.ok(fit[2] <= fit[3] + 1, 'alt çubuk ekran dışında: ' + fit.join(','));
    if (name === 'telefon') await p.screenshot({ path: require('os').tmpdir() + '/kasa-buyuk-yazi.png' });
    await p.reload();
    assert.equal(await p.getAttribute('#btnBig', 'aria-pressed'), 'true');            // hatırlanır
    await p.click('#btnBig');
    assert.equal(await p.getByRole('button', { name: 'Büyük yazı' }).count(), 1);
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('KOLAYLIK SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('kolayliklar.js')).slice(0, 2).join(' | ')); process.exit(1); });
