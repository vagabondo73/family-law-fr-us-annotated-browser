#!/usr/bin/env python3
"""Enumerate Missouri (mo, moctapp) CourtListener clusters from the Free Law Project quarterly bulk data (S3,
no API quota): dockets CSV -> Missouri docket ids; opinion-clusters CSV -> clusters filed >= SINCE; citations CSV ->
reporter citations. Streams bz2 through grep (never stored). Output raw/mpj/bulk_dockets.jsonl, bulk_clusters.jsonl,
bulk_citations.jsonl.   Usage: python3 scripts/mpj_bulk.py [--date 2026-06-30] [--since 2019-06-01] [--step dockets|clusters|citations]"""
import csv, io, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import RAW
csv.field_size_limit(10**9)
B = 'https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data'
DATE = sys.argv[sys.argv.index('--date') + 1] if '--date' in sys.argv else '2026-06-30'
SINCE = sys.argv[sys.argv.index('--since') + 1] if '--since' in sys.argv else '2019-06-01'
STEP = sys.argv[sys.argv.index('--step') + 1] if '--step' in sys.argv else 'all'


def stream(name, grep_args):
    cmd = f"curl -s --retry 5 '{B}/{name}-{DATE}.csv.bz2' | bzip2 -dc | grep -a {grep_args}"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, text=True, errors='replace')
    return p


def header(name):
    out = subprocess.run(f"curl -s -r 0-300000 '{B}/{name}-{DATE}.csv.bz2' | bzip2 -dc 2>/dev/null | head -1", shell=True, capture_output=True, text=True).stdout
    return next(csv.reader([out.strip()]))


def dockets():
    H = header('dockets'); ci = H.index('court_id')
    p = stream('dockets', "-E ',\"(mo|moctapp)\",'")
    out = open(RAW + '/bulk_dockets.jsonl', 'w'); n = bad = 0
    for line in p.stdout:
        try: row = next(csv.reader([line]))
        except Exception: bad += 1; continue
        if len(row) != len(H): bad += 1; continue
        if row[ci] not in ('mo', 'moctapp'): continue
        d = dict(zip(H, row)); n += 1
        out.write(json.dumps({k: d[k] for k in ('id', 'court_id', 'docket_number', 'case_name', 'date_filed', 'slug')}) + '\n')
    print('dockets', n, 'bad', bad, flush=True)


def clusters():
    ids = [json.loads(l)['id'] for l in open(RAW + '/bulk_dockets.jsonl')]
    pf = RAW + '/bulk_docket_patterns.txt'
    open(pf, 'w').write('\n'.join(f',"{i}",' for i in ids) + '\n')
    H = header('opinion-clusters'); di = H.index('docket_id')
    p = stream('opinion-clusters', f"-F -f {pf}")
    idset = set(ids); out = open(RAW + '/bulk_clusters.jsonl', 'w'); n = bad = old = 0
    for line in p.stdout:
        try: row = next(csv.reader([line]))
        except Exception: bad += 1; continue
        if len(row) != len(H): bad += 1; continue
        d = dict(zip(H, row))
        if d['docket_id'] not in idset: continue
        if d['date_filed'] < SINCE: old += 1; continue
        n += 1
        out.write(json.dumps({k: d[k] for k in ('id', 'date_filed', 'slug', 'case_name', 'case_name_full', 'precedential_status', 'docket_id', 'source', 'judges')}) + '\n')
    print('clusters', n, 'older', old, 'bad(multiline rows skipped)', bad, flush=True)


def citations():
    ids = [json.loads(l)['id'] for l in open(RAW + '/bulk_clusters.jsonl')]
    H = header('citations'); ci = H.index('cluster_id')
    pf = RAW + '/bulk_cluster_patterns.txt'; open(pf, 'w').write('\n'.join(f',"{i}"' for i in ids) + '\n')
    p = stream('citations', f"-F -f {pf}")
    idset = set(ids); out = open(RAW + '/bulk_citations.jsonl', 'w'); n = 0
    for line in p.stdout:
        try: row = next(csv.reader([line]))
        except Exception: continue
        if len(row) != len(H): continue
        d = dict(zip(H, row))
        if d['cluster_id'] in idset:
            n += 1; out.write(json.dumps(d) + '\n')
    print('citations', n, flush=True)


def clusters_full():
    """Robust pass: full CSV parse of the cluster stream (handles multi-line quoted fields skipped by the grep pass)."""
    idset = {json.loads(l)['id'] for l in open(RAW + '/bulk_dockets.jsonl')}
    have = {json.loads(l)['id'] for l in open(RAW + '/bulk_clusters.jsonl')} if os.path.exists(RAW + '/bulk_clusters.jsonl') else set()
    cmd = f"curl -s --retry 5 '{B}/opinion-clusters-{DATE}.csv.bz2' | bzip2 -dc"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    rd = csv.reader(io.TextIOWrapper(p.stdout, encoding='utf-8', errors='replace', newline=''))
    H = next(rd); di = H.index('docket_id'); fi = H.index('date_filed')
    out = open(RAW + '/bulk_clusters.jsonl', 'a'); n = 0
    for row in rd:
        if len(row) != len(H) or row[di] not in idset or row[fi] < SINCE: continue
        d = dict(zip(H, row))
        if d['id'] in have: continue
        have.add(d['id']); n += 1
        out.write(json.dumps({k: d[k] for k in ('id', 'date_filed', 'slug', 'case_name', 'case_name_full', 'precedential_status', 'docket_id', 'source', 'judges')}) + '\n'); out.flush()
    print('clusters_full added', n, flush=True)


if STEP == 'clusters_full': clusters_full()
if STEP in ('all', 'dockets'): dockets()
if STEP in ('all', 'clusters'): clusters()
if STEP in ('all', 'citations'): citations()
