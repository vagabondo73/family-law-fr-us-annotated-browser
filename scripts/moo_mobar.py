#!/usr/bin/env python3
"""Discovery feed: The Missouri Bar weekly case summaries (news.mobar.org/cases-MMDDYY/), fetched through pplx_sdk.
Saves raw HTML to raw/moo/mobar/<slug>.html and parsed entries to raw/moo/mobar_entries.jsonl
(one per listed opinion: week, category, heading, summary, case_name, court, docket(s), official courts.mo.gov file.jsp URL).
Resumable: already-fetched slugs are skipped. Usage: moo_mobar.py [since YYYY-MM-DD] (default 2025-06-20)."""
import json, os, re, sys, html, datetime as dt, pplx_sdk
ROOT=os.environ.get('FLB_ROOT','/home/user/workspace/flb'); D=ROOT+'/raw/moo/mobar'; os.makedirs(D,exist_ok=True)
def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
MONTHS='January|February|March|April|May|June|July|August|September|October|November|December'
def parse(slug,h):
    title=re.search(r'Case summaries for ([^<]+?)</',h,re.I); week=clean(title.group(1)) if title else None
    out=[]; cat=None
    for m in re.finditer(r'<h2[^>]*>(.*?)</h2>|<p>(.*?)</p>',h,re.S):
        if m.group(1) is not None: cat=clean(m.group(1)); continue
        p=m.group(2)
        a=list(re.finditer(r'<a href="(https?://www\.courts\.mo\.gov/file\.jsp\?id=\d+)"[^>]*>\s*<i>(.*?)</i>\s*</a>(.*?)(?=<a href|$)',p,re.S))
        if not a: continue
        head=re.search(r'<strong>(.*?)</strong>',p,re.S)
        summ=p.split('</strong>',1)[-1].split('<a href',1)[0]
        ov=re.search(r'<a href="(https?://www\.courts\.mo\.gov/file\.jsp\?id=\d+)"[^>]*>\(Overview summary\)',p)
        for x in a:
            tail=clean(x.group(3)); court=re.split(r'\s[–-]\s',tail)[0] if tail else None
            dks=re.findall(r'\b(SC|ED|WD|SD)\s?(\d{5,6})\b',tail)
            out.append({'slug':slug,'week':week,'category':cat,'heading':clean(head.group(1)) if head else None,'summary':clean(summ),
                'case_name':clean(x.group(2)),'court_line':tail,'court':court,'dockets':[a_+b for a_,b in dks],'official_url':x.group(1),
                'overview_url':ov.group(1) if ov else None})
    return week,out
def main():
    since=dt.date.fromisoformat(sys.argv[1]) if len(sys.argv)>1 else dt.date(2025,6,20)
    today=dt.date.today(); seeds=set()
    d=since
    while d<=today+dt.timedelta(days=7):
        seeds.add(f"https://news.mobar.org/cases-{d:%m%d%y}/"); d+=dt.timedelta(days=1)
    have={f[:-5] for f in os.listdir(D) if f.endswith('.html')}
    tried=set(open(D+'/_tried2.txt').read().split()) if os.path.exists(D+'/_tried2.txt') else set()
    tf=open(D+'/_tried2.txt','a'); recent=lambda u: dt.datetime.strptime(u.rstrip('/')[-6:],'%m%d%y').date()>=today-dt.timedelta(days=21)
    frontier=sorted(u for u in seeds if u.rstrip('/').split('/')[-1] not in have and (u not in tried or recent(u)))
    while frontier:
        batch=frontier[:40]; frontier=frontier[40:]
        try: res=pplx_sdk.content.fetch(batch,return_html=True)
        except Exception as e: print('err',e,flush=True); continue
        for u,r in zip(batch,res):
            tf.write(u+'\n')
            if not r.raw_html or not re.search(r'Case summaries for',r.raw_html,re.I): continue
            slug=u.rstrip('/').split('/')[-1]; open(f'{D}/{slug}.html','w').write(r.raw_html); have.add(slug)
            for l in set(re.findall(r'href="(https://news\.mobar\.org/cases?-\d{6}/?)"',r.raw_html)):
                l=l.rstrip('/')+'/'; s=l.rstrip('/').split('/')[-1]
                try: ld=dt.datetime.strptime(s[6:],'%m%d%y').date()
                except ValueError: continue
                if ld>=since and s not in have and l not in tried and l not in frontier and l not in batch: frontier.append(l)
        tf.flush(); print('fetched',len(have),'frontier',len(frontier),flush=True)
    # complementary discovery: search-index lookup for weeks still without a page (irregular slugs such as case-101025, cases-032025)
    got=set()
    for f in os.listdir(D):
        if f.endswith('.html'):
            w,_=parse(f[:-5],open(f'{D}/{f}',errors='ignore').read()); got.add(f[:-5])
    wk=since-dt.timedelta(days=(since.weekday()-4)%7); qs=[]
    while wk<=today:
        end=wk+dt.timedelta(days=6)
        qs.append((f"Missouri Bar case summaries for {wk:%B} {wk.day}-{end.day}, {end.year}", wk)); wk+=dt.timedelta(days=7)
    covered=set()
    for f in got:
        try: covered.add(dt.datetime.strptime(f[-6:],'%m%d%y').date())
        except ValueError: pass
    need=[(q,w) for q,w in qs if not any(5<=(c-w).days<=9 for c in covered)]
    print('weeks lacking a page',len(need),flush=True)
    for i in range(0,len(need),10):
        R=pplx_sdk.search.web_many([q for q,_ in need[i:i+10]],domains=['news.mobar.org'])
        urls=sorted({h.url for r in R if r.ok for h in r.result if re.search(r'/cases?-\d{6}/?$',h.url) and h.url.rstrip('/').split('/')[-1] not in got})
        for u,r in zip(urls,pplx_sdk.content.fetch(urls,return_html=True) if urls else []):
            if r.raw_html and re.search(r'Case summaries for',r.raw_html,re.I):
                s=u.rstrip('/').split('/')[-1]; open(f'{D}/{s}.html','w').write(r.raw_html); got.add(s); print('found',s,flush=True)
    ents=[]
    for f in sorted(os.listdir(D)):
        if f.endswith('.html'): ents+=parse(f[:-5],open(f'{D}/{f}',errors='ignore').read())[1]
    with open(ROOT+'/raw/moo/mobar_entries.jsonl','w') as o:
        for e in ents: o.write(json.dumps(e,ensure_ascii=False)+'\n')
    print('weeks',len(have),'entries',len(ents))
if __name__=='__main__': main()
