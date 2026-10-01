#!/usr/bin/env python3
"""Gap-fill text channel 2: CourtListener v4 search by docket number (OR-groups of 15) for Mobar-listed dockets lacking text.
Appends results (group 'moo-docket') to raw/moj/cl/hits.jsonl so scripts/moj_text.py fetches their PDFs from public storage.
Anonymous rate: 1 request / 12 s, exponential back-off on 429. Resumable via raw/moo/cl_done.txt."""
import json, os, re, time, urllib.request, urllib.parse, urllib.error
ROOT=os.environ.get('FLB_ROOT','/home/user/workspace/flb')
UA={'User-Agent':'flb-research (family-law annotated browser; polite)'}
def get(url):
    w=60
    for _ in range(8):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60))
        except urllib.error.HTTPError as e:
            if e.code==429: print('429 sleep',w,flush=True); time.sleep(w); w=min(w*2,960); continue
            raise
        except Exception as e: print('err',e,flush=True); time.sleep(30)
    return {}
st=[json.loads(l) for l in open(ROOT+'/raw/moo/text_status.jsonl')]
need=sorted({x['docket'] for x in st if x['status']=='no-copy-found'})
done=set(open(ROOT+'/raw/moo/cl_done.txt').read().split()) if os.path.exists(ROOT+'/raw/moo/cl_done.txt') else set()
need=[d for d in need if d not in done]; print('dockets',len(need),flush=True)
hf=open(ROOT+'/raw/moj/cl/hits.jsonl','a'); df=open(ROOT+'/raw/moo/cl_done.txt','a'); n=0
for i in range(0,len(need),15):
    b=need[i:i+15]
    q='docketNumber:('+' OR '.join(f'"{d[:2]}{d[2:]}" OR "{d[:2]} {d[2:]}"' for d in b)+')'
    url='https://www.courtlistener.com/api/rest/v4/search/?'+urllib.parse.urlencode({'type':'o','court':'mo moctapp','q':q,'filed_after':'2025-06-01'})
    while url:
        d=get(url)
        for r in d.get('results',[]):
            r.pop('meta',None)
            for o in r.get('opinions',[]): o.pop('snippet',None); o.pop('cites',None)
            hf.write(json.dumps({'g':'moo-docket',**r})+'\n'); n+=1
        hf.flush(); url=d.get('next'); time.sleep(12)
    for x in b: df.write(x+'\n')
    df.flush(); print('batch',i,'hits',n,flush=True)
