#!/usr/bin/env python3
"""Build data/interps/mo-sc-proc.json, data/interps/mo-app-proc.json and data/coverage/mo-proc-interps.json
from raw/mpj/screen.jsonl + raw/mpj/cap_hits_v2.jsonl + raw/mpj/cl_hits.jsonl."""
import json, os, re, sys, collections, datetime
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import ROOT, RAW, VER
from mpj_screen import load_norms
REP = {'sw2d': 'S.W.2d', 'sw3d': 'S.W.3d', 'mo': 'Mo.', 'mo-app': 'Mo. App.'}
DIST = {'W.D.': ', Western District', 'E.D.': ', Eastern District', 'S.D.': ', Southern District'}


def district(docket, text=''):
    s = (docket or '') + ' ' + (text or '')
    for pat, d in ((r'\bW\.?D\.?\s?\d|WESTERN DISTRICT|Western District', 'W.D.'), (r'\bE\.?D\.?\s?\d|EASTERN DISTRICT|Eastern District', 'E.D.'),
                   (r'\bS\.?D\.?\s?\d|SOUTHERN DISTRICT|Southern District', 'S.D.')):
        if re.search(pat, s): return d
    return None


def meta_cap(m):
    court_raw = m.get('court') or ''
    sc = 'Supreme Court' in court_raw
    fp = m.get('first_page'); vol = m['vol']; rep = m['rep']
    cl_c = f"https://www.courtlistener.com/c/{REP[rep]}/{vol}/{int(fp) if fp and str(fp).isdigit() else fp}/"
    alts = [{'label': 'Caselaw Access Project (Harvard) — case JSON', 'url': f"https://static.case.law/{rep}/{vol}/cases/{m['file']}.json"}]
    iid = ('mo-sc' if sc else 'mo-app') + '-proc-cap' + str(m['cap_id'])
    y = (m['date'] or '')[:4]
    if sc:
        court = 'Supreme Court of Missouri'; paren = f'(Mo. {y})'
    else:
        d = district(m.get('docket'))
        if court_raw and not court_raw.startswith('Missouri Court of Appeals'):
            court = court_raw; paren = f'(Mo. App. {y})'
        else:
            court = 'Missouri Court of Appeals' + (DIST[d] if d else ''); paren = f'(Mo. App. {d + " " if d else ""}{y})'
    sw = [c for c in m.get('cites') or [] if 'S.W.' in c] or (m.get('cites') or [])
    cit = f"{m['name']}, {sw[0] if sw else ('No. ' + m['docket'] if m.get('docket') else '')} {paren}".replace('  ', ' ')
    return iid, {'id': iid, 'authority': 'mo-sc' if sc else 'mo-app', 'court': court, 'date': m['date'], 'number': m.get('docket') or None, 'ecli': None,
                 'citation': cit, 'publication': 'published', 'official_url': cl_c, 'alt_urls': alts}


def meta_cl(m):
    sc = m['court_id'] == 'mo'
    clurl = 'https://www.courtlistener.com' + m['absolute_url']
    du = m.get('download_url') or ''
    official = du if 'courts.mo.gov' in du else clurl
    alts = [{'label': 'CourtListener', 'url': clurl}] if official != clurl else []
    if m.get('local_path'): alts.append({'label': 'CourtListener PDF copy', 'url': 'https://storage.courtlistener.com/' + m['local_path']})
    iid = ('mo-sc' if sc else 'mo-app') + '-proc-cl' + str(m['cl'])
    y = (m['date'] or '')[:4]
    if sc: court = 'Supreme Court of Missouri'; paren = f'(Mo. {y})'
    else:
        d = district(m.get('docket'))
        court = 'Missouri Court of Appeals' + (DIST[d] if d else ''); paren = f'(Mo. App. {d + " " if d else ""}{y})'
    sw = [c for c in m.get('cites') or [] if 'S.W.' in c]
    cit = f"{m['name']}, {sw[0] if sw else ('No. ' + m['docket'] if m.get('docket') else '')} {paren}".replace('  ', ' ')
    return iid, {'id': iid, 'authority': 'mo-sc' if sc else 'mo-app', 'court': court, 'date': m['date'], 'number': m.get('docket') or None, 'ecli': None,
                 'citation': cit, 'publication': 'published', 'official_url': official, 'alt_urls': alts}


def label(n):
    return ('§ ' + n['num'] + ' RSMo') if n['corpus'] == 'mo-rsmo' else ('Rule ' + n['num'])


def main():
    N = load_norms(); BYID = {v['id']: v for v in N.values()}
    meta = {}
    for l in open(RAW + f'/cap_hits_{VER}.jsonl'):
        x = json.loads(l); x.pop('hits', None); meta[x['key']] = x
    if os.path.exists(RAW + '/cl_hits.jsonl'):
        for l in open(RAW + '/cl_hits.jsonl'):
            x = json.loads(l); x.pop('hits', None); meta[x['key']] = x
    out = {'mo-sc': [], 'mo-app': []}; led = collections.Counter(); bynorm = collections.defaultdict(list); basis = collections.Counter()
    per_norm = collections.defaultdict(collections.Counter)
    for l in open(RAW + '/screen.jsonl'):
        x = json.loads(l)
        if x.get('status') != 'screened': continue
        norms = []; ex = []; issues = []
        for k, d in x['secs'].items():
            per_norm[k][d['decision']] += 1
            if d['decision'] not in ('a', 'b'): continue
            n = BYID[d['norm']]; e = {'norm': n['id'], 'basis': d['decision']}
            if d.get('version'): e['cited_version'] = 'revisor bid ' + str(d['version'])
            elif d.get('version_eff'): e['cited_version'] = 'version effective ' + d['version_eff']
            if d['decision'] == 'b':
                e['b_method'] = 'text-identical'
                if d['b_how'] == 'subsection':
                    e['b_justification'] = (f"The opinion ({x['date']}) applied {label(n)} as in force from {d.get('version_eff')} ({('revisor bid ' + str(d.get('version'))) if d.get('version') else 'data/mo-history'}) and cites subsection(s) "
                                            f"{', '.join(d['subs_checked'])}; the version comparison in data/mo-history shows these subsections unchanged in the current text in force since {d['D']}, so the interpreted language is identical in wording and function.")
                elif d['b_how'] == 'whole-section':
                    vref = f"revisor bid {d.get('version')}" if d.get('version') else f"version effective {d.get('version_eff')}"
                    e['b_justification'] = f"The version of {label(n)} in force at the date of the opinion ({x['date']}; {vref}) is identical to the current text in force since {d['D']} (data/mo-history identical_to_current = true, text comparison)."
                else:
                    q = d['quoted'][0]
                    e['b_justification'] = (f"The opinion ({x['date']}) predates the current version of {label(n)} (in force since {d['D']}) but quotes the language it applies — “{q}” — "
                                            "and that language appears verbatim (normalized for punctuation/case) in the current text"
                                            + (" and in the version in force at the date of the opinion" if d.get('version') else "")
                                            + "; the interpreted language is therefore identical in wording and function.")
            norms.append(e); basis[d['decision']] += 1
            ex += [(n['id'], s) for s in d['excerpts']]
            issues += n.get('issues') or []
        if not norms: continue
        m = meta[x['key']]
        iid, r = meta_cap(m) if x['key'].startswith('cap:') else meta_cl(m)
        seen = []; per = collections.defaultdict(list)
        for k, s in ex: per[k].append(s)
        while len(seen) < 3 and any(per.values()):
            for k in list(per):
                if per[k] and len(seen) < 3:
                    s = per[k].pop(0)
                    if s not in seen: seen.append(s)
        lab = ', '.join(label(BYID[e['norm']]) for e in norms[:6]) + (' and others' if len(norms) > 6 else '')
        r.update({'summary': f"{r['court']} opinion applying or construing {lab} (neutral index summary; see verbatim excerpts).",
                  'summary_is_official': False, 'excerpts': seen, 'titrage': [], 'norms': norms, 'issues': sorted(set(issues)), 'axes': ['procedure'], 'lang': 'en'})
        out[r['authority']].append(r)
        for e in norms: bynorm[e['norm']].append(iid)
    today = datetime.date.today().isoformat()
    for c, L in out.items():
        L.sort(key=lambda r: (r['date'] or '', r['id']), reverse=True)
        json.dump({'corpus': c + '-proc', 'authority': c, 'generated': today, 'interps': L}, open(f'{ROOT}/data/interps/{c}-proc.json', 'w'), ensure_ascii=False, indent=2)
    json.dump(bynorm, open(RAW + '/norm_interps.json', 'w'), indent=1)
    json.dump({k: dict(v) for k, v in sorted(per_norm.items())}, open(RAW + '/per_norm_decisions.json', 'w'), indent=1)
    print({c: len(L) for c, L in out.items()}, dict(basis))
    ledger(out, basis, per_norm, N, bynorm)
    return out, basis, per_norm, N


def recall():
    if os.path.exists(RAW + '/recall_check.json'): return json.load(open(RAW + '/recall_check.json'))
    import ast
    part = [ast.literal_eval(l) for l in open(RAW + '/recall.log') if l.startswith('{')] if os.path.exists(RAW + '/recall.log') else []
    return {'status': 'partial — remaining queries throttled by CourtListener (HTTP 429); rerun scripts/mpj_recall.py', 'results': part}


def ledger(out, basis, per_norm, N, bynorm):
    sc = json.load(open(RAW + '/screen_counts.json'))
    op = sc['opinions']; lk = sc['links']
    cand = op.get('cap:candidates', 0) - op.get('cap:dup-of-cl', 0) + op.get('cl:candidates', 0)
    screened = sum(v for k, v in op.items() if k.endswith(':screened') or 'excluded' in k)
    notext = op.get('cl:no-text', 0)
    fam = collections.Counter()
    for k, d in per_norm.items():
        fam[(k.split('.')[0] if k[0] == 'R' else 'S:' + k[2:5])] += sum(v for kk, v in d.items() if kk in ('a', 'b'))
    tot_cl = 0; cl_st = collections.Counter()
    if os.path.exists(RAW + '/cl_hits.jsonl'):
        for l in open(RAW + '/cl_hits.jsonl'): cl_st[json.loads(l).get('status')] += 1
    nt = 0; nn = 0
    if os.path.exists(RAW + '/cl_list.jsonl'):
        seen = set()
        for l in open(RAW + '/cl_list.jsonl'):
            r = json.loads(l)
            if r['cluster_id'] in seen: continue
            seen.add(r['cluster_id']); nt += 1
            if not os.path.exists(f"{RAW}/text/{r['cluster_id']}.txt"): nn += 1
    miss = sc.get('missing_norm_keys', {})
    L = {'corpus': 'mo-proc-interps', 'interp_files': ['data/interps/mo-sc-proc.json', 'data/interps/mo-app-proc.json'], 'axis': 'procedure',
         'norms_expected': len(N), 'norms_done': len(N), 'norms_with_interps': len(bynorm),
         'interps_candidates': cand, 'interps_screened': screened, 'interps_included': sum(len(v) for v in out.values()),
         'interps_included_by_authority': {k: len(v) for k, v in out.items()},
         'norm_links_included': dict(basis), 'norm_link_decisions': lk,
         'opinion_level': op, 'cl_2019plus': {'clusters_enumerated': nt, 'clusters_without_text': nn, 'scan_status': dict(cl_st)},
         'included_links_by_rule_or_chapter': dict(sorted(fam.items())),
         'method': ('Candidates enumerated by FULL-TEXT citation scanning rather than per-string search queries (a strict superset of '
                    'queries such as \"Rule 55.27\", \"Rule 74.06(b)\", \"section 506.500\", \"§ 506.500\"): (1) every Missouri opinion in the Caselaw '
                    'Access Project volumes S.W.2d 1–999, S.W.3d 1–579, Mo. 340–365, Mo. App. 231–241 (static.case.law, court opinion text only — no '
                    'head matter/concurrences/dissents); (2) every PUBLISHED CourtListener cluster of courts mo + moctapp filed 2019-06-01 or later, enumerated '
                    'from Free Law Project bulk data (dockets/opinion-clusters CSV) and the REST v4 search API, text from the CourtListener storage copy '
                    '(docket number verified in the text). Citation patterns: Rule(s) NN.NN(sub) for Rules 41–101, and RSMo sections 506–517, 525. '
                    'Screening per opinion×norm: norm record must exist in data/norms (mo-rules / mo-rsmo); Rule 84.16(b) summary orders excluded; '
                    'bare mentions excluded (needs a citing sentence with interpretive/operative language, or a verified quotation of the norm); sentences '
                    'referring to a former/prior version excluded; temporal rule SCOPE §2: (a) opinion date >= in_force_since; (b) only with text-identical '
                    'proof — whole-section / unchanged-subsection comparison in data/mo-history, or ≥8-word quotation of the norm found verbatim (normalized) '
                    'in the current text; otherwise excluded. Excerpts: 1–4 verbatim sentences from the opinion text that cite the norm, ranked for interpretive '
                    'content (heuristic, not hand-reviewed). Summaries are neutral index summaries (not official). official_url: courts.mo.gov when the '
                    'CourtListener record carries it, else CourtListener (opinion page or citation-lookup URL).'),
         'gaps': [
             f"{lk.get('no-norm-record', 0)} opinion×norm links point to rule/section numbers with no record in data/norms (renumbered/repealed rules, or norms not yet ingested by the norms agent); top: "
             + ', '.join(f'{k} ({v})' for k, v in list(miss.items())[:25]),
             f"{lk.get('excluded-prior-text-not-shown-identical', 0)} links excluded because the opinion predates the current effective date and no text-identical proof was available (prior rule texts are not published on courts.mo.gov; amendment orders not ingested) — a functional-review pass could recover some.",
             f"{lk.get('excluded-no-effective-date', 0)} links excluded because the norm record lacks in_force_since.",
             f"{nn} CourtListener clusters (2019+) without retrievable text (no storage copy matched); not screened.",
             (f"Of the {nn} clusters without text, {len(json.load(open(RAW + '/ocr_candidates.json')))} have a matching storage PDF that is image-only (scanned; no text layer) — OCR not applied to keep excerpts strictly verbatim; list in raw/mpj/ocr_candidates.json."
              if os.path.exists(RAW + '/ocr_candidates.json') else 'image-only PDFs not counted'),
             'courts.mo.gov answers HTTP 403 to automated clients: official_url is courts.mo.gov only when CourtListener carries the courts.mo.gov download_url (API-enumerated records); otherwise the CourtListener opinion page or citation-lookup URL (SCHEMA/AGENT_BRIEF fallback).',
             'Bulk opinion-clusters rows with multi-line quoted fields were first skipped by the grep pass and then recovered by a full CSV parse (clusters_full step, +11).',
             'Excerpts and the interpretive/mention-only filter are automated heuristics; no manual review of the ~all included records.',
             'CAP coverage ends with S.W.3d vol. 579 (mid-2019); opinions after that come from CourtListener only.',
             'Opinions interpreting family norms are recorded here only with their procedural-norm links; the same decision may also appear in mo-sc.json / mo-app.json (family axis) under a different id.'],
         'recall_check_vs_courtlistener_search': recall(),
         'updated': datetime.date.today().isoformat(),
         'refresh': ['python3 scripts/mpj_cap.py  # only if VER bumped in mpj_common', 'python3 scripts/mpj_bulk.py --date <latest quarterly bulk date>',
                     'python3 scripts/mpj_s3match.py', 'python3 scripts/mpj_enum.py --since <bulk date minus 7 days>  # API tail, polite',
                     'python3 scripts/mpj_text.py', 'python3 scripts/mpj_scan.py', 'python3 scripts/mpj_recall.py  # optional recall check', 'python3 scripts/mpj_screen.py', 'python3 scripts/mpj_build.py']}
    json.dump(L, open(ROOT + '/data/coverage/mo-proc-interps.json', 'w'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
