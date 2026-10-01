// QA for "Search outside the dataset" + "Propose for inclusion" on norm pages (SPA + static content pages).
import { createRequire } from 'module'; const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_PATH || 'playwright');
const B = process.argv[2] || 'http://localhost:8765/', OUT = process.argv[3] || 'qa/screens/', PFX = process.argv[4] || 'out';
const IDS = (process.env.NORMS || 'fr-cc-371-1,mo-rsmo-452.375,eu-reg-2019-1111-art-10').split(',');
const V = [['d', { viewport: { width: 1440, height: 900 }, colorScheme: 'light' }], ['dd', { viewport: { width: 1440, height: 900 }, colorScheme: 'dark' }],
  ['m', { viewport: { width: 390, height: 844 }, isMobile: true, colorScheme: 'light' }], ['md', { viewport: { width: 390, height: 844 }, isMobile: true, colorScheme: 'dark' }]];
const b = await chromium.launch(); const errs = [];
for (const [tag, opt] of V) {
  const ctx = await b.newContext(opt);
  for (const id of IDS) {
    const p = await ctx.newPage();
    p.on('pageerror', (e) => errs.push(`${tag} ${id}: ${e.message}`));
    p.on('console', (m) => { if (m.type() === 'error' && !/frame|fonts/i.test(m.text())) errs.push(`${tag} ${id}: ${m.text()}`); });
    const t0 = Date.now();
    await p.goto(`${B}#/norm/${id}`, { waitUntil: 'load' });
    try { await p.waitForSelector('#outside-h', { timeout: 15000 }); } catch { errs.push(`${tag} ${id}: no outside section`); }
    const ms = Date.now() - t0;
    const info = await p.evaluate(() => { const s = document.querySelector('section.outside');
      return { h1: document.querySelector('#main h1')?.textContent.trim().slice(0, 50), interps: document.querySelector('#interps .cnt')?.textContent,
        warn: s?.querySelector('.warnline')?.textContent.trim().slice(0, 60), links: [...(s?.querySelectorAll('a') || [])].map((a) => [a.textContent.trim().slice(0, 45), a.href.slice(0, 150)]) }; });
    if (!info.links.some((l) => l[1].includes('github.com/vagabondo73/family-law-fr-us-annotated-browser/issues/new'))) errs.push(`${tag} ${id}: no proposal link`);
    if (tag === 'd') console.log(id, ms + 'ms', JSON.stringify(info));
    await p.evaluate(() => document.querySelector('section.outside')?.scrollIntoView({ block: 'start' }));
    await p.waitForTimeout(300);
    await p.screenshot({ path: `${OUT}${PFX}-${tag}-${id.replace(/[.]/g, '_')}.png` });
    if (tag === 'd') { // static page
      await p.goto(`${B}content/${id}.html`, { waitUntil: 'load' });
      const st = await p.evaluate(() => { const h = [...document.querySelectorAll('h2')].find((x) => /hors du corpus/.test(x.textContent));
        let el = h?.nextElementSibling, n = 0, gh = false; while (el && el.tagName !== 'H2') { n += el.querySelectorAll('a').length; gh ||= !!el.querySelector('a[href*="issues/new"]'); el = el.nextElementSibling; }
        return { found: !!h, links: n, propose: gh }; });
      console.log('  static', JSON.stringify(st)); if (!st.found || !st.propose) errs.push(`static ${id}: missing block`);
    }
    await p.close();
  }
  await ctx.close();
}
await b.close(); console.log('ERRORS', JSON.stringify(errs));
