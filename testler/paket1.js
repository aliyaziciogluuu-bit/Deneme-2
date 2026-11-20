// Döviz Kasası, Paket 1: eski fiyat uyarısı, tek altın fiyatı, belge no, hesap dökümü, ekran düzeltmeleri,
// kayıp kaydı, yedek hatırlatması ve gün sonu yedeği.
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const fmt = (d) => d.slice(8) + '.' + d.slice(5, 7) + '.' + d.slice(0, 4);
const SEED = {
  tx: [
    { id: '1', seq: 1, date: iso(3), type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: iso(2), type: 'in', cur: 'USD', amount: 1000, rate: 50, note: '' },
    { id: '3', seq: 3, date: iso(2), type: 'in', cur: 'B22', amount: 50, rate: 5400, note: '' },
  ],
  rates: { USD: 50.4, HAS: 6000 }, sell: { USD: 50.5, HAS: 6010 },
  myRates: { USD: { buy: 50.2, sell: 50.8 }, HAS: { buy: 5990, sell: 6050 }, B22: { buy: 5450, sell: 5800 } },
  calc: { mil: { sell: { 22: 930 }, buy: {} }, labor: { 22: { v: 100, unit: 'gr' } } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
};
const MARKET = { USD: { Buying: 50.4, Selling: 50.5, Change: 0 }, HAS: { Buying: 6000, Selling: 6010, Change: 0 } };

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (name, opts, seed, ui, marketUp) => {
    const ctx = await b.newContext(opts);
    const net = { up: marketUp !== false };
    await ctx.route(/truncgil/, (r) => net.up ? r.fulfill({ contentType: 'application/json', body: JSON.stringify(MARKET) }) : r.abort());
    await ctx.route(/er-api|frankfurter|gold-api/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    const dialogs = [];
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => { dialogs.push(d.message()); d.accept(); });
    await p.addInitScript(([seed, ui]) => {
      if (!localStorage.getItem('doviz-kasasi-v1')) {
        localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed));
        if (ui) localStorage.setItem('doviz-kasasi-ui', JSON.stringify(ui));
      }
      window.__shared = 0; navigator.canShare = () => true; navigator.share = () => { window.__shared++; return Promise.resolve(); };
    }, [seed, ui]);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    return { ctx, p, txt, store, dialogs, net };
  };

  // ================= 1. Eski fiyat uyarısı =================
  {
    const old = new Date(Date.now() - 2.5 * 3600e3).toISOString();
    let o = await open('eski', { viewport: { width: 420, height: 860 } }, { ...SEED, ratesUpdated: old, auto: { USD: { on: true, b: -0.1, s: 0.2 } } }, null, false);
    await o.p.waitForTimeout(400);
    assert.ok(await o.p.isVisible('#staleBanner'));
    assert.ok((await o.txt('#staleText')).includes('2 saattir güncellenemedi'), await o.txt('#staleText'));
    o.net.up = true;
    await o.p.click('#btnStaleRefresh');
    await o.p.waitForSelector('#staleBanner', { state: 'hidden' });
    await o.ctx.close();
    // otomatik kur yoksa (kurlar elle) uyarı çıkmaz
    o = await open('elle', { viewport: { width: 420, height: 860 } }, { ...SEED, ratesUpdated: old }, null, false);
    await o.p.waitForTimeout(400);
    assert.ok(await o.p.isHidden('#staleBanner'));
    await o.ctx.close();
  }

  for (const [name, opts] of [['telefon', { ...devices['iPhone 13'] }], ['masaustu', { viewport: { width: 1200, height: 900 } }]]) {
    const { ctx, p, txt, store, dialogs } = await open(name, opts, SEED, { backupAt: new Date(Date.now() - 2 * 864e5).toISOString(), backupTx: 3 });

    // ================= 2. Tek altın fiyatı =================
    await p.click('button[data-go="hesap"]');
    assert.ok(!(await p.isChecked('#hasLinkChk')));
    await p.check('#hasLinkChk');
    let st = await store();
    assert.equal(st.hasLink, true);
    assert.deepEqual(st.myRates.B22, { buy: 5486.84, sell: 5726.5 });                 // 5990 × 0,916 ; 6050 × 0,930 + 100
    await p.fill('#hasSell', '6100'); await p.dispatchEvent('#hasSell', 'change');
    assert.equal((await store()).myRates.B22.sell, 5773);                            // 6100 × 0,93 + 100
    await p.fill('#kGram', '10');
    assert.ok((await txt('#kOut')).includes('Müşteriden alınacak: ₺57.730,00'));      // = 10 × 5.773: iki fiyat aynı
    await p.click('button[data-go="kasa"]'); await p.click('button[data-go="kurlar"]');
    assert.ok((await txt('#myRates')).includes('has fiyatından'));
    await p.click('[data-toggle="otokur"]');
    assert.equal(await p.locator('#au-B22').count(), 0);                             // bağlıyken otomatik kura girmez
    await p.fill('#mr-sell-B22', '5900'); await p.dispatchEvent('#mr-sell-B22', 'change');
    st = await store();
    assert.equal(st.hasLink, false); assert.equal(st.myRates.B22.sell, 5900);       // elle yazınca bağlantı kapanır
    await p.click('button[data-go="hesap"]');
    await p.check('#hasLinkChk');                                                    // yeniden aç

    // ================= 5a. Büyük tutar ve açıklayıcı bildirim =================
    await p.click('button[data-go="islem"]');
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tIn"]'); await p.fill('#fAmount', '100');
    assert.equal(await txt('#fTotal'), 'Müşteriye ödeyin: ₺5.020,00');
    await p.click('label[for="tOut"]');
    assert.equal(await txt('#fTotal'), 'Müşteriden alın: ₺5.080,00');
    // ================= 3. Belge no =================
    await p.click('label[for="tIn"]');
    if (await p.isHidden('#fDoc')) await p.click('[data-toggle="txmore"]');
    await p.fill('#fDoc', 'A-123');
    await p.click('#btnSave');
    assert.equal(await txt('#toastMsg'), '100,00 USD alındı · ₺5.020,00 ödendi.');
    st = await store();
    assert.equal(st.tx[st.tx.length - 1].doc, 'A-123');
    assert.equal(await p.inputValue('#fDoc'), '');
    await p.click('label[for="tOut"]'); await p.fill('#fAmount', '10'); await p.click('#btnSave');   // belgesiz satış
    await p.click('button[data-go="gun"]');
    const bar = await txt('#closeBar');
    assert.ok(bar.includes('Belge no girilmemiş 1 işlem var.'), bar);
    // "Günü kapat" özetin üstünde
    assert.ok(await p.evaluate(() => { const c = document.getElementById('closeBar'), d = document.querySelector('.daystats');
      return !!(c.compareDocumentPosition(d) & Node.DOCUMENT_POSITION_FOLLOWING); }));
    await p.click('button[data-go="liste"]');
    assert.ok((await txt('#txBody')).includes('Belge A-123'));
    const [csv] = await Promise.all([p.waitForEvent('download'), p.click('#btnCsv')]);
    const csvText = require('fs').readFileSync(await csv.path(), 'utf8');
    assert.ok(csvText.includes('Belge no') && csvText.includes('"A-123"'), csvText.slice(0, 200));

    // ================= 5e. Hesap: tek parçayı doğrudan kasaya işle =================
    await p.click('button[data-go="hesap"]');
    await p.click('#kKarats button[data-k="22"]');
    await p.fill('#kGram', '10');
    const n0 = (await store()).tx.length;
    await p.click('#kPostOne');
    st = await store();
    const sold = st.tx[st.tx.length - 1];
    assert.equal(st.tx.length, n0 + 1);
    assert.deepEqual([sold.type, sold.cur, sold.amount], ['out', 'B22', 10]);
    assert.ok(Math.abs(sold.amount * sold.rate - 57730) < 1e-6);
    assert.ok((await txt('#toastMsg')).startsWith('10 gr 22 Ayar Bilezik satıldı · ₺57.730,00 alındı · bu satıştan'), await txt('#toastMsg'));
    assert.equal(await p.locator('#kList li').count(), 1);
    assert.ok((await txt('#kList')).includes('kasaya işlendi'));
    await p.click('#toastUndo');
    assert.equal((await store()).tx.length, n0);
    assert.equal(await p.locator('#kList li').count(), 0);
    assert.equal(await p.inputValue('#kGram'), '');                                  // işlendikten sonra kutu boşalır
    await p.fill('#kGram', '10'); await p.click('#kPostOne');
    // ================= 4. Hesap dökümü =================
    assert.equal((await txt('#kReceipt')), 'Döküm');
    await p.click('#kReceipt');
    assert.ok((await txt('#receipt')).includes('HESAP DÖKÜMÜ · BELGE DEĞİLDİR'));
    await p.click('#rcClose');

    // ================= 6. Kayıp kaydı =================
    await p.click('button[data-go="kasa"]');
    const usd = p.locator('#balBody tr', { hasText: 'USD' });
    if (name === 'telefon') await usd.locator('td.title').click();
    await usd.getByRole('button', { name: 'USD kaybı gir' }).click();
    await p.fill('#dlgInput', '20'); await p.click('#dlgForm button[type="submit"]');
    assert.equal(await txt('#toastMsg'), 'USD kaybı kaydedildi · ₺1.000,36 kârdan düşüldü.');   // 20 × 50,018 ortalama maliyet (55.020 / 1.100)
    st = await store();
    const loss = st.tx[st.tx.length - 1];
    assert.deepEqual([loss.type, loss.cur, loss.amount, loss.loss, loss.note], ['out', 'USD', 20, true, 'Kayıp']);
    await p.click('button[data-go="gun"]');
    assert.equal(await txt('#dExp'), '₺1.000,36');
    await p.click('button[data-go="liste"]');
    assert.ok((await txt('#txBody')).includes('Kayıp'));

    // ================= 7. Yedek hatırlatması ve gün sonu yedeği =================
    await p.click('button[data-go="islem"]');
    assert.ok(await p.isVisible('#backupBanner'));
    assert.ok((await txt('#backupText')).startsWith('Son yedekten beri'), await txt('#backupText'));
    await p.click('button[data-go="gun"]');
    await p.click('#btnCloseDay');
    await p.click('#wizNext'); await p.click('#wizNext');
    assert.ok(await p.isChecked('#wzBackup'));                                       // yedek varsayılan olarak işaretli
    await p.click('#wizNext');
    await p.waitForFunction(() => window.__shared === 1);
    await p.waitForFunction(() => JSON.parse(localStorage.getItem('doviz-kasasi-ui')).backupTx > 3);
    await p.click('button[data-go="islem"]');
    assert.ok(await p.isHidden('#backupBanner'));
    // kapanmış güne işlem: yarının tarihiyle kaydetme önerisi
    await p.click('#quick button:has-text("USD")'); await p.click('label[for="tIn"]'); await p.fill('#fAmount', '5');
    await p.click('#btnSave');
    assert.ok(dialogs.some((d) => d.startsWith('Bugün kapatıldı. Bu işlem yarının tarihiyle (' + fmt(iso(-1)) + ')')), dialogs.join('|'));
    st = await store();
    assert.equal(st.tx[st.tx.length - 1].date, iso(-1));
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('PAKET 1 SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('paket1.js')).slice(0, 2).join(' | ')); process.exit(1); });
