#!/usr/bin/env python3
"""QA: every excerpt must occur verbatim (whitespace-normalised) in the fetched source text."""
import json,re,glob,os
ROOT='/home/user/workspace/flb'
capid={}
for l in open(ROOT+'/raw/moj/cap_index.jsonl'):
    m=json.loads(l); capid[str(m['id'])]=m['fn']
import glob
OTT={}
for p in glob.glob(ROOT+'/raw/moj/ott/*.txt'):
    if os.path.basename(p).startswith('_'): continue
    m=json.loads(open(p,errors='ignore').readline()[7:])
    if m.get('docket') and re.search(r'-d?'+re.sub(r'\D','',m['docket'])+r'$',m['url'].rstrip('/')): OTT[m['docket'].lower()]=p
def src(iid):
    if '-cap' not in iid and '-cl' not in iid: return open(OTT[iid.split('-',2)[2]],errors='ignore').read()
    if '-cap' in iid: return open(f"{ROOT}/raw/moj/cap/{capid[iid.split('-cap')[1]]}.txt",errors='ignore').read()
    return open(f"{ROOT}/raw/moj/text/{iid.split('-cl')[1]}.txt",errors='ignore').read()
w=lambda s: re.sub(r'\s+',' ',s)
bad=0; n=0
for c in ('mo-sc','mo-app'):
    for r in json.load(open(f'{ROOT}/data/interps/{c}.json'))['interps']:
        T=w(src(r['id']))
        for e in r['excerpts']:
            n+=1
            if w(e) not in T: bad+=1; print('NOT VERBATIM',r['id'],e[:100])
print('excerpts',n,'not verbatim',bad)
