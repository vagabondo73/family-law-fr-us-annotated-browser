#!/usr/bin/env python3
"""Enumerate ALL published (precedential) CourtListener opinions of courts mo + moctapp filed on/after 2019-06-01
(CAP full-text coverage ends with S.W.3d vol. 579, mid-2019). Superset of every citation-string query; screening is
done locally on full text (mpj_text.py / mpj_scan.py). Cursor pagination, polite (>=2.5 s between calls, backoff on 429).
Resumable: raw/mpj/cl_list.jsonl + raw/mpj/cl_enum_state.json.  Usage: python3 scripts/mpj_enum.py [--since YYYY-MM-DD]"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import RAW
UA = {'User-Agent': 'flb-research (family-law annotated browser; polite)'}
SINCE = sys.argv[sys.argv.index('--since') + 1] if '--since' in sys.argv else '2019-06-01'


def get(url):
    wait = 60
    while True:
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                ra = e.headers.get('Retry-After'); w = int(ra) + 5 if (ra and ra.isdigit()) else wait
                print('HTTP', e.code, 'sleep', w, flush=True); time.sleep(w); wait = min(wait * 2, 900); continue
            raise
        except Exception as e:
            print('ERR', e, flush=True); time.sleep(30)


def main():
    os.makedirs(RAW, exist_ok=True)
    stp = RAW + '/cl_enum_state.json'
    st = json.load(open(stp)) if os.path.exists(stp) else {}
    key = 'since:' + SINCE
    s = st.get(key, {})
    if s.get('done') and '--refresh' not in sys.argv: print('done', s); return
    url = s.get('next') or 'https://www.courtlistener.com/api/rest/v4/search/?' + urllib.parse.urlencode(
        {'type': 'o', 'court': 'mo moctapp', 'filed_after': SINCE, 'stat_Published': 'on', 'order_by': 'dateFiled asc'})
    f = open(RAW + '/cl_list.jsonl', 'a')
    while url:
        d = get(url)
        for r in d.get('results', []):
            r.pop('meta', None)
            for o in r.get('opinions', []): o.pop('snippet', None); o.pop('cites', None); o.pop('meta', None)
            f.write(json.dumps(r) + '\n')
        f.flush()
        s = {'count': d.get('count'), 'next': d.get('next'), 'pages': s.get('pages', 0) + 1}
        url = d.get('next'); s['done'] = not url
        st[key] = s; json.dump(st, open(stp, 'w'))
        print(key, s['count'], s['pages'], flush=True)
        time.sleep(2.5)


if __name__ == '__main__':
    main()
