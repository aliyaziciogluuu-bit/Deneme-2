// Döviz Kasası "Hesap" bölümünün tarayıcı sınaması (dosyadan açar; ağ gerekmez).
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const OUT = require('fs').mkdtempSync(require('path').join(require('os').tmpdir(), 'kasa-'));   // ekran görüntüleri
// Dosya, sahte bir http adresinden sunulur: file:// adresinde tarayıcı deposu yeniden yüklemede güvenilir değil.
const URL = 'http://kasa.test/doviz-kasasi.html';
const SEED = {
  tx: [
    { id: 'a', seq: 1, date: '2026-11-01', type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
    { id: 'b', seq: 2, date: '2026-11-02', type: 'in', cur: 'B22', amount: 100, rate: 2700, note: 'Stok' },
    { id: 'c', seq: 3, date: '2026-11-02', type: 'in', cur: 'CEYREK', amount: 10, rate: 9800, note: 'Stok' },
  ],
  rates: { GA: 3000, HAS: 2990, USD: 40, CEYREK: 9900 }, sell: { GA: 3010, HAS: 3000, CEYREK: 10000 },
  myRates: { HAS: { buy: 2950, sell: 3050 }, USD: { buy: 39.9, sell: 40.2 }, CEYREK: { buy: 9850, sell: 10100 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr',
};

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (name, opts, seed, ui) => {
    const ctx = await b.newContext(opts);
    await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());   // fiyat servislerine gitmesin
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    const dialogs = [];
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => { dialogs.push(d.message()); d.accept(); });
    await p.addInitScript(([seed, ui]) => {
      if (seed && !localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed));
      if (ui && !localStorage.getItem('doviz-kasasi-ui')) localStorage.setItem('doviz-kasasi-ui', JSON.stringify(ui));
    }, [seed, ui]);
    await p.goto(URL);
    await p.click('button[data-go="hesap"]');
    const txt = async (id) => (await p.textContent('#' + id)).replace(/\s+/g, ' ').trim();
    const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
    return { ctx, p, txt, store, dialogs };
  };

  const run = async (name, opts, shots) => {
    const { ctx, p, txt, store, dialogs } = await open(name, opts, SEED);
    // --- Has altın fiyatım kartı
    assert.equal(await p.inputValue('#hasBuy'), '2950');
    assert.equal(await p.inputValue('#hasSell'), '3050');
    assert.ok((await txt('hasInfo')).includes('Piyasa 2.990,00 / 3.000,00'), await txt('hasInfo'));
    // --- Satış: 22 ayar 10 gr, has satış 3050, milyem 916, işçilik 100 ₺/gr
    assert.equal(await p.inputValue('#kHas'), '3050');
    assert.equal(await p.inputValue('#kMil'), '916');
    await p.fill('#kGram', '10');
    await p.fill('#kLabor', '100');
    let out = await txt('kOut');
    assert.ok(out.includes('₺27.938,00') && out.includes('₺1.000,00'), out);     // 10 × 0,916 × 3050
    assert.ok(out.includes('Müşteriden alınacak: ₺28.938,00'), out);
    await p.click('#kAdd');
    // işçilik milyem ve toplam olarak
    await p.fill('#kGram', '10'); await p.selectOption('#kUnit', 'mil'); await p.fill('#kLabor', '30');
    out = await txt('kOut'); assert.ok(out.includes('₺915,00') && out.includes('₺28.853,00'), out);
    await p.selectOption('#kUnit', 'total'); await p.fill('#kLabor', '2500');
    assert.ok((await txt('kOut')).includes('₺30.438,00'));
    await p.selectOption('#kUnit', 'gr'); await p.fill('#kLabor', '100'); await p.dispatchEvent('#kLabor', 'change');
    // has fiyatını karttan değiştirince hesap da değişir ve kur tablosuna yazılır
    await p.fill('#hasSell', '3100'); await p.dispatchEvent('#hasSell', 'change');
    assert.equal(await p.inputValue('#kHas'), '3100');
    assert.deepEqual((await store()).myRates.HAS, { buy: 2950, sell: 3100 });
    assert.ok((await txt('hasInfo')).includes('son güncellemeniz: bugün'));
    await p.fill('#hasSell', '3050'); await p.dispatchEvent('#hasSell', 'change');
    // --- Bozdurma: 14 ayar 5 gr, 0,5 gr taş, alış milyemi 575, has alış 2950
    await p.click('label[for="kBuy"]');
    await p.click('#kKarats button[data-k="14"]');
    assert.equal(await p.inputValue('#kHas'), '2950');
    assert.equal(await p.inputValue('#kMil'), '585');
    assert.ok(await p.isHidden('#kLaborF') && await p.isVisible('#kDeductF') && await p.isHidden('#kOldF'));
    await p.fill('#kMil', '575'); await p.dispatchEvent('#kMil', 'change');
    await p.fill('#kGram', '5'); await p.fill('#kDeduct', '0,5');
    out = await txt('kOut');
    assert.ok(out.includes('Net ağırlık: 4,5 gr') && /Has karşılığı: 2,58[78] gr/.test(out), out);
    assert.ok(out.includes('Müşteriye ödenecek: ₺7.633,13'), out);              // 4,5 × 0,575 × 2950
    await p.click('#kAdd');
    // --- Ziynet: 3 çeyrek satış, kendi satış kuru 10100, eski tarih indirimi 50
    await p.click('label[for="kSell"]');
    await p.selectOption('#kCoin', 'CEYREK');
    assert.ok(await p.isHidden('#kMilF') && await p.isHidden('#kLaborF') && await p.isVisible('#kOldF'));
    assert.equal(await txt('kGramLbl'), 'Adet');
    assert.equal(await p.inputValue('#kHas'), '10100');
    await p.fill('#kGram', '3');
    assert.ok((await txt('kOut')).includes('Müşteriden alınacak: ₺30.300,00'));
    await p.fill('#kOld', '50'); await p.dispatchEvent('#kOld', 'change');
    assert.ok((await txt('kOut')).includes('Müşteriden alınacak: ₺30.150,00'));
    await p.fill('#kGram', '2,5');
    assert.ok((await txt('kOut')).includes('Adedi tam sayı olarak yazın'));
    await p.fill('#kGram', '3');
    await p.click('#kAdd');
    await p.click('label[for="kBuy"]');                                         // bozdurmada alış kuru gelir
    assert.equal(await p.inputValue('#kHas'), '9850');
    assert.equal(await p.inputValue('#kOld'), '50');                            // indirim hatırlanır
    // --- Liste ve net
    assert.equal(await p.locator('#kList li').count(), 3);
    assert.equal(await txt('kSumSell'), '₺59.088,00');                           // 28.938 + 30.150
    assert.equal(await txt('kSumBuy'), '₺7.633,13');
    assert.equal(await txt('kNetLbl'), 'Müşteriden alınacak');
    assert.equal(await txt('kNet'), '₺51.454,87');
    await p.screenshot({ path: shots + '-liste.png', fullPage: true });
    // --- Fiş
    await p.click('#kReceipt');
    assert.ok(await p.isVisible('#receipt'));
    assert.equal(await p.locator('#rcBody tr').count(), 3);
    assert.ok((await txt('rcTotals')).includes('Müşteriden alınacak₺51.454,87'), await txt('rcTotals'));
    await p.fill('#rcName', 'Ayşe Hanım');
    assert.equal(await txt('rcCust'), 'Müşteri: Ayşe Hanım');
    await p.screenshot({ path: shots + '-fis.png' });
    await p.click('#rcClose');
    assert.ok(await p.isHidden('#receipt'));
    // --- Kasaya işle: 3 işlem yazılır, stok ve TL kasası değişir
    const before = await store();
    await p.click('#kPost');
    assert.ok(dialogs.some((d) => d.includes('3 satır kasaya işlenecek')), dialogs.join('|'));
    let st = await store();
    assert.equal(st.tx.length, before.tx.length + 3);
    const added = st.tx.slice(-3);
    assert.deepEqual(added.map((t) => [t.type, t.cur, t.amount]), [['out', 'B22', 10], ['in', 'A14', 4.5], ['out', 'CEYREK', 3]]);
    assert.ok(Math.abs(added[0].amount * added[0].rate - 28938) < 1e-6 && Math.abs(added[1].amount * added[1].rate - 7633.13) < 1e-6);
    assert.ok(await p.isDisabled('#kPost'));
    assert.ok((await txt('kList')).includes('kasaya işlendi'));
    await p.click('button[data-go="kasa"]');
    // TL: 500.000 − 270.000 − 98.000 + 28.938 − 7.633,13 + 30.150 = 183.454,87
    assert.equal(await txt('sTL'), '₺183.454,87');
    await p.click('button[data-go="gun"]');
    // Kâr: bilezik 10 × (2893,8 − 2700) = 1.938 + çeyrek 3 × (10.050 − 9.800) = 750
    assert.equal(await txt('dProfit'), '+₺2.688,00');
    // --- Geri al: işlemler silinir, satırlar yeniden işlenebilir olur
    await p.click('#toastUndo');
    st = await store();
    assert.equal(st.tx.length, before.tx.length);
    await p.click('button[data-go="hesap"]');
    assert.ok(!(await txt('kList')).includes('kasaya işlendi'));
    assert.ok(await p.isEnabled('#kPost'));
    // --- Kasada olmayan ürün satılamaz; hiçbir şey yazılmaz
    await p.click('label[for="kSell"]'); await p.click('#kKarats button[data-k="18"]');
    await p.fill('#kGram', '5'); await p.click('#kAdd');
    await p.click('#kPost');
    assert.ok(dialogs.some((d) => d.includes('Kasaya işlenemedi') && d.includes('18 Ayar Altın')), dialogs.join('|'));
    assert.equal((await store()).tx.length, before.tx.length);
    await p.click('#kList li:last-child .x');
    // --- Hatalar ve esnek giriş
    await p.click('label[for="kBuy"]'); await p.click('#kKarats button[data-k="14"]');
    await p.fill('#kGram', '5'); await p.fill('#kDeduct', '6');
    assert.ok((await txt('kOut')).includes('Düşülecek ağırlık, toplam ağırlıktan küçük olmalı'));
    await p.fill('#kDeduct', ''); await p.fill('#kMil', '0,575');
    assert.ok((await txt('kOut')).includes('₺8.481,25'));                        // 5 × 0,575 × 2950
    await p.fill('#kHas', '3000');
    assert.ok((await txt('kSrc')).includes('elle girildi') && (await txt('kOut')).includes('₺8.625,00'));
    // --- Kalıcılık
    await p.reload();
    await p.click('button[data-go="hesap"]');
    assert.equal(await p.locator('#kList li').count(), 3);
    assert.equal(await p.inputValue('#kLabor'), '100');
    await p.click('label[for="kBuy"]'); await p.click('#kKarats button[data-k="14"]');
    assert.equal(await p.inputValue('#kMil'), '575');
    await p.click('label[for="kSell"]');
    assert.equal(await p.inputValue('#kMil'), '585');
    st = await store();
    assert.equal(st.calc.mil.buy['14'], 575);
    assert.deepEqual(st.calc.labor['22'], { v: 100, unit: 'gr' });
    assert.equal(st.calc.old.CEYREK, 50);
    // --- Listeyi temizle; diğer bölümler çalışıyor; yeni varlıklar işlem formunda var
    await p.click('#kListClear');
    assert.equal(await p.locator('#kList li').count(), 0);
    assert.ok(await p.isHidden('#kListCard'));                                  // boş liste yer kaplamaz
    await p.click('button[data-go="islem"]');
    assert.ok((await p.locator('#fCur option').allTextContents()).some((t) => t.includes('14 Ayar Altın')));
    await p.selectOption('#fCur', 'USD');
    await p.fill('#fAmount', '100'); await p.fill('#fRate', '40');
    await p.click('#btnSave');
    assert.equal((await store()).tx.length, before.tx.length + 1);
    await ctx.close();
  };
  await run('telefon', { ...devices['iPhone 13'] }, OUT + '/tel');
  await run('masaustu', { viewport: { width: 1200, height: 900 } }, OUT + '/pc');

  // Boş kurulum: fiyat yoksa uyarır. Eski sürümden kalan liste satırları sorun çıkarmaz.
  const e = await open('bos', { viewport: { width: 420, height: 800 } }, null,
    { calcList: [{ mode: 'sell', karat: 22, gram: 10, total: 100, note: 'eski' }, 'bozuk'] });
  assert.equal(await e.p.locator('#kList li').count(), 0);
  assert.equal(await e.p.inputValue('#kHas'), '');
  assert.ok((await e.txt('kSrc')).includes('Fiyat yok'));
  await e.p.fill('#kGram', '3');
  assert.ok((await e.txt('kOut')).includes('Has altın fiyatını yazın'));
  await e.p.click('#hasMarket');
  assert.ok(e.dialogs.some((d) => d.includes('Piyasa fiyatı yok')));
  await e.ctx.close();

  await b.close();
  assert.deepEqual(errors, []);
  console.log('TÜM SINAMALAR GEÇTİ');
})().catch((e) => { console.error("HATA", e.message, (e.stack||"").split("\n").filter(l=>l.includes("t.js")).slice(0,2).join(" | ")); process.exit(1); });
