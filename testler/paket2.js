// Döviz Kasası: hafta sonu makası, bekleyen müşteri alarmları, dökümde yorum/yol bağlantısı, kartı açılmış gram altın.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const MARKET = { USD: { Buying: 50, Selling: 50.2, Change: 0 }, GRA: { Buying: 6000, Selling: 6010, Change: 0 } };
const SEED = {
  tx: [
    { id: '1', seq: 1, date: '2026-11-16', type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: '2026-11-16', type: 'in', cur: 'USD', amount: 1000, rate: 49, note: '' },
  ],
  rates: { USD: 50, GA: 6000 }, sell: { USD: 50.2, GA: 6010 },
  myRates: { USD: { buy: 49.9, sell: 50.4 }, GA: { buy: 5980, sell: 6040 } },
  auto: { USD: { on: true, b: -0.1, s: 0.2 } },
  ratesUpdated: '2020-01-01T00:00:00Z', rateSrc: 'tr',
};

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (name, opts, when) => {
    const ctx = await b.newContext(opts);
    await ctx.route(/truncgil/, (r) => r.fulfill({ contentType: 'application/json', body: JSON.stringify(MARKET) }));
    await ctx.route(/er-api|frankfurter|gold-api|wa\.me/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    const dialogs = [];
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => { dialogs.push(d.message()); d.accept(); });
    if (when) await p.clock.install({ time: when });
    await p.addInitScript((seed) => {
      if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed));
      navigator.share = (d) => { window.__shared = d.text; return Promise.resolve(); };
      window.open = (u) => { window.__opened = u; return null; };
    }, SEED);
    await p.goto(URL);
    await p.waitForFunction(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')).ratesUpdated > '2021');   // fiyatlar alındı
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    return { ctx, p, txt, store, dialogs };
  };

  // ================= 1. Hafta sonu makası =================
  {
    // Cumartesi öğlen
    const o = await open('cumartesi', { viewport: { width: 1200, height: 900 } }, new Date('2026-11-21T12:00:00'));
    const { p, txt, store } = o;
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="kurlar"]'); await p.click('[data-toggle="otokur"]');
    assert.ok(await p.isHidden('#wkTimes'));
    await p.check('#wkOn');
    assert.ok(await p.isVisible('#wkTimes'));
    assert.equal(await txt('#wkNow'), 'Şu an hafta sonu farkı geçerli.');
    await p.fill('#au-wb-USD', '−0,50'); await p.fill('#au-ws-USD', '0,60'); await p.dispatchEvent('#au-ws-USD', 'change');
    let st = await store();
    assert.deepEqual(st.auto.USD, { on: true, b: -0.1, s: 0.2, wb: -0.5, ws: 0.6 });
    assert.deepEqual(st.myRates.USD, { buy: 49.5, sell: 50.8 });                     // hafta sonu: 50 − 0,50 ; 50,2 + 0,60
    assert.ok((await txt('#autoRows')).includes('Hafta sonu: 49,5000 / 50,8000'));
    // Pazartesi 10:00'a gelince hafta içi farkı kendiliğinden döner
    await p.clock.setSystemTime(new Date('2026-11-23T10:00:00'));
    await p.clock.runFor(61000);
    await p.waitForFunction(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')).myRates.USD.buy === 49.9);
    st = await store();
    assert.equal(st.myRates.USD.sell, 50.4);
    assert.deepEqual(st.weekend, { on: true, fri: '18:00', mon: '09:30' });
    await o.ctx.close();
    // Cuma 17:00 hafta içi, Cuma 18:30 hafta sonu
    const f = await open('cuma', { viewport: { width: 1200, height: 900 } }, new Date('2026-11-20T17:00:00'));
    await f.p.evaluate(() => { const k = JSON.parse(localStorage.getItem('doviz-kasasi-v1'));
      k.weekend = { on: true, fri: '18:00', mon: '09:30' }; k.auto.USD.wb = -0.5; k.auto.USD.ws = 0.6; localStorage.setItem('doviz-kasasi-v1', JSON.stringify(k)); });
    await f.p.reload();
    await f.p.click('button[data-go="kasa"]'); await f.p.click('button[data-go="kurlar"]');
    assert.equal(await f.txt('#wkNow'), 'Şu an hafta içi farkı geçerli.');
    await f.p.clock.setSystemTime(new Date('2026-11-20T18:30:00'));
    await f.p.clock.runFor(61000);
    await f.p.waitForFunction(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')).myRates.USD.buy === 49.5);
    await f.ctx.close();
  }

  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const { ctx, p, txt, store, dialogs } = await open(name, opts);

    // ================= 2. Bekleyen müşteri alarmları =================
    await p.click('button[data-go="cari"]'); await p.click('button[data-go="alarm"]');
    assert.equal(await p.getAttribute('#tabs button[data-go="cari"]', 'aria-current'), 'page');
    assert.ok(await p.isVisible('#aEmpty'));
    await p.click('[data-toggle="alarm"]');
    await p.selectOption('#aCur', 'USD');
    assert.equal(await txt('#aNow'), 'Şu anki satış kurunuz: 50,4000');
    await p.fill('#aName', 'Ayşe Hanım'); await p.fill('#aPhone', '0532 111 22 33'); await p.fill('#aTarget', '50');
    await p.click('#aForm button[type="submit"]');
    await p.click('#aSell'.replace('#', 'label[for="') + '"]');
    assert.equal(await txt('#aTargetLbl'), 'Alış kurunuz en az (₺)');
    await p.fill('#aName', 'Mehmet Bey'); await p.fill('#aTarget', '49');
    await p.click('#aForm button[type="submit"]');
    assert.equal(await p.locator('#aList li').count(), 2);
    // Mehmet satmak istiyor, hedef ≥ 49, alış kurumuz 49,9 → hemen tetiklenir; Ayşe almak istiyor, ≤ 50 hedefi henüz değil
    assert.ok(await p.isVisible('#alertBanner'));
    assert.equal(await txt('#alertText'), 'Mehmet Bey için beklenen USD fiyatı geldi.');
    const hit = p.locator('#aList li.hit');
    assert.equal(await hit.count(), 1);
    await hit.getByRole('button', { name: 'Mesaj gönder' }).click();                  // telefonsuz: paylaşım menüsü
    assert.ok((await p.evaluate(() => window.__shared)).startsWith('Merhaba Mehmet Bey, Yazıcıoğlu Çilek Döviz olarak haber vermek istedik: beklediğiniz USD fiyatı geldi. Şu an alış fiyatımız 49,9000 ₺.'));
    await hit.getByRole('button', { name: 'Tamam' }).click();
    assert.ok(await p.isHidden('#alertBanner'));
    // Satış kurumuz 50'ye inince Ayşe'nin alarmı çalar; telefon varsa WhatsApp bağlantısı açılır
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="kurlar"]');
    await p.fill('#mr-sell-USD', '50'); await p.dispatchEvent('#mr-sell-USD', 'change');
    await p.click('button[data-go="cari"]'); await p.click('button[data-go="alarm"]');
    assert.equal(await txt('#alertText'), 'Ayşe Hanım için beklenen USD fiyatı geldi.');
    await p.locator('#aList li.hit').getByRole('button', { name: 'Mesaj gönder' }).click();
    const opened = await p.evaluate(() => window.__opened);
    assert.ok(opened.startsWith('https://wa.me/905321112233?text=Merhaba%20Ay%C5%9Fe%20Han%C4%B1m'), opened);
    // Uyarı ana sayfada da görünür, "Göster" alarmlara götürür
    await p.click('button[data-go="islem"]');
    assert.ok(await p.isVisible('#alertBanner'));
    await p.click('#btnAlertGo');
    assert.ok(await p.isVisible('#aList'));
    // Silme
    await p.locator('#aList li', { hasText: 'Mehmet Bey' }).getByRole('button', { name: '×' }).click();
    assert.equal((await store()).alerts.length, 1);

    // ================= 3. Dökümde yorum ve yol tarifi bağlantısı =================
    await p.click('button[data-go="hesap"]');
    await p.click('#kCoin'); await p.selectOption('#kCoin', '');
    await p.fill('#kGram', '5'); await p.click('#kAdd');
    await p.click('#kReceipt');
    await p.click('#rcLinkSet');
    await p.fill('#dlgInput', 'g.page/bizim'); await p.click('#dlgForm button[type="submit"]');
    assert.equal(await txt('#dlgMsg'), 'Bağlantı https:// ile başlamalı.');
    await p.fill('#dlgInput', 'https://g.page/r/ornek/review'); await p.click('#dlgForm button[type="submit"]');
    await p.waitForFunction(() => document.getElementById('dlgTitle').textContent === 'Yol tarifi bağlantısı');
    await p.fill('#dlgInput', 'https://maps.app.goo.gl/ornek'); await p.click('#dlgForm button[type="submit"]');
    assert.ok((await txt('#rcLinks')).includes('Bizi değerlendirin: https://g.page/r/ornek/review'));
    await p.click('#rcShare');
    const shared = await p.evaluate(() => window.__shared);
    assert.ok(shared.includes('(Bilgi amaçlı hesap dökümüdür; belge değildir.)') && shared.includes('Yol tarifi: https://maps.app.goo.gl/ornek'), shared);
    await p.click('#rcClose');
    assert.deepEqual((await store()).links, { review: 'https://g.page/r/ornek/review', maps: 'https://maps.app.goo.gl/ornek' });

    // ================= 4. Kartı açılmış gram altın =================
    await p.click('button[data-go="islem"]');
    await p.click('[data-toggle="txmore"]').catch(() => {});
    if (await p.isHidden('#fCur')) await p.click('[data-toggle="txmore"]');
    await p.selectOption('#fCur', 'GA'); await p.dispatchEvent('#fCur', 'change');
    await p.click('label[for="tIn"]');
    assert.ok(await p.isVisible('#wornField'));
    assert.equal(await txt('#fWornLbl'), 'Kartı açılmış / yıpranmış');
    await p.check('#fWorn'); await p.fill('#fWornD', '40'); await p.dispatchEvent('#fWornD', 'change');
    assert.equal(await p.inputValue('#fRate'), '5940');                             // 5980 − 40
    await p.fill('#fAmount', '10'); await p.click('#btnSave');
    const st = await store();
    const last = st.tx[st.tx.length - 1];
    assert.deepEqual([last.cur, last.rate, last.note], ['GA', 5940, 'Kartı açılmış']);
    assert.equal(st.worn.GA, 40);
    // Çeyrekte "Eski tarihli" olarak çıkar (alışta da satışta da); 22 ayarda çıkmaz
    await p.selectOption('#fCur', 'CEYREK'); await p.dispatchEvent('#fCur', 'change');
    assert.equal(await txt('#fWornLbl'), 'Eski tarihli');
    await p.selectOption('#fCur', 'B22'); await p.dispatchEvent('#fCur', 'change');
    assert.ok(await p.isHidden('#wornField'));
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('PAKET 2 SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('paket2.js')).slice(0, 2).join(' | ')); process.exit(1); });
