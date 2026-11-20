// Hecemece (hecemece/index.html): günlük hece bulmacası. Bulmacanın herkese aynı gelmesi, doğru/yanlış/ipucu/cevap akışı,
// sonuç ve paylaşım metni, karne ve seri, yarım oyunun saklanması, alıştırma, dar ekranda taşma.
const { chromium } = require('playwright');
const assert = require('assert');
const ROOT = require('path').resolve(__dirname, '..');
const URL = 'https://oyun.test/hecemece/index.html';

(async () => {
  const b = await chromium.launch();
  const errors = [];
  const open = async (name, opts = {}, zaman) => {
    const ctx = await b.newContext({ viewport: { width: 390, height: 780 }, ...opts });
    await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
    await ctx.route('https://oyun.test/**', (r) => r.fulfill({ path: ROOT + new globalThis.URL(r.request().url()).pathname }));
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write']);
    const p = await ctx.newPage();
    if (zaman) await p.clock.install({ time: new Date(zaman) });
    p.on('pageerror', (e) => errors.push(name + ': ' + e.message));
    await p.goto(URL);
    return { ctx, p };
  };
  const durum = (p) => p.evaluate(() => JSON.parse(JSON.stringify(window.Hecemece.durum())));
  // Etkin kelimeyi (ya da verilen heceleri) fişlere dokunarak kurar.
  const kur = async (p, heceler) => {
    for (const h of heceler) {
      const buyuk = h.replace(/i/g, 'İ').replace(/ı/g, 'I').toUpperCase();
      await p.locator('#fisler .fis[aria-pressed="false"]', { hasText: new RegExp('^' + buyuk + '$') }).first().click();
    }
    await p.waitForTimeout(520);
  };

  // 1) İlk açılış: nasıl oynanır penceresi, altı satır, fiş sayısı hecelerin toplamı
  const { ctx, p } = await open('telefon', {}, '2026-11-20T10:00:00');
  assert(await p.locator('#dlgNasil').evaluate((d) => d.open), 'ilk açılışta nasıl oynanır penceresi açılmalı');
  await p.click('#dlgNasil [data-kapat]');
  let s = await durum(p);
  assert.strictEqual(s.gun, 1);
  assert.strictEqual(await p.textContent('#gunEtiket'), '#1 · 20 Kasım');
  assert.strictEqual(await p.locator('#sorular .soru').count(), 6);
  const toplamHece = s.kelimeler.reduce((a, k) => a + k.h.length, 0);
  assert.strictEqual(await p.locator('#fisler .fis').count(), toplamHece);
  assert(s.kelimeler[5].gizli && !s.kelimeler.slice(0, 5).some((k) => k.gizli), 'gizli kelime sonda olmalı');
  assert((await p.textContent('#sorular li:nth-child(6)')).includes('Gizli kelime'), 'gizli kelimenin ipucu görünmemeli');
  assert(!(await p.textContent('#sorular li:nth-child(6)')).includes(s.kelimeler[5].c));
  assert.strictEqual(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, 'yatay taşma olmamalı');

  // 2) Doğru kurulan kelime: satırda hecelenmiş cevap ve işaret, fişler azalır
  await kur(p, s.kelimeler[0].h);
  s = await durum(p);
  assert(s.kelimeler[0].cozuldu && s.kelimeler[0].hata === 0);
  assert.strictEqual(await p.textContent('#sorular li:nth-child(1) .cevap'), s.kelimeler[0].h.join('-') + '✓');
  assert.strictEqual(await p.locator('#fisler .fis').count(), toplamHece - s.kelimeler[0].h.length);
  assert.strictEqual(s.aktif, 1, 'sıradaki kelimeye geçmeli');
  assert(s.basladi, 'ilk dokunuşta süre başlamalı');

  // 3) Yanlış deneme hata sayılır, yuvalar boşalır; sonra doğrusu
  const yanlis = s.kelimeler[1].h.slice().reverse();
  const tersAyni = yanlis.join('|') === s.kelimeler[1].h.join('|');
  if (!tersAyni) {
    await kur(p, yanlis);
    s = await durum(p);
    assert.strictEqual(s.kelimeler[1].hata, 1);
    assert.strictEqual(s.yuvalar.length, 0);
    assert(!s.kelimeler[1].cozuldu);
  }
  await kur(p, s.kelimeler[1].h);
  s = await durum(p);
  assert(s.kelimeler[1].cozuldu);

  // 4) İpucu: ilk hece kilitli gelir, düğme "Cevabı aç" olur; kalan hecelerle çözülür
  await p.click('#btnIpucu');
  s = await durum(p);
  assert.strictEqual(s.kelimeler[2].ipucu, 1);
  assert.strictEqual(s.kilit, 1);
  assert.strictEqual(await p.locator('#yuvalar .fis.kilitli').count(), 1);
  assert.strictEqual(await p.textContent('#btnIpucu'), 'Cevabı aç');
  await p.click('#yuvalar .fis.kilitli', { force: true });
  assert.strictEqual((await durum(p)).yuvalar.length, 1, 'kilitli fiş kaldırılamaz');
  await kur(p, s.kelimeler[2].h.slice(1));
  s = await durum(p);
  assert(s.kelimeler[2].cozuldu && !s.kelimeler[2].acildi);

  // 5) Yarım oyun saklanır: sayfa yenilenince aynı yerden sürer
  await p.reload();
  assert(!(await p.locator('#dlgNasil').evaluate((d) => d.open)), 'pencere ikinci kez açılmamalı');
  s = await durum(p);
  assert.strictEqual(s.kelimeler.filter((k) => k.cozuldu).length, 3);
  assert.strictEqual(await p.locator('#sorular .soru.cozuldu').count(), 3);

  // 6) Cevabı aç: iki kez ipucu
  await p.click('#btnIpucu');
  await p.click('#btnIpucu');
  s = await durum(p);
  assert(s.kelimeler[3].cozuldu && s.kelimeler[3].acildi);
  assert.strictEqual(await p.locator('#sorular li:nth-child(4) .cevap.acildi').count(), 1);

  // 7) Başka satırın kelimesi kurulursa o satır çözülür (hata sayılmaz); Sil ve geri tuşu yuvayı boşaltır
  assert.strictEqual(s.aktif, 4);
  await p.locator('#fisler .fis[aria-pressed="false"]').first().click();
  assert.strictEqual((await durum(p)).yuvalar.length, 1);
  await p.click('#btnSil');
  assert.strictEqual((await durum(p)).yuvalar.length, 0);
  if (s.kelimeler[4].h.length === s.kelimeler[5].h.length) {
    await kur(p, s.kelimeler[5].h);
    s = await durum(p);
    assert(s.kelimeler[5].cozuldu && s.kelimeler[4].hata === 0);
    await kur(p, s.kelimeler[4].h);
  } else {
    await kur(p, s.kelimeler[4].h);
    s = await durum(p);
    assert.strictEqual(s.aktif, 5);
    await kur(p, s.kelimeler[5].h);
  }

  // 8) Sonuç: not, kareler, süre, seri, karne
  s = await durum(p);
  assert(s.bitti && s.sayildi);
  assert(await p.isVisible('#sonuc') && !(await p.isVisible('#oyun')));
  const puan = (k) => (k.acildi ? 0 : k.ipucu ? 1 : k.hata === 0 ? 3 : k.hata === 1 ? 2 : 1);
  const toplam = s.kelimeler.reduce((a, k) => a + puan(k), 0);
  const not = toplam >= 17 ? 'Pekiyi' : toplam >= 13 ? 'İyi' : toplam >= 9 ? 'Orta' : 'Geçer';
  assert.strictEqual(await p.textContent('#damga'), not);
  assert.strictEqual(await p.locator('#kareler i').count(), 6);
  assert.strictEqual(await p.locator('#kareler i.ki').count(), 1, 'ipuçlu kelime mavi');
  assert((await p.textContent('#sonucBilgi')).includes('Seri 1 gün'));
  assert(/^\d\d:\d\d:\d\d$/.test(await p.textContent('#geriSayim')));
  assert((await p.textContent('#sorular li:nth-child(6)')).includes(s.kelimeler[5].c), 'gizli kelimenin ipucu sonunda görünür');

  await p.click('#btnPaylas');
  const metin = await p.evaluate(() => navigator.clipboard.readText());
  const satirlar = metin.split('\n');
  assert.strictEqual(satirlar[0], 'Hecemece #1 · ' + not);
  assert(/^[🟩🟨🟧🟦⬛]{5}\+[🟩🟨🟧🟦⬛]$/u.test(satirlar[1]), 'kareler: ' + satirlar[1]);
  assert(satirlar[1].includes('🟦') && satirlar[1].includes('⬛'));
  assert(satirlar[2].startsWith('⏱ ') && satirlar[2].endsWith('🔥 1'));
  assert.strictEqual(satirlar[3], 'https://oyun.test/hecemece/index.html');

  await p.click('#btnKarne');
  assert.strictEqual(await p.textContent('#kOynanan'), '1');
  assert.strictEqual(await p.textContent('#kSeri'), '1');
  await p.click('#dlgKarne [data-kapat]');

  // 9) Alıştırma: karneyi etkilemez, günün sonucuna dönülür
  await p.click('#btnAlistirma');
  s = await durum(p);
  assert(!s.gunluk && !s.bitti);
  assert.strictEqual(await p.textContent('#gunEtiket'), 'Alıştırma');
  for (let i = 0; i < 6; i++) { s = await durum(p); await kur(p, s.kelimeler[s.aktif].h); }
  s = await durum(p);
  assert(s.bitti);
  assert(!(await p.isVisible('#btnPaylas')) && await p.isVisible('#btnGunluk'));
  assert.strictEqual(await p.evaluate(() => JSON.parse(localStorage.getItem('hecemece-v1')).karne.oynanan), 1);
  await p.click('#btnGunluk');
  s = await durum(p);
  assert(s.gunluk && s.bitti && s.gun === 1);

  // 10) Ertesi gün: yeni bulmaca, seri 2; iki gün atlanırsa seri sıfırlanır
  await p.clock.setFixedTime(new Date('2026-11-21T09:00:00'));
  await p.reload();
  s = await durum(p);
  assert.strictEqual(s.gun, 2);
  assert(!s.bitti);
  const gun1 = (await p.evaluate(() => window.Hecemece.yeniOyun(1, true).kelimeler.map((k) => k.w)));
  assert(!s.kelimeler.some((k) => gun1.includes(k.w)), 'art arda günlerde kelime yinelenmemeli');
  for (let i = 0; i < 6; i++) { s = await durum(p); await kur(p, s.kelimeler[s.aktif].h); }
  assert.strictEqual(await p.textContent('#damga'), 'Pekiyi');
  assert((await p.textContent('#sonucBilgi')).includes('Seri 2 gün'));
  await p.clock.setFixedTime(new Date('2026-11-24T09:00:00'));
  await p.reload();
  await p.click('#btnKarne');
  assert.strictEqual(await p.textContent('#kSeri'), '0');
  assert.strictEqual(await p.textContent('#kEnUzun'), '2');
  assert.strictEqual(await p.textContent('#kPekiyi'), '1');
  await ctx.close();

  // 11) Bulmaca herkese aynı: başka cihazda aynı gün aynı kelimeler ve aynı fiş dizilişi
  const a = await open('cihaz-a', {}, '2026-12-05T08:00:00');
  const c = await open('cihaz-b', { viewport: { width: 360, height: 640 }, colorScheme: 'dark' }, '2026-12-05T23:30:00');
  const sa = await durum(a.p), sc = await durum(c.p);
  assert.strictEqual(sa.gun, 16);
  assert.deepStrictEqual(sa.kelimeler.map((k) => k.w), sc.kelimeler.map((k) => k.w));
  assert.deepStrictEqual(sa.fisler.map((f) => f.h), sc.fisler.map((f) => f.h));
  await c.p.click('#dlgNasil [data-kapat]');
  assert.strictEqual(await c.p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, '360 pikselde taşma olmamalı');

  // 12) Bir tur boyunca hiçbir kelime yinelenmez; her bulmacada fişlerle bütün kelimeler kurulabilir
  const tur = await a.p.evaluate(() => {
    const H = window.Hecemece, n = Math.floor(H.havuz.length / 6), gorulen = new Set();
    let yinelenen = 0, gizliKisa = 0, enCokFis = 0;
    for (let g = 1; g <= n; g++) {
      const o = H.yeniOyun(g, true);
      o.kelimeler.forEach((k) => { if (gorulen.has(k.w)) yinelenen++; gorulen.add(k.w); });
      if (o.kelimeler[5].h.length < 3) gizliKisa++;
      enCokFis = Math.max(enCokFis, o.fisler.length);
      if (o.fisler.map((f) => f.h).sort().join() !== o.kelimeler.flatMap((k) => k.h).sort().join()) throw new Error('fişler tutmuyor: ' + g);
    }
    return { n, yinelenen, gizliKisa, enCokFis, tek: gorulen.size };
  });
  assert.strictEqual(tur.yinelenen, 0);
  assert.strictEqual(tur.tek, tur.n * 6);
  console.log('tur:', JSON.stringify(tur));
  await a.ctx.close(); await c.ctx.close();

  await b.close();
  assert.deepStrictEqual(errors, []);
  console.log('hecemece: tamam');
})().catch((e) => { console.error(e); process.exit(1); });
