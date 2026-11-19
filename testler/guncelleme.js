// Döviz Kasası: yeni sürümün telefona ulaşması (önbellek ve "yeni sürüm hazır" uyarısı).
// GitHub Pages gibi "max-age=600" başlığıyla yanıt veren küçük bir yerel sunucu kullanır.
const { chromium } = require('playwright');
const assert = require('assert');
const http = require('http');
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.webmanifest': 'application/manifest+json',
  '.svg': 'image/svg+xml', '.png': 'image/png' };

(async () => {
  let version = null;            // null: dosyadaki sürüm; değilse sunucunun verdiği sürüm
  let splitFetch = null;         // doluysa: sayfa açılışına eski, sayfanın kendi denetimine bu sürüm verilir
  let down = false;
  const server = http.createServer((req, res) => {
    if (down) return req.socket.destroy();
    const file = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
    let body = fs.readFileSync(file);
    if (file.endsWith('doviz-kasasi.html')) {
      // Sayfanın kendi sürüm denetimi önbelleği tümüyle atlar ('no-store' → Pragma: no-cache)
      const v = splitFetch && req.headers.pragma === 'no-cache' ? splitFetch : version;
      if (v) body = Buffer.from(body.toString('utf8').replace(/(<meta name="surum" content=")[^"]+/, '$1' + v));
    }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'max-age=600' });
    res.end(body);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const URL = 'http://localhost:' + server.address().port + '/doviz-kasasi.html';

  // İstek yakalama (route) tarayıcı önbelleğini kapatır; burada önbellek açık kalmalı. Fiyat servislerine
  // gidilmesin diye yerel sunucu dışındaki bütün adresler çözümlenemez yapılır.
  const b = await chromium.launch({ args: ['--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost'] });
  const ctx = await b.newContext({ viewport: { width: 420, height: 800 } });
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', (e) => errors.push(e.message));
  const build = () => p.evaluate(() => document.querySelector('meta[name="surum"]').content);

  // 1) İlk açılış: uyarı yok; çevrimdışı önbellek kurulur
  await p.goto(URL);
  const first = await build();
  assert.ok(first, 'sürüm etiketi yok');
  await p.evaluate(() => navigator.serviceWorker.ready);
  await p.reload();                                             // sayfa artık önbellek katmanının denetiminde
  await p.waitForFunction(() => !!navigator.serviceWorker.controller);
  assert.ok(await p.isHidden('#updBanner'));
  await p.evaluate(() => localStorage.setItem('doviz-kasasi-v1', JSON.stringify({ tx: [{ id: 'a', seq: 1, date: '2026-11-01', type: 'in', cur: 'TRY', amount: 1234, rate: 1, note: '' }] })));

  // 2) Sunucuda yeni sürüm var, uygulama açık: uyarı çıkar
  splitFetch = 'YENI-1';
  await p.reload();
  assert.equal(await build(), first);                           // açık sayfa hâlâ eski
  await p.waitForSelector('#updBanner:not([hidden])');
  assert.ok((await p.textContent('#updBanner')).includes('yeni sürümü hazır'));

  // 3) "Yenile": tarayıcının 10 dakikalık önbelleğine rağmen yeni sürüm gelir; kayıtlar durur
  splitFetch = null; version = 'YENI-1';
  await Promise.all([p.waitForNavigation(), p.click('#btnUpdate')]);
  assert.equal(await build(), 'YENI-1');
  assert.ok(await p.isHidden('#updBanner'));
  assert.ok((await p.textContent('#mTL')).includes('1.234'));

  // 4) Uygulamayı kapatıp yeniden açmak (olağan açılış) da en yeni sürümü getirir; tarayıcının 10 dakikalık
  //    önbelleği bunu geciktirmez
  version = 'YENI-2';
  await p.goto('about:blank');
  await p.goto(URL);
  assert.equal(await build(), 'YENI-2');

  // 5) İnternet yokken uygulama önbellekten açılır
  down = true;
  await p.reload();
  assert.equal(await build(), 'YENI-2');
  assert.ok((await p.textContent('#mTL')).includes('1.234'));
  assert.ok(await p.isHidden('#updBanner'));

  await b.close();
  server.close();
  assert.deepEqual(errors, []);
  console.log('GÜNCELLEME SINAMALARI GEÇTİ');
})().catch((e) => { console.error('HATA', e.message, (e.stack || '').split('\n').filter((l) => l.includes('guncelleme.js')).slice(0, 2).join(' | ')); process.exit(1); });
