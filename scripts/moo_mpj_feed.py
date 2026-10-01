#!/usr/bin/env python3
"""Feed gap-fill opinions (republished copies, raw/moo/proc_candidates.jsonl) into the procedural pipeline and run the
mpj screen + build through the mpj scripts. Candidate texts are scanned with mpj_common.scan_text; records (key 'rep:<docket>')
are appended to raw/mpj/cl_hits.jsonl (previous 'rep:' lines replaced; dockets already held by mpj are skipped);
mpj_build.meta_cl is wrapped so 'rep:' records get id mo-<sc|app>-proc-<docket>, official_url = courts.mo.gov (Mobar)
and text_source 'republished copy (<site>)'. Run after scripts/mpj_scan.py (which rewrites cl_hits.jsonl)."""
import json, os, re, sys
ROOT=os.environ.get('FLB_ROOT','/home/user/workspace/flb'); sys.path.insert(0,ROOT+'/scripts')
import mpj_common, mpj_screen, mpj_build
RAW=mpj_common.RAW; P=RAW+'/cl_hits.jsonl'
keep=[l for l in open(P) if not l.startswith('{"key": "rep:')]
held={re.sub(r'\D','',json.loads(l).get('docket') or '')[-6:] for l in keep}
new=[]
for l in open(ROOT+'/raw/moo/proc_candidates.jsonl'):
    c=json.loads(l); dk=re.sub(r'\D','',c['docket'])
    if dk in held: continue
    raw=open(ROOT+'/'+c['text_path'],errors='ignore').read(); meta=json.loads(raw.split('\n',1)[0][7:]); t=raw.split('\n',1)[1]
    h=mpj_common.scan_text(t)
    if not h: continue
    new.append({'key':'rep:'+c['docket'].lower(),'name':c['caseName'],'date':c['dateFiled'],'docket':c['docket'],'court_id':c['court_id'],'cites':[],
        'absolute_url':None,'download_url':c['official_url'],'local_path':None,'cl_status':'Published','status':'screened','len':len(t),'hits':h,
        'text_source':c['text_source'],'rep_url':meta.get('url'),'rep_site':meta.get('site') or 'ott.law'})
with open(P,'w') as f:
    f.writelines(keep)
    for r in new: f.write(json.dumps(r,ensure_ascii=False)+'\n')
print('rep records',len(new),flush=True)
_orig=mpj_build.meta_cl
def meta_cl(m):
    if not m['key'].startswith('rep:'): return _orig(m)
    sc=m['court_id']=='mo'; y=(m['date'] or '')[:4]; iid=('mo-sc' if sc else 'mo-app')+'-proc-'+m['docket'].lower()
    if sc: court='Supreme Court of Missouri'; paren=f'(Mo. banc {y})'
    else:
        d=mpj_build.district(m.get('docket')); court='Missouri Court of Appeals'+(mpj_build.DIST[d] if d else ''); paren=f'(Mo. App. {d+" " if d else ""}{y})'
    return iid,{'id':iid,'authority':'mo-sc' if sc else 'mo-app','court':court,'date':m['date'],'number':m['docket'],'ecli':None,
        'citation':f"{m['name']}, No. {m['docket']} {paren}",'publication':'published','official_url':m['download_url'] or m['rep_url'],
        'alt_urls':[{'label':m['rep_site']+' republished copy (full text)','url':m['rep_url']}],'text_source':m['text_source']}
mpj_build.meta_cl=meta_cl
mpj_screen.main(); mpj_build.main()

# keep the gap-fill provenance in the procedural ledger (mpj_build rewrites the file)
import json as _json, datetime as _dt, os as _os
_p=_os.path.join(_os.path.dirname(__file__),'..','data','coverage','mo-proc-interps.json')
_c=_json.load(open(_p))
_c['gapfill_feed']={"method":"Missouri Bar weekly case summaries (news.mobar.org) -> republished copies (ott.law, FindLaw, casemine, Justia) via search index; docket and date verified in text; official_url = courts.mo.gov file.jsp from the Mobar entry","script":"scripts/moo_weekly.py / scripts/moo_mpj_feed.py","updated":_dt.date.today().isoformat()}
_json.dump(_c,open(_p,'w'),ensure_ascii=False,indent=2)
