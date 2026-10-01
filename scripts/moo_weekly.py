#!/usr/bin/env python3
"""mo-gapfill weekly operation: newest Missouri Bar weekly summaries since last run -> discovery -> text (republished copies)
-> moj screen (+functional review) -> build -> QA; proc candidates for mpj. State: raw/moo/weekly_state.json."""
import json, os, subprocess, datetime as dt
ROOT=os.environ.get('FLB_ROOT','/home/user/workspace/flb'); SP=ROOT+'/raw/moo/weekly_state.json'
st=json.load(open(SP)) if os.path.exists(SP) else {'last_run':'2025-09-26'}
since=(dt.date.fromisoformat(st['last_run'])-dt.timedelta(days=21)).isoformat()   # overlap: late postings / re-issued weeks
def run(*a): print('+',' '.join(a),flush=True); subprocess.run(['python3',*a],cwd=ROOT,check=True)
run('scripts/moo_mobar.py',since); run('scripts/moo_text.py',since); run('scripts/moo_text2.py'); run('scripts/moo_proc.py','2025-10-01')
run('scripts/moj_screen.py'); run('scripts/moj_funcreview.py'); run('scripts/moj_screen.py'); run('scripts/moj_build.py'); run('scripts/moj_qa.py'); run('scripts/mpj_scan.py'); run('scripts/moo_mpj_feed.py')
st['last_run']=dt.date.today().isoformat(); json.dump(st,open(SP,'w'))
