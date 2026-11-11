const { chromium } = require('playwright'); const fs = require('fs');
const file = process.argv[2], out = process.argv[3];
const html = fs.readFileSync(file, 'utf8'); const PAL = {}; for (const m of html.match(/const PAL = \{([\s\S]*?)\};/)[1].matchAll(/(\w): '(#[0-9a-f]{6})'/g)) PAL[m[1]] = m[2];
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 360, height: 640 }, deviceScaleFactor: 3 });
  const errs = []; pg.on('pageerror', e => errs.push(String(e.stack || e)));
  await pg.addInitScript(() => { try { localStorage.setItem('golgekuyu.meta.v1', JSON.stringify({ souls: 86, best: 12, runs: 9, kills: 240, bossKills: 2, classes: { warrior: true, archer: true }, tip: true, sound: false, music: false,
    hints: { enemy: 1, kill: 1, skill: 1, potion: 1, explore: 1, chest: 1, merchant: 1, fountain: 1, trap: 1, shrine: 1, anvil: 1, tomb: 1, stairs: 1 } })); } catch (e) {} });
  await pg.goto('file://' + file); await pg.waitForTimeout(900);
  await pg.screenshot({ path: out + '/screenshots/5-siniflar.png' });
  await pg.click('[data-a=start]'); await pg.waitForTimeout(300);
  const run = (stop) => pg.evaluate((stop) => { const g = __gk; let n = 0;
    while (n++ < 20000 && !g.over) { const G = g.G, p = G.p; p.hp = g.S.maxHp;
      if (g.modal) { if (stop === g.modal) return g.modal; g.modal === 'level' ? g.ACT.perk(p.choices[0]) : g.modal === 'loot' ? g.ACT.equip() : g.ACT.close(); continue; }
      const ms = g.visMobs();
      if (stop === 'fight' && G.floor >= 3 && ms.length >= 3 && ms.some(m => Math.abs(m.x - p.x) + Math.abs(m.y - p.y) === 1)) return 'fight';
      if (stop === 'boss' && ms.some(m => m.boss && Math.abs(m.x - p.x) + Math.abs(m.y - p.y) <= 2)) return 'boss';
      if (ms.length) { const t = ms.slice().sort((a, q) => (Math.abs(a.x - p.x) + Math.abs(a.y - p.y)) - (Math.abs(q.x - p.x) + Math.abs(q.y - p.y)))[0]; g.handleTap(t.x, t.y); continue; }
      if (g.exploreStep() === false) g.descend(); } return 'end'; }, stop);
  const hitShot = async (name) => { await pg.waitForTimeout(2400); await pg.evaluate(() => { const g = __gk, p = g.G.p, m = g.visMobs().slice().sort((a, q) => (Math.abs(a.x - p.x) + Math.abs(a.y - p.y)) - (Math.abs(q.x - p.x) + Math.abs(q.y - p.y)))[0]; m.hp = Math.max(m.hp, 60); g.handleTap(m.x, m.y); });
    await pg.waitForTimeout(90); await pg.screenshot({ path: out + '/screenshots/' + name }); };
  console.log(await run('fight')); await hitShot('1-savas.png');
  console.log(await run('level')); await pg.waitForTimeout(1700); await pg.screenshot({ path: out + '/screenshots/3-guc-sec.png' });
  console.log(await run('loot')); await pg.waitForTimeout(1700); await pg.screenshot({ path: out + '/screenshots/4-ganimet.png' });
  console.log(await run('boss')); await hitShot('2-patron.png');
  // feature graphic
  const sprites = await pg.evaluate((PAL) => { const mk = (rows, k) => { const c = document.createElement('canvas'); c.width = c.height = 10 * k; const x = c.getContext('2d'); x.fillStyle = '#120d1c';
      for (let j = 0; j < 8; j++) for (let i = 0; i < 8; i++) if (rows[j][i] !== '.') { x.fillRect(i * k, (j + 1) * k, 3 * k, k); x.fillRect((i + 1) * k, j * k, k, 3 * k); }
      for (let j = 0; j < 8; j++) for (let i = 0; i < 8; i++) { const ch = rows[j][i]; if (ch !== '.') { x.fillStyle = PAL[ch]; x.fillRect((i + 1) * k, (j + 1) * k, k, k); } } return c.toDataURL(); };
    const o = {}; for (const n of ['warrior', 'archer', 'mage', 'rogue', 'skeleton', 'slime', 'orc', 'ghost', 'demon', 'dragon', 'chest', 'bat', 'spider']) o[n] = mk(__gk.SPR[n], 8); return o; }, PAL);
  const fg = await b.newPage({ viewport: { width: 1024, height: 500 }, deviceScaleFactor: 1 });
  const im = (n, s, st) => `<img src="${sprites[n]}" style="width:${s}px;height:${s}px;image-rendering:pixelated;${st || ''}">`;
  await fg.setContent(`<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400;600;700&display=swap">
  <style>body{margin:0;width:1024px;height:500px;background:#0d0a14;overflow:hidden;font-family:'Pixelify Sans',monospace;position:relative}
  .floor{position:absolute;left:0;right:0;bottom:0;height:150px;background:#3b3450;border-top:10px solid #9c93b3;box-shadow:0 -40px 0 #7a7191, 0 -50px 0 #544c69}
  .glow{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 62%, rgba(242,163,58,.22), rgba(13,10,20,0) 60%)}
  h1{position:absolute;left:0;right:0;top:44px;margin:0;text-align:center;font-size:124px;line-height:1;color:#f2a33a;text-shadow:0 8px 0 #6a2f0c,0 16px 0 #000;letter-spacing:2px}
  p{position:absolute;left:0;right:0;top:196px;margin:0;text-align:center;font-size:30px;color:#ece4d0;text-shadow:0 3px 0 #000}
  .row{position:absolute;left:0;right:0;bottom:44px;display:flex;justify-content:center;align-items:flex-end;gap:10px}</style>
  <div class="floor"></div><div class="glow"></div><h1>Gölgekuyu</h1><p>Her iniş daha derine. Her ölüm seni güçlendirir.</p>
  <div class="row">${im('mage', 88)}${im('archer', 88)}${im('warrior', 100)}${im('rogue', 88)}<span style="width:20px"></span>${im('chest', 64)}<span style="width:20px"></span>
  ${im('skeleton', 88, 'transform:scaleX(-1)')}${im('slime', 80, 'transform:scaleX(-1)')}${im('orc', 96, 'transform:scaleX(-1)')}${im('dragon', 144, 'transform:scaleX(-1)')}</div>`);
  await fg.waitForTimeout(1200); await fg.screenshot({ path: out + '/feature-1024x500.png' });
  console.log('errs', errs); await b.close();
})();
