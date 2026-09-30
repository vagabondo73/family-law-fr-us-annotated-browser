#!/usr/bin/env python3
"""Fetch opinion texts for all candidate clusters (resumable cache raw/moj/text/<cluster>.txt).
Channels: CourtListener storage PDF (local_path) -> pdftotext; else Caselaw Access Project static.case.law (S.W.2d/S.W.3d)."""
import json, os, re, subprocess, time, urllib.request, sys
from concurrent.futures import ThreadPoolExecutor
ROOT='/home/user/workspace/flb'; TD=ROOT+'/raw/moj/text'; os.makedirs(TD,exist_ok=True); MD=ROOT+'/raw/moj/capmeta'; os.makedirs(MD,exist_ok=True)
UA={'User-Agent':'flb-research'}
import threading; LOCK=threading.Lock()
def http(url, binary=False):
    for k in range(3):
        try:
            b=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read()
            return b if binary else b.decode('utf-8','ignore')
        except urllib.error.HTTPError as e:
            if e.code in (403,404): return None
            time.sleep(5*(k+1))
        except Exception: time.sleep(5*(k+1))
    return None
def capmeta(rep,vol):
    p=f'{MD}/{rep}_{vol}.json'
    with LOCK:
        if os.path.exists(p):
            try: return json.load(open(p))
            except Exception: pass
        t=http(f'https://static.case.law/{rep}/{vol}/CasesMetadata.json')
        d=json.loads(t) if t else []
        json.dump(d,open(p+'.tmp','w')); os.replace(p+'.tmp',p); return d
def fetch(r):
    try: return _fetch(r)
    except Exception as e: print('ERR',r.get('cluster_id'),e,flush=True); return 'err'
def _fetch(r):
    cid=r['cluster_id']; out=f'{TD}/{cid}.txt'
    if os.path.exists(out): return 'cached'
    o=(r.get('opinions') or [{}])[0]
    txt=None; src=None
    if o.get('local_path'):
        b=http('https://storage.courtlistener.com/'+o['local_path'],binary=True)
        if b:
            pf=f'/tmp/moj_{cid}.pdf'; open(pf,'wb').write(b)
            txt=subprocess.run(['pdftotext','-layout',pf,'-'],capture_output=True,text=True,timeout=60).stdout; os.remove(pf); src='cl-pdf'
    if not txt:
        for c in r.get('citation') or []:
            m=re.match(r'(\d+) S\.W\.(2d|3d) (\d+)$',c)
            if not m: continue
            rep='sw'+m.group(2); meta=capmeta(rep,m.group(1))
            cs=[x for x in meta if x['first_page']==m.group(3) and x['jurisdiction']['name']=='Mo.']
            if not cs: continue
            j=http(f'https://static.case.law/{rep}/{m.group(1)}/cases/{cs[0]["file_name"]}.json')
            if not j: continue
            d=json.loads(j); cb=d.get('casebody',{})
            parts=[cb.get('head_matter','')]+[ (op.get('type','')+' '+(op.get('author') or '')+'\n'+op.get('text','')) for op in cb.get('opinions',[])]
            txt='\n\n'.join(parts); src=f'cap:{rep}/{m.group(1)}/{cs[0]["file_name"]}'; break
    if not txt: open(out+'.none','w').write('none'); return 'none'
    open(out,'w').write(f'##SRC {src}\n'+txt); return src.split(':')[0]
def main():
    seen={}; 
    for l in open(ROOT+'/raw/moj/cl/hits.jsonl'):
        r=json.loads(l); seen.setdefault(r['cluster_id'],r)
    todo=[r for c,r in seen.items() if not os.path.exists(f'{TD}/{c}.txt') and not os.path.exists(f'{TD}/{c}.txt.none')]
    print('todo',len(todo),'of',len(seen),flush=True)
    import collections; C=collections.Counter()
    with ThreadPoolExecutor(3) as ex:
        for i,res in enumerate(ex.map(fetch,todo)):
            C[res]+=1
            if i%50==0: print(i,dict(C),flush=True)
    print('done',dict(C),flush=True)
main()
