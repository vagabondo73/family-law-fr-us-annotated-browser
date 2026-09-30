// Rendering primitives: legal text, titles, badges, interpretation cards.
import { esc, fmtDate, highlight, icon } from './util.js';
import { t } from './i18n.js';

export function normTitle(n) {
  const num = n.num ?? '';
  if (n.kind === 'judge-made-rule') return n.heading || num;
  if (n.lang === 'fr') {
    if (n.kind === 'article') return `Article ${num}`;
    if (n.kind === 'treaty-article') return `Article ${num}`;
    return String(num);
  }
  if (/§|U\.S\.C|C\.F\.R|Rule|Art\./.test(num)) return num;
  if (n.kind === 'treaty-article' || n.kind === 'article') return `Article ${num}`;
  if (n.kind === 'rule') return `Rule ${num}`;
  if (n.corpus === 'mo-rsmo') return `Section ${num}, RSMo`;
  if (n.kind === 'section') return `§ ${num}`;
  return String(num);
}
export const normShort = (n) => (n.kind === 'judge-made-rule' ? n.heading : `${normTitle(n)}`);

export function statusBadge(status, lang) {
  const s = String(status || '').toLowerCase();
  const cls = /abrog|repeal|terminated|denounc|périm|expired|not in force|plus en vigueur/.test(s) ? 'bad' : /sign|pending|not.ratif|transit|différ|modifi/.test(s) ? 'warn' : /vigueur|in force|force/.test(s) ? 'ok' : '';
  return status ? `<span class="badge ${cls}" title="${t('status', lang)}">${esc(status)}</span>` : '';
}
export const fixtureBadges = (r, lang) =>
  (r.fixture ? `<span class="badge fx" title="Development fixture">${t('fixture', lang)}</span>` : '') +
  (r.fixture_unverified ? `<span class="badge fx" title="Wording not verified against the official source">${t('unverified', lang)}</span>` : '');

export function pubBadge(p) {
  if (!p) return '';
  const label = { B: 'Bulletin', P: 'Publié', R: 'Rapport', L: 'Lettre', GC: 'Grande Chambre', Lebon: 'Lebon', published: 'Published' }[p] || p;
  return `<span class="badge acc" title="Publication">${esc(label)}</span>`;
}
export function basisBadge(link, lang) {
  if (!link) return '';
  if (link.basis === 'a') return `<span class="badge ok" title="${esc(t('basisATip', lang))}">${t('basisA', lang)}</span>`;
  return `<span class="badge warn" title="${esc(t('basisBTip', lang))}">${t('basisB', lang)}${link.b_method ? ' · ' + esc(t('bMethod', lang, link.b_method)) : ''}</span>`;
}

// Detect enumerations to reproduce native indentation.
const SEQ = {
  us: [/^\([a-z]\)/, /^\(\d+\)/, /^\([A-Z]\)/, /^\((?:i|ii|iii|iv|v|vi|vii|viii|ix|x)\)/],
  mo: [/^\d+\.\s/, /^\(\d+\)/, /^\([a-z]\)/],
  def: [/^\d+\.\s/, /^(?:\(\d+\)|[a-z]\)|\([a-z]\))/, /^(?:\(i+\)|[ivx]+\))/],
};
function levelOf(line, family, prev) {
  const seq = SEQ[family] || SEQ.def;
  if (family === 'us' && /^\((?:i|v|x)\)/.test(line) && prev >= 3) return 4;
  for (let i = 0; i < seq.length; i++) if (seq[i].test(line)) return i + 1;
  return 0;
}
export function legalText(n, terms = []) {
  const family = n.corpus?.startsWith('us-') || n.corpus === 'mo-rules' ? 'us' : n.corpus?.startsWith('mo-') ? 'mo' : 'def'; // Mo. Sup. Ct. Rules follow the FRCP (a)(1)(A)(i) pattern
  const lines = String(n.text || '').split(/\n+/).map((s) => s.trim()).filter(Boolean);
  const numberAl = n.lang === 'fr';
  let prev = 0, al = 0, lastLevel = 0;
  const html = lines.map((line) => {
    const lv = levelOf(line, family, prev);
    if (lv) prev = lv;
    const cls = lv ? `l${lv}` : lastLevel ? `l${lastLevel}` : '';
    if (lv) lastLevel = lv;
    al++;
    const m = /^(\((?:\d{1,3}|[a-zA-Z]{1,4})\)|\d{1,3}\.|[a-z]\))(\s)/.exec(line);
    const body = m ? `<span class="mk">${esc(m[1])}</span>${m[2]}${highlight(line.slice(m[0].length), terms)}` : highlight(line, terms);
    return `<p class="${cls}" id="al-${al}">${numberAl ? `<span class="al" aria-hidden="true">${al}</span>` : ''}${body}</p>`;
  }).join('');
  return `<div class="legal" lang="${esc(n.lang || 'fr')}">${html || '<p>—</p>'}</div>`;
}
export function ruleText(n, terms = []) {
  // quotes marked with “ ” are verbatim case language
  const h = highlight(n.summary_rule || '', terms).replace(/“([^”]+)”/g, '“<q>$1</q>”');
  return `<div class="legal rule" lang="${esc(n.lang || 'en')}"><p>${h}</p></div>`;
}

export function linksRow(rec, lang, extra = '') {
  const alt = (rec.alt_urls || []).filter((u) => u.url).map((u) =>
    `<a class="btn sm" href="${esc(u.url)}" target="_blank" rel="noopener">${esc(u.label || u.url)} ${icon.ext}</a>`).join('');
  return `<div class="links">${rec.official_url ? `<a class="btn sm primary" href="${esc(rec.official_url)}" target="_blank" rel="noopener">${t('openOfficial', lang)} ${icon.ext}</a>` : ''}${alt}${extra}</div>`;
}

export function interpCard(it, { normId = null, open = false, terms = [], showNorms = false, normLabel = (id) => id } = {}) {
  const lang = it.lang || 'fr';
  const link = normId ? it.norms?.find((l) => l.norm === normId) : null;
  const bBlocks = (link ? [link] : it.norms || []).filter((l) => l.basis === 'b').map((l) =>
    `<div class="bjust"><b>${t('bJust', lang)}${normId ? '' : ' — ' + esc(normLabel(l.norm))}</b>${l.b_method ? ` <span class="badge warn">${esc(t('bMethod', lang, l.b_method))}</span>` : ''}<br>${esc(l.b_justification)}${l.cited_version ? `<div class="ids">${esc(l.cited_version)}</div>` : ''}</div>`).join('');
  const summ = it.summary ? `<div class="lab">${it.summary_is_official ? t('officialSummary', lang) : t('summary', lang)}</div><p class="summ">${highlight(it.summary, terms)}</p>` : '';
  const tit = it.titrage?.length ? `<div class="lab">${t('titrage', lang)}</div>${it.titrage.map((x) => `<div class="titrage">${esc(x)}</div>`).join('')}` : '';
  const ceHtml = it.classement_ce?.length ? `<div class="lab">Classement CE</div>${it.classement_ce.map((x) => `<div class="titrage">${esc(x)}</div>`).join('')}` : '';
  const ex = it.excerpts?.length ? `<div class="lab">${t('excerpts', lang)}</div>${it.excerpts.map((e) => `<blockquote lang="${esc(lang)}">${highlight(e, terms)}</blockquote>`).join('')}` : '';
  const norms = showNorms && it.norms?.length ? `<div class="lab">${t('interpreted', lang)}</div><ul class="rlist">${it.norms.map((l) =>
    `<li><a class="row" href="#/norm/${esc(l.norm)}"><span class="num">${esc(l.norm)}</span><span class="ttl">${esc(normLabel(l.norm))}</span><span class="aux">${basisBadge(l, lang)}</span></a></li>`).join('')}</ul>` : '';
  const ids = [it.number, it.ecli].filter(Boolean).map(esc).join(' · ');
  return `<details class="interp" id="i-${esc(it.id)}" data-id="${esc(it.id)}" ${open ? 'open' : ''}>
  <summary><div class="cit">${highlight(it.citation || it.id, terms)}</div>
    <div class="cmeta"><span>${esc(it.court || '')}</span><span>${fmtDate(it.date, lang)}</span>${pubBadge(it.publication)}${basisBadge(link, lang)}${fixtureBadges(it, lang)}</div></summary>
  <div class="ib">${ids ? `<div class="ids" style="margin-top:10px">${ids}</div>` : ''}${bBlocks ? `<div class="lab">${t('bJust', lang)}</div>${bBlocks}` : ''}${tit}${ceHtml}${summ}${ex}${norms}
    ${linksRow(it, lang, `<a class="btn sm" href="#/interp/${esc(it.id)}">${icon.link} Permalink</a>`)}</div>
</details>`;
}

export const skeleton = (n = 6) => `<div aria-busy="true">${'<div class="sk" style="width:' + '70%"></div>'}${Array.from({ length: n }, (_, i) => `<div class="sk" style="width:${60 + ((i * 37) % 40)}%"></div>`).join('')}</div>`;
