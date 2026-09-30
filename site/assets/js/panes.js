// Left pane (source tree: side → corpus → hierarchy path → norm) and right pane (issue tree).
import { esc, fold, natCmp, $, $$ } from './util.js';
import { state, manifest, loadCorpus, issues, issueMembers, issueMembersAsync, corpusMeta, inAxis, corpusAxisCount, issueSideAxis, axesMeta } from './store.js';
import { normTitle } from './components.js';

// ---------------- source tree ----------------
function buildHierarchy(norms) {
  const root = { children: new Map(), norms: [] };
  for (const n of norms) {
    let node = root;
    for (const p of n.path || []) {
      const key = p.id || p.label;
      if (!node.children.has(key)) node.children.set(key, { label: p.label, key, children: new Map(), norms: [] });
      node = node.children.get(key);
    }
    node.norms.push(n);
  }
  return root;
}
const countNorms = (node) => node.norms.length + [...node.children.values()].reduce((a, c) => a + countNorms(c), 0);

function renderNode(node, depth, pathKey) {
  const kids = [...node.children.values()].map((c) => {
    const k = pathKey + '/' + c.key;
    return `<li><details data-k="${esc(k)}"><summary class="tn"><span class="chev">▶</span><span>${esc(c.label)}</span><span class="cnt">${countNorms(c)}</span></summary><ul data-lazy="${esc(k)}"></ul></details></li>`;
  }).join('');
  const leaves = node.norms.slice().sort((a, b) => natCmp(a.num, b.num)).map((n) =>
    `<li><a class="tn leaf" href="#/norm/${esc(n.id)}" data-norm="${esc(n.id)}"><span class="num">${esc(n.kind === 'judge-made-rule' ? '◆' : n.num)}</span><span class="lbl">${esc(n.heading || normTitle(n))}</span>${n.ni ? `<span class="cnt ni" title="${n.ni} interprétation(s) retenue(s) / qualifying interpretation(s)">${n.ni}</span>` : ''}</a></li>`).join('');
  return kids + leaves || '<li class="empty">—</li>';
}

const hier = new Map(); // corpus id -> hierarchy (respecting current filter)
function nodeAt(cid, k) {
  let node = hier.get(cid);
  for (const part of k.split('/').slice(2)) node = node?.children.get(part);
  return node;
}

async function fillCorpus(det) {
  const cid = det.dataset.corpus;
  const ul = det.querySelector(':scope > ul');
  if (ul.dataset.filled === '1') return;
  ul.innerHTML = '<li class="empty">…</li>';
  const c = await loadCorpus(cid);
  let norms = (c?.norms || []).filter((n) => inAxis(n));
  if (state.treeFilter) norms = norms.filter((n) => state.treeFilter.has(n.id));
  hier.set(cid, buildHierarchy(norms));
  ul.innerHTML = c ? renderNode(hier.get(cid), 0, 'c/' + cid) : '<li class="empty">Corpus indisponible / unavailable</li>';
  ul.dataset.filled = '1';
  markCurrent();
}

export async function renderTree() {
  const M = await manifest();
  const tree = $('#tree');
  hier.clear();
  const filt = state.treeFilter;
  const proc = state.axis === 'procedure';
  let html = M.sides.map((s) => {
    const cs = M.corpora.filter((c) => c.group === s.id && corpusAxisCount(c) > 0);
    if (!cs.length && state.axis !== 'family') return '';
    const label = s.lang === 'fr' ? s.label_fr : s.label_en;
    const inner = cs.length ? cs.map((c) => {
      const n = filt ? (filt.byCorpus.get(c.id) || 0) : corpusAxisCount(c);
      if (filt && !n) return '';
      const lbl = c.lang === 'fr' ? c.label_fr : c.label_en;
      return `<li><details data-corpus="${esc(c.id)}" ${filt ? 'open' : ''}><summary class="tn corpus"><span class="chev">▶</span><span>${esc(lbl)}</span><span class="cnt">${n}</span></summary><ul></ul></details></li>`;
    }).join('') : '';
    if (filt && !inner) return '';
    return `<li><details data-side="${s.id}" open><summary class="tn side"><span class="chev">▶</span><span class="dot ${s.id}"></span><span>${esc(label)}</span></summary><ul>${inner || '<li class="empty">Corpus en préparation / in preparation</li>'}</ul></details></li>`;
  }).join('');
  if (proc) {
    const maps = (M.mappings || []).map((m) => `<li><a class="tn leaf xnav" href="#/mapping/${esc(m.id)}"><span class="num">⇄</span><span class="lbl">${esc(m.label_fr)} <span class="bil">/ ${esc(m.label_en)}</span></span><span class="cnt">${m.count}</span></a></li>`).join('');
    const sb = M.sibling_browsers || {};
    const ext = [sb.cpc && `<li><a class="tn leaf xnav" href="${esc(sb.cpc)}" target="_blank" rel="noopener"><span class="num">↗</span><span class="lbl">CPC annoté <span class="bil">(site externe / external)</span></span></a></li>`,
      sb.frcp && `<li><a class="tn leaf xnav" href="${esc(sb.frcp)}" target="_blank" rel="noopener"><span class="num">↗</span><span class="lbl">FRCP annotated <span class="bil">(external)</span></span></a></li>`].filter(Boolean).join('');
    html = `<li><details data-side="xmap" open><summary class="tn side"><span class="chev">▶</span><span class="dot fr"></span><span>CPC ↔ Missouri</span></summary><ul>${maps || '<li class="empty">Table de correspondance en préparation / mapping in preparation</li>'}${ext}</ul></details></li>` + html;
  }
  tree.innerHTML = html || '<li class="empty" style="padding:12px">Aucune disposition pour ce filtre / No provision for this filter</li>';
  $$('details[data-corpus]', tree).forEach((d) => {
    d.addEventListener('toggle', () => d.open && fillCorpus(d));
    if (d.open) fillCorpus(d);
  });
  if (!tree.dataset.bound) { tree.addEventListener('toggle', onLazyToggle, true); tree.dataset.bound = '1'; }
  renderFilterChip();
}
function onLazyToggle(e) {
  const d = e.target;
  if (!(d instanceof HTMLDetailsElement) || !d.open || !d.dataset.k) return;
  const ul = d.querySelector(':scope > ul[data-lazy]');
  if (!ul || ul.dataset.filled === '1') return;
  const cid = d.dataset.k.split('/')[1];
  const node = nodeAt(cid, d.dataset.k);
  ul.innerHTML = node ? renderNode(node, 0, d.dataset.k) : '';
  ul.dataset.filled = '1';
  markCurrent();
}

export function markCurrent() {
  const cur = state.currentNorm;
  $$('#tree a.leaf[aria-current]').forEach((a) => a.removeAttribute('aria-current'));
  if (!cur) return;
  const a = $(`#tree a.leaf[data-norm="${CSS.escape(cur)}"]`);
  if (a) a.setAttribute('aria-current', 'page');
}

// Expand the tree down to a norm and scroll it into view.
export async function revealNorm(norm) {
  state.currentNorm = norm.id;
  const det = $(`#tree details[data-corpus="${CSS.escape(norm.corpus)}"]`);
  if (!det) return;
  det.closest('details[data-side]')?.setAttribute('open', '');
  if (!det.open) det.open = true;
  await fillCorpus(det);
  let k = 'c/' + norm.corpus;
  for (const p of norm.path || []) {
    k += '/' + (p.id || p.label);
    const d = $(`#tree details[data-k="${CSS.escape(k)}"]`);
    if (!d) break;
    if (!d.open) { d.open = true; onLazyToggle({ target: d }); }
  }
  markCurrent();
  const a = $(`#tree a.leaf[data-norm="${CSS.escape(norm.id)}"]`);
  if (a) {
    const pane = $('#pane-l');
    const r = a.getBoundingClientRect(), pr = pane.getBoundingClientRect();
    if (r.top < pr.top + 40 || r.bottom > pr.bottom) a.scrollIntoView({ block: 'center' });
  }
}

// ---------------- issue filter ----------------
export async function setIssueFilter(issueId) {
  if (!issueId) { state.treeFilter = null; state.activeIssue = null; }
  else {
    const I = await issues();
    const ax = I.nodes.get(issueId)?.axis;
    if (ax && ax !== state.axis) { state.activeIssue = issueId; await setAxis(ax); }
    const mem = await issueMembersAsync(I, issueId);
    const set = new Set(mem.norms.map((r) => r[0]));
    // norms cited by interpretations tagged with the issue are relevant too
    const byCorpus = new Map();
    mem.norms.forEach((r) => byCorpus.set(r[3], (byCorpus.get(r[3]) || 0) + 1));
    set.byCorpus = byCorpus;
    state.treeFilter = set;
    state.activeIssue = issueId;
  }
  await renderTree();
  highlightIssue();
}
async function renderFilterChip() {
  const box = $('#filterchip-l');
  if (!state.activeIssue) { box.innerHTML = ''; return; }
  const I = await issues();
  const n = I.nodes.get(state.activeIssue);
  box.innerHTML = `<div class="filterchip" title="${esc(n?.label || state.activeIssue)}"><span>⚑ ${esc(n?.label || state.activeIssue)}</span><button type="button" aria-label="Retirer le filtre / Clear filter">×</button></div>`;
  box.querySelector('button').onclick = () => setIssueFilter(null);
}

// ---------------- issue tree (right) ----------------
function issueNodeHtml(n, I, lang) {
  const cnt = n.count ?? (() => { const mem = issueMembers(I, n.id); return mem.norms.length + mem.interps.length; })();
  const kids = n.children || [];
  if (!kids.length) return `<li data-iid="${esc(n.id)}"><a class="tn" href="#/issue/${esc(n.id)}" data-issue="${esc(n.id)}"><span class="chev"></span><span>${esc(n.label)}</span><span class="cnt">${cnt || ''}</span></a></li>`;
  return `<li data-iid="${esc(n.id)}"><details><summary class="tn"><span class="chev">▶</span><a href="#/issue/${esc(n.id)}" data-issue="${esc(n.id)}" style="color:inherit;text-decoration:none">${esc(n.label)}</a><span class="cnt">${cnt || ''}</span></summary><ul>${kids.map((c) => issueNodeHtml(c, I, lang)).join('')}</ul></details></li>`;
}
export async function renderIssues() {
  const I = await issues();
  const M = await manifest();
  const box = $('#itree');
  const sides = I.sides.filter((s) => issueSideAxis(s) === state.axis);
  if (!sides.length) { box.innerHTML = '<p class="empty-state" style="margin:8px">Arbre des questions en préparation.<br>Issue tree in preparation.</p>'; return; }
  box.innerHTML = sides.map((s) => {
    const sm = M.sides.find((x) => x.id === (s.group || s.side));
    const label = s.label_en || s.label_fr ? (s.lang === 'fr' ? s.label_fr || s.label_en : s.label_en || s.label_fr) : sm ? (sm.lang === 'fr' ? sm.label_fr : sm.label_en) : s.side;
    const g = s.group || s.side;
    return `<details class="iside-d" data-group="${esc(g)}" open><summary class="iside"><span class="chev">▶</span><span class="dot ${esc(g)}"></span>${esc(label)}</summary><ul class="tree itree" lang="${esc(s.lang)}">${(s.nodes || []).map((n) => issueNodeHtml(n, I, s.lang)).join('')}</ul></details>`;
  }).join('');
  const inp = $('#ifilter');
  inp.oninput = () => {
    const q = fold(inp.value.trim());
    $$('#itree li[data-iid]').forEach((li) => {
      const self = fold(li.querySelector('.tn')?.textContent || '');
      const any = !q || fold(li.textContent).includes(q);
      li.hidden = !any;
      const d = li.querySelector(':scope > details');
      if (d && q) d.open = any && !self.includes(q) ? true : d.open || any;
    });
  };
  highlightIssue();
}
export function highlightIssue() {
  $$('#itree .tn.active').forEach((e) => e.classList.remove('active'));
  const id = state.activeIssue;
  if (!id) return;
  const a = $(`#itree [data-issue="${CSS.escape(id)}"]`);
  if (!a) return;
  (a.closest('.tn') || a).classList.add('active');
  let d = a.closest('details');
  while (d) { d.open = true; d = d.parentElement.closest('details'); }
}

// ---------------- axis switch ----------------
export async function setAxis(ax, { force = false } = {}) {
  if (!axesMeta().some((a) => a.id === ax)) ax = 'family';
  if (ax === state.axis && !force) return false;
  state.axis = ax;
  document.body.dataset.axis = ax;
  $$('.axis button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.axis === ax)));
  if (state.activeIssue) { const I = await issues(); if ((I.nodes.get(state.activeIssue)?.axis || 'family') !== ax) { state.activeIssue = null; state.treeFilter = null; } }
  await Promise.all([renderTree(), renderIssues()]);
  return true;
}

// Open the issue-tree section of the current norm's / decision's side, collapse the others, scroll it into view.
export function focusIssueSide(group) {
  const secs = $$('#itree details.iside-d');
  const hit = secs.find((d) => d.dataset.group === group);
  if (!hit) return;
  secs.forEach((d) => { d.open = d === hit; });
  const pane = $('#pane-r');
  const el = hit.querySelector('.tn.active') || hit;
  const top = el.getBoundingClientRect().top - pane.getBoundingClientRect().top + pane.scrollTop;
  pane.scrollTop = Math.max(0, top - (el === hit ? 96 : pane.clientHeight / 2));
}
