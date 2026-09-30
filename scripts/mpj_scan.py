#!/usr/bin/env python3
"""Scan CourtListener opinion texts (raw/mpj/text/<cluster>.txt) for procedural-norm citations -> raw/mpj/cl_hits.jsonl"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import RAW, scan_text
UNPUB = re.compile(r'(?i)(memorandum supplementing order|pursuant to rule 84\.16\(b\)|summary order|not an opinion of the court and shall not be (?:reported|cited))')


def main():
    seen = {}
    for l in open(RAW + '/cl_list.jsonl'):
        r = json.loads(l)
        if r['cluster_id'] not in seen or not r.get('via'): seen[r['cluster_id']] = r   # API search record (has courts.mo.gov download_url) wins over bulk
    out = open(RAW + '/cl_hits.jsonl', 'w'); n = {'total': 0, 'no-text': 0, 'hits': 0, 'unpub': 0}
    for cid, r in seen.items():
        n['total'] += 1
        o = [x for x in (r.get('opinions') or [])]
        base = {'key': f'cl:{cid}', 'cl': cid, 'name': r.get('caseName'), 'date': r.get('dateFiled'), 'docket': r.get('docketNumber'),
                'court_id': r.get('court_id'), 'cites': r.get('citation') or [], 'absolute_url': r.get('absolute_url'),
                'download_url': next((x.get('download_url') for x in o if x.get('download_url')), None),
                'local_path': next((x.get('local_path') for x in o if x.get('local_path')), None), 'cl_status': r.get('status')}
        p = f'{RAW}/text/{cid}.txt'
        if r.get('status') != 'Published':
            base['status'] = 'excluded-unpublished'; n['unpub'] += 1; out.write(json.dumps(base) + '\n'); continue
        if not os.path.exists(p):
            base['status'] = 'no-text'; n['no-text'] += 1; out.write(json.dumps(base) + '\n'); continue
        raw = open(p, errors='ignore').read(); head, t = raw.split('\n', 1)
        base['src'] = head[6:]
        if 'key=' in head and not base.get('local_path'): base['local_path'] = head.split('key=', 1)[1].strip()
        if UNPUB.search(t[:6000]) and len(t) < 6000:
            base['status'] = 'excluded-84.16b-summary-order'; out.write(json.dumps(base) + '\n'); continue
        h = scan_text(t)
        if not h: continue
        base.update({'status': 'screened', 'len': len(t), 'hits': h}); n['hits'] += 1
        out.write(json.dumps(base, ensure_ascii=False) + '\n')
    print(n)


if __name__ == '__main__':
    main()
