// Döviz Kasası: sade görünüm (beş sekme ve alt sekmeler, tek satır başlık, açılır bölümler, dokununca açılan satırlar).
const { chromium, devices } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'http://kasa.test/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = { tx: [
  { id: '1', seq: 1, date: iso(3), type: 'in', cur: 'TRY', amount: 500000, rate: 1, note: 'Açılış' },
  { id: '2', seq: 2, date: iso(2), type: 'in', cur: 'USD', amount: 2000, rate: 50, note: '' },
  { id: '3', seq: 3, date: iso(0), type: 'out', cur: 'USD', amount: 500, rate: 51, note: 'Ahmet Bey' },
  { id: '4', seq: 4, date: iso(0), type: 'out', cur: 'USD', amount: 100, rate: 50, note: '', cari: 'Mehmet Usta' } ],
  rates: { USD: 50.4, HAS: 6021 }, sell: { USD: 50.5, HAS: 6022 }, myRates: { USD: { buy: 50.2, sell: 50.6 } },
  ratesUpdated: new Date().toISOString(), rateSrc: 'tr' };

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (name, opts) => {
    const ctx = await b.newContext(opts);
    await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());
    await ctx.route('http://kasa.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    p.on('dialog', (d) => d.accept());
    await p.addInitScript((seed) => { if (!localStorage.getItem('doviz-kasasi-v1')) localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed)); }, SEED);
    await p.goto(URL);
    return { ctx, p };
  };

  // ===================== Telefon =====================
  let { ctx, p } = await open('telefon', { ...devices['iPhone 13'] });
  // Başlık tek satır: yükseklik küçük, düğmeler simge ama adları duruyor
  const head = await p.locator('header.top').boundingBox();
  assert.ok(head.height < 70, 'başlık yüksekliği ' + head.height);
  assert.ok(await p.isHidden('#btnInstall'));
  assert.equal(await p.getByRole('button', { name: 'Tutarları gizle' }).count(), 1);
  assert.equal(await p.getByRole('button', { name: 'Fiyatları güncelle' }).count(), 1);
  assert.ok((await p.locator('#btnHide').boundingBox()).width <= 44);
  await p.click('#btnHide');
  assert.equal(await p.getAttribute('#btnHide', 'aria-pressed'), 'true');
  assert.equal(await p.getByRole('button', { name: 'Tutarları göster' }).count(), 1);
  await p.click('#btnHide');
  // Alt bilgi yalnızca İşlemler sekmesinde
  assert.ok(await p.isHidden('footer'));
  // --- Cari: form kapalı gelir; düğmeyle ya da kişiye dokununca açılır
  await p.click('button[data-go="cari"]');
  assert.ok(await p.isHidden('#cariForm'));
  assert.deepEqual(await p.locator('#subtabs button').allTextContents(), ['Cari', 'Toptancı']);
  assert.equal((await p.textContent('[data-toggle="cari"]')).trim(), '＋ Hareket ekle');
  await p.click('#persons .person .n');                       // kişiye dokun
  assert.ok(await p.isVisible('#cariForm'));
  assert.equal(await p.inputValue('#cPerson'), 'Mehmet Usta');
  assert.equal((await p.textContent('[data-toggle="cari"]')).trim(), 'Kapat');
  await p.click('[data-toggle="cari"]');
  assert.ok(await p.isHidden('#cariForm'));
  await p.click('button[data-go="toptanci"]');                 // alt sekme
  assert.ok(await p.isHidden('#wForm') && await p.isHidden('#persons'));
  assert.equal(await p.getAttribute('#tabs button[data-go="cari"]', 'aria-current'), 'page');   // ana sekme seçili kalır
  await p.click('[data-toggle="toptanci"]');
  assert.ok(await p.isVisible('#wForm'));
  // --- Kasa: sayım ve ürün formu kapalı; bakiye satırı sade, dokununca ayrıntı
  await p.click('button[data-go="kasa"]');
  assert.deepEqual(await p.locator('#subtabs button').allTextContents(), ['Bakiyeler', 'Kurlarım', 'Vitrin']);
  assert.ok(await p.isHidden('#countGrid') && await p.isHidden('#btnCountApply') && await p.isHidden('#iForm'));
  assert.ok(await p.isVisible('#sTotal') && await p.isHidden('#sTL'));          // telefonda yalnızca toplam kartı
  const usdRow = p.locator('#balBody tr', { hasText: 'USD' });
  assert.ok(await usdRow.locator('td[data-label="Bakiye"]').isVisible() && await usdRow.locator('td[data-label="TL değeri"]').isVisible());
  assert.ok(await usdRow.locator('input.rate').isHidden() && await usdRow.locator('button').first().isHidden());
  await usdRow.locator('td.title').click();
  assert.ok(await usdRow.locator('input.rate').isVisible() && await usdRow.locator('button').first().isVisible());
  // ayrıntı açıkken fiyat değişince (yeniden çizim) açık kalır
  await usdRow.locator('input.rate').fill('50,8'); await usdRow.locator('input.rate').dispatchEvent('change');
  assert.ok(await p.locator('#balBody tr', { hasText: 'USD' }).locator('input.rate').isVisible());
  await p.click('[data-toggle="sayim"]');
  assert.ok(await p.isVisible('#countGrid') && await p.isVisible('#btnCountApply'));
  // --- Vitrin alt sekmesi: ürün formu kapalı
  await p.click('button[data-go="vitrin"]');
  assert.ok(await p.isHidden('#iForm') && await p.isVisible('#iCount') && await p.isHidden('#balBody'));
  // --- Kurlarım: çevirici kapalı
  await p.click('button[data-go="kurlar"]');
  assert.ok(await p.isHidden('#cvAmount'));
  await p.click('[data-toggle="cevirici"]');
  assert.ok(await p.isVisible('#cvAmount'));
  // --- Rapor → İşlemler: satır sade; dokununca Düzenle / Sil çıkar
  await p.click('button[data-go="gun"]');
  assert.deepEqual(await p.locator('#subtabs button').allTextContents(), ['Rapor', 'İşlemler']);
  await p.click('button[data-go="liste"]');
  assert.ok(await p.isVisible('footer'));
  const row = p.locator('#txBody tr', { hasText: 'Ahmet Bey' });
  assert.ok(await row.locator('button').first().isHidden());
  const rowH = (await row.boundingBox()).height;
  assert.ok(rowH < 110, 'işlem satırı yüksekliği ' + rowH);
  await row.locator('td').nth(2).click();
  assert.ok(await row.getByRole('button', { name: 'Düzenle' }).isVisible() && await row.getByRole('button', { name: 'Sil' }).isVisible());
  await row.getByRole('button', { name: 'Düzenle' }).click();   // düzenleme formu açılır; tarih ve açıklama görünür
  assert.equal(await p.textContent('#formTitle'), 'İşlemi düzenle');
  assert.ok(await p.isVisible('#fDate') && await p.isVisible('#fNote'));
  assert.ok(await p.isHidden('#subtabs'));                      // ana sayfada alt sekme yok
  await p.click('#btnCancel');
  // --- Hesap: ziynet açılır listeden seçilir; boş liste kartı görünmez
  await p.click('button[data-go="hesap"]');
  assert.ok(await p.isHidden('#kListCard'));
  await p.selectOption('#kCoin', 'TAM');
  assert.equal((await p.textContent('#kGramLbl')).trim(), 'Adet');
  await p.click('#kKarats button[data-k="14"]');
  assert.equal(await p.inputValue('#kCoin'), '');
  await p.fill('#kGram', '5'); await p.click('#kAdd');
  assert.ok(await p.isVisible('#kListCard'));
  // --- Açık / kapalı durumu hatırlanır
  await p.reload();
  assert.ok(await p.isHidden('#fDate'));                        // yeni işlemde ek alanlar kapalı gelir
  await p.click('[data-toggle="txmore"]');
  assert.ok(await p.isVisible('#fDate') && await p.isVisible('#fCur'));
  await p.click('button[data-go="kasa"]');
  assert.ok(await p.isVisible('#countGrid'));
  await p.click('button[data-go="cari"]');
  assert.ok(await p.isHidden('#cariForm'));
  await p.click('button[data-go="toptanci"]');
  assert.ok(await p.isVisible('#wForm'));
  // --- Sayfalar kısa: telefonda en uzun sekme iki buçuk ekranı geçmez
  assert.equal(await p.locator('#tabs button').count(), 5);
  for (const path of [['islem'], ['hesap'], ['kasa'], ['kasa', 'kurlar'], ['kasa', 'vitrin'], ['cari'], ['cari', 'toptanci'], ['gun'], ['gun', 'liste']]) {
    for (const t of path) await p.click('button[data-go="' + t + '"]');
    const h = await p.evaluate(() => document.documentElement.scrollHeight);
    assert.ok(h < 1900, path.join(' → ') + ' çok uzun: ' + h);
  }
  await ctx.close();

  // ===================== Masaüstü =====================
  ({ ctx, p } = await open('masaustu', { viewport: { width: 1200, height: 900 } }));
  assert.ok((await p.textContent('#btnRates')).includes('Fiyatları güncelle'));      // yazı görünür
  assert.ok((await p.locator('#btnRates').boundingBox()).width > 120);
  await p.click('button[data-go="kasa"]');
  assert.ok(await p.locator('#balBody tr', { hasText: 'USD' }).locator('input.rate').isVisible());   // tabloda her şey açık
  assert.ok(await p.isVisible('#sTL'));                                              // masaüstünde dört özet kutusu
  await p.click('button[data-go="gun"]'); await p.click('button[data-go="liste"]');
  assert.ok(await p.locator('#txBody tr', { hasText: 'Ahmet Bey' }).getByRole('button', { name: 'Düzenle' }).isVisible());
  await ctx.close();

  await b.close();
  assert.deepEqual(errors, []);
  console.log('SADE GÖRÜNÜM SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('sade-gorunum.js')).slice(0, 2).join(' | ')); process.exit(1); });
