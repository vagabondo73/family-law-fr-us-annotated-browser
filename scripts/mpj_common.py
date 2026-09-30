#!/usr/bin/env python3
"""Shared helpers for the Missouri PROCEDURAL case-law pipeline (mpj_*).
Norm keys: 'R:<rule>' (Supreme Court Rules 41-101, e.g. R:55.27) and 'S:<section>' (RSMo ch. 506-517, 525)."""
import re, html, json, collections
ROOT = '/home/user/workspace/flb'
RAW = ROOT + '/raw/mpj'
VER = 'v3'   # CAP scan output version (cap_hits_<VER>.jsonl)
PRIORITY_RULES = {41, 42, 43, 44, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 65, 66, 67, 74, 75, 78, 81, 82, 83, 84, 88, 90}
PRIORITY_CH = {'506', '508', '509', '510', '511', '513', '516', '525'}
# "Rule 55.27(a)(6)", "Rules 55.27 and 55.33", "Supreme Court Rule 74.06(b)", "Civil Rule 84.04", "Rule No. 74.04"
RULE_RE = re.compile(r'\bRules?\s+(?:No\.\s*)?((?:\d{2,3}\.\d{2}(?:\([a-z0-9]{1,4}\))*(?:\s*(?:,|and|or|&|through|to|-)\s*)?)+)')
RNUM_RE = re.compile(r'(\d{2,3})\.(\d{2})((?:\([a-z0-9]{1,4}\))*)')
SEC_RE = re.compile(r'(?<![\d.$,])((?:50[6-9]|51[0-7]|525)\.\d{3})(?:\.(\d{1,2}))?((?:\([a-z0-9]{1,3}\))*)(?![\d])')
KEY = re.compile(r'(?i)\b(means|requires?|required|provides?|provision|mandat\w*|interpret\w*|plain (?:language|meaning)|legislat\w*|statut\w*|shall|must|authori[sz]\w*|permits?|prohibit\w*|purpose|intent|applies|apply|construe\w*|standard|purpose of rule|under rule|pursuant to)\b')
QUOTE = re.compile(r'["\u201c]([^"\u201c\u201d]{40,1200})["\u201d]')


def rule_ok(n):
    return 41 <= int(n) <= 101


def find_keys(s):
    """return list of (key, sub) found in sentence s"""
    out = []
    for m in RULE_RE.finditer(s):
        for r in RNUM_RE.finditer(m.group(1)):
            if rule_ok(r.group(1)):
                out.append(('R:%s.%s' % (int(r.group(1)), r.group(2)), r.group(3) or ''))
    for m in SEC_RE.finditer(s):
        out.append(('S:' + m.group(1), (m.group(2) or '') + (m.group(3) or '')))
    return out


ABBR = re.compile(r'(?:\bv|\bvs|Mo|App|Inc|Co|Corp|Ltd|No|Nos|Rev|Stat|Supp|Ann|Id|id|cf|Cf|e\.g|i\.e|al|Dist|Div|Ct|Cir|Sec|sec|Art|art|Const|Mr|Mrs|Ms|Dr|Jr|Sr|St|Ry|Bros|Assn|Ass\'n|Univ|Dept|Gov|Fed|Civ|Crim|Proc|Prac|Ed|ed|Cum|R|U\.S|S\.W|S\.Ct|L\.Ed|F|Cal|Ill|Kan|Neb|Okla|Ark|Tenn|Ky|Iowa|Wash|Ariz|Colo|Tex|Mich|Wis|Minn|Pa|Ga|Fla|Va|Md|Mass|Conn|Ohio|N\.Y|N\.J|App\.\s?Ct|et\s?seq|Ch|ch|Sess|Laws|L|para|p|pp|Vol|vol)\.$')
_SPLIT = re.compile(r'(?<=[a-z0-9\)\]"\u201d\u2019][.?!])["\u201d]?\s+(?=[A-Z\u201c"(\u00a7])')


def sentences(t):
    out = []; start = 0
    for m in _SPLIT.finditer(t):
        pre = t[max(start, m.start() - 12):m.start()].rstrip('"\u201d')
        if ABBR.search(pre) or re.search(r'\b[A-Z]\.$', pre):   # abbreviation / initial, not a sentence end
            continue
        out.append((start, m.end())); start = m.end()
    out.append((start, len(t)))
    return out


def clean(s):
    return re.sub(r'\s+', ' ', s).strip()


def norm(s):
    s = html.unescape(s or '').replace('\u00ad', '').replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
    s = re.sub(r'[\u2014\u2013-]+', ' ', s); s = re.sub(r'[^\w\s]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()


def scan_text(t, max_sents=8, max_quotes=6):
    """Locate procedural-norm citations; return {key: {n, subs, sents:[(text,key_flag)], quotes:[...]}}"""
    found = {}
    for pg in t.split('\f'):
        for a, b in sentences(pg):
            s = pg[a:b]
            ks = find_keys(s)
            if not ks: continue
            cs = clean(s)
            for k, sub in ks:
                f = found.setdefault(k, {'n': 0, 'subs': [], 'sents': [], 'quotes': []})
                f['n'] += 1
                if sub and sub not in f['subs']: f['subs'].append(sub)
                if 25 <= len(cs) <= 900 and len(f['sents']) < max_sents and cs not in [x for x, _ in f['sents']]:
                    f['sents'].append((cs, bool(KEY.search(cs)) or bool(QUOTE.search(cs))))
    if found:
        full = clean(t)
        for k, f in found.items():
            num = k[2:]
            pat = (r'Rules?\s+(?:No\.\s*)?(?:\d{2,3}\.\d{2}[^A-Za-z]{0,40})*' + re.escape(num)) if k[0] == 'R' else r'(?<![\d.])' + re.escape(num) + r'(?![\d])'
            for m in re.finditer(pat, full):
                win = full[max(0, m.start() - 700):m.end() + 1000]
                for q in QUOTE.finditer(win):
                    qq = q.group(1).strip()
                    if len(qq.split()) >= 8 and qq not in f['quotes'] and len(f['quotes']) < max_quotes:
                        f['quotes'].append(qq)
    return found
