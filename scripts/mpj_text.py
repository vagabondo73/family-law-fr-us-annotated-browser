#!/usr/bin/env python3
"""Fetch opinion texts for every CourtListener cluster in raw/mpj/cl_list.jsonl (resumable cache raw/mpj/text/<cluster>.txt).
Channels in order: (1) family agent's cache raw/moj/text/<cluster>.txt (read-only reuse); (2) CourtListener storage PDF
(local_path, static S3 file, not the API) -> pdftotext; (3) CourtListener REST v4 /opinions/<id>/ (plain_text/html),
<=1 req/s with backoff on 429. Lead/combined opinion only (not separate concurrences/dissents)."""
import json, os, re, sys, time, subprocess, html, urllib.request, urllib.error, threading
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import RAW, ROOT
TD = RAW + '/text'; os.makedirs(TD, exist_ok=True)
UA = {'User-Agent': 'flb-research (family-law annotated browser; polite)'}
API_LOCK = threading.Lock(); LAST = [0.0]
LEAD = ('010combined', '020lead', '015unamimous', '025plurality', '050addendum')


def http(url, binary=False, api=False):
    wait = 60
    for k in range(6):
        if api:
            with API_LOCK:
                dt = time.time() - LAST[0]
                if dt < 2.0: time.sleep(2.0 - dt)
                LAST[0] = time.time()
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
            return b if binary else b.decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 401): return None
            if e.code == 429:
                ra = e.headers.get('Retry-After'); w = int(ra) + 5 if (ra and ra.isdigit()) else wait
                print('429 sleep', w, flush=True); time.sleep(w); wait = min(wait * 2, 600); continue
            time.sleep(5 * (k + 1))
        except Exception:
            time.sleep(5 * (k + 1))
    return None


def pick(r):
    ops = r.get('opinions') or []
    lead = [o for o in ops if o.get('type') in LEAD]
    return (lead or ops or [{}])[0]


def fetch(r):
    cid = r['cluster_id']; out = f'{TD}/{cid}.txt'
    if os.path.exists(out) or os.path.exists(out + '.none'): return 'cached'
    fam = f'{ROOT}/raw/moj/text/{cid}.txt'
    if os.path.exists(fam):
        t = open(fam, errors='ignore').read()
        if t.startswith('##SRC cl-pdf'):
            open(out, 'w').write(t); return 'moj-cache'
    o = pick(r); txt = None; src = None
    if o.get('local_path'):
        b = http('https://storage.courtlistener.com/' + o['local_path'], binary=True)
        if b:
            pf = f'/tmp/mpj_{cid}.pdf'; open(pf, 'wb').write(b)
            txt = subprocess.run(['pdftotext', '-layout', pf, '-'], capture_output=True, text=True).stdout; os.remove(pf); src = 'cl-pdf'
    if not (txt and len(txt) > 500):   # storage copy by S3 listing + name match + docket verification (no API)
        import mpj_s3match
        c = {'id': str(cid), 'date_filed': r.get('dateFiled'), 'case_name': r.get('caseName'), 'case_name_full': r.get('caseNameFull') or r.get('caseName'),
             'docket_number': r.get('docketNumber')}
        st, _, k = mpj_s3match.work(c)
        if st in ('ok', 'cached'): return 's3match'
        if os.path.exists(out + '.none'): os.remove(out + '.none')
    if not (txt and len(txt) > 500) and o.get('id') and '--api-text' in sys.argv:   # REST opinions endpoint (requires auth for anonymous as of 2026-09)
        j = http(f"https://www.courtlistener.com/api/rest/v4/opinions/{o['id']}/?fields=plain_text,html_with_citations,html,xml_harvard,html_lawbox,html_columbia", api=True)
        if j:
            d = json.loads(j)
            if (d.get('plain_text') or '').strip():
                txt = d['plain_text']; src = 'cl-api-plain'
            else:
                h = d.get('html_with_citations') or d.get('html') or d.get('xml_harvard') or d.get('html_lawbox') or d.get('html_columbia') or ''
                h = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</h\d>', '\n', h)
                txt = html.unescape(re.sub(r'<[^>]+>', '', h)); src = 'cl-api-html'
    if not (txt and len(txt.strip()) > 200):
        open(out + '.none', 'w').write('none'); return 'none'
    open(out, 'w').write(f'##SRC {src} opinion={o.get("id")}\n' + txt); return src


def main():
    seen = {}
    for l in open(RAW + '/cl_list.jsonl'):
        r = json.loads(l); seen.setdefault(r['cluster_id'], r)
    todo = [r for c, r in seen.items() if not os.path.exists(f'{TD}/{c}.txt') and not os.path.exists(f'{TD}/{c}.txt.none')]
    print('todo', len(todo), 'of', len(seen), flush=True)
    import collections; C = collections.Counter()
    with ThreadPoolExecutor(3) as ex:
        for i, res in enumerate(ex.map(fetch, todo)):
            C[res] += 1
            if i % 50 == 0: print(i, dict(C), flush=True)
    print('done', dict(C), flush=True)


if __name__ == '__main__':
    main()
