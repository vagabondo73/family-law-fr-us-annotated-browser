// Bootstrap + hash router. Routes: #/ · #/norm/<id> · #/interp/<id> · #/issue/<id> · #/corpus/<id> · #/compare/<id>
//                                  #/search?q=… · #/sources · #/coverage · #/axis/<family|procedure> · #/mapping/<id>?art=&q=&eq=
import { $, $$, esc, debounce, icon } from './util.js';
import { manifest, state, corpusMeta } from './store.js';
import { renderTree, renderIssues, markCurrent, highlightIssue, setAxis } from './panes.js';
import * as V from './views.js';
import { buildIndex, search } from './search.js';

function parse() {
  const h = decodeURI(location.hash.replace(/^#/, '')) || '/';
  const [path, qs] = h.split('?');
  const parts = path.split('/').filter(Boolean);
  return { parts, params: new URLSearchParams(qs || '') };
}

async function route() {
  const { parts, params } = parse();
  const [k, ...rest] = parts;
  const id = rest.join('/');
  state.currentNorm = k === 'norm' || k === 'compare' ? id : null;
  markCurrent();
  document.body.classList.remove('show-l', 'show-r');
  document.body.classList.toggle('no-right', ['sources', 'coverage', 'compare', 'mapping'].includes(k));
  setTab('m');
  $$('.hnav a[data-nav]').forEach((a) => a.toggleAttribute('aria-current', a.dataset.nav === k));
  try {
    switch (k) {
      case 'norm': await V.viewNorm(id, params); break;
      case 'interp': await V.viewInterp(id); break;
      case 'issue': await V.viewIssue(id); break;
      case 'corpus': await V.viewCorpus(id, params); break;
      case 'compare': await V.viewCompare(id); break;
      case 'search': await V.viewSearch(params); break;
      case 'sources': await V.viewSources(); break;
      case 'coverage': await V.viewCoverage(); break;
      case 'axis': await setAxis(id || 'family'); await V.viewHome(); break;
      case 'mapping': await V.viewMapping(id || (state.manifest.mappings?.[0]?.id ?? 'cpc-mo'), params); break;
      default: await V.viewHome();
    }
  } catch (e) {
    console.error(e);
    $('#main').innerHTML = `<h1 class="t">Erreur / Error</h1><p class="empty-state">${esc(e.message)}</p>`;
  }
  document.documentElement.lang = $('#main article')?.getAttribute('lang') || 'fr';
  if (!params.get('i') && !params.get('at')) window.scrollTo(0, 0);
  highlightIssue();
}

function setTab(tab) {
  $$('.tabs-m button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.tab === tab));
  document.body.classList.toggle('show-l', tab === 'l');
  document.body.classList.toggle('show-r', tab === 'r');
}

function initChrome(M) {
  // axis switcher (family law / comparative civil procedure) — only when the manifest declares several axes
  const axes = M.axes || [];
  const axBox = $('#axis');
  if (axes.length > 1 && axBox) {
    axBox.innerHTML = axes.map((a) => `<button type="button" data-axis="${esc(a.id)}" aria-pressed="${a.id === state.axis}" title="${esc(a.label_fr)} / ${esc(a.label_en)} (${a.norms})"><span class="afr">${esc(a.label_fr)}</span><span class="aen"> / ${esc(a.label_en)}</span><span class="ash">${a.id === 'family' ? 'Famille' : 'Procédure'}</span></button>`).join('');
    axBox.hidden = false;
    $$('button', axBox).forEach((b) => (b.onclick = () => { location.hash = '#/axis/' + b.dataset.axis; }));
  }
  document.body.dataset.axis = state.axis;
  // theme (in memory; defaults to system preference)
  const btn = $('#btn-theme');
  const paint = () => { btn.innerHTML = document.documentElement.dataset.theme === 'dark' ? icon.sun : icon.moon; };
  btn.onclick = () => { const r = document.documentElement; r.dataset.theme = r.dataset.theme === 'dark' ? 'light' : 'dark'; paint(); };
  paint();
  $('#btn-issues').onclick = () => document.body.classList.toggle('show-r');
  $$('.tabs-m button').forEach((b) => (b.onclick = () => setTab(b.dataset.tab)));
  $('#collapse-all').onclick = () => $$('#tree details[data-corpus], #tree details[data-k]').forEach((d) => (d.open = false));
  // copy-permalink buttons (delegated)
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-copy]');
    if (!b) return;
    try { await navigator.clipboard.writeText(b.dataset.copy); } catch { /* clipboard unavailable: show link */ }
    const old = b.innerHTML; b.textContent = '✓ ' + (document.documentElement.lang === 'en' ? 'Link copied' : 'Lien copié / copied');
    setTimeout(() => (b.innerHTML = old), 1500);
  });
  // on mobile, navigating from a pane closes it
  ['#tree', '#itree'].forEach((s) => $(s).addEventListener('click', (e) => { if (e.target.closest('a[href^="#/"]')) setTimeout(() => setTab('m'), 0); }));

  // fixture / build banner
  if (M.fixture) $('#banner').innerHTML = `<div class="banner" role="status"><b>FIXTURE</b> — Données de démonstration pour le développement, pas le corpus validé. / Development fixture data, not the validated corpus. <a href="fixtures/README.md">README</a></div>`;

  // header quick search (index built lazily on first focus)
  const q = $('#q'), box = $('#qs');
  if (matchMedia('(max-width: 760px)').matches) q.placeholder = 'Rechercher / Search';
  let sel = -1;
  q.addEventListener('focus', () => buildIndex(), { once: true });
  const run = debounce(async () => {
    const v = q.value.trim();
    if (v.length < 2) { box.classList.remove('open'); return; }
    const { hits, total, terms } = await search(v, { limit: 8 });
    sel = -1;
    box.innerHTML = hits.map(({ doc }, i) => {
      const href = doc.type === 'norm' ? `#/norm/${esc(doc.id)}?hl=${encodeURIComponent(terms.join(','))}` : `#/interp/${esc(doc.id)}`;
      const c = doc.corpus ? corpusMeta(doc.corpus) : null;
      return `<a role="option" href="${href}" data-i="${i}"><span class="dot ${doc.group}"></span> ${esc(doc.title)}${doc.type === 'norm' && doc.sub ? ' — ' + esc(doc.sub.slice(0, 80)) : ''}<small>${doc.type === 'norm' ? esc(c ? (c.lang === 'fr' ? c.label_fr : c.label_en) : '') : esc(doc.sub)}</small></a>`;
    }).join('') + `<a href="#/search?q=${encodeURIComponent(v)}"><strong>${total} résultat(s) / result(s) →</strong></a>`;
    box.classList.add('open');
  }, 140);
  q.addEventListener('input', run);
  q.addEventListener('keydown', (e) => {
    const items = $$('a', box);
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items.forEach((a, i) => a.classList.toggle('sel', i === sel));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      location.hash = sel >= 0 && items[sel] ? items[sel].getAttribute('href') : '#/search?q=' + encodeURIComponent(q.value);
      box.classList.remove('open'); q.blur();
    } else if (e.key === 'Escape') { box.classList.remove('open'); q.blur(); }
  });
  box.addEventListener('click', () => box.classList.remove('open'));
  document.addEventListener('click', (e) => { if (!e.target.closest('.search')) box.classList.remove('open'); });
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); q.focus(); }
  });
}

async function boot() {
  const M = await manifest();
  if (!M) {
    $('#main').innerHTML = `<h1 class="t">Données indisponibles / Data unavailable</h1>
      <p class="empty-state">data/manifest.json est introuvable. Lancez <code>python3 scripts/site_build.py</code> puis servez <code>site/</code>. /
      data/manifest.json not found — run <code>python3 scripts/site_build.py</code>, then serve <code>site/</code>.</p>`;
    return;
  }
  initChrome(M);
  await Promise.all([renderTree(), renderIssues()]);
  window.addEventListener('hashchange', route);
  route();
}
boot();
