import { createRequire } from 'module'; const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_PATH || 'playwright');
const B = process.argv[2] || 'http://localhost:8765/', OUT = process.argv[3] || 'qa/screens/', PFX = process.argv[4] || 'fx';
const b = await chromium.launch(); const errs = [];
const V = [['d', { viewport: { width: 1440, height: 900 }, colorScheme: 'light' }], ['dd', { viewport: { width: 1440, height: 900 }, colorScheme: 'dark' }], ['m', { viewport: { width: 390, height: 844 }, isMobile: true, colorScheme: 'light' }]];
const R = (process.env.ROUTES || '#/axis/procedure,#/mapping/cpc-mo,#/norm/mo-rules-74.16,#/norm/fr-cpc-1107,#/issue/mo-proc.judgments,#/axis/family').split(',');
for (const [tag, opt] of V) {
  const ctx = await b.newContext(opt);
  for (const r of R) {
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errs.push(`${tag} ${r}: ${e.message}`));
    p.on('console', (m) => { if (m.type() === 'error' && !/frame|fonts/i.test(m.text())) errs.push(`${tag} ${r}: ${m.text()}`); });
    await p.goto(B + r, { waitUntil: 'load' });
    try { await p.waitForSelector('#main h1', { timeout: 15000 }); } catch { errs.push(`${tag} ${r}: no h1`); }
    await p.waitForTimeout(600);
    const info = await p.evaluate(() => ({ axis: document.body.dataset.axis, h1: document.querySelector('#main h1')?.textContent.slice(0, 60),
      tree: [...document.querySelectorAll('#tree summary.corpus, #tree a.xnav')].map((x) => x.textContent.trim().slice(0, 40)).slice(0, 8),
      issues: [...document.querySelectorAll('#itree .iside')].map((x) => x.textContent.trim()), corr: document.querySelectorAll('table.corr tbody tr').length,
      xl: document.querySelectorAll('#main a[href*="annotated-browser"]').length }));
    if (tag === 'd') console.log(r, JSON.stringify(info));
    await p.screenshot({ path: `${OUT}${PFX}-${tag}-${r.replace(/[#/?=%&.]+/g, '_').replace(/^_+|_+$/g, '')}.png` });
    await p.close();
  }
  await ctx.close();
}
await b.close(); console.log('ERRORS', JSON.stringify(errs));
