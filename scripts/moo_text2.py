#!/usr/bin/env python3
"""Text channel 3: republished copies on FindLaw / casemine / Justia located via the Perplexity search index
(query = case name + docket) and read with pplx_sdk.content.fetch. Verifies the docket number in the text and picks the
filing date as the date in the text that falls within the Mobar week (week start-10d .. week end+3d).
Stores to raw/moj/ott/<site>-<docket>.txt with ##META (site, verified_docket) for the normal moj screen.
Updates raw/moo/text_status.jsonl (status 'rep-copy'). Family-category opinions first. Resumable."""
import json, os, re, sys, datetime as dt, collections, pplx_sdk
ROOT=os.environ.get('FLB_ROOT','/home/user/workspace/flb'); sys.path.insert(0,ROOT+'/scripts')
from moo_text import wk_end
SITES={'caselaw.findlaw.com':'FindLaw','www.casemine.com':'casemine','casemine.com':'casemine','law.justia.com':'Justia','missourisupremecourtopinions.justia.com':'Justia'}
MON='January|February|March|April|May|June|July|August|September|October|November|December'
sp=ROOT+'/raw/moo/text_status.jsonl'; st={}
for l in open(sp): x=json.loads(l); st[x['docket']]=x
ents={}
for l in open(ROOT+'/raw/moo/mobar_entries.jsonl'):
    e=json.loads(l)
    if e['dockets']: ents.setdefault(e['dockets'][0],e)
fam=lambda e: bool(re.search(r'family|protection|juvenile|adoption|paternity|custody|dissolution',(e['category'] or '')+' '+(e['heading'] or '')+' '+(e['summary'] or ''),re.I))
todo=[(d,ents[d]) for d,x in st.items() if x['status']=='no-copy-found' and d in ents and not x.get('rep_tried')]
todo.sort(key=lambda t: not fam(t[1])); print('todo',len(todo),'family',sum(fam(e) for _,e in todo),flush=True)
f=open(sp,'a')
for i in range(0,len(todo),10):
    b=todo[i:i+10]
    try: R=pplx_sdk.search.web_many([f"{e['case_name'][:80]} {dk}" for dk,e in b])
    except Exception as ex: print('search err',ex,flush=True); continue
    cand={dk:[h.url for h in (r.result if r.ok else []) if h.domain in SITES or any(s in h.url for s in SITES)][:2] for (dk,e),r in zip(b,R)}
    urls=sorted({u for v in cand.values() for u in v})
    try: pages={p.url:p for p in (pplx_sdk.content.fetch(urls) if urls else [])}
    except Exception as ex: print('fetch err',ex,flush=True); pages={}
    for dk,e in b:
        res={**st[dk],'rep_tried':True}
        we=wk_end(e); wd=dt.date.fromisoformat(we) if we else None
        for u in cand[dk]:
            p=pages.get(u); t=(p.content if p else '') or ''
            if len(t)<3000: continue
            dg=re.sub(r'\D','',dk)
            if not re.search(r'(?:ED|WD|SD|SC)\s?'+dg+r'\b',t) and dg not in re.sub(r'\s','',t): continue
            dates=[]
            for m in re.finditer(r'(?:%s)\.? \d{1,2},? \d{4}'%MON,t):
                try: dates.append(dt.datetime.strptime(re.sub(r'[.,]','',m.group(0)),'%B %d %Y').date())
                except ValueError: pass
            ok=[d for d in dates if wd and wd-dt.timedelta(days=17)<=d<=wd+dt.timedelta(days=3)]
            if not ok: continue
            date=collections.Counter(ok).most_common(1)[0][0]
            site=next(v for k,v in SITES.items() if k in u)
            meta={'url':u,'official':e['official_url'],'docket':dk,'dates':[date.strftime('%B %-d, %Y')],'title':e['case_name'],'site':site,
                  'verified_docket':True,'mobar':{k:e[k] for k in ('week','category','heading','court','case_name')}}
            open(f"{ROOT}/raw/moj/ott/{site.lower()}-{dk.lower()}.txt",'w').write('##META '+json.dumps(meta,ensure_ascii=False)+'\n'+t)
            res={'docket':dk,'status':'rep-copy','site':site,'url':u,'official_url':e['official_url'],'date':date.isoformat(),'rep_tried':True}; break
        f.write(json.dumps(res)+'\n'); st[dk]=res
    f.flush(); print('batch',i,collections.Counter(x['status'] for x in st.values()),flush=True)
