// Search over the PREBUILT index written by scripts/site_shards.py (build_search):
//   data/search/meta.json        {n, chunk, facets, groups, shards:{key:size}, stop}
//   data/search/p/<key>.json     {token: [doc, weight, doc, weight, …]}   key = first 2 chars of the token
//   data/search/docs/<k>.json    [[type, id, title, sub, group, src, date, fixture, lead], …]
// Only the posting shards for the query's tokens and the doc chunks of the displayed hits are fetched.
import { fold } from './util.js';
import { getJSON } from './store.js';

let STOP = new Set();
let metaP = null;
export function tokens(s) {
  const out = [];
  for (const m of fold(s).matchAll(/[a-z0-9]+(?:[-.][a-z0-9]+)*/g)) {
    const w = m[0];
    out.push(w);
    if (/[-.]/.test(w)) w.split(/[-.]/).forEach((p) => p && out.push(p));
  }
  return out;
}
const shardKey = (tk) => (tk.length >= 2 ? tk.slice(0, 2) : '_' + tk);

export function buildIndex(onProgress = () => {}) {
  if (!metaP) metaP = getJSON('data/search/meta.json').then((m) => { if (m) STOP = new Set(m.stop || []); onProgress(1, 1); return m; });
  return metaP;
}
async function postings(tk, meta) {
  const key = shardKey(tk);
  if (!(key in (meta.shards || {}))) return {};
  return (await getJSON(`data/search/p/${encodeURIComponent(key)}.json`)) || {};
}
async function docsFor(ids, meta) {
  const chunks = [...new Set(ids.map((d) => Math.floor(d / meta.chunk)))];
  const got = await Promise.all(chunks.map((k) => getJSON(`data/search/docs/${k}.json`).then((a) => [k, a || []])));
  const m = new Map(got);
  return (d) => {
    const r = m.get(Math.floor(d / meta.chunk))?.[d % meta.chunk];
    if (!r) return null;
    const [t, id, title, sub, group, src, date, fx, lead] = r;
    return { type: t ? 'interp' : 'norm', id, title, sub, group, corpus: t ? null : src, authority: t ? src : null, date, fixture: !!fx, text: lead,
      lang: group === 'us' || group === 'mo' ? 'en' : 'fr' };
  };
}
// facet char = 48 + group*16 + type*8 + axesbits*2 + ce
const facetOf = (meta, d) => meta.facets.charCodeAt(d) - 48;

export async function search(q, { type = 'all', group = 'all', axis = 'all', ce = false, limit = 50, offset = 0 } = {}) {
  const meta = await buildIndex();
  if (!meta) return { hits: [], terms: [], total: 0 };
  const qt = [...new Set(tokens(q).filter((x) => !STOP.has(x)))];
  if (!qt.length) return { hits: [], terms: [], total: 0 };
  const shards = await Promise.all(qt.map((tk) => postings(tk, meta)));
  let scores = null;
  qt.forEach((tk, i) => {
    const sh = shards[i];
    const keys = tk.length >= 2 ? Object.keys(sh).filter((k) => k.startsWith(tk)) : sh[tk] ? [tk] : [];
    const m = new Map();
    for (const k of keys) {
      const bonus = k === tk ? 2 : 1;
      const p = sh[k];
      for (let j = 0; j < p.length; j += 2) { const v = p[j + 1] * bonus; if (v > (m.get(p[j]) || 0)) m.set(p[j], v); }
    }
    if (scores === null) scores = m;
    else { const nx = new Map(); for (const [d, s] of scores) if (m.has(d)) nx.set(d, s + m.get(d)); scores = nx; }
  });
  const gi = meta.groups.indexOf(group);
  let cand = [...(scores || new Map())].filter(([d]) => {
    const f = facetOf(meta, d);
    if (gi >= 0 && (f >> 4) !== gi) return false;
    if (type !== 'all' && ((f >> 3) & 1) !== (type === 'interp' ? 1 : 0)) return false;
    if (axis !== 'all' && !(((f >> 1) & 3) & (axis === 'procedure' ? 2 : 1))) return false;
    if (ce && !(f & 1)) return false;
    return true;
  });
  const total = cand.length;
  cand.sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  // title/sub phrase bonus on a window around the requested page, then page
  const win = cand.slice(0, offset + limit + 100);
  const get = await docsFor(win.map(([d]) => d), meta);
  const fq = fold(q.trim());
  const hits = win.map(([d, s]) => {
    const doc = get(d);
    if (doc && (fold(doc.title).includes(fq) || fold(doc.sub).includes(fq))) s += 20;
    return { doc, score: s };
  }).filter((h) => h.doc);
  hits.sort((a, b) => b.score - a.score || a.doc.title.localeCompare(b.doc.title, 'fr', { numeric: true }));
  return { hits: hits.slice(offset, offset + limit), total, terms: qt };
}

export function snippet(text, terms, len = 220) {
  const s = String(text || '');
  const f = fold(s);
  let at = -1;
  for (const t of terms) { const i = f.indexOf(t); if (i !== -1 && (at === -1 || i < at)) at = i; }
  if (at === -1) return s.slice(0, len) + (s.length > len ? '…' : '');
  const start = Math.max(0, at - 70);
  return (start ? '…' : '') + s.slice(start, start + len) + (start + len < s.length ? '…' : '');
}
