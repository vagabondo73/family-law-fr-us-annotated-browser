#!/usr/bin/env python3
"""Screen all candidate opinions: published check, locate perimeter-section citations, temporal rule (SCOPE §2),
extract verbatim excerpts. Output raw/moj/screen.jsonl (one line per cluster, with per-section decisions)."""
import json, os, re, sys, html, collections
ROOT='/home/user/workspace/flb'; TD=ROOT+'/raw/moj/text'
def norm(s):
    s=html.unescape(s).replace('\u00ad','').replace('\u2019',"'").replace('\u2018',"'").replace('\u201c','"').replace('\u201d','"')
    s=re.sub(r'[\u2014\u2013-]+',' ',s); s=re.sub(r'[^\w\s]',' ',s.lower()); return re.sub(r'\s+',' ',s).strip()
def body_only(t):
    t=re.sub(r'­+-{3,}.*$','',t).strip(); t=re.sub(r'-{6,}\s*$','',t).strip()
    m=re.search(r'\.\s—\s',t); return t[m.end():] if m else t
def subsections(t):
    ms=list(re.finditer(r'(?:^|\s)(\d{1,2})\.\s(?=[A-Z(])',t)); keep=[]; want=1
    for m in ms:
        if int(m.group(1))==want: keep.append(m); want+=1
    out={}
    for i,m in enumerate(keep):
        out[str(i+1)]=t[m.start():keep[i+1].start() if i+1<len(keep) else len(t)]
    return out
SEC={}   # keyed by norm id; built from data/norms/mo-rsmo.json + data/mo-history (other agent) and data/norms/mo-rules.json
for n in json.load(open(ROOT+'/data/norms/mo-rsmo.json'))['norms']:
    d={'id':n['id'],'num':n['num'],'D':n.get('in_force_since'),'nbody':norm(n.get('text') or ''),'repealed':n.get('status')!='in force','versions':[]}
    hp=ROOT+'/data/mo-history/'+n['num']+'.json'
    if os.path.exists(hp):
        for v in json.load(open(hp)).get('versions',[]):
            d['versions'].append({'eff':v.get('effective'),'end':v.get('end'),'bid':v.get('bid'),'url':v.get('url'),'identical':v.get('identical_to_current'),
                                  'changed':v.get('subsections_changed_vs_current') or [],'nbody':norm(v.get('text') or '')})
    SEC[n['num']]=d
RULE={}
for n in json.load(open(ROOT+'/data/norms/mo-rules.json'))['norms']:
    RULE[n['id']]={'id':n['id'],'num':n['num'],'D':n.get('in_force_since'),'nbody':norm(n.get('text') or ''),'repealed':False,'versions':[]}
RULEPAT=re.compile(r'(?:Rules?|Rule No\.)\s+(\d{2}\.\d{2})(?:\(([a-z0-9]{1,3})\))?')
FORMPAT=re.compile(r'Form (?:No\. )?14\b')
CITE=re.compile(r'(?<![\d.$])((?:45[1-5]|21[01]|474|565|432|193|516)\.\d{3,4})(?:\.(\d{1,2}))?(?:\((\d{1,2})\))?(?![\d])')
KEY=re.compile(r'(?i)\b(means|requires?|required|provides?|provision|mandat|interpret|plain (?:language|meaning)|legislat|statut\w*|shall|must|authori[sz]|permits?|prohibit|purpose|intent|applies|apply|construe|standard)\b')
UNPUB=re.compile(r'(?i)(memorandum supplementing order|pursuant to rule 84\.16\(b\)|order affirming judgment pursuant to rule|summary order|not an opinion of the court and shall not be (?:reported|cited))')
QUOTE=re.compile(r'["\u201c]([^"\u201c\u201d]{40,900})["\u201d]')
def sentences(t):
    # t: whitespace-preserving text; split on sentence ends
    out=[]; start=0
    for m in re.finditer(r'(?<=[a-z0-9\)\]"\u201d’][.?!])["\u201d]?\s+(?=[A-Z\u201c"(§])',t):
        out.append((start,m.end())); start=m.end()
    out.append((start,len(t))); return out
def clean(s): return re.sub(r'\s+',' ',s).strip()
def screen(cid, t, date):
    if UNPUB.search(t[:6000]) and len(t)<5000: return {'cid':cid,'status':'excluded-84.16b'}
    # remove line-number/footnote noise per page: work page by page for pdf to avoid cross-page sentences
    pages=t.split('\f')
    found=collections.defaultdict(lambda:{'n':0,'subs':set(),'sents':[]})
    for pg in pages:
        for a,b in sentences(pg):
          for s in re.split(r'(?<=[.”"])\s\.\s(?=[A-Z§“"(])', pg[a:b]):   # CAP inline footnote separators ' . '
              hitsx=[]
              for m in CITE.finditer(s):
                  if m.group(1) in SEC: hitsx.append((m.group(1),m.group(2)))
              for m in RULEPAT.finditer(s):
                  rid='mo-rules-'+m.group(1)
                  if rid in RULE: hitsx.append((rid,None))
              if FORMPAT.search(s) and 'mo-rules-form-14' in RULE: hitsx.append(('mo-rules-form-14',None))
              for sec,sub in hitsx:
                  f=found[sec]; f['n']+=1
                  if sub: f['subs'].add(sub)
                  cs=clean(s)
                  if 60<=len(cs)<=900 and cs not in [x for x,_ in f['sents']]:
                      f['sents'].append((cs, bool(KEY.search(cs)) or bool(QUOTE.search(cs))))
    full=clean(t); nfull=None
    res={'cid':cid,'status':'screened','date':date,'secs':{}}
    for sec,f in found.items():
        if (sec.startswith('mo-rules') or sec.startswith('516.')) and not any(k.split('.')[0] in ('451','452','453','454','455','210','211') for k in found if not k.startswith('mo-rules')):
            res['secs'][sec]={'norm':sec if sec.startswith('mo-rules') else 'mo-rsmo-'+sec,'decision':'excluded-not-family-case'}; continue
        S=SEC.get(sec) or RULE[sec]; dec={'norm':S['id'],'n':f['n'],'subs':sorted(f['subs'])}
        strong=[x for x,k in f['sents'] if k]
        if not (strong or f['n']>=2): dec['decision']='excluded-mention-only'; res['secs'][sec]=dec; continue
        ex=(strong+[x for x,k in f['sents'] if not k])[:3]
        dec['excerpts']=ex
        if not ex: dec['decision']='excluded-no-usable-excerpt'; res['secs'][sec]=dec; continue
        D=S['D']; dec['D']=D
        if S.get('repealed'): dec['decision']='excluded-repealed'; res['secs'][sec]=dec; continue
        if D and date>=D: dec['decision']='a'; res['secs'][sec]=dec; continue
        ver=None
        for v in S['versions']:
            if v['eff'] and v['eff']<=date and (v['end'] is None or date<v['end']): ver=v
        dec['version']=ver['bid'] if ver else None
        dec['version_eff']=ver['eff'] if ver else None
        if ver and ver.get('identical'):
            dec['decision']='b'; dec['b_how']='whole-section'; res['secs'][sec]=dec; continue
        if ver and f['subs'] and not (set(f['subs']) & set(ver['changed'])):
            dec['decision']='b'; dec['b_how']='subsection'; res['secs'][sec]=dec; continue
        # quoted statutory language near citations
        qs=[]
        pat=re.escape(S['num']) if sec in SEC else (r'Rules?\s+'+re.escape(S['num']) if not sec.startswith('mo-rules-form') else r'Form (?:No\. )?14')
        for m in re.finditer(pat, full):
            win=full[max(0,m.start()-700):m.end()+900]
            for q in QUOTE.finditer(win):
                nq=norm(q.group(1))
                if len(nq.split())>=8 and nq in S['nbody'] and (ver is None or not ver.get('nbody') or nq in ver['nbody']):
                    qs.append(q.group(1).strip())
        if qs:
            dec['decision']='b'; dec['b_how']='quoted'; dec['quoted']=list(dict.fromkeys(qs))[:3]; res['secs'][sec]=dec; continue
        dec['decision']='excluded-prior-text-not-shown-identical'; res['secs'][sec]=dec
    return res
def main():
    out=open(ROOT+'/raw/moj/screen.jsonl','w'); C=collections.Counter(); capcites={}
    for l in open(ROOT+'/raw/moj/cap_index.jsonl'):
        m=json.loads(l)
        for c in m['cites']: capcites[c]=m['fn']
    # CL hits (enumerated by citation strings via CourtListener search)
    clhits={}; groups=collections.defaultdict(set)
    for l in open(ROOT+'/raw/moj/cl/hits.jsonl'):
        r=json.loads(l); clhits.setdefault(r['cluster_id'],r); groups[r['cluster_id']].add(r['g'])
    # reuse the procedural agent's CourtListener bulk-data + API-tail set (raw/mpj, read-only): texts symlinked into raw/moj/text
    import glob as _g
    ottdk=set()
    for p in _g.glob(ROOT+'/raw/moj/ott/*.txt'):
        if os.path.basename(p).startswith('_'): continue
        m=json.loads(open(p,errors='ignore').readline()[7:])
        if m.get('docket') and re.search(r'-d?'+re.sub(r'\D','',m['docket'])+r'$',m['url'].rstrip('/')): ottdk.add(re.sub(r'\D','',m['docket']))
    mydk={re.sub(r'\D','',r.get('docketNumber') or '') for r in clhits.values()}
    for fn in ('cl_list.jsonl','cl_hits.jsonl'):
        pth=ROOT+'/raw/mpj/'+fn
        if not os.path.exists(pth): continue
        for l in open(pth):
            r=json.loads(l)
            if not r.get('cluster_id'): continue
            cid=int(r['cluster_id'])
            if cid in clhits or not r.get('dateFiled') or r.get('court_id') not in ('mo','moctapp'): continue
            dk=re.sub(r'\D','',r.get('docketNumber') or '')
            if dk and (dk in ottdk or dk in mydk): C['mpj:dup-docket']+=1; continue
            src=ROOT+f'/raw/mpj/text/{cid}.txt'; dst=f'{TD}/{cid}.txt'
            if not os.path.exists(src): C['mpj:no-text']+=1; continue
            if not os.path.exists(dst): os.symlink(src,dst)
            r['cluster_id']=cid; clhits[cid]=r; groups[cid].add('mpj-bulk'); C['mpj:added']+=1
    cap2cl={}
    for cid,r in clhits.items():
        capfn=next((capcites[c] for c in r.get('citation') or [] if c in capcites),None)
        if capfn: cap2cl[capfn]=cid; C['cl-dup-of-cap']+=1; continue
        base={'key':f'cl:{cid}','cl':cid,'groups':sorted(groups[cid]),'meta':{k:r.get(k) for k in ['caseName','dateFiled','docketNumber','court_id','citation','absolute_url','status']},
              'download_url':(r.get('opinions') or [{}])[0].get('download_url'),'local_path':(r.get('opinions') or [{}])[0].get('local_path')}
        p=f'{TD}/{cid}.txt'
        if r.get('status')!='Published': x={'status':'excluded-unpublished'}
        elif not os.path.exists(p): x={'status':'no-text'}
        else:
            raw=open(p,errors='ignore').read(); base['src']=raw.split('\n',1)[0][6:]
            x=screen(base['key'], raw.split('\n',1)[1], r['dateFiled'])
        x.update(base); C['cl:'+x['status']]+=1; out.write(json.dumps(x,ensure_ascii=False)+'\n')
    CAPD=ROOT+'/raw/moj/cap'
    for l in open(ROOT+'/raw/moj/cap_index.jsonl'):
        m=json.loads(l)
        if m['nsec']==0: continue
        raw=open(f"{CAPD}/{m['fn']}.txt",errors='ignore').read()
        body=raw.split('\n',1)[1]
        parts=re.split(r'\n\n(?=[a-z][a-z\-]* — )', body)
        keep=[p for p in parts[1:] if not re.match(r'(dissent|concurr)', p)]   # drop head matter, dissents, concurrences
        x=screen('cap:'+m['fn'], '\n\n'.join(keep) if keep else '', m['date'])
        x.update({'key':'cap:'+m['fn'],'cap':m,'cl':cap2cl.get(m['fn']),'src':'cap'}); C['cap:'+x['status']]+=1
        out.write(json.dumps(x,ensure_ascii=False)+'\n')
    # ott.law mirror pages found through the Perplexity search index (2019-2026 gap), de-duplicated by docket
    known=set()
    for r in clhits.values():
        if r.get('docketNumber'): known.add(re.sub(r'\D','',r['docketNumber']))
    for l in open(ROOT+'/raw/moj/cap_index.jsonl'):
        m=json.loads(l)
        if m.get('docket'): known.add(re.sub(r'\D','',m['docket']))
    import glob, datetime as _dt
    for p in sorted(q for q in glob.glob(ROOT+'/raw/moj/ott/*.txt') if not os.path.basename(q).startswith('_')):
        raw=open(p,errors='ignore').read(); meta=json.loads(raw.split('\n',1)[0][7:])
        dk=re.sub(r'\D','',meta.get('docket') or '')
        slugd=re.search(r'-d?(\d{5,6})$', meta['url'].rstrip('/'))
        if not dk or not (meta.get('verified_docket') or (slugd and slugd.group(1)==dk)): C['ott:docket-unverified']+=1; continue
        if dk in known or not meta.get('dates'): C['ott:dup-or-unparsed']+=1; continue
        known.add(dk)
        import collections as _c
        date=_dt.datetime.strptime(_c.Counter(meta['dates']).most_common(1)[0][0],'%B %d, %Y').date().isoformat()
        if date<'2019-01-01': C['ott:pre-2019']+=1; continue
        x=screen('ott:'+os.path.basename(p)[:-4], raw.split('\n',1)[1], date)
        x.update({'key':'ott:'+os.path.basename(p)[:-4],'ott':meta,'src':'ott'}); C['ott:'+x['status']]+=1
        out.write(json.dumps(x,ensure_ascii=False)+'\n')
    print(dict(C))
main()
