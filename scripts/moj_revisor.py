#!/usr/bin/env python3
"""Fetch RSMo perimeter sections + all historical versions from revisor.mo.gov (cached, resumable).
Output: raw/moj/sections.jsonl  one line per section: {sec, heading, effective, text, versions:[{bid,eff,end,text}]}"""
import re, html, json, os, time, subprocess, datetime
ROOT='/home/user/workspace/flb'; RD=ROOT+'/raw/moj/revisor'
CH={'451':None,'452':None,'453':None,'454':None,'455':None,'210':('210.817','210.854'),
    '211':('211.442','211.487'),'474':[('474.010','474.010'),('474.150','474.290')],
    '565':[('565.072','565.076'),('565.150','565.156')],'432':('432.010','432.010')}
import pplx_sdk
def prefetch(pairs):
    pairs=[(u,p) for u,p in pairs if not (os.path.exists(p) and os.path.getsize(p)>2000)]
    for i in range(0,len(pairs),25):
        b=pairs[i:i+25]
        try: res=pplx_sdk.content.fetch([u for u,_ in b], return_html=True)
        except Exception as e: print('PF ERR',e,flush=True); continue
        for (u,p),r in zip(b,res):
            h=r.raw_html or ''
            if h and 'Blocked' not in h[:3000]: open(p,'w',encoding='utf-8').write(h)
        print('prefetched',i+len(b),'/',len(pairs),flush=True)
def get(url, path):
    if not (os.path.exists(path) and os.path.getsize(path)>2000): prefetch([(url,path)])
    if os.path.exists(path) and os.path.getsize(path)>2000: return open(path,encoding='utf-8',errors='ignore').read()
    return ''
def _old_get(url, path):
    if os.path.exists(path) and os.path.getsize(path)>2000: return open(path,encoding='utf-8',errors='ignore').read()
    for k in range(4):
        r=subprocess.run(['curl','-s','-L','-m','40','-A','Mozilla/5.0 flb-research','-o',path,url])
        time.sleep(0.8)
        if os.path.exists(path) and os.path.getsize(path)>2000: return open(path,encoding='utf-8',errors='ignore').read()
        time.sleep(5*(k+1))
    return ''
def flat(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def num(sec): a,b=sec.split('.'); return (int(a), float('0.'+b))
def inr(sec,rg):
    if rg is None: return True
    if isinstance(rg,tuple): rg=[rg]
    return any(num(a)<=num(sec)<=num(b) for a,b in rg)
def mdY(s):
    m,d,y=s.split('/'); return f'{int(y):04d}-{int(m):02d}-{int(d):02d}'
def parse_text(page, sec):
    t=flat(page)
    m=re.search(r'Effective\s*-\s*([0-9]{1,2} \w{3} \d{4})', t)
    eff=datetime.datetime.strptime(m.group(1),'%d %b %Y').date().isoformat() if m else None
    i=t.find(sec+'. ', m.end() if m else 0)
    j=t.find('---- end of effective', i)
    body=t[i:j] if i>=0 else ''
    k=re.search(r'\((?:L\.|RSMo|CC|Rev) ?\d{4}', body)
    hist=''
    if k: hist=body[k.start():]; body=body[:k.start()].strip()
    # heading = up to ' — 1.' or first ' — ' followed by text
    hm=re.match(re.escape(sec)+r'\.\s*(.*?)\s—\s(?=[0-9A-Z(])', body)
    heading=hm.group(1) if hm else body[len(sec)+2:len(sec)+120]
    return eff, heading, body, hist
def versions(page, sec):
    out=[]
    for m in re.finditer(r'bid=(\d+)"[^>]*>\s*'+re.escape(sec)+r'\s*</a>\s*</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>', page):
        out.append({'bid':m.group(1),'eff':mdY(m.group(2).strip()) if m.group(2).strip() else None,'end':mdY(m.group(3).strip()) if m.group(3).strip() else None})
    return out
def main():
    done={}
    outp=ROOT+'/raw/moj/sections.jsonl'
    if os.path.exists(outp):
        for l in open(outp): d=json.loads(l); done[d['sec']]=d
    f=open(outp,'a')
    for ch,rg in CH.items():
        cp=get(f'https://revisor.mo.gov/main/OneChapter.aspx?chapter={ch}', f'{RD}/ch{ch}.html')
        secs=sorted(set(re.findall(r'section=('+ch+r'\.\d+)', cp)), key=num)
        secs=[x for x in secs if inr(x,rg)]
        prefetch([(f'https://revisor.mo.gov/main/OneSection.aspx?section={x}', f'{RD}/{x}.html') for x in secs])
        vp=[]
        for x in secs:
            p=f'{RD}/{x}.html'
            if os.path.exists(p):
                for v in versions(open(p,errors='ignore').read(),x):
                    if v['end']: vp.append((f'https://revisor.mo.gov/main/OneSection.aspx?section={x}&bid={v["bid"]}', f'{RD}/{x}_{v["bid"]}.html'))
        prefetch(vp)
        for sec in secs:
            if not inr(sec,rg) or sec in done: continue
            p=get(f'https://revisor.mo.gov/main/OneSection.aspx?section={sec}', f'{RD}/{sec}.html')
            if not p: print('FAIL',sec,flush=True); continue
            eff,heading,body,hist=parse_text(p,sec)
            vs=versions(p,sec)
            for v in vs:
                if v['end'] is None: v['text']=body; continue
                vp=get(f'https://revisor.mo.gov/main/OneSection.aspx?section={sec}&bid={v["bid"]}', f'{RD}/{sec}_{v["bid"]}.html')
                v['eff_page'],_,v['text'],_=parse_text(vp,sec) if vp else (None,None,'',None)
            rec={'sec':sec,'chapter':ch,'heading':heading,'effective':eff,'text':body,'history_note':hist[:500],'versions':vs,
                 'repealed': ('repealed' in heading.lower()) or len(body)<60}
            f.write(json.dumps(rec,ensure_ascii=False)+'\n'); f.flush(); done[sec]=rec
            print(sec,eff,len(vs),flush=True)
main()
