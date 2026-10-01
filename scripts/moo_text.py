#!/usr/bin/env python3
"""Text acquisition for Mobar-listed opinions (dated >= SINCE): dedupe by docket; skip dockets already held
(CourtListener sets raw/moj/cl + raw/mpj, CAP, ott pages); otherwise locate a republished copy on ott.law through the
Perplexity search index (docket verified against page URL and text) and store it in raw/moj/ott/ for the normal moj screen.
courts.mo.gov is never queried (robots/terms; pplx returns bad_robots_code). Writes raw/moo/text_status.jsonl. Resumable."""
import json, os, re, sys, pplx_sdk
ROOT=os.environ.get('FLB_ROOT','/home/user/workspace/flb')
sys.path.insert(0,ROOT+'/scripts'); import moj_ott
SINCE=sys.argv[1] if len(sys.argv)>1 else '2025-09-26'
AB={'Jan':'January','Feb':'February','Mar':'March','Apr':'April','Jun':'June','Jul':'July','Aug':'August','Sep':'September','Sept':'September','Oct':'October','Nov':'November','Dec':'December'}
def wk_end(e):
    import datetime as dt
    w=re.sub(r'\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)\.?(?=\s)',lambda m:AB[m.group(1)],e['week'] or '')
    m=re.search(r'([A-Z][a-z]+) (\d+)\s*[-–]\s*(?:([A-Z][a-z]+) )?(\d+)[,.]? (\d{4})',w)
    try: return dt.datetime.strptime(f"{m.group(3) or m.group(1)} {m.group(4)} {m.group(5)}",'%B %d %Y').date().isoformat()
    except (ValueError,AttributeError):   # irregular heading: fall back to the posting date in the slug (cases-MMDDYY)
        try: return (dt.datetime.strptime(e['slug'][-6:],'%m%d%y').date()-dt.timedelta(days=1)).isoformat()
        except ValueError: return None
def held():
    dk=set()
    for p in (ROOT+'/raw/moj/cl/hits.jsonl',ROOT+'/raw/mpj/cl_list.jsonl'):
        for l in open(p):
            r=json.loads(l); cid=r.get('cluster_id')
            if not cid: continue
            if os.path.exists(f"{ROOT}/raw/moj/text/{cid}.txt") or os.path.exists(f"{ROOT}/raw/mpj/text/{cid}.txt"):
                dk.add(re.sub(r'\D','',r.get('docketNumber') or ''))
    for f in os.listdir(ROOT+'/raw/moj/ott'):
        if f.startswith('_'): continue
        m=re.search(r'-d?(\d{5,6})\.txt$',f)
        if m: dk.add(m.group(1))
    return dk
def main():
    H=held(); st={}
    sp=ROOT+'/raw/moo/text_status.jsonl'
    if os.path.exists(sp):
        for l in open(sp): x=json.loads(l); st[x['docket']]=x
    ents={}
    for l in open(ROOT+'/raw/moo/mobar_entries.jsonl'):
        e=json.loads(l); we=wk_end(e)
        if not we or we<SINCE or not e['dockets']: continue
        ents.setdefault(e['dockets'][0],e)
    todo=[]
    for dk,e in ents.items():
        if re.sub(r'\D','',dk) in H: st.setdefault(dk,{'docket':dk,'status':'held'}); continue
        if dk in st and st[dk]['status']!='error': continue
        todo.append((dk,e))
    print('mobar dockets',len(ents),'todo',len(todo),flush=True)
    f=open(sp,'a')
    for i in range(0,len(todo),10):
        b=todo[i:i+10]
        try: R=pplx_sdk.search.web_many([f"{dk} {e['case_name'][:70]}" for dk,e in b],domains=['ott.law'])
        except Exception as ex: print('search err',ex,flush=True); continue
        cand={}
        for (dk,e),r in zip(b,R):
            d=re.sub(r'\D','',dk)
            cand[dk]=[h.url for h in (r.result if r.ok else []) if re.search(r'-d?'+d+r'/?$',h.url)][:1]
        urls=sorted({u for v in cand.values() for u in v})
        pages={p.url:p for p in (pplx_sdk.content.fetch(urls,return_html=True) if urls else [])}
        for dk,e in b:
            res={'docket':dk,'status':'no-copy-found','official_url':e['official_url']}
            for u in cand[dk]:
                p=pages.get(u)
                if not p or not p.raw_html: continue
                meta,t=moj_ott.parse(u,p.raw_html)
                if re.sub(r'\D','',dk) not in re.sub(r'\s','',t): continue
                meta['official']=e['official_url']; meta['mobar']={k:e[k] for k in ('week','category','heading','court','case_name')}
                slug=re.sub(r'[^a-z0-9-]','',u.rstrip('/').split('/')[-1])[:120]
                open(f"{ROOT}/raw/moj/ott/{slug}.txt",'w').write('##META '+json.dumps(meta,ensure_ascii=False)+'\n'+t)
                res={'docket':dk,'status':'ott-copy','url':u,'official_url':e['official_url']}; break
            f.write(json.dumps(res)+'\n')
        f.flush(); print('batch',i,flush=True)
    import collections; print(collections.Counter(x['status'] for x in st.values()))
if __name__=='__main__': main()
