#!/usr/bin/env python3
"""Enumerate CourtListener candidates (courts mo + moctapp) citing perimeter RSMo sections. Resumable.
Output raw/moj/cl/hits.jsonl (one line per search result per group), raw/moj/cl/enum_state.json"""
import json, os, re, time, urllib.request, urllib.parse, urllib.error, sys
ROOT='/home/user/workspace/flb'; CL=ROOT+'/raw/moj/cl'; RD=ROOT+'/raw/moj/revisor'
ORDER=['452','454','453','451','455','210','211','474','565','432']
RG={'210':[('210.817','210.854')],'211':[('211.442','211.487')],'474':[('474.010','474.010'),('474.150','474.290')],
    '565':[('565.072','565.076'),('565.150','565.156')],'432':[('432.010','432.010')]}
def num(s): a,b=s.split('.'); return (int(a), float('0.'+b))
def inr(sec,ch): return ch not in RG or any(num(a)<=num(sec)<=num(b) for a,b in RG[ch])
FILED_AFTER='2018-01-01'  # older opinions are enumerated locally from CAP full text (moj_cap.py)
UA={'User-Agent':'flb-research (family-law annotated browser; polite)'}
def get(url):
    wait=60
    while True:
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60))
        except urllib.error.HTTPError as e:
            if e.code==429 or e.code>=500:
                print('HTTP',e.code,'sleep',wait,flush=True); time.sleep(wait); wait=min(wait*2,1800); continue
            raise
        except Exception as e:
            print('ERR',e,flush=True); time.sleep(30)
def extra_groups():
    # Missouri rules / forms (family-relevant)
    return [('rules-88',['"Rule 88.01"','"Rule 88.02"','"Rule 88.03"','"Rule 88.04"','"Rule 88.05"','"Rule 88.06"','"Rule 88.07"','"Rule 88.08"','"Rule 88.09"','"Rule 88.10"','"Rule 88.11"','"Rule 88.12"','"Rule 88.13"']),
            ('form14',['"Form 14"','"Form No. 14"'])]
def groups():
    out=[]
    NN=[n['num'] for n in json.load(open(ROOT+'/data/norms/mo-rsmo.json'))['norms']]
    for ch in ORDER+['193','516']:
        p=f'{RD}/ch{ch}.html'
        if ch=='452':
            secs=sorted({s for s in re.findall(r'section=('+ch+r'\.\d+)', open(p,errors='ignore').read()) if inr(s,ch)}, key=num)
        else:
            secs=sorted({s for s in NN if s.split('.')[0]==ch}, key=num)  # perimeter from data/norms/mo-rsmo.json
        step=12 if ch=='452' else (30 if ch in ('454','453','451','455','210') else 6)  # smaller groups avoid slow/timeout queries
        for i in range(0,len(secs),step):
            chunk=secs[i:i+step]; terms=[]
            for s in chunk:
                terms.append(f'"{s}"')
                terms += [f'"{s}.{k}"' for k in range(1,13 if ch=='452' else 8)]
            out.append((f'{ch}:{chunk[0]}-{chunk[-1]}', terms))
    return out+extra_groups()
def main():
    stp=CL+'/enum_state.json'
    st=json.load(open(stp)) if os.path.exists(stp) else {}
    hf=open(CL+'/hits.jsonl','a')
    for gid,terms in groups():
        s=st.get(gid,{})
        if s.get('done'): continue
        url=s.get('next') or 'https://www.courtlistener.com/api/rest/v4/search/?'+urllib.parse.urlencode({'type':'o','court':'mo moctapp','q':' OR '.join(terms),'order_by':'dateFiled desc','filed_after':FILED_AFTER})
        while url:
            d=get(url)
            for r in d.get('results',[]):
                r.pop('meta',None)
                for o in r.get('opinions',[]): o.pop('snippet',None); o.pop('cites',None)
                hf.write(json.dumps({'g':gid,**r})+'\n')
            hf.flush()
            s={'count':d.get('count'),'next':d.get('next'),'pages':s.get('pages',0)+1}
            url=d.get('next'); s['done']= not url
            st[gid]=s; json.dump(st,open(stp,'w'))
            print(gid,s['count'],s['pages'],flush=True)
            time.sleep(6)
main()
