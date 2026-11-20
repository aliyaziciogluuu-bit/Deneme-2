// Döviz Kasası: şifreli yedek (al, yanlış/doğru parolayla yükle), telefon içi otomatik kopyalar ve geri yükleme.
const { chromium } = require('playwright');
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
// Şifreleme yalnızca güvenli bağlamda çalışır: localhost güvenli sayılır (istek diskten karşılanır, sunucu gerekmez)
const URL = 'http://localhost:9876/doviz-kasasi.html';
const iso = (back) => { const d = new Date(Date.now() - back * 864e5);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const SEED = { tx: [
  { id: '1', seq: 1, date: iso(2), type: 'in', cur: 'TRY', amount: 10000, rate: 1, note: 'Açılış' },
  { id: '2', seq: 2, date: iso(1), type: 'in', cur: 'USD', amount: 100, rate: 50, note: 'Gizli müşteri' }],
  myRates: { USD: { buy: 50, sell: 51 } }, rates: { USD: 50 }, ratesUpdated: new Date().toISOString() };

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const ctx = await b.newContext({ viewport: { width: 420, height: 860 } });
  await ctx.route(/truncgil|er-api|frankfurter|gold-api/, (r) => r.abort());
  await ctx.route('http://localhost:9876/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
  const p = await ctx.newPage();
  const dialogs = [];
  p.on('pageerror', (e) => errors.push(e.message));
  p.on('dialog', (d) => { dialogs.push(d.message()); d.accept(); });
  await p.addInitScript((seed) => {
    if (!sessionStorage.getItem('seeded')) { localStorage.setItem('doviz-kasasi-v1', JSON.stringify(seed)); sessionStorage.setItem('seeded', '1'); }
    navigator.canShare = () => true;
    navigator.share = (d) => d.files[0].text().then((t) => { window.__file = { name: d.files[0].name, text: t }; });
  }, SEED);
  await p.goto(URL);
  const txt = async (sel) => (await p.textContent(sel)).replace(/\s+/g, ' ').trim();
  const store = () => p.evaluate(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')));
  assert.ok(await p.evaluate(() => window.isSecureContext && !!crypto.subtle));

  // ================= Şifreli yedek =================
  await p.click('button[data-go="gun"]'); await p.click('button[data-go="liste"]');
  await p.click('#btnBkPass');
  await p.fill('#dlgInput', '123'); await p.click('#dlgForm button[type="submit"]');
  assert.equal(await txt('#dlgMsg'), 'Parola en az 6 karakter olmalı.');
  assert.equal(await p.getAttribute('#dlgInput', 'type'), 'password');
  await p.fill('#dlgInput', 'cilek-2026'); await p.click('#dlgForm button[type="submit"]');
  assert.equal(await txt('#btnBkPass'), 'Yedek parolası ✓');
  assert.ok((await txt('#backupInfo')).startsWith('Yedekler şifreli.'));
  await p.click('#btnExport');
  await p.waitForFunction(() => window.__file, null, { timeout: 20000 });
  const file = await p.evaluate(() => window.__file);
  assert.ok(file.name.startsWith('cilek-doviz-yedek-sifreli-'));
  const env = JSON.parse(file.text);
  assert.equal(env.format, 'doviz-kasasi-sifreli'); assert.equal(env.rounds, 600000);
  assert.ok(!file.text.includes('Gizli müşteri') && !file.text.includes('"tx"'));   // içerik okunamaz
  assert.ok(!file.text.includes('cilek-2026'));                                   // parola dosyada yok
  // parola uygulama verisinde de yok (yalnız tercihlerde)
  assert.ok(!JSON.stringify(await store()).includes('cilek-2026'));

  // Yedeği başka bir "telefona" yükle: önce yanlış, sonra doğru parola
  const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'kasa-')), 'yedek.json');
  fs.writeFileSync(tmp, file.text);
  await p.evaluate(() => { localStorage.clear(); });
  await p.reload();
  { const e = await store(); assert.ok(!e || e.tx.length === 0); }               // yeni telefon: boş
  await p.click('button[data-go="gun"]'); await p.click('button[data-go="liste"]');
  await p.setInputFiles('#fileImport', tmp);
  await p.waitForSelector('#dlg[open]');
  assert.equal(await txt('#dlgTitle'), 'Şifreli yedek');
  await p.fill('#dlgInput', 'yanlis-parola'); await p.click('#dlgForm button[type="submit"]');
  await p.waitForFunction(() => document.getElementById('dlgMsg').textContent.includes('Parola yanlış'), null, { timeout: 20000 });
  await p.fill('#dlgInput', 'cilek-2026'); await p.click('#dlgForm button[type="submit"]');
  await p.waitForFunction(() => (JSON.parse(localStorage.getItem('doviz-kasasi-v1') || '{"tx":[]}')).tx.length === 2, null, { timeout: 20000 });
  assert.equal((await store()).tx[1].note, 'Gizli müşteri');

  // ================= Otomatik kopyalar =================
  // Önceki günlerin kopyalarını taklit et ve bugünkü kopyanın alındığını bekle
  await p.waitForFunction(() => new Promise((ok) => {
    const r = indexedDB.open('doviz-kasasi-kopya', 1);
    r.onsuccess = () => { const q = r.result.transaction('snap').objectStore('snap').getAll(); q.onsuccess = () => ok(q.result.some((x) => x.kind === 'gun')); };
    r.onerror = () => ok(false);
  }), null, { timeout: 10000 });
  await p.evaluate(([d3, data]) => new Promise((ok) => {
    const r = indexedDB.open('doviz-kasasi-kopya', 1);
    r.onsuccess = () => {
      const t = r.result.transaction('snap', 'readwrite'), st = t.objectStore('snap');
      for (let i = 1; i <= 9; i++) {
        const d = new Date(Date.now() - i * 864e5), key = d.toISOString().slice(0, 10);
        st.put({ d: key, kind: 'gun', at: d.toISOString(), n: 1, data: i === 3 ? data : JSON.stringify({ tx: [] }) });
      }
      t.oncomplete = () => ok();
    };
  }), [iso(3), JSON.stringify({ tx: [{ id: 'X', seq: 1, date: iso(3), type: 'in', cur: 'TRY', amount: 777, rate: 1, note: 'eski gün' }] })]);
  // yeni bir işlem kopyaları budar: en fazla 7 günlük kopya kalır
  await p.click('button[data-go="islem"]');
  await p.click('#quick button:has-text("TL")'); await p.fill('#fAmount', '5'); await p.click('#btnSave');
  await p.waitForTimeout(2500);
  await p.click('button[data-go="gun"]'); await p.click('button[data-go="liste"]');
  await p.click('#btnSnaps');
  await p.waitForFunction(() => document.querySelectorAll('#snapList li').length > 0);
  const items = await p.locator('#snapList li').allTextContents();
  assert.ok(items.filter((t) => t.includes('günü')).length <= 7, items.join(' | '));
  assert.ok(items.some((t) => t.includes('Yedek yükleme öncesi')), items.join(' | '));   // yükleme öncesi durum saklandı
  // 3 gün önceki kopyayı geri yükle, sonra geri al
  const day3 = iso(3).slice(8) + '.' + iso(3).slice(5, 7) + '.' + iso(3).slice(0, 4) + ' günü';
  await p.locator('#snapList li', { hasText: day3 }).getByRole('button', { name: 'Geri yükle' }).click();
  await p.waitForFunction(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')).tx.length === 1);
  assert.equal((await store()).tx[0].note, 'eski gün');
  assert.equal(await txt('#toastMsg'), 'Kopya geri yüklendi.');
  await p.click('#toastUndo');
  await p.waitForFunction(() => JSON.parse(localStorage.getItem('doviz-kasasi-v1')).tx.length === 3);

  // Şifrelemeyi kapat: yedek yine açık metin
  await p.click('#btnBkPass'); await p.fill('#dlgInput', ''); await p.click('#dlgForm button[type="submit"]');
  assert.equal(await txt('#btnBkPass'), 'Yedek parolası');
  await p.evaluate(() => { window.__file = null; });
  await p.click('#btnExport');
  await p.waitForFunction(() => window.__file);
  assert.ok((await p.evaluate(() => window.__file.text)).includes('"tx"'));
  await b.close();
  assert.deepEqual(errors, []);
  console.log('YEDEK SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('yedek.js')).slice(0, 2).join(' | ')); process.exit(1); });
