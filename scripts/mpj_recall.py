#!/usr/bin/env python3
"""Recall cross-check of the local full-text citation scan against CourtListener citation-string search
(courts mo+moctapp, published, filed >= 2019-06-01). For each string: CL count, first 2 pages of cluster ids, and the share
of those clusters (with local text) in which mpj_scan detected the norm key. Output raw/mpj/recall_check.json"""
import json, os, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import RAW
from mpj_enum import get
TESTS = [('"Rule 55.27"', 'R:55.27'), ('"Rule 74.06"', 'R:74.06'), ('"Rule 74.04"', 'R:74.04'), ('"Rule 88.01"', 'R:88.01'),
         ('"506.500"', 'S:506.500'), ('"516.120"', 'S:516.120'), ('"Rule 67.01"', 'R:67.01'), ('"512.020"', 'S:512.020')]


def main():
    hits = {}
    for l in open(RAW + '/cl_hits.jsonl'):
        x = json.loads(l); hits[x['cl']] = x
    have_text = {int(f.split('.')[0]) for f in os.listdir(RAW + '/text') if f.endswith('.txt')}
    res = []
    for q, key in TESTS:
        url = 'https://www.courtlistener.com/api/rest/v4/search/?' + urllib.parse.urlencode({'type': 'o', 'court': 'mo moctapp', 'q': q, 'filed_after': '2019-06-01', 'stat_Published': 'on'})
        ids = []; count = None
        for page in range(2):
            d = get(url); count = d.get('count'); ids += [r['cluster_id'] for r in d.get('results', [])]
            url = d.get('next'); time.sleep(3)
            if not url: break
        withtext = [i for i in ids if i in have_text]
        found = [i for i in withtext if key in ((hits.get(i) or {}).get('hits') or {})]
        local_total = sum(1 for x in hits.values() if key in (x.get('hits') or {}))
        r = {'query': q, 'key': key, 'cl_count': count, 'sampled': len(ids), 'sampled_with_local_text': len(withtext), 'detected_locally': len(found),
             'missed_ids': [i for i in withtext if i not in found], 'local_total_clusters_citing': local_total}
        print(r, flush=True); res.append(r)
    json.dump(res, open(RAW + '/recall_check.json', 'w'), indent=1)


main()
