// Data access layer. Everything is lazy and tolerant: a missing file yields null / empty, never a crash.
const cache = new Map();
export async function getJSON(path) {
  if (cache.has(path)) return cache.get(path);
  const p = fetch(path, { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);
  cache.set(path, p);
  return p;
}

export const state = { manifest: null, activeIssue: null, treeFilter: null, axis: 'family' };

// ---------- axes (SCOPE §4.5): family law / comparative civil procedure ----------
export const axisOf = (n) => (n?.axes?.length ? n.axes : ['family']);
export const inAxis = (n, ax = state.axis) => axisOf(n).includes(ax);
export const axesMeta = () => state.manifest?.axes?.length ? state.manifest.axes
  : [{ id: 'family', label_fr: 'Droit de la famille', label_en: 'Family law' }];
export const corpusAxisCount = (c, ax = state.axis) => (c.axes ? c.axes[ax] || 0 : ax === 'family' ? c.norms : 0);
export const issueSideAxis = (s) => s.axis || 'family';
export const getMapping = (id) => getJSON(`data/mapping/${id}.json`);

export async function manifest() {
  if (!state.manifest) state.manifest = await getJSON('data/manifest.json');
  return state.manifest;
}

export function corpusMeta(cid) { return state.manifest?.corpora.find((c) => c.id === cid) || null; }
export function sideMeta(gid) { return state.manifest?.sides.find((s) => s.id === gid) || null; }
export function corpusOfNormId(id) {
  const ids = (state.manifest?.corpora || []).map((c) => c.id).sort((a, b) => b.length - a.length);
  return ids.find((c) => id.startsWith(c + '-')) || null;
}
export const groupOfSide = (side) => ({ fr: 'fr', eu: 'eu-int', int: 'eu-int', us: 'us', mo: 'mo' }[side] || 'eu-int');
export const groupOfAuthority = (a) => (a?.startsWith('fr-') ? 'fr' : a?.startsWith('us-') ? 'us' : a?.startsWith('mo-') ? 'mo' : 'eu-int');
export const langOfGroup = (g) => (g === 'us' || g === 'mo' ? 'en' : 'fr');

// Corpus = light index (tree + counts) + text chunks (t<k>) + interpretation chunks (i<k>), all loaded on demand.
const corpora = new Map();
export async function loadCorpus(cid) {
  if (corpora.has(cid)) return corpora.get(cid);
  const p = getJSON(`data/corpus/${cid}.json`).then((d) => {
    if (!d) return null;
    if (d.paths) d.norms.forEach((n) => { n.path = d.paths[n.p] || []; });
    d.byId = new Map(d.norms.map((n) => [n.id, n]));
    return d;
  });
  corpora.set(cid, p);
  return p;
}
async function textChunk(cid, k) {
  const d = await getJSON(`data/corpus/${cid}/t${k}.json`);
  return new Map((d?.norms || []).map((n) => [n.id, n]));
}
export async function interpChunk(cid, k) {
  if (k == null || k < 0) return {};
  const d = await getJSON(`data/corpus/${cid}/i${k}.json`);
  return d?.interps || {};
}
// light record only (tree/labels) — no text fetch
export async function getNormLight(id) {
  const cid = corpusOfNormId(id);
  if (!cid) return null;
  const c = await loadCorpus(cid);
  return c?.byId.get(id) || null;
}
// full record + the interpretations it references: { norm, corpus: { interps } }
export async function getNorm(id) {
  const cid = corpusOfNormId(id);
  if (!cid) return null;
  const c = await loadCorpus(cid);
  const light = c?.byId.get(id);
  if (!light) return null;
  if (!c.chunks) return { norm: light, corpus: c }; // legacy un-sharded bundle
  const [texts, its] = await Promise.all([textChunk(cid, light.tc), interpChunk(cid, light.ic)]);
  const full = texts.get(id) || light;
  return { norm: { ...full, ni: light.ni }, corpus: { id: cid, interps: its } };
}
export async function getInterp(id) {
  const idx = await getJSON('data/interp-index.json');
  const e = idx?.[id];
  if (!e) return null;
  const path = Array.isArray(e) ? `data/interps/${e[0]}/${e[1]}.json` : `data/interps/${e}.json`;
  const d = await getJSON(path);
  return d?.interps.find((i) => i.id === id) || null;
}
export async function interpsOf(norm, corpus) {
  return (norm.interps || []).map((i) => corpus.interps?.[i]).filter(Boolean);
}

// ---------- issues ----------
let issueCache = null;
export async function issues() {
  if (issueCache) return issueCache;
  const d = (await getJSON('data/issues.json')) || { sides: [] };
  const nodes = new Map();
  const walk = (list, parent, side, lang, axis, root) => list.forEach((n) => {
    nodes.set(n.id, { ...n, parent, side, lang, axis, root: root || n.id });
    walk(n.children || [], n.id, side, lang, axis, root || n.id);
  });
  d.sides.forEach((s) => walk(s.nodes || [], null, s.side, s.lang, s.axis || 'family', null));
  const shards = await getJSON('data/issue-shards.json');
  // legacy single index file when no shard map exists
  const index = shards ? {} : (await getJSON('data/issue-index.json')) || {};
  issueCache = { sides: d.sides, nodes, index, shards, loaded: new Set() };
  return issueCache;
}
// load the index shard(s) needed for an issue id (its top-level node; undeclared ids fall back to the longest declared prefix)
export async function ensureIssueIndex(I, id) {
  if (!I.shards) return;
  const parts = String(id).split('.');
  let root = null;
  for (let j = parts.length; j > 0 && !root; j--) root = I.nodes.get(parts.slice(0, j).join('.'))?.root || null;
  const keys = [root && I.shards[root] ? root : '_orphans'];
  await Promise.all(keys.filter((k) => I.shards[k] && !I.loaded.has(k)).map(async (k) => {
    const d = await getJSON(`data/issue-index/${I.shards[k]}.json`);
    Object.assign(I.index, d || {});
    I.loaded.add(k);
  }));
}
export async function issueMembersAsync(I, id) { await ensureIssueIndex(I, id); return issueMembers(I, id); }
export function issueAncestors(I, id) {
  const out = [];
  let n = I.nodes.get(id);
  while (n) { out.unshift(n); n = n.parent ? I.nodes.get(n.parent) : null; }
  return out;
}
export function issueDescendants(I, id) {
  const out = [id];
  const n = I.nodes.get(id);
  (n?.children || []).forEach((c) => out.push(...issueDescendants(I, c.id)));
  return out;
}
// norms/interps tagged with the issue or any descendant (also: tagged with an undeclared deeper id sharing the prefix)
export function issueMembers(I, id) {
  const ids = new Set(issueDescendants(I, id));
  Object.keys(I.index).forEach((k) => { if (k.startsWith(id + '.')) ids.add(k); });
  const norms = new Map(), interps = new Map();
  ids.forEach((k) => {
    (I.index[k]?.norms || []).forEach((r) => norms.set(r[0], r));
    (I.index[k]?.interps || []).forEach((r) => interps.set(r[0], r));
  });
  return { norms: [...norms.values()], interps: [...interps.values()], ids };
}
export const inIssue = (tagged, ids) => (tagged || []).some((x) => ids.has(x) || [...ids].some((i) => x.startsWith(i + '.')));
