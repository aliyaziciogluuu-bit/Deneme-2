// Döviz Kasası: satış iadesi (kâr geri alınır, mal maliyetiyle stoğa döner, para geri ödenir).
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = {
  tx: [
    { id: '1', seq: 1, date: iso(3), type: 'in', cur: 'TRY', amount: 100000, rate: 1, note: 'Açılış' },
    { id: '2', seq: 2, date: iso(3), type: 'in', cur: 'USD', amount: 1000, rate: 50, note: '' },
    { id: '3', seq: 3, date: iso(2), type: 'in', cur: 'USD', amount: 1000, rate: 52, note: '' },          // ortalama 51
    { id: 'S', seq: 4, date: iso(1), type: 'out', cur: 'USD', amount: 100, rate: 53, note: 'Ahmet Bey' },   // kâr 200
    { id: '5', seq: 5, date: iso(0), type: 'in', cur: 'USD', amount: 100, rate: 60, note: '' },           // iade sonrası maliyeti değiştirir
  ],
  rates: { USD: 53 }, sell: { USD: 53.2 }, myRates: { USD: { buy: 52.8, sell: 53.4 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
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
    await p.addInitScript((seed) => { if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed)); }, SEED);
    await p.goto(URL);
    const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    const sale = () => p.locator('#txBody tr', { hasText: 'Ahmet Bey' }).first();
    const openRow = async (row) => { if (name === 'telefon') await row.locator('td').nth(2).click(); };

    await p.click('button[data-go="gun"]'); await p.click('#dayPrev');
    assert.equal(await txt('#dProfit'), '+₺200,00');                                   // dünkü satışın kârı
    await p.click('button[data-go="liste"]');
    // alışlarda iade düğmesi yok
    const buyRow = p.locator('#txBody tr', { hasText: '+3.000' });
    assert.equal(await p.locator('#txBody tr', { hasText: '60,0000' }).getByRole('button', { name: 'İade' }).count(), 0);
    await openRow(sale());
    await sale().getByRole('button', { name: 'İade' }).click();
    assert.ok((await txt('#dlgText')).includes('53,0000 kurundan geri ödenir') && (await txt('#dlgText')).includes('En fazla 100,00'));
    assert.equal(await p.inputValue('#dlgInput'), '100');                             // varsayılan: tamamı
    await p.fill('#dlgInput', '150'); await p.click('#dlgForm button[type="submit"]');
    assert.equal(await txt('#dlgMsg'), 'En fazla 100,00 iade edilebilir.');
    await p.fill('#dlgInput', '40'); await p.click('#dlgForm button[type="submit"]');
    assert.equal(await txt('#toastMsg'), 'İade kaydedildi · müşteriye ₺2.120,00 ödenecek.');   // 40 × 53
    let st = await store();
    let r = st.tx[st.tx.length - 1];
    assert.deepEqual([r.type, r.cur, r.amount, r.rate, r.ret, r.date], ['in', 'USD', 40, 53, 'S', iso(0)]);
    assert.ok(Math.abs(r.basis - 51) < 1e-9, 'birim maliyet ' + r.basis);              // satıştaki ortalama maliyet
    // Rapor: bugünün kârı −80 (40 × 2), dünkü kâr değişmez
    await p.click('button[data-go="gun"]'); await p.click('#dayToday');
    assert.equal(await txt('#dProfit'), '−₺80,00');
    await p.click('#dayPrev');
    assert.equal(await txt('#dProfit'), '+₺200,00');
    // Kasa: TL 100.000 − 50.000 − 52.000 + 5.300 − 6.000 − 2.120 = −4.820 ; USD 2.000 − 100 + 100 + 40 = 2.040
    await p.click('button[data-go="kasa"]');
    assert.equal(await txt('#sTL'), '−₺4.820,00');
    assert.ok((await txt('#balBody')).includes('2.040,00'));
    // Analiz: dolar kârı 200 − 80 = 120
    await p.click('button[data-go="gun"]'); await p.click('#modeAn'); await p.selectOption('#anRange', 'all');
    assert.equal(await txt('#dProfit'), '+₺120,00');
    assert.ok((await txt('#anBody')).includes('+₺120,00'));
    await p.click('#modeDay');
    // Kısmi iadeden sonra kalan 60; ikinci iadede varsayılan 60
    await p.click('button[data-go="liste"]');
    await openRow(sale());
    await sale().getByRole('button', { name: 'İade' }).click();
    assert.equal(await p.inputValue('#dlgInput'), '60');
    assert.ok((await txt('#dlgText')).includes('Daha önce iade edilen: 40,00'));
    await p.click('#dlgForm button[type="submit"]');
    assert.equal(await txt('#toastMsg'), 'İade kaydedildi · müşteriye ₺3.180,00 ödenecek.');
    await openRow(sale());
    await sale().getByRole('button', { name: 'İade' }).click();
    assert.ok(dialogs.some((d) => d.includes('tamamı zaten iade edildi')));
    // İadesi olan satış silinemez / düzenlenemez
    await sale().getByRole('button', { name: 'Sil' }).click();
    assert.ok(dialogs.some((d) => d.includes('Önce iade kaydını silin')));
    await sale().getByRole('button', { name: 'Düzenle' }).click();
    assert.ok(dialogs.some((d) => d.includes('düzenlemek için önce iade kaydını silin')));
    // İade satırı: "İade" etiketi, yalnızca Sil; silince kâr geri gelir
    const retRow = p.locator('#txBody tr', { hasText: 'İade ·' }).first();
    assert.ok((await txt('#txBody')).includes('İade'));
    await openRow(retRow);
    assert.equal(await retRow.getByRole('button', { name: 'Düzenle' }).count(), 0);
    await retRow.getByRole('button', { name: 'Sil' }).click();
    await p.click('button[data-go="gun"]'); await p.click('#dayToday');
    assert.equal(await txt('#dProfit'), '−₺80,00');                                   // 60'lık iade silindi, 40'lık kaldı
    // Kalıcılık ve yedekten yükleme
    await p.reload();
    st = await store();
    assert.equal(st.tx.filter((t) => t.ret === 'S').length, 1);
    await ctx.close();
  }
  await b.close();
  assert.deepEqual(errors, []);
  console.log('İADE SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('iade.js')).slice(0, 2).join(' | ')); process.exit(1); });
