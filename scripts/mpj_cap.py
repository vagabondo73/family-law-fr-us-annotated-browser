#!/usr/bin/env python3
"""Local full-text enumeration over Caselaw Access Project (static.case.law) volume zips (S.W.3d 1-579, S.W.2d 1-999,
Mo. 340-365, Mo. App. 231-241): every Missouri opinion is scanned with the procedural citation patterns of mpj_common
(Rules 41-101; RSMo 506-517, 525). No full texts stored: only citing sentences + quotations near the citation.
Resumable. Output raw/mpj/cap_hits_<VER>.jsonl, cap_done_<VER>.txt, cap_stats_<VER>.jsonl (VER in mpj_common; older versions superseded)"""
import json, os, io, zipfile, urllib.request, urllib.error, time, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import RAW, VER, scan_text
os.makedirs(RAW, exist_ok=True)


def vol(job):
    rep, v = job
    for k in range(5):
        try:
            b = urllib.request.urlopen(urllib.request.Request(f'https://static.case.law/{rep}/{v}.zip', headers={'User-Agent': 'flb-research'}), timeout=180).read(); break
        except urllib.error.HTTPError as e:
            if e.code == 404: return (job, '404', [], 0)
            time.sleep(10 * (k + 1))
        except Exception:
            time.sleep(10 * (k + 1))
    else:
        return (job, 'fail', [], 0)
    z = zipfile.ZipFile(io.BytesIO(b)); out = []; nmo = 0
    for n in z.namelist():
        if not n.startswith('json/'): continue
        d = json.loads(z.read(n))
        if (d.get('jurisdiction') or {}).get('name') != 'Mo.': continue
        nmo += 1
        cb = d.get('casebody') or {}
        ops = cb.get('opinions') or []
        maj = [o for o in ops if o.get('type') in ('majority', 'per-curiam', 'per_curiam')] or ops[:1]
        text = '\n\n'.join((o.get('text') or '') for o in maj)   # court's opinion only (no head matter, concurrences, dissents)
        tlen = len(text); short84 = tlen < 4000 and '84.16(b)' in text
        hits = scan_text(text)
        if not hits: continue
        fn = n[5:-5]
        out.append({'key': f'cap:{rep}_{v}_{fn}', 'cap_id': d['id'], 'name': d.get('name_abbreviation'), 'date': d.get('decision_date'),
                    'docket': d.get('docket_number'), 'cites': [c['cite'] for c in d.get('citations', [])], 'court': (d.get('court') or {}).get('name'),
                    'rep': rep, 'vol': v, 'file': fn, 'first_page': d.get('first_page'),
                    'optypes': [o.get('type') for o in ops], 'len': tlen, 'summary_order_84_16b': short84, 'hits': hits})
    return (job, 'ok', out, nmo)


def main():
    donep = RAW + f'/cap_done_{VER}.txt'; done = set(open(donep).read().split()) if os.path.exists(donep) else set()
    jobs = [('sw3d', v) for v in range(579, 0, -1)] + [('sw2d', v) for v in range(999, 0, -1)] + [('mo', v) for v in range(340, 366)] + [('mo-app', v) for v in range(231, 242)]
    jobs = [j for j in jobs if f'{j[0]}/{j[1]}' not in done]
    fi = open(RAW + f'/cap_hits_{VER}.jsonl', 'a'); fd = open(donep, 'a'); fs = open(RAW + f'/cap_stats_{VER}.jsonl', 'a')
    with ThreadPoolExecutor(4) as ex:
        for job, st, idx, nmo in ex.map(vol, jobs):
            if st in ('ok', '404'):
                for m in idx: fi.write(json.dumps(m, ensure_ascii=False) + '\n')
                fi.flush(); fd.write(f'{job[0]}/{job[1]}\n'); fd.flush()
                fs.write(json.dumps({'vol': f'{job[0]}/{job[1]}', 'st': st, 'mo_cases': nmo, 'hits': len(idx)}) + '\n'); fs.flush()
            print(job, st, nmo, len(idx), flush=True)


if __name__ == "__main__":
    main()
