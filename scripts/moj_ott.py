#!/usr/bin/env python3
"""Via the Perplexity search index + ott.law mirror pages (which link the official courts.mo.gov file.jsp PDF):
 mode 'gap'  : enumerate 2019-2026 Missouri appellate family opinions (search), fetch pages, save text to raw/moj/ott/<slug>.txt
 mode 'urls' : for included interps lacking a courts.mo.gov link (>=1997), search by case name + docket, confirm docket on page,
               record official courts.mo.gov URL in raw/moj/ott_urls.jsonl
Resumable (JSONL checkpoints). courts.mo.gov itself is never accessed (its terms prohibit automated access)."""
import json, os, re, sys, html, pplx_sdk
ROOT='/home/user/workspace/flb'; OD=ROOT+'/raw/moj/ott'; os.makedirs(OD,exist_ok=True)
def page_text(h):
    h=re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S)
    return html.unescape(re.sub(r'[ \t]+',' ',re.sub(r'<[^>]+>','\n',re.sub(r'<br\s*/?>|</p>','\n',h))))
def parse(url,h):
    t=page_text(h); flat=re.sub(r'\s+',' ',t)
    import collections as _c; off=[u for u,_ in _c.Counter(re.findall(r'https?://www\.courts\.mo\.gov/file\.jsp\?id=\d+',h)).most_common()]
    dk=re.findall(r'\b((?:ED|WD|SD|SC)\s?\d{5,6})\b',flat)
    dt=re.findall(r'(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, (?:19|20)\d\d',flat)
    title=re.search(r'<title>(.*?)</title>',h,re.S)
    return {'url':url,'official':off[0] if off else None,'docket':dk[0].replace(' ','') if dk else None,'dates':dt[:3],
            'title':html.unescape(title.group(1)).split('|')[0].strip() if title else None},t
def fetch_many(urls):
    out=[]
    for i in range(0,len(urls),40):
        try: out+=pplx_sdk.content.fetch(urls[i:i+40],return_html=True)
        except Exception as e: print('fetch err',e,flush=True)
    return out
def gap():
    seen=set(l.strip() for l in open(OD+'/_urls.txt')) if os.path.exists(OD+'/_urls.txt') else set()
    topics=["dissolution of marriage property division","maintenance spousal","child support Form 14","child custody best interests","relocation of child",
            "motion to modify custody","termination of parental rights","adoption consent","paternity","order of protection adult abuse","UCCJEA jurisdiction",
            "UIFSA foreign support order","prenuptial antenuptial agreement","separation agreement unconscionable","guardian ad litem","grandparent visitation",
            "emancipation child support","attorney fees dissolution","marital property separate property","parenting plan"]
    qs=[f"Missouri Court of Appeals {y} opinion {tp}" for y in range(2019,2027) for tp in topics]+[f"Supreme Court of Missouri {y} opinion {tp}" for y in range(2019,2027) for tp in topics[:10]]
    qdone=set(l.strip() for l in open(OD+'/_q.txt')) if os.path.exists(OD+'/_q.txt') else set()
    qf=open(OD+'/_q.txt','a'); uf=open(OD+'/_urls.txt','a')
    for i in range(0,len(qs),10):
        b=[q for q in qs[i:i+10] if q not in qdone]
        if not b: continue
        try: R=pplx_sdk.search.web_many(b, domains=['ott.law'])
        except Exception as e: print('search err',e,flush=True); continue
        new=[]
        for q,r in zip(b,R):
            if r.ok:
                for hh in r.result:
                    if '/missouri-courts/opinions/' in hh.url and hh.url not in seen: seen.add(hh.url); new.append(hh.url); uf.write(hh.url+'\n')
            qf.write(q+'\n')
        uf.flush(); qf.flush()
        for r in fetch_many(new):
            if not r.raw_html: continue
            meta,t=parse(r.url,r.raw_html)
            slug=re.sub(r'[^a-z0-9-]','',r.url.rstrip('/').split('/')[-1])[:120]
            open(f'{OD}/{slug}.txt','w').write('##META '+json.dumps(meta)+'\n'+t)
        print('gap batch',i,len(new),flush=True)
def urls():
    capid={}
    for l in open(ROOT+'/raw/moj/cap_index.jsonl'):
        m=json.loads(l); capid[str(m['id'])]=m
    outp=ROOT+'/raw/moj/ott_urls.jsonl'; done=set()
    if os.path.exists(outp):
        for l in open(outp): done.add(json.loads(l)['iid'])
    todo=[]
    for c in ('mo-sc','mo-app'):
        for r in json.load(open(f'{ROOT}/data/interps/{c}.json'))['interps']:
            if 'courts.mo.gov' in r['official_url'] or r['date']<'1997' or r['id'] in done or not r['number']: continue
            dk=re.sub(r'[^0-9]','',r['number'])
            if len(dk)<4: continue
            name=r['citation'].split(',')[0]
            todo.append((r['id'],name,dk,r['date']))
    print('url todo',len(todo),flush=True)
    f=open(outp,'a')
    for i in range(0,len(todo),10):
        b=todo[i:i+10]
        try: R=pplx_sdk.search.web_many([f"{n} {dk} Missouri" for _,n,dk,_ in b], domains=['ott.law'])
        except Exception as e: print('search err',e,flush=True); continue
        cand={}
        for (iid,n,dk,d),r in zip(b,R):
            hits=[h.url for h in (r.result if r.ok else []) if '/missouri-courts/opinions/' in h.url][:2]
            cand[iid]=hits
        pages={p.url:p for p in fetch_many(sorted({u for v in cand.values() for u in v}))}
        for iid,n,dk,d in b:
            res={'iid':iid,'official':None,'ott':None}
            for u in cand[iid]:
                p=pages.get(u)
                if not p or not p.raw_html: continue
                meta,_=parse(u,p.raw_html)
                flat=re.sub(r'\s+','',p.raw_html)
                if meta['official'] and meta['docket'] and re.sub(r'\D','',meta['docket'])==dk:
                    res={'iid':iid,'official':meta['official'],'ott':u,'docket':meta['docket']}; break
            f.write(json.dumps(res)+'\n')
        f.flush(); print('url batch',i,flush=True)
if __name__=='__main__':
    {'gap':gap,'urls':urls}[sys.argv[1]]()
