#!/usr/bin/env python3
"""Feed for the procedural pipeline (mpj): Rule/Form citations in gap-fill opinions (ott copies with Mobar metadata, and
any opinion dated >= SINCE in raw/moj/ott) -> raw/moo/proc_candidates.jsonl (one record per opinion)."""
import json, os, re, sys, glob, collections
ROOT=os.environ.get('FLB_ROOT','/home/user/workspace/flb'); SINCE=sys.argv[1] if len(sys.argv)>1 else '2025-10-01'
import datetime as dt
out=open(ROOT+'/raw/moo/proc_candidates.jsonl','w'); n=0
for p in sorted(glob.glob(ROOT+'/raw/moj/ott/*.txt')):
    if os.path.basename(p).startswith('_'): continue
    raw=open(p,errors='ignore').read(); m=json.loads(raw.split('\n',1)[0][7:])
    if not m.get('dates') or not m.get('docket'): continue
    date=dt.datetime.strptime(collections.Counter(m['dates']).most_common(1)[0][0],'%B %d, %Y').date().isoformat()
    if date<SINCE: continue
    rules=sorted(set(re.findall(r'\bRules?\s+(\d{2,3}\.\d{2}(?:\([a-z0-9]+\))*)',raw)))
    if not rules: continue
    out.write(json.dumps({'key':'ott:'+os.path.basename(p)[:-4],'docket':m['docket'],'court_id':'mo' if m['docket'].startswith('SC') else 'moctapp',
        'dateFiled':date,'caseName':(m.get('mobar') or {}).get('case_name') or m.get('title'),'official_url':m.get('official'),
        'text_path':os.path.relpath(p,ROOT),'text_source':'republished copy (%s)'%(m.get('site') or 'ott.law'),'rule_cites':rules,'status':'Published'})+'\n'); n+=1
print('proc candidates',n)
