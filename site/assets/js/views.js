// Center-pane views. Each returns an HTML string (or mounts into `main`) and never throws on missing data.
import { esc, fmtDate, fmtDateTime, hostOf, icon, natCmp, $, $$, debounce } from './util.js';
import { t, bi } from './i18n.js';
import {
  state, manifest, getJSON, loadCorpus, getNorm, getInterp, corpusMeta, sideMeta, groupOfSide, langOfGroup,
  issues, issueAncestors, issueMembers, issueMembersAsync, inIssue, corpusOfNormId, groupOfAuthority, getNormLight, interpChunk,
  axisOf, inAxis, corpusAxisCount, getMapping, axesMeta,
} from './store.js';
import { normTitle, statusBadge, fixtureBadges, legalText, ruleText, linksRow, interpCard, basisBadge, skeleton } from './components.js';
import { buildIndex, search, snippet } from './search.js';
import { revealNorm, setIssueFilter, highlightIssue, setAxis, focusIssueSide } from './panes.js';

const main = () => $('#main');
const setTitle = (s) => { document.title = `${s} — Family Law Annotated Browser`; };
const footer = () => `<footer class="ft">Normes et interprétations obligatoires — liens vers les sources officielles ; textes projetés sans valeur officielle. /
  Binding norms and interpretations — linked to official sources; projected texts carry no official authority.
  · <a href="content/index.html">Agent-readable static pages</a> · <a href="data/manifest.json">manifest.json</a></footer>`;

function notFound(what, lang = 'fr') {
  main().innerHTML = `<h1 class="t">${t('notFound', lang)}</h1><p class="empty-state">${esc(what)}</p>${footer()}`;
}
function crumbsFor(n, lang) {
  const M = state.manifest;
  const g = groupOfSide(n.side);
  const s = sideMeta(g);
  const c = corpusMeta(n.corpus);
  const parts = [`<span class="dot ${g}"></span><span>${esc(s ? (lang === 'fr' ? s.label_fr : s.label_en) : g)}</span>`,
    `<a href="#/corpus/${esc(n.corpus)}">${esc(c ? (c.lang === 'fr' ? c.label_fr : c.label_en) : n.corpus)}</a>`,
    ...(n.path || []).map((p) => `<a href="#/corpus/${esc(n.corpus)}?at=${encodeURIComponent(p.id || p.label)}">${esc(p.label)}</a>`)];
  return `<nav class="crumbs" aria-label="Fil d'Ariane / Breadcrumb">${parts.join('<span class="sep">›</span>')}</nav>`;
}
async function normLabelResolver(ids) {
  const out = new Map();
  await Promise.all([...new Set(ids)].map(async (id) => {
    const n = await getNormLight(id);
    out.set(id, n ? `${normTitle(n)}${n.kind !== 'judge-made-rule' && n.heading ? ' — ' + n.heading : ''}` : id);
  }));
  return (id) => out.get(id) || id;
}

// ------------------------------------------------------------------ home
export async function viewHome() {
  const M = await manifest();
  if (state.axis === 'procedure') return viewProcHome();
  setTitle('Accueil / Home');
  const bySide = M.sides.map((s) => {
    const cs = M.corpora.filter((c) => c.group === s.id && corpusAxisCount(c, 'family') > 0);
    const norms = cs.reduce((a, c) => a + corpusAxisCount(c, 'family'), 0);
    const lang = s.lang;
    return `<a class="card" href="${cs[0] ? '#/corpus/' + esc(cs[0].id) : '#/'}">
      <h3><span class="dot ${s.id}"></span>${esc(lang === 'fr' ? s.label_fr : s.label_en)}</h3>
      <div class="big">${norms}</div><p>${lang === 'fr' ? 'dispositions' : 'provisions'} · ${cs.length} ${lang === 'fr' ? 'corpus' : cs.length === 1 ? 'corpus' : 'corpora'}</p>
      <p style="margin-top:6px">${cs.map((c) => esc(c.lang === 'fr' ? c.label_fr : c.label_en)).join(' · ') || (lang === 'fr' ? 'en préparation' : 'in preparation')}</p></a>`;
  }).join('');
  main().innerHTML = `
  <h1 class="t">Droit de la famille annoté — France ↔ États-Unis / Missouri</h1>
  <p class="sub">Family Law Annotated Browser — France ↔ United States (federal) / Missouri, with EU and international instruments</p>
  <div class="prose">
    <p>Un univers juridique fermé : les <strong>normes obligatoires</strong> du droit de la famille et leurs <strong>interprétations obligatoires</strong>, chaque disposition ouvrant les décisions retenues selon la règle temporelle, avec un arbre des questions. Les textes sont projetés depuis les sources officielles, vers lesquelles chaque fiche renvoie.</p>
    <p lang="en">A closed legal universe of binding family-law norms and binding interpretations. Each provision opens the qualifying decisions under the temporal rule; an issue tree indexes both. Texts are projected from official sources, and every record links back to the official page.</p>
  </div>
  <div class="cards" style="margin:22px 0">${bySide}</div>
  ${procCard(M)}
  <h2 class="s">Règle temporelle <span class="bil">/ Temporal rule</span> (SCOPE §2)</h2>
  <div class="cards">
    <div class="card"><h3><span class="badge ok">${t('basisA', 'fr')}</span></h3><p>Décision rendue à compter de la date D de la version en vigueur. <span lang="en">Decided on or after D(norm), the date the current wording took effect.</span></p></div>
    <div class="card"><h3><span class="badge warn">${t('basisB', 'fr')}</span></h3><p>Décision antérieure à D, mais texte interprété identique en lettre et en fonction — justification écrite. <span lang="en">Earlier decision on wording identical in text and function — written justification shown.</span></p></div>
    <div class="card"><h3>${M.totals.norms} · ${M.totals.interps}</h3><p>dispositions · interprétations <span class="bil">/ provisions · interpretations</span><br>${M.totals.issues} questions · ${M.totals.sources} sources</p></div>
  </div>
  <h2 class="s">Accès <span class="bil">/ Access</span></h2>
  <div class="prose"><p>Permaliens <span class="bil">/ Permalinks</span> : <code>#/norm/&lt;id&gt;</code>, <code>#/interp/&lt;id&gt;</code>, <code>#/issue/&lt;id&gt;</code>, <code>#/corpus/&lt;id&gt;</code>.
  Pages statiques lisibles sans JavaScript <span class="bil">/ static pages readable without JavaScript</span> : <a href="content/index.html">content/index.html</a>. Données <span class="bil">/ Data</span> : <a href="data/manifest.json">data/manifest.json</a>.</p>
  <p class="note">Généré <span class="bil">/ generated</span> ${fmtDateTime(M.generated)} · source : <code>${esc(M.source)}</code>${M.build_report?.error ? ` · <a href="data/build-report.json">${M.build_report.error} build errors</a>` : ''}</p></div>
  ${footer()}`;
}

// ------------------------------------------------------------------ comparative civil procedure axis
const EQ = { equivalent: ['équivalent', 'equivalent', 'ok'], partial: ['partiel', 'partial', 'warn'], functional: ['fonctionnel', 'functional', 'acc'], none: ['aucun', 'none', ''] };
const eqBadge = (e, lang) => { const m = EQ[e] || [e || '?', e || '?', '']; return `<span class="badge eq ${m[2]}" title="${esc(m[0])} / ${esc(m[1])}">${esc(lang === 'en' ? m[1] : m[0])}</span>`; };
function procCard(M) {
  const ax = (M.axes || []).find((a) => a.id === 'procedure');
  if (!ax) return '';
  const maps = (M.mappings || []).reduce((a, m) => a + m.count, 0);
  return `<h2 class="s">Axe indépendant <span class="bil">/ Independent axis</span></h2>
  <div class="cards"><a class="card" href="#/axis/procedure"><h3>⇄ ${esc(ax.label_fr)} <span class="bil">/ ${esc(ax.label_en)}</span></h3>
  <div class="big">${ax.norms}</div><p>règles et dispositions du Missouri · ${maps} articles du CPC mis en correspondance <span class="bil">/ Missouri provisions · ${maps} CPC articles mapped</span></p></a></div>`;
}
export async function viewProcHome() {
  const M = await manifest();
  setTitle('Procédure civile comparée / Comparative civil procedure');
  const ax = (M.axes || []).find((a) => a.id === 'procedure') || { norms: 0 };
  const cs = M.corpora.filter((c) => corpusAxisCount(c, 'procedure') > 0);
  const sb = M.sibling_browsers || {};
  const cards = cs.map((c) => `<a class="card" href="#/corpus/${esc(c.id)}"><h3><span class="dot ${esc(c.group)}"></span>${esc(c.lang === 'fr' ? c.label_fr : c.label_en)}</h3>
    <div class="big">${corpusAxisCount(c, 'procedure')}</div><p>${c.lang === 'fr' ? 'dispositions (axe procédure)' : 'provisions on the procedure axis'}</p></a>`).join('');
  const maps = (M.mappings || []).map((m) => `<a class="card" href="#/mapping/${esc(m.id)}"><h3>⇄ ${esc(m.label_fr)}</h3><div class="big">${m.count}</div><p>${esc(m.label_en)}${m.fixture ? ' <span class="badge fx">fixture</span>' : ''}</p></a>`).join('');
  main().innerHTML = `<h1 class="t">Procédure civile comparée — CPC ↔ Missouri</h1>
  <p class="sub">Comparative civil procedure — French Code de procédure civile ↔ Missouri Supreme Court Rules 41–101 and RSMo chs. 506–517, 525</p>
  <div class="prose"><p>Axe indépendant de l'arbre du droit de la famille. Côté Missouri : règles et dispositions législatives avec leurs interprétations obligatoires (Cour suprême du Missouri, arrêts publiés des cours d'appel), selon la même règle temporelle. Côté français : <strong>renvois uniquement</strong> vers le <a href="${esc(sb.cpc || '#')}" target="_blank" rel="noopener">CPC annoté</a> et Légifrance ; côté fédéral : renvois vers le <a href="${esc(sb.frcp || '#')}" target="_blank" rel="noopener">FRCP annotated browser</a>.</p>
  <p lang="en">An axis independent of the family-law tree. Missouri side: rules and statutes with their binding interpretations under the same temporal rule. French side: <strong>cross-links only</strong> to the CPC annotated browser and Légifrance; federal side: links to the FRCP annotated browser where a counterpart exists.</p></div>
  <div class="cards" style="margin:22px 0">${maps || '<div class="card"><h3>⇄ CPC ↔ Missouri</h3><p>Table de correspondance en préparation. / Mapping in preparation.</p></div>'}${cards || '<div class="card"><p>Corpus procédural en préparation. / Procedural corpus in preparation.</p></div>'}</div>
  <p class="note">${ax.norms} dispositions sur cet axe <span class="bil">/ provisions on this axis</span> · <a href="#/axis/family">← ${esc(axesMeta()[0].label_fr)} <span class="bil">/ ${esc(axesMeta()[0].label_en)}</span></a></p>${footer()}`;
}
function corrPanel(rows, lang, selfId, label) {
  if (!rows?.length) return '';
  const en = lang === 'en';
  const body = rows.map((r) => {
    const cpc = `<span class="num">art. ${esc(r.cpc_article)}</span>`;
    const cl = [r.fr_norm && r.fr_norm !== selfId ? `<a href="#/norm/${esc(r.fr_norm)}">${en ? 'in this corpus' : 'dans ce corpus'}</a>` : '',
      r.cpc_url ? `<a href="${esc(r.cpc_url)}" target="_blank" rel="noopener">CPC annoté ↗</a>` : '',
      r.legifrance_url ? `<a href="${esc(r.legifrance_url)}" target="_blank" rel="noopener">Légifrance ↗</a>` : ''].filter(Boolean).join(' · ');
    const mo = (r.mo_norms || []).map((m) => m === selfId ? `<strong>${esc(label(m))}</strong>` : `<a href="#/norm/${esc(m)}">${esc(label(m))}</a>`).join('<br>') || '—';
    const fr = (r.frcp || []).map((x) => `<a href="${esc(x.url)}" target="_blank" rel="noopener">FRCP ${esc(x.rule)} ↗</a>`).join(' · ') || '—';
    const note = en ? r.note_en || r.note_fr : r.note_fr || r.note_en;
    return `<tr><td>${cpc}<div class="lk">${cl}</div></td><td>${mo}</td><td>${eqBadge(r.equivalence, lang)}</td><td>${fr}</td><td class="nt">${esc(note || '')}</td></tr>`;
  }).join('');
  return `<h2 class="s">Correspondances <span class="bil">/ Correspondences</span> — CPC ↔ Missouri <span class="cnt">${rows.length}</span></h2>
    <div class="tscroll"><table class="data corr"><thead><tr><th>CPC</th><th>Missouri</th><th>${en ? 'Equivalence' : 'Équivalence'}</th><th>FRCP</th><th>Note</th></tr></thead><tbody>${body}</tbody></table></div>
    <p class="note">${en ? 'French and federal sides are cross-links to the sibling annotated browsers (no content duplicated).' : 'Côtés français et fédéral : renvois vers les navigateurs annotés (aucune reprise de contenu).'} <a href="#/mapping/${esc(rows[0].map || 'cpc-mo')}">${en ? 'Full correspondence table' : 'Table complète'} →</a></p>`;
}
function outsidePanel(n, lang) {
  const links = n.outside || [];
  if (!links.length && !n.propose_url) return '';
  const en = lang === 'en';
  const L = (x) => (en ? x.label_en : x.label_fr);
  return `<section class="outside" aria-labelledby="outside-h">
    <h2 class="s" id="outside-h">${en ? 'Search outside the dataset' : 'Rechercher hors du corpus'} <span class="bil">/ ${en ? 'Rechercher hors du corpus' : 'Search outside the dataset'}</span></h2>
    <p class="warnline"><strong>${en ? 'Outside the closed universe — unscreened.' : 'Hors de l\u2019univers clos — non filtré.'}</strong>
      ${en ? 'These external searches are not screened under the temporal rule (SCOPE §2): a decision found there is not a qualifying interpretation until proposed and reviewed.'
           : 'Ces recherches externes ne sont pas soumises à la règle temporelle (SCOPE §2) : une décision trouvée n\u2019est pas une interprétation retenue tant qu\u2019elle n\u2019a pas été proposée et examinée.'}</p>
    <p class="note">${en ? 'Pre-filled query' : 'Requête pré-remplie'} : <code>${esc(n.outside_q || '')}</code>
      <button class="btn sm" type="button" data-copy="${esc(n.outside_q || '')}">${icon.link} ${en ? 'Copy' : 'Copier'}</button></p>
    <div class="actions">${links.map((x) => `<a class="btn" href="${esc(x.url)}" target="_blank" rel="noopener nofollow" title="${esc((x.manual || x.human) ? (en ? x.note_en : x.note_fr) : (en ? 'opens an external search' : 'ouvre une recherche externe'))}">${esc(L(x))}${x.manual ? ' *' : ''}${x.human ? ' †' : ''} ${icon.ext}</a>`).join('')}</div>
    ${links.some((x) => x.manual) ? `<p class="note">* ${esc(en ? links.find((x) => x.manual).note_en : links.find((x) => x.manual).note_fr)}</p>` : ''}
    ${links.some((x) => x.human) ? `<p class="note">† ${en ? 'Opens in your own browser. Légifrance, FindLaw and Google Scholar block robots, so these links could not be machine-verified; you may be asked to pass a short human check.' : 'S’ouvre dans votre navigateur. Légifrance, FindLaw et Google Scholar bloquent les robots : ces liens n’ont pas pu être vérifiés automatiquement ; une courte vérification humaine peut vous être demandée.'}</p>` : ''}
    ${n.propose_url ? `<div class="actions"><a class="btn primary" href="${esc(n.propose_url)}" target="_blank" rel="noopener nofollow">${en ? 'Propose for inclusion' : 'Proposer pour inclusion'} <span class="bil">/ ${en ? 'Proposer pour inclusion' : 'Propose for inclusion'}</span> ${icon.ext}</a></div>
      <p class="note">${en ? 'Opens a pre-filled GitHub issue (labels: proposal, needs-screening). Give the decision citation, its official URL and why it qualifies under basis (a) or (b).'
                           : 'Ouvre un ticket GitHub pré-rempli (étiquettes : proposal, needs-screening). Indiquer la citation, l\u2019URL officielle et pourquoi la décision relève de la base (a) ou (b).'}</p>` : ''}
  </section>`;
}
function xlinksPanel(n, lang) {
  if (!n.xlinks?.length) return '';
  return `<h2 class="s">${lang === 'en' ? 'External annotated browsers' : 'Navigateurs annotés externes'} <span class="bil">/ cross-links</span></h2>
    <div class="actions">${n.xlinks.map((x) => `<a class="btn" href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.label)} ${icon.ext}</a>`).join('')}</div>`;
}
export async function viewMapping(id, params) {
  main().innerHTML = skeleton(12);
  if (state.axis !== 'procedure') await setAxis('procedure');
  const m = await getMapping(id);
  if (!m) return notFound(`${id} — table de correspondance indisponible / correspondence table unavailable`, 'fr');
  setTitle(m.label_fr);
  const ids = [...new Set(m.entries.flatMap((e) => e.mo_norms || []))];
  const label = await normLabelResolver(ids);
  const q0 = params.get('q') || '', eq0 = params.get('eq') || 'all', art = params.get('art');
  const counts = {}; m.entries.forEach((e) => { counts[e.equivalence] = (counts[e.equivalence] || 0) + 1; });
  const facet = (v, lab) => `<button class="facet" type="button" data-eq="${v}" aria-pressed="${eq0 === v}">${lab}</button>`;
  main().innerHTML = `<article lang="fr"><h1 class="t">${esc(m.label_fr)}</h1><p class="sub">${esc(m.label_en)}</p>
    ${m.fixture ? '<p class="banner" style="position:static">FIXTURE — qualifications illustratives, non revues. / Illustrative, unreviewed qualifications.</p>' : ''}
    <div class="prose"><p>Article par article du Code de procédure civile vers les règles et dispositions du Missouri. Le texte et la jurisprudence du CPC restent sur le <a href="${esc(state.manifest.sibling_browsers?.cpc || '#')}" target="_blank" rel="noopener">CPC annoté</a> et Légifrance (renvois). <span lang="en">Article-to-rule map; the CPC text and case law stay on the sibling browser and Légifrance (links only).</span></p></div>
    <form class="sbox" id="mform"><label class="sr-only" for="mq">Filtre</label><input id="mq" type="search" value="${esc(q0)}" placeholder="art. 56 · 55.05 · assignation · attorney fees"><button class="btn primary" type="submit">OK</button></form>
    <div class="facets">${facet('all', `Toutes / All · ${m.entries.length}`)}${Object.keys(EQ).map((k) => facet(k, `${EQ[k][0]} / ${EQ[k][1]} · ${counts[k] || 0}`)).join('')}</div>
    <div id="mres"></div></article>${footer()}`;
  const fold2 = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  let limit = 300;
  const draw = () => {
    const q = fold2($('#mq').value.trim()).replace(/^art\.?\s*/, '');
    let rows = m.entries.filter((e) => eq0 === 'all' || e.equivalence === eq0);
    if (q) rows = rows.filter((e) => fold2(e.cpc_article) === q || fold2([e.cpc_article, e.note_fr, e.note_en, ...(e.mo_norms || []).map(label), ...(e.frcp || []).map((x) => 'frcp ' + x.rule)].join(' ')).includes(q));
    const shown = rows.slice(0, limit).map((e) => ({ ...e, map: m.id }));
    $('#mres').innerHTML = `<p class="note">${rows.length} article(s)</p>` + (corrPanel(shown, 'fr', null, label).replace(/^<h2[^]*?<\/h2>/, '').replace(/<p class="note">[^]*$/, '') || '<p class="empty-state">—</p>') +
      (rows.length > limit ? `<button class="btn" id="more" type="button">Afficher tout / Show all (${rows.length})</button>` : '');
    const more = $('#more'); if (more) more.onclick = () => { limit = Infinity; draw(); };
    if (art) { const tr = [...$$('#mres tr')].find((r) => r.querySelector('.num')?.textContent === 'art. ' + art); if (tr) { tr.classList.add('hl-row'); tr.scrollIntoView({ block: 'center' }); } }
  };
  draw();
  $('#mform').onsubmit = (e) => { e.preventDefault(); draw(); };
  $('#mq').oninput = debounce(draw, 150);
  $$('.facet[data-eq]').forEach((b) => (b.onclick = () => { location.hash = `#/mapping/${id}?` + new URLSearchParams({ eq: b.dataset.eq, q: $('#mq').value }).toString(); }));
}

// ------------------------------------------------------------------ norm
export async function viewNorm(id, params) {
  main().innerHTML = skeleton(10);
  const r = await getNorm(id);
  const lang0 = langOfGroup(groupOfSide(corpusOfNormId(id)?.split('-')[0]));
  if (!r) return notFound(`${id} — ${t('notFoundNorm', lang0)}`, lang0);
  const { norm: n, corpus } = r;
  const lang = n.lang || 'fr';
  if (!inAxis(n)) await setAxis(axisOf(n)[0]);
  focusIssueSide(groupOfSide(n.side));
  setTitle(`${normTitle(n)} ${n.heading ? '— ' + n.heading : ''}`);
  revealNorm(n);
  const terms = params.get('hl') ? params.get('hl').split(',') : [];
  const its = (n.interps || []).map((i) => corpus.interps?.[i]).filter(Boolean);
  const ruleSrc = (n.rule_sources || []).map((i) => corpus.interps?.[i]).filter(Boolean);
  const I = await issues();
  const issueChips = (n.issues || []).map((iid) => `<a class="badge" style="text-transform:none" href="#/issue/${esc(iid)}">${esc(I.nodes.get(iid)?.label || iid)}</a>`).join(' ');
  const xl = await normLabelResolver([...(n.xrefs || []), ...(n.correspondences || []).flatMap((c) => c.mo_norms || [])]);
  const parties = n.parties ? `<h2 class="s">${t('parties', lang)}</h2><table class="parties">${Object.entries(n.parties).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</table>` : '';
  const title = n.kind === 'judge-made-rule' ? `<h1 class="t">${esc(n.heading)}</h1><p class="sub">${esc(n.num || '')}</p>`
    : `<h1 class="t"><span class="n">${esc(normTitle(n))}</span></h1>${n.heading ? `<p class="sub">${esc(n.heading)}</p>` : ''}`;
  const body = n.kind === 'judge-made-rule'
    ? `<h2 class="s">${t('summaryRule', lang)}</h2>${ruleText(n, terms)}
       <h2 class="s">${t('ruleSources', lang)} <span class="cnt">${ruleSrc.length}</span></h2>${ruleSrc.map((it) => interpCard(it, { normId: n.id, open: true, terms })).join('') || `<p class="empty-state">—</p>`}`
    : `<h2 class="s">${t('currentText', lang)}</h2>${legalText(n, terms)}`;
  const otherIts = n.kind === 'judge-made-rule' ? its.filter((i) => !(n.rule_sources || []).includes(i.id)) : its;

  main().innerHTML = `<article lang="${esc(lang)}">
    ${crumbsFor(n, lang)}${title}
    <div class="metarow">${statusBadge(n.status, lang)}${fixtureBadges(n, lang)}
      ${n.in_force_since ? `<span><span class="k">${t('inForceSince', lang)}</span> <strong>${fmtDate(n.in_force_since, lang)}</strong></span>` : ''}
      ${n.applies_to?.length ? `<span><span class="k">${t('appliesTo', lang)}</span> ${n.applies_to.map(esc).join(' · ')}</span>` : ''}
      <span class="ids">${esc(Object.entries(n.source_ids || {}).filter(([, v]) => (typeof v === 'string' || typeof v === 'number') && String(v).length <= 40 && !/[\s/]/.test(String(v)) && !/^[0-9a-f]{32,}$/.test(String(v))).map(([k, v]) => (/^\d+$/.test(String(v)) ? `${k} ${v}` : v)).join(' · '))}</span></div>
    <div class="actions">
      ${n.official_url ? `<a class="btn primary" href="${esc(n.official_url)}" target="_blank" rel="noopener">${icon.ext} ${t('openOfficial', lang)}</a>` : ''}
      ${n.kind !== 'judge-made-rule' ? `<a class="btn" href="#/compare/${esc(n.id)}">${icon.cmp} ${t('compare', lang)}</a>` : ''}
      <button class="btn" type="button" data-copy="${esc(location.href.split('#')[0] + '#/norm/' + n.id)}">${icon.link} ${t('permalink', lang)}</button>
      <a class="btn" href="content/${esc(n.id)}.html">${icon.doc} ${t('staticPage', lang)}</a>
      ${(n.alt_urls || []).map((u) => `<a class="btn" href="${esc(u.url)}" target="_blank" rel="noopener">${esc(u.label)} ${icon.ext}</a>`).join('')}
    </div>
    ${body}${parties}
    ${xlinksPanel(n, lang)}${corrPanel(n.correspondences, lang, n.id, xl)}
    ${n.xrefs?.length ? `<h2 class="s">${t('seeAlso', lang)}</h2><ul class="rlist">${n.xrefs.map((x) => `<li><a class="row" href="#/norm/${esc(x)}"><span class="num">${esc(x)}</span><span class="ttl">${esc(xl(x))}</span><span></span></a></li>`).join('')}</ul>` : ''}
    ${issueChips ? `<h2 class="s">${t('issues', lang)}</h2><div style="display:flex;flex-wrap:wrap;gap:6px">${issueChips}</div>` : ''}
    <h2 class="s" id="interps">${t('interps', lang)} <span class="cnt">${otherIts.length}</span></h2>
    ${otherIts.length ? `<div class="toolbar">
      <label>${t('sort', lang)} <select data-f="sort"><option value="desc">${t('newest', lang)}</option><option value="asc">${t('oldest', lang)}</option></select></label>
      <select data-f="basis" aria-label="basis"><option value="all">${t('allBasis', lang)}</option><option value="a">${t('basisA', lang)}</option><option value="b">${t('basisB', lang)}</option></select>
      ${state.activeIssue ? `<label><input type="checkbox" data-f="issue"> ${t('onlyIssue', lang)} (${esc(I.nodes.get(state.activeIssue)?.label || state.activeIssue)})</label>` : ''}
      <button class="btn sm" type="button" data-f="expand">${t('expandAll', lang)}</button><button class="btn sm" type="button" data-f="collapse">${t('collapseAll', lang)}</button>
    </div><div id="ilist"></div>` : `<p class="empty-state">${t('noInterps', lang)}</p>`}
    ${outsidePanel(n, lang)}
  </article>${footer()}`;

  const list = $('#ilist');
  if (list) {
    const f = { sort: 'desc', basis: 'all', issue: false };
    const draw = () => {
      let arr = otherIts.slice();
      if (f.basis !== 'all') arr = arr.filter((i) => i.norms.find((l) => l.norm === n.id)?.basis === f.basis);
      if (f.issue && state.activeIssue) { const ids = issueMembers(I, state.activeIssue).ids; arr = arr.filter((i) => inIssue(i.issues, ids)); }
      arr.sort((a, b) => (f.sort === 'asc' ? 1 : -1) * String(a.date).localeCompare(String(b.date)));
      list.innerHTML = arr.map((it) => interpCard(it, { normId: n.id, terms, open: arr.length <= 3 })).join('') || `<p class="empty-state">—</p>`;
    };
    draw();
    $$('[data-f]', main()).forEach((el) => {
      const k = el.dataset.f;
      if (k === 'expand' || k === 'collapse') el.onclick = () => $$('#ilist details').forEach((d) => (d.open = k === 'expand'));
      else el.onchange = () => { f[k] = el.type === 'checkbox' ? el.checked : el.value; draw(); };
    });
  }
  const target = params.get('i');
  if (target) { const d = document.getElementById('i-' + target); if (d) { d.open = true; d.scrollIntoView({ block: 'start' }); } }
}

// ------------------------------------------------------------------ interpretation
export async function viewInterp(id) {
  main().innerHTML = skeleton(8);
  const it = await getInterp(id);
  if (!it) return notFound(`${id} — interprétation absente du corpus publié / interpretation not in the published corpus.`);
  const lang = it.lang || 'fr';
  setTitle(it.citation || id);
  const lab = await normLabelResolver((it.norms || []).map((l) => l.norm));
  const g = groupOfAuthority(it.authority);
  const s = sideMeta(g);
  focusIssueSide(g);
  main().innerHTML = `<article lang="${esc(lang)}">
    <nav class="crumbs"><span class="dot ${g}"></span><span>${esc(s ? (lang === 'fr' ? s.label_fr : s.label_en) : g)}</span><span class="sep">›</span><span>${esc(it.court || it.authority)}</span></nav>
    <h1 class="t">${esc(it.citation || id)}</h1>
    <div class="metarow"><span>${esc(it.court || '')}</span><span>${fmtDate(it.date, lang)}</span>${fixtureBadges(it, lang)}</div>
    <div class="actions">${it.official_url ? `<a class="btn primary" href="${esc(it.official_url)}" target="_blank" rel="noopener">${icon.ext} ${t('openOfficial', lang)}</a>` : ''}
      <button class="btn" type="button" data-copy="${esc(location.href.split('#')[0] + '#/interp/' + it.id)}">${icon.link} ${t('permalink', lang)}</button></div>
    ${interpCard(it, { open: true, showNorms: true, normLabel: lab })}
    ${it.issues?.length ? `<h2 class="s">${t('issues', lang)}</h2><div style="display:flex;flex-wrap:wrap;gap:6px">${(await Promise.all(it.issues.map(async (iid) => { const I = await issues(); return `<a class="badge" style="text-transform:none" href="#/issue/${esc(iid)}">${esc(I.nodes.get(iid)?.label || iid)}</a>`; }))).join(' ')}</div>` : ''}
  </article>${footer()}`;
}

// ------------------------------------------------------------------ issue
export async function viewIssue(id) {
  const I = await issues();
  const node = I.nodes.get(id);
  if (!node) return notFound(`Question inconnue / Unknown issue: ${id}`);
  if (state.activeIssue !== id) await setIssueFilter(id);
  highlightIssue();
  const lang = node.lang || 'fr';
  setTitle(node.label);
  const anc = issueAncestors(I, id);
  const mem = await issueMembersAsync(I, id);
  const g = node.side;
  const s = sideMeta(g);
  // resolve interp → court/date quickly from index rows [id, citation, date, authority]
  const normsByCorpus = new Map();
  mem.norms.forEach((r) => { if (!normsByCorpus.has(r[3])) normsByCorpus.set(r[3], []); normsByCorpus.get(r[3]).push(r); });
  const normHtml = [...normsByCorpus].sort((a, b) => (corpusMeta(a[0])?.order ?? 99) - (corpusMeta(b[0])?.order ?? 99)).map(([cid, rows]) => {
    const c = corpusMeta(cid);
    return `<h3 style="font:600 var(--text-sm) var(--font-ui);margin:14px 0 4px;color:var(--ink-2)">${esc(c ? (c.lang === 'fr' ? c.label_fr : c.label_en) : cid)}</h3><ul class="rlist">${rows.sort((a, b) => natCmp(a[1], b[1])).map((r) =>
      `<li><a class="row" href="#/norm/${esc(r[0])}"><span class="num">${esc(r[1])}</span><span class="ttl">${esc(r[2] || '')}</span><span class="aux"></span></a></li>`).join('')}</ul>`;
  }).join('');
  const intHtml = mem.interps.sort((a, b) => String(b[2]).localeCompare(String(a[2]))).map((r) =>
    `<li><a class="row" href="#/interp/${esc(r[0])}"><span class="num">${esc(r[2] || '')}</span><span class="ttl">${esc(r[1] || r[0])}</span><span class="aux">${esc(r[3] || '')}</span></a></li>`).join('');
  main().innerHTML = `<article lang="${esc(lang)}">
    <nav class="crumbs"><span class="dot ${esc(g)}"></span><span>${esc(s ? (lang === 'fr' ? s.label_fr : s.label_en) : g)}</span>${anc.slice(0, -1).map((a) => `<span class="sep">›</span><a href="#/issue/${esc(a.id)}">${esc(a.label)}</a>`).join('')}</nav>
    <h1 class="t">${esc(node.label)}</h1><p class="ids">${esc(id)}</p>
    <div class="actions"><button class="btn" type="button" data-copy="${esc(location.href.split('#')[0] + '#/issue/' + id)}">${icon.link} ${t('permalink', lang)}</button>
      <button class="btn" type="button" id="clear-issue">× ${lang === 'fr' ? 'Retirer le filtre de l’index' : 'Clear index filter'}</button></div>
    ${node.children?.length ? `<h2 class="s">${t('subIssues', lang)}</h2><div style="display:flex;flex-wrap:wrap;gap:6px">${node.children.map((c) => `<a class="badge" style="text-transform:none" href="#/issue/${esc(c.id)}">${esc(c.label)}${c.count != null ? ' · ' + c.count : ''}</a>`).join('')}</div>` : ''}
    <h2 class="s">${t('norms', lang)} <span class="cnt">${mem.norms.length}</span></h2>${normHtml || `<p class="empty-state">—</p>`}
    <h2 class="s">${t('interpsShort', lang)} <span class="cnt">${mem.interps.length}</span></h2>${intHtml ? `<ul class="rlist">${intHtml}</ul>` : `<p class="empty-state">—</p>`}
  </article>${footer()}`;
  $('#clear-issue').onclick = () => { setIssueFilter(null); location.hash = '#/'; };
}

// ------------------------------------------------------------------ corpus (table of contents)
export async function viewCorpus(cid, params) {
  const c = corpusMeta(cid);
  if (!c) return notFound(`Corpus ${cid} — non publié / not published yet.`);
  main().innerHTML = skeleton(12);
  const d = await loadCorpus(cid);
  const lang = c.lang;
  const label = lang === 'fr' ? c.label_fr : c.label_en;
  setTitle(label);
  const s = sideMeta(c.group);
  const norms = (d?.norms || []).slice().sort((a, b) => natCmp(a.num, b.num));
  // group consecutive norms by path, in document order (natural sort by path then num)
  const key = (n) => (n.path || []).map((p) => p.label).join(' › ');
  const groups = new Map();
  norms.forEach((n) => { const k = key(n); if (!groups.has(k)) groups.set(k, { path: n.path || [], items: [] }); groups.get(k).items.push(n); });
  let last = [];
  const toc = [...groups.values()].map((g) => {
    let h = '';
    g.path.forEach((p, i) => { if (last[i] !== p.label) h += `<h3 class="d${i + 1}" id="p-${esc(p.id || p.label)}" style="margin-left:${i * 14}px">${esc(p.label)}</h3>`; });
    last = g.path.map((p) => p.label);
    return h + `<ul class="rlist" style="margin-left:${g.path.length * 14}px">${g.items.sort((a, b) => natCmp(a.num, b.num)).map((n) =>
      `<li><a class="row" href="#/norm/${esc(n.id)}"><span class="num">${esc(n.kind === 'judge-made-rule' ? '◆' : n.num)}</span><span class="ttl">${esc(n.heading || normTitle(n))}</span><span class="aux">${(n.ni ?? (n.interps || []).length) ? ((n.ni ?? n.interps.length) + ' ' + (lang === 'fr' ? 'interpr.' : 'interp.')) : ''}</span></a></li>`).join('')}</ul>`;
  }).join('');
  main().innerHTML = `<article lang="${esc(lang)}">
    <nav class="crumbs"><span class="dot ${c.group}"></span><span>${esc(s ? (lang === 'fr' ? s.label_fr : s.label_en) : c.group)}</span></nav>
    <h1 class="t">${esc(label)}</h1>
    <div class="metarow"><span><strong>${c.norms}</strong> ${lang === 'fr' ? 'dispositions' : 'provisions'}</span><span><strong>${c.interps}</strong> ${lang === 'fr' ? 'interprétations' : 'interpretations'}</span>${c.fixture ? fixtureBadges({ fixture: true }, lang) : ''}
      <a href="content/corpus-${esc(cid)}.html">${t('staticPage', lang)}</a></div>
    <h2 class="s">${t('toc', lang)}</h2><div class="toc">${toc || `<p class="empty-state">—</p>`}</div>
  </article>${footer()}`;
  const at = params.get('at');
  if (at) document.getElementById('p-' + at)?.scrollIntoView({ block: 'start' });
}

// ------------------------------------------------------------------ search
export async function viewSearch(params) {
  const q = params.get('q') || '';
  const type = params.get('t') || 'all';
  const group = params.get('g') || 'all';
  const axis = params.get('a') || 'all';
  const ce = params.get('ce') === '1';
  setTitle(`Recherche / Search: ${q}`);
  const M = await manifest();
  const facet = (k, v, lab, cur) => `<button class="facet" type="button" data-k="${k}" data-v="${v}" aria-pressed="${cur === v}">${lab}</button>`;
  main().innerHTML = `<h1 class="t">Recherche <span class="bil">/ Search</span></h1>
    <form class="sbox" id="sform"><label class="sr-only" for="sq">Query</label><input id="sq" type="search" value="${esc(q)}" placeholder="371-1 · prestation compensatoire · habitual residence · 16-25.256"><button class="btn primary" type="submit">OK</button></form>
    <div class="facets">${facet('t', 'all', 'Tout / All', type)}${facet('t', 'norm', 'Dispositions / Provisions', type)}${facet('t', 'interp', 'Interprétations / Interpretations', type)}
      <span style="width:12px"></span>${facet('g', 'all', 'Tous côtés / All sides', group)}${M.sides.map((s) => facet('g', s.id, esc(s.lang === 'fr' ? s.label_fr : s.label_en), group)).join('')}
      ${(M.axes || []).length > 1 ? `<span style="width:12px"></span>${facet('a', 'all', 'Tous axes / All axes', axis)}${M.axes.map((x) => facet('a', x.id, `${esc(x.label_fr)} / ${esc(x.label_en)}`, axis)).join('')}` : ''}
      ${M.classement_ce ? `<span style="width:12px"></span>${facet('ce', ce ? '0' : '1', 'Classement CE', ce ? '0' : '')}` : ''}</div>
    <div id="sres"><p class="progress">Indexation… / Indexing…</p></div>${footer()}`;
  const go = (patch) => {
    const p = new URLSearchParams({ q: $('#sq').value, t: type, g: group, a: axis, ...(ce ? { ce: '1' } : {}), ...patch });
    location.hash = '#/search?' + p.toString();
  };
  $('#sform').onsubmit = (e) => { e.preventDefault(); go({}); };
  $$('.facet').forEach((b) => (b.onclick = () => go({ [b.dataset.k]: b.dataset.v })));
  await buildIndex((d, n) => { const el = $('#sres .progress'); if (el) el.textContent = `Indexation… / Indexing… ${d}/${n}`; });
  if (!q.trim()) { $('#sres').innerHTML = '<p class="note">Saisissez une requête. / Type a query. Numbers (371-1, 452.375), words (prefix match), citations, ECLI.</p>'; return; }
  const PAGE = 50;
  let offset = 0;
  const row = (terms) => ({ doc }) => {
    const href = doc.type === 'norm' ? `#/norm/${esc(doc.id)}?hl=${encodeURIComponent(terms.join(','))}` : `#/interp/${esc(doc.id)}`;
    const c = doc.corpus ? corpusMeta(doc.corpus) : null;
    return `<li><a class="rt" href="${href}">${esc(doc.title)}${doc.type === 'norm' && doc.sub ? ' — ' + esc(doc.sub) : ''}</a>
      <div class="rm"><span class="dot ${doc.group}"></span>${doc.type === 'norm' ? esc(c ? (c.lang === 'fr' ? c.label_fr : c.label_en) : doc.corpus) : esc(doc.sub) + ' · ' + fmtDate(doc.date, doc.lang)}
      <span class="badge">${doc.type === 'norm' ? 'norme' : 'interp.'}</span>${doc.fixture ? '<span class="badge fx">fixture</span>' : ''}</div>
      <p class="rs">${hlSnippet(doc.text, terms)}</p></li>`;
  };
  const first = await search(q, { type, group, axis, ce, limit: PAGE });
  $('#sres').innerHTML = `<p class="note">${first.total} résultat${first.total > 1 ? 's' : ''} / result${first.total === 1 ? '' : 's'}</p><ul class="res" id="rlist">${first.hits.map(row(first.terms)).join('')}</ul>
    ${first.total > PAGE ? '<button class="btn" type="button" id="smore">Plus de résultats / More results</button>' : ''}`;
  const more = $('#smore');
  if (more) more.onclick = async () => {
    offset += PAGE;
    const r = await search(q, { type, group, axis, ce, limit: PAGE, offset });
    $('#rlist').insertAdjacentHTML('beforeend', r.hits.map(row(r.terms)).join(''));
    if (offset + PAGE >= r.total) more.remove();
  };
}
import { highlight } from './util.js';
const hlSnippet = (text, terms) => highlight(snippet(text, terms), terms);

// ------------------------------------------------------------------ compare
function wordDiff(a, b) {
  const A = a.split(/(\s+)/).filter((x) => x !== ''), B = b.split(/(\s+)/).filter((x) => x !== '');
  const norm = (w) => w.replace(/\s+/g, ' ');
  if (A.length * B.length > 4e6) return '<p>Texte trop long pour le comparateur / Text too long to diff.</p>';
  const dp = Array.from({ length: A.length + 1 }, () => new Uint16Array(B.length + 1));
  for (let i = A.length - 1; i >= 0; i--) for (let j = B.length - 1; j >= 0; j--)
    dp[i][j] = norm(A[i]) === norm(B[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  let i = 0, j = 0, out = '', changes = 0;
  while (i < A.length && j < B.length) {
    if (norm(A[i]) === norm(B[j])) { out += esc(A[i]); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { out += `<del>${esc(A[i++])}</del>`; changes++; }
    else { out += `<ins>${esc(B[j++])}</ins>`; changes++; }
  }
  while (i < A.length) { out += `<del>${esc(A[i++])}</del>`; changes++; }
  while (j < B.length) { out += `<ins>${esc(B[j++])}</ins>`; changes++; }
  return { html: out, changes };
}
export async function viewCompare(id) {
  const r = await getNorm(id);
  if (!r) return notFound(id);
  const n = r.norm, lang = n.lang || 'fr';
  setTitle(`${t('compare', lang)} — ${normTitle(n)}`);
  revealNorm(n);
  const M = state.manifest;
  const host = hostOf(n.official_url);
  const pol = M.frame_policy?.[host] || M.frame_policy?.[host.replace(/^www\./, '')] || 'unknown';
  const fallback = `<div class="frame-fallback"><p>${t('frameDenied', lang)}</p><p class="ids">${esc(n.official_url)}</p>
    <a class="btn primary" href="${esc(n.official_url)}" target="_blank" rel="noopener">${icon.ext} ${t('newTab', lang)}</a></div>`;
  const right = !n.official_url ? '<p class="empty-state">—</p>' : pol === 'deny' ? fallback
    : `<iframe id="ofr" src="${esc(n.official_url)}" title="${esc(t('officialPage', lang))}" referrerpolicy="no-referrer" sandbox="allow-scripts allow-same-origin allow-popups allow-forms"></iframe>
       <p class="note">${t('frameMaybe', lang)} <a href="${esc(n.official_url)}" target="_blank" rel="noopener">${t('newTab', lang)} ↗</a></p>`;
  main().innerHTML = `<article lang="${esc(lang)}">${crumbsFor(n, lang)}
    <h1 class="t">${t('compare', lang)} — ${esc(normTitle(n))}</h1>
    <div class="actions"><a class="btn" href="#/norm/${esc(n.id)}">← ${t('back', lang)}</a>
      <a class="btn primary" href="${esc(n.official_url)}" target="_blank" rel="noopener">${icon.ext} ${t('openOfficial', lang)}</a>
      <span class="segmented" role="group"><button type="button" data-m="sbs" aria-pressed="true">${t('sideBySide', lang)}</button><button type="button" data-m="diff" aria-pressed="false">${t('diff', lang)}</button></span></div>
    <div id="m-sbs" class="cmp" style="margin-top:14px">
      <div class="col"><h2 class="s" style="margin-top:0">${t('projected', lang)} · ${fmtDate(n.in_force_since, lang)}</h2>${legalText(n)}</div>
      <div class="col"><h2 class="s" style="margin-top:0">${t('officialPage', lang)} · ${esc(host)}</h2>${right}</div>
    </div>
    <div id="m-diff" hidden style="margin-top:14px">
      <label class="note" for="paste">${t('pasteOfficial', lang)}</label>
      <textarea id="paste" placeholder="…"></textarea>
      <h2 class="s">${t('diffTitle', lang)}</h2><div id="dout" class="diff"></div>
    </div></article>${footer()}`;
  $$('.segmented button').forEach((b) => (b.onclick = () => {
    $$('.segmented button').forEach((x) => x.setAttribute('aria-pressed', x === b));
    $('#m-sbs').hidden = b.dataset.m !== 'sbs'; $('#m-diff').hidden = b.dataset.m !== 'diff';
  }));
  const run = debounce(() => {
    const v = $('#paste').value.trim();
    if (!v) { $('#dout').innerHTML = ''; return; }
    const d = wordDiff(String(n.text || '').replace(/\s+/g, ' ').trim(), v.replace(/\s+/g, ' '));
    $('#dout').innerHTML = typeof d === 'string' ? d : d.changes ? d.html : `<strong>${t('identical', lang)}</strong>`;
  }, 250);
  $('#paste').oninput = run;
  // If the frame never fires load within 8 s, assume it was blocked and show the fallback.
  const fr = $('#ofr');
  if (fr) {
    let loaded = false;
    fr.addEventListener('load', () => { loaded = true; });
    setTimeout(() => { if (!loaded && document.body.contains(fr)) fr.outerHTML = fallback; }, 8000);
  }
}

// ------------------------------------------------------------------ sources
export async function viewSources() {
  setTitle('Sources');
  main().innerHTML = skeleton(8);
  const d = (await getJSON('data/sources.json')) || { sources: [] };
  const rep = d.update_report;
  const statusB = (r) => {
    if (!r) return '<span class="badge">—</span>';
    const cls = { error: 'bad', changed: 'warn', blocked: 'warn', unchanged: 'ok', 'no-baseline': '', skipped: '' }[r.status] ?? '';
    return `<span class="badge ${cls}" title="${esc(r.error || r.note || '')}">${esc(r.status || (r.changed ? 'changed' : 'unchanged'))}</span>`;
  };
  const rows = d.sources.map((s) => `<tr>
    <td><strong>${esc(s.label || s.id)}</strong><div class="ids">${esc(s.id)}</div></td>
    <td>${(s.corpora || []).map((c) => `<a href="#/corpus/${esc(c)}">${esc(c)}</a>`).join(', ')}</td>
    <td><code>${esc(s.check || '')}</code><div class="ids">${esc(s.channel || '')}</div></td>
    <td>${s.official ? `<a href="${esc(s.official)}" target="_blank" rel="noopener">${esc(hostOf(s.official))} ↗</a>` : '—'}</td>
    <td>${esc(s.last_checked ? fmtDate(s.last_checked, 'en') : '—')}${s.check_result?.checked ? `<div class="ids">${esc(fmtDateTime(s.check_result.checked))}</div>` : ''}</td>
    <td class="ids">${esc(String(s.last_version ?? '—').slice(0, 16))}</td>
    <td>${statusB(s.check_result)}${s.fixture ? ' <span class="badge fx">fixture</span>' : ''}</td></tr>`).join('');
  main().innerHTML = `<h1 class="t">Sources <span class="bil">/ Sources</span></h1>
    <p class="note">Registre des sources officielles et canaux d’ingestion (data/sources*.json), vérifiés chaque semaine (le lundi) par GitHub Actions ; les changements ouvrent un ticket — aucun texte n’est réécrit automatiquement. /
    Registry of official sources and ingestion channels, checked weekly (Mondays); detected changes open an issue — legal content is never rewritten automatically.</p>
    ${rep ? `<div class="metarow"><span><span class="k">Dernier contrôle / Last check</span> <strong>${esc(fmtDateTime(rep.generated))}</strong></span><span>${rep.changed_count ?? 0} changed</span><span>${rep.error_count ?? 0} errors</span><span>${rep.blocked_count ?? 0} blocked</span></div>` : '<p class="note">Aucun rapport de contrôle encore / No update report yet (data/update-report.json).</p>'}
    ${d.sources.length ? `<div class="tbl-wrap"><table class="data"><thead><tr><th>Source</th><th>Corpus</th><th>Check / channel</th><th>Official</th><th>Last checked</th><th>Version</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="empty-state">Registre en préparation / Registry in preparation.</p>'}
    ${footer()}`;
}

// ------------------------------------------------------------------ coverage
export async function viewCoverage() {
  setTitle('Couverture / Coverage');
  main().innerHTML = skeleton(8);
  const d = (await getJSON('data/coverage.json')) || { coverage: [] };
  const M = await manifest();
  const pct = (a, b) => (b ? Math.min(100, Math.round((100 * a) / b)) : 0);
  const rows = d.coverage.map((c) => {
    const cm = corpusMeta(c.corpus);
    return `<tr><td><strong>${cm ? `<a href="#/corpus/${esc(c.corpus)}">${esc(cm.lang === 'fr' ? cm.label_fr : cm.label_en)}</a>` : esc(c.corpus)}</strong><div class="ids">${esc(c.corpus)}</div></td>
      <td class="n">${c.norms_done ?? '—'} / ${c.norms_expected ?? '—'}<div class="bar" title="${pct(c.norms_done, c.norms_expected)}%"><i style="width:${pct(c.norms_done, c.norms_expected)}%"></i></div></td>
      <td class="n">${c.interps_candidates ?? '—'}</td><td class="n">${c.interps_screened ?? '—'}<div class="bar"><i style="width:${pct(c.interps_screened, c.interps_candidates)}%"></i></div></td>
      <td class="n">${c.interps_included ?? '—'}</td>
      <td style="max-width:280px">${esc(c.method || '')}${c.gaps?.length ? `<details><summary class="note">${c.gaps.length} gap${c.gaps.length > 1 ? 's' : ''}</summary><ul>${c.gaps.map((g) => `<li>${esc(g)}</li>`).join('')}</ul></details>` : ''}</td>
      <td>${esc(c.updated ? fmtDate(c.updated, 'en') : '—')}${c.fixture ? ' <span class="badge fx">fixture</span>' : ''}</td></tr>`;
  }).join('');
  const missing = M.corpora.filter((c) => !d.coverage.find((x) => x.corpus === c.id));
  main().innerHTML = `<h1 class="t">Couverture <span class="bil">/ Coverage</span></h1>
    <p class="note">Registre honnête de complétude par corpus (data/coverage/*.json) : normes attendues vs traitées, décisions candidates, examinées, retenues ; lacunes connues. /
    Honest completeness ledger per corpus: expected vs processed norms, candidate / screened / included decisions, known gaps.</p>
    ${d.coverage.length ? `<div class="tbl-wrap"><table class="data"><thead><tr><th>Corpus</th><th>Norms done / expected</th><th>Candidates</th><th>Screened</th><th>Included</th><th>Method · gaps</th><th>Updated</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="empty-state">Aucun registre de couverture / No coverage ledger yet.</p>'}
    ${missing.length ? `<p class="note" style="margin-top:12px">Sans registre / Without ledger: ${missing.map((c) => esc(c.id)).join(', ')}</p>` : ''}
    ${footer()}`;
}
