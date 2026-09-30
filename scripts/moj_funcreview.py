#!/usr/bin/env python3
"""Functional review (SCOPE §2 (b), b_method functional-review) of pre-D links that failed the text-identity test but
for which the version in force at the opinion date is available in data/mo-history. LLM-assisted (pplx_sdk.llm.extract);
resumable output raw/moj/funcreview.jsonl keyed by (key, section)."""
import json, os, re, sys, pplx_sdk
ROOT='/home/user/workspace/flb'
def flat(s): return re.sub(r'\s+',' ',s or '').strip()
def subsections(t):
    t=flat(t); ms=list(re.finditer(r'(?:^|\s)(\d{1,2})\.\s(?=[A-Z(])',t)); keep=[]; want=1
    for m in ms:
        if int(m.group(1))==want: keep.append(m); want+=1
    if not keep: return {'whole':t}
    return {str(i+1):t[m.start():keep[i+1].start() if i+1<len(keep) else len(t)].strip() for i,m in enumerate(keep)}
CUR={n['num']:n for n in json.load(open(ROOT+'/data/norms/mo-rsmo.json'))['norms']}
def hist(num):
    p=f'{ROOT}/data/mo-history/{num}.json'
    return {v['bid']:v for v in json.load(open(p))['versions']} if os.path.exists(p) else {}
outp=ROOT+'/raw/moj/funcreview.jsonl'
done=set()
if os.path.exists(outp):
    for l in open(outp): d=json.loads(l); done.add((d['key'],d['sec']))
items=[]
for l in open(ROOT+'/raw/moj/screen.jsonl'):
    x=json.loads(l)
    for sec,d in x.get('secs',{}).items():
        if d['decision']!='excluded-prior-text-not-shown-identical' or not d.get('version') or (x['key'],sec) in done: continue
        v=hist(sec).get(d['version'])
        if not v: continue
        old=subsections(v.get('text')); new=subsections(CUR[sec]['text'])
        changed=sorted(set(v.get('subsections_changed_vs_current') or []) | ({k for k in set(old)|set(new) if old.get(k)!=new.get(k)}), key=lambda k:(len(k),k))
        cited=[s for s in d['subs']] or []
        comp={k:{'version_at_opinion_date':(old.get(k) or '(absent)')[:3000],'current':(new.get(k) or '(absent)')[:3000]} for k in (cited or changed)[:6]}
        items.append({'key':x['key'],'sec':sec,'date':x['date'],'version':d['version'],'version_eff':v.get('effective'),'D':d['D'],
            'cited_subsections':cited,'changed_subsections':changed,'excerpts':d.get('excerpts',[])[:3],'compare':comp,'n_old_subs':len(old),'n_new_subs':len(new)})
print('todo',len(items),flush=True)
INSTR=("You review whether a Missouri appellate opinion's interpretation of an RSMo section still applies to the CURRENT text. "
 "Given the opinion date, the opinion's excerpts citing the section, the subsections it cites (may be empty), and the text of the relevant/changed "
 "subsections in the version in force at the opinion date vs the current version: (1) identify which subsection(s) the opinion interprets (use the excerpts; "
 "if none cited, infer from content, or 'unclear'); (2) decide include=true ONLY if the interpreted language is identical in wording and function in the current text "
 "(differences limited to other subsections, renumbering, cross-reference updates, gender-neutral or stylistic edits, or additions that do not alter the interpreted rule). "
 "include=false if the interpreted language was changed in substance, or if you cannot tell which language was interpreted. "
 "reason: 1-3 precise English sentences naming the subsection(s) compared and what did or did not change (quote at most a few words).")
SCHEMA={'type':'object','properties':{'include':{'type':'boolean'},'interpreted_subsections':{'type':'array','items':{'type':'string'}},
  'renumbered_to':{'type':'string'},'reason':{'type':'string'}},'required':['include','interpreted_subsections','reason']}
f=open(outp,'a')
for i in range(0,len(items),40):
    b=items[i:i+40]
    try: res=pplx_sdk.llm.extract(items=[json.dumps(it,ensure_ascii=False) for it in b],instruction=INSTR,output_schema=SCHEMA,max_tokens=16384)
    except Exception as e: print('ERR',e,flush=True); continue
    for it,r in zip(b,res):
        if r.error: continue
        f.write(json.dumps({'key':it['key'],'sec':it['sec'],'version':it['version'],'version_eff':it['version_eff'],'D':it['D'],'cited':it['cited_subsections'],
            'compare':it['compare'],**r.result},ensure_ascii=False)+'\n')
    f.flush(); print('batch',i+len(b),'/',len(items),flush=True)
