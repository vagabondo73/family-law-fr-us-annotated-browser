#!/usr/bin/env python3
"""Step 1 validation: recall of the Mobar weekly feed vs CourtListener published mo+moctapp opinions filed 2025-07-01..09-30."""
import json, re, collections, os
ROOT=os.environ.get('FLB_ROOT','/home/user/workspace/flb')
CL=json.load(open(ROOT+'/raw/moo/cl_q3_2025.json'))
E=[json.loads(l) for l in open(ROOT+'/raw/moo/mobar_entries.jsonl')]
mdk=collections.defaultdict(list)
for e in E:
    for d in e['dockets']: mdk[re.sub(r'\D','',d)].append(e)
hit=[];miss=[]
for r in CL:
    dks=re.findall(r'\d{5,6}',r.get('docketNumber') or '')
    (hit if any(d in mdk for d in dks) else miss).append(r)
weeks=sorted({e['week'] for e in E if e['week'] and re.search(r'(July|August|September).*2025',e['week'])})
q3=[e for e in E if e['week'] in weeks]
res={'courtlistener_q3_2025':len(CL),'present_in_mobar':len(hit),'recall':round(len(hit)/len(CL),3),'mobar_weeks_q3':len(weeks),
     'mobar_entries_q3':len(q3),'by_court_missing':dict(collections.Counter(r['court_id'] for r in miss)),
     'missing':[(r['docketNumber'],r['dateFiled'],r['caseName'][:60]) for r in miss],
     'mobar_mentions_84_16b':sum(1 for e in q3 if re.search(r'84\.16',e['summary'] or ''))}
json.dump(res,open(ROOT+'/raw/moo/recall_q3_2025.json','w'),indent=1); print(json.dumps({k:v for k,v in res.items() if k!='missing'})); print(res['missing'][:40])
