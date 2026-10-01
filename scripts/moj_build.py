#!/usr/bin/env python3
"""Build data/interps/mo-sc.json, data/interps/mo-app.json and coverage ledgers from raw/moj/screen.jsonl."""
import json, os, re, collections, datetime
ROOT='/home/user/workspace/flb'
NORMS={n['id']:n for f in ('mo-rsmo','mo-rules') for n in json.load(open(f'{ROOT}/data/norms/{f}.json'))['norms']}
BYNUM={n['num']:n for n in NORMS.values() if n['corpus']=='mo-rsmo'}
def nid(k): return k if k.startswith('mo-rules') else BYNUM[k]['id']
def district(text, docket, court):
    s=(docket or '')+' '+(court or '')+' '+text[:3000]
    for pat,d in ((r'\bWD\s?\d|WESTERN DISTRICT|Western District','W.D.'),(r'\bED\s?\d|EASTERN DISTRICT|Eastern District','E.D.'),(r'\bSD\s?\d|SOUTHERN DISTRICT|Southern District','S.D.')):
        if re.search(pat,s): return d
    return None
REP={'sw2d':'S.W.2d','sw3d':'S.W.3d','mo':'Mo.','mo-app':'Mo. App.'}
def rec_for(x):
    if x['key'].startswith('cap:'):
        m=x['cap']; text=open(f"{ROOT}/raw/moj/cap/{m['fn']}.txt",errors='ignore').read()
        sc='Supreme Court' in (m['court'] or ''); name=m['name']; date=m['date']; docket=m['docket']
        cites=m['cites']; court_raw=m['court']
        vol,rep=m['vol'],m['rep']; fp=m['first_page']; fn=m['fn'].split('_',2)[2]
        caseurl=f'https://static.case.law/{rep}/{vol}/cases/{fn}.json'
        cl_c=f'https://www.courtlistener.com/c/{REP[rep]}/{vol}/{fp}/'
        official=cl_c; alts=[{'label':'Caselaw Access Project (Harvard) — case JSON','url':caseurl}]
        if x.get('cl'): alts.append({'label':'CourtListener','url':f"https://www.courtlistener.com/opinion/{x['cl']}/"})
        iid=('mo-sc' if sc else 'mo-app')+'-cap'+str(m['id'])
    elif x['key'].startswith('ott:'):
        m=x['ott']; text=open(f"{ROOT}/raw/moj/ott/{x['key'][4:]}.txt",errors='ignore').read()
        sc=(m['docket'] or '').startswith('SC'); name=m['title']; date=x['date']; docket=m['docket']; cites=[]; court_raw=None
        official=m['official'] or m['url']; alts=[{'label':(m['site']+' republished copy (full text)') if m.get('site') else 'Ott Law Firm mirror (full text)','url':m['url']}]
        if m.get('mobar'): alts.append({'label':'The Missouri Bar weekly case summary','url':'https://news.mobar.org/'})
        iid=('mo-sc' if sc else 'mo-app')+'-'+docket.lower()
    else:
        m=x['meta']; text=open(f"{ROOT}/raw/moj/text/{x['cl']}.txt",errors='ignore').read()
        sc=m['court_id']=='mo'; name=m['caseName']; date=m['dateFiled']; docket=m['docketNumber']; cites=m.get('citation') or []; court_raw=None
        clurl='https://www.courtlistener.com'+m['absolute_url']
        du=x.get('download_url') or ''
        official=du if 'courts.mo.gov' in du else clurl
        alts=[{'label':'CourtListener','url':clurl}]
        if x.get('local_path'): alts.append({'label':'CourtListener PDF copy','url':'https://storage.courtlistener.com/'+x['local_path']})
        iid=('mo-sc' if sc else 'mo-app')+'-cl'+str(x['cl'])
    y=date[:4]
    if sc: court='Supreme Court of Missouri'; paren=f'(Mo. banc {y})'
    else:
        d=district(text,docket,court_raw)
        if court_raw and not court_raw.startswith('Missouri Court of Appeals'): court=court_raw; paren=f'(Mo. App. {y})'
        else: court='Missouri Court of Appeals'+({'W.D.':', Western District','E.D.':', Eastern District','S.D.':', Southern District'}[d] if d else ''); paren=f'(Mo. App. {d+" " if d else ""}{y})'
    sw=[c for c in cites if 'S.W.' in c]
    cit=f"{name}, {sw[0] if sw else ('No. '+docket if docket else '')} {paren}".replace('  ',' ')
    return iid, sc, {'id':iid,'authority':'mo-sc' if sc else 'mo-app','court':court,'date':date,'number':docket or None,'ecli':None,
            'citation':cit,'publication':'published','official_url':official,'alt_urls':alts}
FR={}
if os.path.exists(ROOT+'/raw/moj/funcreview.jsonl'):
    for l in open(ROOT+'/raw/moj/funcreview.jsonl'):
        r=json.loads(l); FR[(r['key'],r['sec'])]=r
_fr_mod={}
def _subs(num,bid):
    import importlib.util
    if 'm' not in _fr_mod:
        src=open(ROOT+'/scripts/moj_funcreview.py').read().split("outp=ROOT")[0]; ns={}; exec(src,ns); _fr_mod['m']=ns
    ns=_fr_mod['m']
    cur=ns['subsections'](ns['CUR'][num]['text']); old=ns['subsections']((ns['hist'](num).get(bid) or {}).get('text'))
    return old,cur
def fr_eval(num,fr):
    subs=[re.sub(r'[^0-9a-z]','',s.split('(')[0].split('.')[-1] if '.' in s else s.split('(')[0]) for s in fr.get('interpreted_subsections') or []]
    subs=[s for s in subs if s and s!='unclear']
    if not subs: return {'status':'excluded-unclear-subsection'}
    old,cur=_subs(num,fr['version'])
    if not all(s in old and s in cur for s in subs): return {'status':'excluded-subsection-not-found'}
    n=lambda s: re.sub(r'\W+',' ',s.lower()).strip()
    base={'subs':subs,'old':{s:old[s] for s in subs},'new':{s:cur[s] for s in subs},'reason':fr.get('reason','')}
    if all(n(old[s])==n(cur[s]) for s in subs): return {**base,'status':'include-ti'}
    return {**base,'status':'include-fr' if fr.get('include') else 'excluded-changed-in-substance'}
def main():
    out={'mo-sc':[], 'mo-app':[]}; led=collections.defaultdict(lambda:collections.Counter()); bynorm=collections.defaultdict(list)
    cand=collections.Counter(); scr=collections.Counter()
    for l in open(ROOT+'/raw/moj/screen.jsonl'):
        x=json.loads(l)
        if x.get('status')!='screened':
            led['_all'][x.get('status')]+=1; continue
        norms=[]; ex=[]; issues=[]
        for k,d in x['secs'].items():
            ch='rules' if k.startswith('mo-rules') else k.split('.')[0]
            led[ch]['candidate-links']+=1; led[ch][d['decision']]+=1
            if d['decision']=='excluded-prior-text-not-shown-identical' and (x['key'],k) in FR:
                fr=FR[(x['key'],k)]; v=fr_eval(k,fr)
                led[ch]['funcreview:'+v['status']]+=1
                if v['status'] in ('include-fr','include-ti'):
                    d=dict(d); d['decision']='b'; d['b_how']=v['status']; d['fr']=v
            if d['decision'] not in ('a','b'): continue
            n=NORMS[nid(k)]
            e={'norm':n['id'],'basis':d['decision']}
            if d.get('version'): e['cited_version']='revisor bid '+str(d['version'])
            if d['decision']=='b':
                e['b_method']='text-identical'
                if d['b_how'] in ('include-fr','include-ti'):
                    v=d['fr']; e['b_method']='functional-review' if d['b_how']=='include-fr' else 'text-identical'
                    comp='; '.join(f"subsection {s}: version text “{v['old'][s][:220]}{'…' if len(v['old'][s])>220 else ''}” / current text “{v['new'][s][:220]}{'…' if len(v['new'][s])>220 else ''}”" for s in v['subs'])
                    e['b_justification']=(f"{'Functional review' if d['b_how']=='include-fr' else 'Subsection comparison'}: the opinion ({x['date']}) applied § {n['num']} RSMo as in force from {d.get('version_eff')} (revisor bid {d.get('version')}); current text in force since {d['D']}. "
                        f"Interpreted subsection(s) identified from the opinion: {', '.join(v['subs'])}. Compared {comp}. "
                        + ("The compared subsection text is identical; later amendments concern other subsections. " if d['b_how']=='include-ti' else "")
                        + (v['reason'] if d['b_how']=='include-fr' else ''))
                elif d['b_how']=='subsection':
                    e['b_justification']=(f"The opinion ({x['date']}) applied § {n['num']} RSMo as in force from {d.get('version_eff')} (revisor bid {d.get('version')}) and cites subsection(s) "
                        f"{', '.join(d['subs'])}; the revisor version comparison (data/mo-history) shows these subsections unchanged in the current text in force since {d['D']}, so the interpreted language is identical in wording and function.")
                elif d['b_how']=='whole-section':
                    e['b_justification']=f"The version of § {n['num']} in force at the date of the opinion ({x['date']}; revisor bid {d.get('version')}) is identical to the current text in force since {d['D']} (data/mo-history identical_to_current)."
                else:
                    q=d['quoted'][0]
                    e['b_justification']=(f"The opinion ({x['date']}) predates the current version of {('§ '+n['num']+' RSMo') if n['corpus']=='mo-rsmo' else n['num']} (in force since {d['D']}) but quotes the statutory/rule language it interprets — “{q}” — "
                        "and that language appears verbatim in the current text"+(" and in the version in force at the date of the opinion" if d.get('version') else "")+"; the interpreted language is therefore identical in wording and function.")
            norms.append(e); ex+= [(n['id'],s) for s in d['excerpts']]
            issues+= n.get('issues') or []
        if not norms: continue
        iid,sc,r=rec_for(x)
        # excerpts: round-robin across norms, max 4
        seen=[]; per=collections.defaultdict(list)
        for k,s in ex: per[k].append(s)
        while len(seen)<4 and any(per.values()):
            for k in list(per):
                if per[k] and len(seen)<4:
                    s=per[k].pop(0)
                    if s not in seen: seen.append(s)
        lab=', '.join(('§ '+NORMS[e['norm']]['num']) if NORMS[e['norm']]['corpus']=='mo-rsmo' else NORMS[e['norm']]['num'] for e in norms[:6])
        r.update({'summary':f"{r['court']} opinion applying or construing {lab}{' RSMo' if any(NORMS[e['norm']]['corpus']=='mo-rsmo' for e in norms) else ''} (neutral index summary; see excerpts).",
                  'summary_is_official':False,'excerpts':seen,'titrage':[],'norms':norms,'issues':sorted(set(issues)),'lang':'en'})
        out[r['authority']].append(r)
        for e in norms: bynorm[e['norm']].append(iid)
    # de-duplicate CourtListener duplicate clusters of the same opinion (same docket + date)
    for c,L in out.items():
        g=collections.defaultdict(list)
        for r in L:
            if r['number']: g[(re.sub(r'\D','',r['number'])[-6:], r['date'])].append(r)
        drop=set()
        for v in g.values():
            cl=[r for r in v if '-cl' in r['id']]
            if len(v)>1 and cl:
                keep=sorted(v,key=lambda r:('-cap' not in r['id'], 'courts.mo.gov' not in r['official_url']))[0]
                for r in v:
                    if r is keep or '-cl' not in r['id']: continue
                    for e in r['norms']:
                        if not any(e['norm']==k['norm'] for k in keep['norms']): keep['norms'].append(e)
                    keep['alt_urls'].append({'label':'CourtListener (duplicate cluster)','url':r['alt_urls'][0]['url']})
                    drop.add(r['id'])
        out[c]=[r for r in L if r['id'] not in drop]
        for k in bynorm: bynorm[k]=[i for i in bynorm[k] if i not in drop]
    add_common(out,bynorm)
    # text_source for republished copies; official courts.mo.gov URLs from The Missouri Bar weekly summaries (by docket)
    MB={}
    if os.path.exists(ROOT+'/raw/moo/mobar_entries.jsonl'):
        for l in open(ROOT+'/raw/moo/mobar_entries.jsonl'):
            e=json.loads(l)
            for d in e['dockets']: MB.setdefault(re.sub(r'\D','',d),e)
    for L in out.values():
        for r in L:
            if any('Ott Law Firm mirror (full text)'==a['label'] for a in r['alt_urls']): r['text_source']='republished copy (ott.law)'
            for a in r['alt_urls']:
                if a['label'].endswith(' republished copy (full text)'): r['text_source']='republished copy (%s)'%a['label'].split(' republished')[0]
            e=MB.get(re.sub(r'\D','',r['number'] or '')[-6:]) or MB.get(re.sub(r'\D','',r['number'] or ''))
            if e and 'courts.mo.gov' not in r['official_url'] and r['date']>='2019-01-01':
                r['alt_urls']=[{'label':'CourtListener / mirror','url':r['official_url']}]+r['alt_urls']; r['official_url']=e['official_url']
    # official courts.mo.gov URLs confirmed via search-index hits on ott.law (docket verified on the page)
    if os.path.exists(ROOT+'/raw/moj/ott_urls.jsonl'):
        OU={}
        for l in open(ROOT+'/raw/moj/ott_urls.jsonl'):
            u=json.loads(l)
            if u.get('official'): OU[u['iid']]=u
        for L in out.values():
            for r in L:
                u=OU.get(r['id'])
                if u and 'courts.mo.gov' not in r['official_url']:
                    r['alt_urls']=[{'label':'CourtListener','url':r['official_url']}]+r['alt_urls']+[{'label':'Ott Law Firm mirror','url':u['ott']}]
                    r['official_url']=u['official']
    today=datetime.date.today().isoformat()
    for c,L in out.items():
        L.sort(key=lambda r:(r['date'],r['id']),reverse=True)
        json.dump({'corpus':c,'generated':today,'interps':L},open(f'{ROOT}/data/interps/{c}.json','w'),ensure_ascii=False,indent=2)
    json.dump(bynorm,open(ROOT+'/raw/moj/norm_interps.json','w'),indent=1)
    return out,led,bynorm
def add_common(out,bynorm):
    spec=json.load(open(ROOT+'/raw/moj/common_rules.json'))
    idx={r['id']:r for L in out.values() for r in L}
    capm={json.loads(l)['fn']:json.loads(l) for l in open(ROOT+'/raw/moj/cap_index.jsonl')}
    hits={}
    for pth in (ROOT+'/raw/moj/cl/hits.jsonl',ROOT+'/raw/mpj/cl_list.jsonl',ROOT+'/raw/mpj/cl_hits.jsonl'):
        if not os.path.exists(pth): continue
        for l in open(pth):
            r=json.loads(l)
            if not r.get('cluster_id'): continue
            r['cluster_id']=int(r['cluster_id']); hits.setdefault(r['cluster_id'],r)
    norms=[]
    def n(s): return re.sub(r'\s+',' ',re.sub(r'[“”"‘’\']','',s)).strip().lower()
    for rule in spec:
        srcids=[]; dates=[]
        segs=[s.strip(' .,;') for i,s in enumerate(re.split(r'[“”]',rule['summary_rule'])) if i%2==1 and len(s)>=25]
        for k in rule['sources']:
            if k.startswith('cap:'):
                m=capm[k[4:]]; x={'key':k,'cap':m,'cl':None}
                text=open(f"{ROOT}/raw/moj/cap/{m['fn']}.txt",errors='ignore').read()
            else:
                r=hits[int(k[3:])]; o=(r.get('opinions') or [{}])[0]
                x={'key':k,'cl':r['cluster_id'],'meta':{kk:r.get(kk) for kk in ['caseName','dateFiled','docketNumber','court_id','citation','absolute_url','status']},'download_url':o.get('download_url'),'local_path':o.get('local_path')}
                text=open(f"{ROOT}/raw/moj/text/{r['cluster_id']}.txt",errors='ignore').read()
            iid,sc,rec=rec_for(x)
            if iid in idx: rec=idx[iid]
            else:
                rec.update({'summary':'','summary_is_official':False,'excerpts':[],'titrage':[],'norms':[],'issues':[],'lang':'en'})
                out[rec['authority']].append(rec); idx[iid]=rec
            flat=re.sub(r'\s+',' ',text)
            # excerpts: sentences of this source containing a quoted segment of the rule
            ex=[]
            for s in segs:
                ns=n(s)
                sents=re.split(r'(?:(?<=[.!?])|(?<=[.!?][”"]))\s+(?=[“"A-Z\[])', flat)
                for se in sents:
                    if ns[:60] in n(se) and 20<len(se)<900 and se not in ex: ex.append(se.strip()); break
            rec['excerpts']=(ex+[e for e in rec['excerpts'] if e not in ex])[:4]
            if not any(e['norm']==rule['id'] for e in rec['norms']):
                rec['norms'].append({'norm':rule['id'],'basis':'a'})
            rec['issues']=sorted(set(rec['issues'])|set(rule['issues']))
            if not rec['summary']:
                rec['summary']=f"{rec['court']} opinion stating the Missouri judge-made rule: {rule['heading']} (neutral index summary; see excerpts)."
            srcids.append(iid); dates.append(rec['date']); bynorm[rule['id']].append(iid)
        latest=idx[srcids[dates.index(max(dates))]]
        norms.append({'id':rule['id'],'corpus':'mo-common','side':'mo','lang':'en','kind':'judge-made-rule','num':rule['id'][10:],
            'heading':rule['heading'],'path':[{'label':'Missouri judge-made family-law rules','id':'mo-common'}],
            'summary_rule':rule['summary_rule'],'rule_sources':srcids,'in_force_since':max(dates),'status':'in force','applies_to':['MO'],
            'official_url':latest['official_url'],'alt_urls':[{'label':'Leading source: '+idx[s]['citation'],'url':idx[s]['official_url']} for s in srcids],
            'source_ids':{},'issues':rule['issues'],'xrefs':[],'interps':srcids})
    json.dump({'corpus':'mo-common','generated':datetime.date.today().isoformat(),'norms':norms},open(ROOT+'/data/norms/mo-common.json','w'),ensure_ascii=False,indent=2)
def write_ledgers(out,led,bynorm):
    now=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    st=json.load(open(ROOT+'/raw/moj/cl/enum_state.json'))
    enum_done=sorted(k for k,v in st.items() if v.get('done')); enum_todo=[]
    import importlib.util
    sp=importlib.util.spec_from_file_location('e',ROOT+'/scripts/moj_enum.py')
    src=open(ROOT+'/scripts/moj_enum.py').read()
    allg=re.findall(r"",'')
    _ns={}; exec(open(ROOT+'/scripts/moj_enum.py').read().rsplit('\nmain()',1)[0], _ns)
    incomplete=[g for g,_ in _ns['groups']() if not st.get(g,{}).get('done')]
    screen=[json.loads(l) for l in open(ROOT+'/raw/moj/screen.jsonl')]
    nclus=len(screen); nscreened=sum(1 for x in screen if x.get('status')=='screened')
    rs=[n for n in NORMS.values() if n['corpus']=='mo-rsmo']; rl=[n for n in NORMS.values() if n['corpus']=='mo-rules']
    for c in ('mo-sc','mo-app'):
        L=out[c]; ids={r['id'] for r in L}
        by={}
        for ch,cnt in led.items():
            if ch=='_all': continue
            by[ch]=dict(cnt)
        inc_links=collections.Counter(e['basis'] for r in L for e in r['norms'])
        normsdone=len({e['norm'] for r in L for e in r['norms']})
        json.dump({'corpus':c,'norms_expected':len(rs)+len(rl),'norms_done':normsdone,
          'interps_candidates':nclus,'interps_screened':nscreened,'interps_included':len(L),
          'links_included_by_basis':dict(inc_links),
          'screening_by_chapter_links_both_courts':by,'excluded_whole_opinions':dict(led['_all']),
          'method':("Gap-fill Oct 2025 -> (pipeline mo-gapfill, scripts/moo_*.py): The Missouri Bar weekly case summaries (news.mobar.org, recall vs CourtListener Q3-2025 published opinions 96.9%) give docket + official courts.mo.gov file.jsp URL; texts from CourtListener where held, else republished copy on ott.law located via the Perplexity search index (docket verified; text_source field). "
          "Candidates = (1) every Missouri Supreme Court / Court of Appeals case in the Caselaw Access Project full-text volumes "
            "(S.W.2d 1-999, S.W.3d 1-579, Mo. 340-365, Mo. App. 231-241; i.e. published opinions to ~Aug 2019) whose text cites a perimeter RSMo "
            "section (regex on 'NNN.NNN[.n][(n)]', which covers 'section', '§' and 'RSMo' forms) or family keywords; plus (2) CourtListener REST v4 search "
            "(court=mo moctapp) for every perimeter section citation string incl. subsection forms 'NNN.NNN.n', filed 2018-01-01 onward (older 452 groups unfiltered), "
            "texts from CourtListener storage PDFs. Screening: CourtListener status=Published, Rule 84.16(b) orders excluded; link kept only when the opinion "
            "has an interpretive sentence citing the norm (keyword/quotation) or >=2 citations; temporal rule SCOPE §2 using data/norms/mo-rsmo.json "
            "in_force_since and data/mo-history: basis a if date >= D; basis b (text-identical) if the version in force at the opinion date is identical, "
            "or all cited subsections are unchanged (subsections_changed_vs_current), or the opinion quotes >=8 words of the interpreted language that appear "
            "verbatim in the current text (and in the then-current version where available); otherwise excluded. Excerpts are verbatim sentences citing the norm. "
            "Version at opinion date is assumed to be the version interpreted (opinions applying an earlier version to earlier facts may be mis-dated)."),
          'gaps':[
            "Opinions after the CAP cut-off (~Aug 2019) come only from CourtListener search (anonymous limit 5 req/min; part of the run was done through a browser session). Query groups completed: "+str(len(enum_done))+"; incomplete: "+(', '.join(incomplete) or 'none')+" (rerun scripts/moj_enum.py). CourtListener returned no Missouri opinions filed in 2026 for the perimeter citations (possible indexing lag); CourtListener full-text coverage of Missouri opinions may itself be incomplete.",
            "official_url: courts.mo.gov file links used only where CourtListener recorded them (download_url); courts.mo.gov blocks automated access and its opinion pages are not in the search index, so CAP-sourced opinions link to the deterministic CourtListener citation URL (https://www.courtlistener.com/c/<reporter>/<vol>/<page>/) with CAP JSON as alt_url.",
            "Summaries are neutral index summaries (no official syllabus available); summary_is_official=false.",
            "Pre-D links not shown text-identical were functionally reviewed (LLM-assisted, scripts/moj_funcreview.py) only where the version in force at the opinion date exists in data/mo-history (1,468 links): included as b functional-review when the interpreted subsection is unchanged in wording/function (justification quotes both texts); excluded when changed in substance or the interpreted subsection could not be identified (counts under 'funcreview:*'). Links whose opinion predates the earliest available version text (~5,400) remain excluded: no prior text to compare.",
            "2019-2026 supplement: Missouri opinions located through the Perplexity search index on the ott.law mirror (docket verified against the page URL), official_url = the courts.mo.gov file.jsp link given on that page; recall of this channel is partial (2026: few opinions indexed). courts.mo.gov itself was not accessed (its terms prohibit automated access).",
            "Rule and ch. 516 (limitations) citations are kept only for opinions that also cite a family-law chapter (451-455, 210, 211); rules without history files: pre-D opinions qualify only by verbatim quotation.",
            "Chapters 193 and 516 were added to the perimeter by the norms agent after the CAP scan; CAP candidates for them were found only when the opinion also met the family keyword filter.",
            "Opinions without text in either channel: "+str(led['_all'].get('no-text',0))+" (not screened)."],
          'updated':now},open(f'{ROOT}/data/coverage/{c}.json','w'),indent=2)
    spec=json.load(open(ROOT+'/raw/moj/common_rules.json'))
    json.dump({'corpus':'mo-common','norms_expected':len(spec),'norms_done':len(spec),'interps_candidates':sum(len(json.load(open(ROOT+f'/raw/moj/common_r{i}.json')).get(k,[])) for i in (1,2,3) for k in json.load(open(ROOT+f'/raw/moj/common_r{i}.json'))),
       'interps_screened':None,'interps_included':len({s for r in spec for s in r['sources']}),
       'method':'Doctrine phrase searches (raw/moj/common_q*.json) over all local Missouri opinion texts (CAP + CourtListener); leading/recent statements selected; every quoted segment of summary_rule machine-verified verbatim against the source texts (scripts/moj_common_check.py).',
       'gaps':['Rule set is a curated selection of recurring doctrines (13 rules), not an exhaustive restatement of Missouri family common law.',
               'Doctrines governed by statute (e.g. non-modifiability of property division, § 452.330.5) are left to mo-rsmo interpretations.',
               'Rule 54.06(b) (long-arm in dissolution cases) is not in data/norms/mo-rules.json; personal-jurisdiction rule cites it via case language only.'],
       'updated':now},open(f'{ROOT}/data/coverage/mo-common.json','w'),indent=2)
if __name__=='__main__':
    out,led,bynorm=main()
    print({c:len(L) for c,L in out.items()}, {c:sum(1 for r in L for e in r['norms'] if e['basis']=='a') for c,L in out.items()})
    json.dump({k:dict(v) for k,v in led.items()},open(ROOT+'/raw/moj/ledger_counts.json','w'),indent=1)
    write_ledgers(out,led,bynorm)
