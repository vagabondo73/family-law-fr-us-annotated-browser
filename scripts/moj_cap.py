#!/usr/bin/env python3
"""Local full-text enumeration over Caselaw Access Project (static.case.law) S.W.2d (1-999) and S.W.3d (1-579):
download each volume zip, keep Missouri cases citing perimeter chapters or family-doctrine keywords. Resumable.
Output: raw/moj/cap/<rep>_<vol>_<file>.txt (text with ##META header), raw/moj/cap_index.jsonl, raw/moj/cap_done.txt"""
import json, os, re, io, zipfile, urllib.request, time, sys
from concurrent.futures import ThreadPoolExecutor
ROOT='/home/user/workspace/flb'; CD=ROOT+'/raw/moj/cap'; os.makedirs(CD,exist_ok=True)
CITE=re.compile(r'(?<![\d.$])(?:45[1-5]|21[01]|474|565|432)\.\d{3,4}')
KW=re.compile(r'(?i)antenuptial|prenuptial|premarital agreement|postnuptial|separation agreement|marital property|separate property|dissolution of marriage|divorce|maintenance|child support|custody|comity|paternity|adoption|termination of parental rights|conflict of laws|restatement \(second\)')
def vol(job):
    rep,v=job
    for k in range(4):
        try:
            b=urllib.request.urlopen(urllib.request.Request(f'https://static.case.law/{rep}/{v}.zip',headers={'User-Agent':'flb-research'}),timeout=120).read(); break
        except urllib.error.HTTPError as e:
            if e.code==404: return (job,'404',0)
            time.sleep(10*(k+1))
        except Exception: time.sleep(10*(k+1))
    else: return (job,'fail',0)
    z=zipfile.ZipFile(io.BytesIO(b)); idx=[]
    for n in z.namelist():
        if not n.startswith('json/'): continue
        d=json.loads(z.read(n))
        if (d.get('jurisdiction') or {}).get('name')!='Mo.': continue
        cb=d.get('casebody') or {}
        ops=cb.get('opinions') or []
        text='\n\n'.join([cb.get('head_matter') or '']+[(o.get('type','')+' — '+(o.get('author') or '')+'\n'+(o.get('text') or '')) for o in ops])
        cites=CITE.findall(text); kws=len(KW.findall(text))
        if not cites and kws<3: continue
        fn=f'{rep}_{v}_{n[5:-5]}'
        meta={'fn':fn,'id':d['id'],'name':d.get('name_abbreviation'),'full_name':d.get('name'),'date':d.get('decision_date'),'docket':d.get('docket_number'),
              'cites':[c['cite'] for c in d.get('citations',[])],'court':(d.get('court') or {}).get('name'),'first_page':d.get('first_page'),'rep':rep,'vol':v,
              'nsec':len(cites),'kw':kws}
        open(f'{CD}/{fn}.txt','w').write('##META '+json.dumps(meta)+'\n'+text); idx.append(meta)
    return (job,'ok',idx)
def main():
    donep=ROOT+'/raw/moj/cap_done.txt'; done=set(open(donep).read().split()) if os.path.exists(donep) else set()
    jobs=[('sw3d',v) for v in range(1,580)]+[('sw2d',v) for v in range(999,0,-1)]+[('mo',v) for v in range(340,366)]+[('mo-app',v) for v in range(231,242)]
    jobs=[j for j in jobs if f'{j[0]}/{j[1]}' not in done]
    fi=open(ROOT+'/raw/moj/cap_index.jsonl','a'); fd=open(donep,'a')
    with ThreadPoolExecutor(4) as ex:
        for job,st,idx in ex.map(vol,jobs):
            if st in ('ok','404'):
                for m in (idx or []): fi.write(json.dumps(m)+'\n')
                fi.flush(); fd.write(f'{job[0]}/{job[1]}\n'); fd.flush()
            print(job,st,len(idx) if idx else 0,flush=True)
main()
