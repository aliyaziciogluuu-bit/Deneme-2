// Döviz Kasası: otomatik kur, eski seri farkı, borç hatırlatma, hızlı işlem şablonları, gün sonu kapanışı.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const fmt = (d) => d.slice(8) + '.' + d.slice(5, 7) + '.' + d.slice(0, 4);
const MARKET = { USD: { Buying: 50, Selling: 50.2, Change: 0 }, EUR: { Buying: 55, Selling: 55.3, Change: 0 },
  GRA: { Buying: 6000, Selling: 6010, Change: 0 }, HAS: { Buying: 5980, Selling: 5990, Change: 0 } };
const SEED = {
  tx: [
    { id: '1', seq: 1, date: iso(3), type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: iso(2), type: 'in', cur: 'USD', amount: 1000, rate: 49.8, note: '' },
    { id: '3', seq: 3, date: iso(1), type: 'out', cur: 'USD', amount: 200, rate: 50.5, note: '' },
    { id: '4', seq: 4, date: iso(1), type: 'out', cur: 'USD', amount: 150, rate: 50, note: 'Pazartesi ödeyecek', cari: 'Ahmet Bey' },
    { id: '5', seq: 5, date: iso(1), type: 'in', cur: 'TRY', amount: 2000, rate: 1, note: 'Emanet', cari: 'Veli Usta' },
  ],
  rates: { USD: 49, EUR: 54, HAS: 5900 }, sell: { USD: 49.2, EUR: 54.3, HAS: 5910 },
  myRates: { USD: { buy: 49.5, sell: 50.5 }, EUR: { buy: 54.5, sell: 55.5 }, HAS: { buy: 5950, sell: 6050 } },
  ratesUpdated: '2020-01-01T00:00:00Z', rateSrc: 'tr',
};

(async () => {
  const b = await chromium.launch();
  const errors = [];
  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const ctx = await b.newContext(opts);
    let market = MARKET;
    await ctx.route(/truncgil/, (r) => r.fulfill({ contentType: 'application/json', body: JSON.stringify(market) }));
    await ctx.route(/er-api|frankfurter|gold-api/, (r) => r.abort());
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
    await p.waitForFunction(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')).rates.USD === 50);   // açılışta fiyatlar güncellendi
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));

    // ================= 1. Otomatik kur =================
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="kurlar"]');
    assert.ok(await p.isHidden('#autoRows'));
    await p.click('[data-toggle="otokur"]');
    await p.fill('#au-b-USD', '−0,10'); await p.fill('#au-s-USD', '0,20');
    await p.check('#au-USD');
    let st = await store();
    assert.deepEqual(st.auto.USD, { on: true, b: -0.1, s: 0.2 });
    assert.deepEqual(st.myRates.USD, { buy: 49.9, sell: 50.4 });                       // 50 − 0,10 ve 50,2 + 0,20
    assert.ok((await txt('#autoRows')).includes('Şu an: 49,9000 / 50,4000'));
    assert.ok((await txt('#myRates')).includes('otomatik'));
    // has için satır: metalde iki ondalık
    await p.fill('#au-b-HAS', '-30'); await p.fill('#au-s-HAS', '45'); await p.check('#au-HAS');
    assert.deepEqual((await store()).myRates.HAS, { buy: 5950, sell: 6035 });
    // fiyatlar güncellenince kur kendiliğinden değişir
    market = { ...MARKET, USD: { Buying: 51, Selling: 51.3, Change: 0 } };
    await p.click('#btnRates');
    await p.waitForFunction(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')).myRates.USD.buy === 50.9);
    assert.equal((await store()).myRates.USD.sell, 51.5);
    // elle kur yazınca o varlığın otomatiği kapanır
    await p.fill('#mr-sell-USD', '52'); await p.dispatchEvent('#mr-sell-USD', 'change');
    st = await store();
    assert.deepEqual(st.auto.USD, { on: false, b: -0.1, s: 0.2 }); assert.equal(st.myRates.USD.sell, 52);   // fark saklanır
    assert.ok(st.auto.HAS && st.auto.HAS.on);
    assert.ok(!(await p.isChecked('#au-USD')));
    // geçersiz fark kaydedilmez
    await p.fill('#au-b-EUR', 'abc'); await p.check('#au-EUR');
    assert.equal((await store()).auto.EUR, undefined);
    await p.uncheck('#au-EUR');
    await p.fill('#au-b-EUR', '');

    // ================= 2. Eski seri / yıpranmış döviz =================
    await p.click('button[data-go="islem"]');
    await p.click('#quick button:has-text("USD")');
    assert.equal(await p.inputValue('#fRate'), '50,9');
    assert.ok(await p.isVisible('#wornField') && await p.isHidden('#fWornD'));
    await p.check('#fWorn');
    assert.ok(await p.isVisible('#fWornD'));
    await p.fill('#fWornD', '0,7'); await p.dispatchEvent('#fWornD', 'change');
    assert.equal(await p.inputValue('#fRate'), '50,2');                                  // 50,9 − 0,7
    await p.fill('#fAmount', '100');
    await p.click('#btnSave');
    st = await store();
    let last = st.tx[st.tx.length - 1];
    assert.deepEqual([last.type, last.cur, last.amount, last.rate, last.note], ['in', 'USD', 100, 50.2, 'Eski seri']);
    assert.equal(st.worn.USD, 0.7);
    assert.ok(!(await p.isChecked('#fWorn')));                                          // form sıfırlandı
    // ikinci kez: fark hatırlanır
    await p.check('#fWorn');
    assert.equal(await p.inputValue('#fWornD'), '0,7');
    assert.equal(await p.inputValue('#fRate'), '50,2');
    await p.uncheck('#fWorn');
    assert.equal(await p.inputValue('#fRate'), '50,9');
    // satışta, altında ve TL'de görünmez
    await p.click('label[for="tOut"]');
    assert.ok(await p.isHidden('#wornField'));
    await p.click('label[for="tIn"]');
    await p.click('#quick button:has-text("Has Altın")');
    assert.ok(await p.isHidden('#wornField'));
    await p.click('#quick button:has-text("TL")');
    assert.ok(await p.isHidden('#wornField'));

    // ================= 3. Hızlı işlem şablonları =================
    assert.ok(await p.isHidden('#tplF'));
    await p.click('#btnTpl');
    assert.equal(await txt('#fMsg'), 'Şablon için önce tutarı yazın.');
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tOut"]'); await p.fill('#fAmount', '100');
    await p.click('#btnTpl');
    await p.click('#btnTpl');
    assert.equal(await txt('#fMsg'), 'Bu şablon zaten var.');
    await p.click('#quick button:has-text("TL")'); await p.click('label[for="tOut"]'); await p.check('#fExp'); await p.fill('#fAmount', '250');
    await p.click('#btnTpl');
    await p.click('#btnCancel').catch(() => {});
    assert.ok(await p.isVisible('#tplF'));
    assert.deepEqual(await p.locator('#tplRow button').allTextContents(), ['100,00 USD sat', 'Masraf ₺250,00', 'Düzenle']);
    const n0 = (await store()).tx.length;
    await p.click('#tplRow button:has-text("100,00 USD sat")');
    st = await store();
    last = st.tx[st.tx.length - 1];
    assert.equal(st.tx.length, n0 + 1);
    assert.deepEqual([last.type, last.cur, last.amount, last.rate, last.date], ['out', 'USD', 100, 52, iso(0)]);
    assert.ok((await txt('#toastMsg')).includes('100,00 USD sat · 52,0000 kaydedildi'));
    await p.click('#toastUndo');                                                          // geri alınabilir
    assert.equal((await store()).tx.length, n0);
    await p.click('#tplRow button:has-text("Masraf")');
    last = (await store()).tx.slice(-1)[0];
    assert.ok(last.exp && last.cur === 'TRY' && last.amount === 250);
    // düzenle: × ile silinir
    await p.click('#tplRow button:has-text("Düzenle")');
    await p.click('#tplRow button:has-text("Masraf")');
    assert.deepEqual(await p.locator('#tplRow button').allTextContents(), ['× 100,00 USD sat', 'Bitti']);
    await p.click('#tplRow button:has-text("Bitti")');
    assert.equal((await store()).tpl.length, 1);
    await p.screenshot({ path: require('os').tmpdir() + '/kasa-' + name + '-sablon.png' });

    // ================= 4. Borç hatırlatma =================
    await p.click('button[data-go="cari"]');
    const ahmet = p.locator('#persons .person', { hasText: 'Ahmet Bey' });
    const veli = p.locator('#persons .person', { hasText: 'Veli Usta' });
    assert.equal(await veli.getByRole('button', { name: 'Hatırlat' }).count(), 0);         // emanet: hatırlatma yok
    await ahmet.getByRole('button', { name: 'Hatırlat' }).click();
    const msg = await p.evaluate(() => window.__shared);
    assert.equal(msg, 'Merhaba Ahmet Bey, Yazıcıoğlu Çilek Döviz olarak kısa bir hatırlatma: hesabınızda 150,00 USD görünüyor. ' +
                      'Uygun olduğunuzda bekleriz. İyi günler dileriz.');

    // ================= 5. Gün sonu kapanışı =================
    await p.click('button[data-go="gun"]');
    await p.click('#dayPrev');                                                            // dün
    assert.ok(await p.isVisible('#btnCloseDay'));
    await p.click('#btnCloseDay');
    assert.ok(dialogs.some((d) => d.startsWith(fmt(iso(1)) + ' kapatılsın mı?')), dialogs.join('|'));
    st = await store();
    assert.deepEqual(st.closed.map((c) => c.d), [iso(1)]);
    assert.ok((await txt('#closeBar')).includes('Bu gün kapatıldı.') && await p.isVisible('#btnReopen'));
    await p.click('#dayPrev');                                                            // önceki gün de kilitli
    assert.ok((await txt('#closeBar')).includes(fmt(iso(1)) + ' kapanışıyla kilitli') && await p.isHidden('#btnReopen'));
    await p.click('#dayToday');
    assert.ok(await p.isVisible('#btnCloseDay'));                                         // bugün açık
    // kilitli günün işlemi silinemez, düzenlenemez; o güne yeni işlem girilemez
    const nTx = (await store()).tx.length;
    await p.click('button[data-go="liste"]');
    const row = p.locator('#txBody tr', { hasText: '50,5000' });
    await row.locator('td').nth(2).click().catch(() => {});
    await row.getByRole('button', { name: 'Sil' }).click();
    assert.ok(dialogs.some((d) => d.includes('ve öncesi kapatıldı (gün sonu)')), dialogs.join('|'));
    assert.equal((await store()).tx.length, nTx);
    await row.getByRole('button', { name: 'Düzenle' }).click();
    await p.fill('#fAmount', '201');
    await p.click('#btnSave');
    assert.ok((await txt('#fMsg')).includes('ve öncesi kapatıldı'));
    await p.click('#btnCancel');
    await p.click('[data-toggle="txmore"]').catch(() => {});
    if (await p.isHidden('#fDate')) await p.click('[data-toggle="txmore"]');
    await p.fill('#fDate', iso(2));
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tIn"]'); await p.fill('#fAmount', '10');
    await p.click('#btnSave');
    assert.ok((await txt('#fMsg')).includes('ve öncesi kapatıldı'));
    // bugüne işlem girilebilir
    await p.fill('#fDate', iso(0)); await p.fill('#fAmount', '10');
    await p.click('#btnSave');
    assert.equal((await store()).tx.length, nTx + 1);
    // bugünü kapat → hızlı işlem ve vitrinden alış da engellenir
    await p.click('button[data-go="gun"]'); await p.click('#modeDay'); await p.click('#dayToday');
    await p.click('#btnCloseDay');
    await p.click('button[data-go="islem"]');
    await p.click('#tplRow button:has-text("100,00 USD sat")');
    assert.ok((await txt('#fMsg')).includes('ve öncesi kapatıldı'));
    assert.equal((await store()).tx.length, nTx + 1);
    // kilidi aç: son kapanış kalkar, bugün yeniden açılır
    await p.click('button[data-go="gun"]'); await p.click('#dayToday');
    await p.click('#btnReopen');
    st = await store();
    assert.deepEqual(st.closed.map((c) => c.d), [iso(1)]);
    assert.ok(await p.isVisible('#btnCloseDay'));
    // ayda ve analizde kapanış çubuğu görünmez
    await p.click('#modeMonth');
    assert.ok(await p.isHidden('#closeBar'));
    await p.click('#modeDay');
    // kalıcılık
    await p.reload();
    st = await store();
    assert.equal(st.closed.length, 1); assert.equal(st.tpl.length, 1); assert.ok(st.auto.HAS.on); assert.equal(st.worn.USD, 0.7);
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('YENİ ÖZELLİK SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('yeni-ozellikler.js')).slice(0, 2).join(' | ')); process.exit(1); });
