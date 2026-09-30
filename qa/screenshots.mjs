// Playwright visual QA: desktop + mobile, light + dark.
// Usage: (cd site && python3 -m http.server 8765 &) ; NODE_PATH=~/node_modules node qa/screenshots.mjs [baseUrl] [outDir]
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_PATH || 'playwright');

const B = process.argv[2] || 'http://localhost:8765/';
const OUT = process.argv[3] || new URL('./screens/', import.meta.url).pathname;
const routes = (process.env.ROUTES || '#/,#/norm/fr-cc-371-1,#/norm/mo-rsmo-452.375,#/issue/fr.divorce,#/search?q=habitual%20residence,#/compare/fr-cc-270,#/sources,#/coverage').split(',');
const variants = [
  { tag: 'desktop-light', viewport: { width: 1440, height: 900 }, colorScheme: 'light' },
  { tag: 'desktop-dark', viewport: { width: 1440, height: 900 }, colorScheme: 'dark' },
  { tag: 'mobile-light', viewport: { width: 390, height: 844 }, colorScheme: 'light', isMobile: true, hasTouch: true },
  { tag: 'mobile-dark', viewport: { width: 390, height: 844 }, colorScheme: 'dark', isMobile: true, hasTouch: true },
];
const errors = [];
const browser = await chromium.launch();
for (const v of variants) {
  const ctx = await browser.newContext(v);
  for (const r of routes) {
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errors.push(`${v.tag} ${r}: ${e.message}`));
    p.on('console', (m) => { if (m.type() === 'error' && !/frame|X-Frame|fonts/.test(m.text())) errors.push(`${v.tag} ${r}: ${m.text()}`); });
    const t0 = Date.now();
    await p.goto(B + r, { waitUntil: 'load', timeout: 30000 });
    try { await p.waitForSelector('#main h1', { timeout: 20000 }); } catch { errors.push(`${v.tag} ${r}: no h1`); }
    if (r.includes('search')) { try { await p.waitForSelector('#sres .res', { timeout: 30000 }); } catch { errors.push(`${v.tag} ${r}: no results`); } }
    await p.waitForTimeout(500);
    const name = r.replace(/[#/?=%&]+/g, '_').replace(/^_+|_+$/g, '') || 'home';
    await p.screenshot({ path: `${OUT}${v.tag}-${name}.png` });
    console.log(v.tag, r, Date.now() - t0, 'ms');
    await p.close();
  }
  await ctx.close();
}
await browser.close();
console.log('ERRORS', JSON.stringify(errors, null, 1));
