#!/usr/bin/env python3
"""Verify every quoted segment of each mo-common summary_rule appears verbatim in one of its rule_sources texts."""
import json,re,sys
ROOT='/home/user/workspace/flb'
def txt(k):
    p=f"{ROOT}/raw/moj/cap/{k[4:]}.txt" if k.startswith('cap:') else f"{ROOT}/raw/moj/text/{k[3:]}.txt"
    s=open(p,errors='ignore').read()
    if k.startswith('cap:'):
        parts=re.split(r'\n\n(?=[a-z][a-z\-]* — )', s.split('\n',1)[1])
        s='\n\n'.join(p for p in parts[1:] if not re.match(r'(dissent|concurr)',p))
    return s
def n(s): return re.sub(r'\s+',' ',re.sub(r'[“”"‘’\']','',s)).strip().lower()
meta={json.loads(l)['fn']:json.loads(l) for l in open(ROOT+'/raw/moj/cap_index.jsonl')}
hits={}
for l in open(ROOT+'/raw/moj/cl/hits.jsonl'):
    r=json.loads(l); hits[str(r['cluster_id'])]=r
bad=0
for r in json.load(open(ROOT+'/raw/moj/common_rules.json')):
    T=' '.join(n(txt(k)) for k in r['sources'])
    for k in r['sources']:
        m=meta.get(k[4:]) if k.startswith('cap:') else hits.get(k[3:])
        print('  ',k, (m.get('name'),m.get('date'),m.get('court')) if k.startswith('cap:') else (m['caseName'],m['dateFiled'],m['court_id']))
    segs=[s for s in re.split(r'[“”]',r['summary_rule'])]
    for i,s in enumerate(segs):
        if i%2==1 or True:
            ss=n(s).strip(' .,;()')
            if len(ss)<25 or '(' in s[:2]: continue
            if ss not in T and i%2==1: print('MISSING',r['id'],'|',s[:120]); bad+=1
print('bad',bad)
