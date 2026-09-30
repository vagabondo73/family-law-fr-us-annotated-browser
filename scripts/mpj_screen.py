#!/usr/bin/env python3
"""Screen every candidate (CAP full-text hits raw/mpj/cap_hits_v2.jsonl + CourtListener hits raw/mpj/cl_hits.jsonl) for
procedural-norm links: norm record exists, publication (84.16(b) summary orders out), interpretive use (not bare mention),
temporal rule SCOPE §2 (a: date >= D(norm); b: text-identical proof via history version or quoted language found verbatim
in the current text). Output raw/mpj/screen.jsonl (one line per opinion) + raw/mpj/screen_counts.json"""
import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
from mpj_common import ROOT, RAW, VER, norm
STRONG = re.compile(r'(?i)\b(means?|meaning|requires?|required|requirements?|provides?|provided that|permits?|permitted|authori[sz]\w*|prohibit\w*|mandat\w*|interpret\w*|constru\w*|plain (?:language|meaning|terms?)|purpose|intent|appl(?:y|ies|ied|icable)|standard|governs?|governed|contemplates?|is designed|is intended|allows?|precludes?|bars?|entitle[sd]?|does not|must|shall|may not|cannot|only if|unless|within the meaning|jurisdiction\w*|waive[sd]?|timely|deadline|discretion)\b')
AXIS = 'procedure'
FORMER = re.compile(r'(?i)(\b(?:former|old|prior|previous|then[- ]existing|superseded|repealed|earlier)\s+(?:version\s+of\s+)?(?:Supreme\s+Court\s+|Civil\s+)?(?:Rules?|§|sections?)\b|\bprior to (?:its|the) (?:\d{4} )?amendment|\bbefore (?:its|the) (?:\d{4} )?amendment|\bas it (?:then )?existed|\b(?:since|was|been|were) (?:amended|repealed|renumbered)|\bin effect at the time|\bthen in effect|(?:Rules?|§|sections?)\s*[\d.]+(?:\([a-z0-9]+\))*,?\s*\((?:19|20)\d\d\))')
BEST = re.compile(r'(?i)\b(means|meaning|requires?|purpose|intent|constru\w*|interpret\w*|plain (?:language|meaning|terms)|provides that|mandatory|jurisdictional|does not apply|applies only|is designed|we hold|held that)\b')


def load_norms():
    N = {}
    for f in ('mo-rules', 'mo-rsmo'):
        p = f'{ROOT}/data/norms/{f}.json'
        for n in json.load(open(p))['norms']:
            if f == 'mo-rules':
                m = re.match(r'(\d{2,3})\.(\d{2})$', n['num'] or '')
                if not m or not (41 <= int(m.group(1)) <= 101): continue
                k = 'R:%d.%s' % (int(m.group(1)), m.group(2))
            else:
                ch = (n['num'] or '').split('.')[0]
                if not (ch in ('525',) or (ch.isdigit() and 506 <= int(ch) <= 517)): continue
                k = 'S:' + n['num']
            d = {'id': n['id'], 'num': n['num'], 'corpus': f, 'D': n.get('in_force_since'), 'nbody': norm(n.get('text') or ''),
                 'repealed': (n.get('status') or 'in force') not in ('in force',), 'versions': [], 'issues': n.get('issues') or []}
            hp = f"{ROOT}/data/mo-history/{n['num']}.json" if f == 'mo-rsmo' else f"{ROOT}/data/mo-history/rule-{n['num']}.json"
            if os.path.exists(hp):
                try:
                    for v in json.load(open(hp)).get('versions', []):
                        d['versions'].append({'eff': v.get('effective'), 'end': v.get('end'), 'bid': v.get('bid'), 'identical': v.get('identical_to_current'),
                                              'changed': v.get('subsections_changed_vs_current') or [], 'nbody': norm(v.get('text') or '')})
                except Exception:
                    pass
            N[k] = d
    return N


def decide(S, f, date):
    dec = {'norm': S['id'], 'n': f['n'], 'subs': f['subs']}
    sents = [(x, k) for x, k in f['sents'] if not FORMER.search(x)]
    if f['sents'] and not sents:
        dec['decision'] = 'excluded-former-version-cited'; return dec
    strong = [s for s, k in sents if STRONG.search(s)]
    vq = [q for q in f['quotes'] if len(norm(q).split()) >= 8 and norm(q) in S['nbody']]   # quotes of the norm's current text
    if not strong and not vq:
        dec['decision'] = 'excluded-mention-only'; return dec
    def score(x):
        sc = 0
        if re.match(r'(?:See|Cf\.|Accord|But see|See also|Compare)\b', x): sc -= 5
        if len(x) < 70: sc -= 3
        if re.search(r'[a-z,;] \d{1,2} [A-Z][a-z]', x) or re.search(r'\s\.\s\.\s|\. \. ', x): sc -= 4   # footnote/page-break interleave
        if BEST.search(x): sc += 3
        if re.search(r'["\u201c]', x): sc += 1
        return -sc
    ranked = sorted(strong, key=score) + [s for s, k in sents if s not in strong]
    good = [x for x in ranked if score(x) <= 0]
    dec['excerpts'] = (good or ranked)[:3]
    if not dec['excerpts']:
        dec['decision'] = 'excluded-no-verbatim-excerpt'; return dec
    D = S['D']; dec['D'] = D
    if S['repealed']: dec['decision'] = 'excluded-repealed'; return dec
    if not D: dec['decision'] = 'excluded-no-effective-date'; return dec
    if not date: dec['decision'] = 'excluded-no-date'; return dec
    if date >= D: dec['decision'] = 'a'; return dec
    ver = None
    for v in S['versions']:
        if v['eff'] and v['eff'] <= date and (v['end'] is None or date < v['end']): ver = v
    if ver:
        dec['version'] = ver['bid']; dec['version_eff'] = ver['eff']
        if ver.get('identical'):
            dec['decision'] = 'b'; dec['b_how'] = 'whole-section'; return dec
        subs1 = sorted({re.match(r'\d+', s).group(0) for s in f['subs'] if re.match(r'\d+', s)})
        if subs1 and not (set(subs1) & set(map(str, ver['changed']))):
            dec['decision'] = 'b'; dec['b_how'] = 'subsection'; dec['subs_checked'] = subs1; return dec
    q2 = [q for q in vq if (ver is None or not ver.get('nbody') or norm(q) in ver['nbody'])]
    if q2:
        dec['decision'] = 'b'; dec['b_how'] = 'quoted'; dec['quoted'] = q2[:3]; return dec
    dec['decision'] = 'excluded-prior-text-not-shown-identical'; return dec


def main():
    N = load_norms(); C = collections.Counter(); K = collections.Counter()
    out = open(RAW + '/screen.jsonl', 'w')
    cl = []
    if os.path.exists(RAW + '/cl_hits.jsonl'):
        cl = [json.loads(l) for l in open(RAW + '/cl_hits.jsonl')]
    clcites = {c for x in cl for c in (x.get('cites') or [])}
    an = lambda z: re.sub(r'[^a-z0-9]', '', (z or '').lower())
    clnd = {(x.get('date'), an(x.get('name'))[:10]) for x in cl}
    cldk = {(x.get('date'), re.sub(r'[^A-Z0-9]', '', (x.get('docket') or '').upper())) for x in cl}
    missing = collections.Counter()
    for src, it in (('cap', open(RAW + f'/cap_hits_{VER}.jsonl')), ('cl', cl)):
        for x in it:
            if isinstance(x, str): x = json.loads(x)
            C[src + ':candidates'] += 1
            if src == 'cap' and (set(x.get('cites') or []) & clcites or (x.get('date'), an(x.get('name'))[:10]) in clnd
                                 or (x.get('date'), re.sub(r'[^A-Z0-9]', '', (x.get('docket') or '').upper()).replace('NO', '', 1)) in cldk):
                C['cap:dup-of-cl'] += 1; continue
            res = {'key': x['key'], 'src': src, 'date': x.get('date'), 'secs': {}}
            if x.get('status') and x['status'] != 'screened':
                res['status'] = x['status']; C[src + ':' + x['status']] += 1; out.write(json.dumps(res) + '\n'); continue
            if x.get('summary_order_84_16b'):
                res['status'] = 'excluded-84.16b-summary-order'; C[src + ':' + res['status']] += 1; out.write(json.dumps(res) + '\n'); continue
            res['status'] = 'screened'; C[src + ':screened'] += 1
            for k, f in x['hits'].items():
                K['links'] += 1
                S = N.get(k)
                if not S:
                    missing[k] += 1; res['secs'][k] = {'decision': 'no-norm-record'}; K['no-norm-record'] += 1; continue
                d = decide(S, f, x.get('date')); res['secs'][k] = d; K[d['decision']] += 1
            out.write(json.dumps(res, ensure_ascii=False) + '\n')
    json.dump({'opinions': dict(C), 'links': dict(K), 'norms_loaded': len(N), 'missing_norm_keys': dict(missing.most_common())},
              open(RAW + '/screen_counts.json', 'w'), indent=1)
    print(dict(C)); print(dict(K)); print('norms', len(N), 'missing keys', len(missing), missing.most_common(15))


if __name__ == '__main__':
    main()
