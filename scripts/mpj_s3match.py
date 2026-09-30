#!/usr/bin/env python3
"""Locate the CourtListener storage copy (pdf/<date>/<slug>.pdf or bin/<date>/<slug>.bin) of every published Missouri
cluster enumerated from bulk data (raw/mpj/bulk_clusters.jsonl), by listing the public S3 bucket per filing date
(no API quota) and matching the case-name slug; download -> pdftotext -> verify the docket number appears in the text
-> raw/mpj/text/<cluster>.txt. Appends synthesized search-style records to raw/mpj/cl_list.jsonl. Resumable."""
import json, os, re, sys, time, subprocess, datetime, urllib.request, urllib.parse, collections
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import RAW
S3 = 'https://com-courtlistener-storage.s3-us-west-2.amazonaws.com'
LD = RAW + '/s3list'; os.makedirs(LD, exist_ok=True); TD = RAW + '/text'; os.makedirs(TD, exist_ok=True)


def http(url, binary=False):
    for k in range(5):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'flb-research'}), timeout=120).read()
            return b if binary else b.decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            if e.code in (403, 404): return None
            time.sleep(5 * (k + 1))
        except Exception:
            time.sleep(5 * (k + 1))
    return None


def listing(date):
    p = f'{LD}/{date}.json'
    if os.path.exists(p): return json.load(open(p))
    keys = []
    y, m, d = date.split('-')
    for pre in (f'pdf/{y}/{m}/{d}/', f'bin/{y}/{m}/{d}/'):
        tok = None
        while True:
            q = {'list-type': '2', 'prefix': pre, 'max-keys': '1000'}
            if tok: q['continuation-token'] = tok
            x = http(S3 + '/?' + urllib.parse.urlencode(q))
            if x is None: break
            keys += re.findall(r'<Key>([^<]+)</Key>', x)
            t = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>', x)
            if not t: break
            tok = t.group(1)
    json.dump(keys, open(p, 'w')); return keys


def an(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def dnorm(s): return re.sub(r'[^A-Z0-9]', '', (s or '').upper())


STOP = {'state', 'missouri', 'interest', 'matter', 'county', 'company', 'director', 'department', 'revenue', 'social', 'services',
        'division', 'children', 'juvenile', 'officer', 'respondent', 'appellant', 'others', 'estate', 'corporation', 'insurance', 'city', 'louis', 'kansas'}


def dockets_of(s):
    return {re.sub(r'\s', '', m) for m in re.findall(r'\b(?:[EWS]D|SC)\s?\d{5,6}\b', (s or '').upper())}


def candidates(c, keys):
    names = [an(c['case_name']), an(c['case_name_full'])]
    out = []
    toks = [w for w in re.findall(r'[a-z]{4,}', (c['case_name'] or '').lower()) if w not in STOP]
    for k in keys:
        stem = re.sub(r'(_\d+)?\.(pdf|bin)$', '', k.rsplit('/', 1)[1]); sa = an(stem)
        if len(sa) < 6: continue
        for nm in names:
            if nm and (nm.startswith(sa) or sa.startswith(nm)):
                out.append(k); break
    if not out and toks:   # fallback: stems containing every distinctive surname token (docket verified after download)
        out = [k for k in keys if all(t in an(k.rsplit('/', 1)[1]) for t in toks)][:6]
    return out


def work(c):
    cid = c['id']; out = f'{TD}/{cid}.txt'
    if os.path.exists(out): return ('cached', c, open(out).readline().split('key=')[-1].strip())
    if os.path.exists(out + '.none') and '--retry-none' not in sys.argv: return ('none-cached', c, None)
    d0 = datetime.date.fromisoformat(c['date_filed'])
    dks = dockets_of(c['docket_number']) or ({dnorm(c['docket_number'])} if c['docket_number'] else set())
    for dd in (0, 1, -1, 2):
        date = (d0 + datetime.timedelta(days=dd)).isoformat()
        for k in candidates(c, listing(date)):
            b = http(f'{S3}/{k}', binary=True)
            if not b: continue
            pf = f'/tmp/mpj_s3_{cid}.pdf'; open(pf, 'wb').write(b)
            t = subprocess.run(['pdftotext', '-layout', pf, '-'], capture_output=True, text=True).stdout; os.remove(pf)
            head = dnorm(t[:6000])
            if len(t) > 500 and dks and any(x in head for x in dks) and 'MISSOURI' in head:
                open(out, 'w').write(f'##SRC cl-storage key={k}\n' + t); return ('ok', c, k)
    open(out + '.none', 'w').write('none'); return ('none', c, None)


def main():
    dk = {json.loads(l)['id']: json.loads(l) for l in open(RAW + '/bulk_dockets.jsonl')}
    cites = collections.defaultdict(list)
    if os.path.exists(RAW + '/bulk_citations.jsonl'):
        for l in open(RAW + '/bulk_citations.jsonl'):
            x = json.loads(l); cites[x['cluster_id']].append(f"{x['volume']} {x['reporter']} {x['page']}")
    cl = []
    for l in open(RAW + '/bulk_clusters.jsonl'):
        c = json.loads(l)
        if c['precedential_status'] != 'Published' or not re.match(r'\d{4}-\d\d-\d\d$', c.get('date_filed') or ''): continue
        d = dk.get(c['docket_id']) or {}
        c['docket_number'] = d.get('docket_number'); c['court_id'] = d.get('court_id'); cl.append(c)
    have = set()
    if os.path.exists(RAW + '/cl_list.jsonl'):
        for l in open(RAW + '/cl_list.jsonl'): have.add(json.loads(l)['cluster_id'])
    fl = open(RAW + '/cl_list.jsonl', 'a'); C = collections.Counter()
    print('published clusters', len(cl), flush=True)
    with ThreadPoolExecutor(4) as ex:
        for i, (st, c, k) in enumerate(ex.map(work, cl)):
            C[st] += 1
            if int(c['id']) not in have:
                fl.write(json.dumps({'cluster_id': int(c['id']), 'caseName': c['case_name'], 'dateFiled': c['date_filed'], 'docketNumber': c['docket_number'],
                                     'court_id': c['court_id'], 'citation': cites.get(c['id'], []), 'absolute_url': f"/opinion/{c['id']}/{c['slug']}/",
                                     'status': c['precedential_status'], 'via': 'bulk-' + 'data', 'opinions': [{'local_path': k, 'download_url': None}]}) + '\n'); fl.flush()
                have.add(int(c['id']))
            if i % 100 == 0: print(i, dict(C), flush=True)
    print('done', dict(C), flush=True)


if __name__ == '__main__':
    main()
