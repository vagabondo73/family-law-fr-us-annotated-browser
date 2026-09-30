// Small helpers shared by all modules.
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const fold = (s) => String(s ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[’‘]/g, "'");
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function fmtDate(iso, lang = 'fr') {
  if (!iso) return '—';
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return esc(iso);
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.toLocaleDateString(lang === 'fr' ? 'fr-FR' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' });
}
export function fmtDateTime(iso, lang = 'en') {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d)) return esc(iso);
  return d.toLocaleString(lang === 'fr' ? 'fr-FR' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short' });
}
export const hostOf = (u) => { try { return new URL(u).hostname; } catch { return ''; } };
export function debounce(fn, ms = 150) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

// Escape `text` and wrap occurrences of folded `terms` in <mark>, preserving the original characters.
export function highlight(text, terms = []) {
  const s = String(text ?? '');
  if (!terms.length) return esc(s);
  const f = fold(s);
  const marks = [];
  for (const t of terms) {
    if (!t || t.length < 2) continue;
    let i = 0;
    while ((i = f.indexOf(t, i)) !== -1) { marks.push([i, i + t.length]); i += t.length; }
  }
  if (!marks.length) return esc(s);
  marks.sort((a, b) => a[0] - b[0]);
  let out = '', pos = 0;
  for (const [a, b] of marks) {
    if (a < pos) continue;
    out += esc(s.slice(pos, a)) + '<mark>' + esc(s.slice(a, b)) + '</mark>';
    pos = b;
  }
  return out + esc(s.slice(pos));
}

export function natCmp(a, b) {
  return String(a ?? '').localeCompare(String(b ?? ''), 'fr', { numeric: true, sensitivity: 'base' });
}

export const icon = {
  ext: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>',
  cmp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="8" height="16" rx="1"/><rect x="13" y="4" width="8" height="16" rx="1"/></svg>',
  link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></svg>',
  doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 3h9l3 3v15H6z"/><path d="M9 11h6M9 15h6"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>',
};
