#!/usr/bin/env python3
"""Find verbatim candidate sentences for Missouri judge-made family-law rules in local texts (CAP + CL)."""
import json, re, os, sys, glob
ROOT='/home/user/workspace/flb'
Q=json.load(open(sys.argv[1]))   # {topic: [regex,...]}
docs=[]
for l in open(ROOT+'/raw/moj/cap_index.jsonl'):
    m=json.loads(l); docs.append(('cap:'+m['fn'], m['date'], m['court'], m['name'], (m['cites'] or [''])[0], f"{ROOT}/raw/moj/cap/{m['fn']}.txt"))
hits={}
for l in open(ROOT+'/raw/moj/cl/hits.jsonl'):
    r=json.loads(l); hits[r['cluster_id']]=r
for cid,r in hits.items():
    p=f'{ROOT}/raw/moj/text/{cid}.txt'
    if os.path.exists(p) and not (r.get('citation') and any('S.W.' in c for c in r['citation']) and r['dateFiled']<'2019-08'):
        docs.append(('cl:'+str(cid), r['dateFiled'], r['court_id'], r['caseName'], (r.get('citation') or [''])[0], p))
out={}
for topic,pats in Q.items():
    rx=[re.compile(p, re.I) for p in pats]; res=[]
    for key,date,court,name,cite,p in docs:
        t=re.sub(r'\s+',' ',open(p,errors='ignore').read())
        for r in rx:
            for m in r.finditer(t):
                a=max(t.rfind('. ',0,m.start()-1),0); b=t.find('. ',m.end()); b=len(t) if b<0 else b+1
                res.append({'key':key,'date':date,'court':court,'name':name,'cite':cite,'sent':t[a+2 if a else 0:b][:700]}); break
    out[topic]=res
    print(topic,len(res),flush=True)
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False,indent=0)
