# -*- coding: utf-8 -*-
"""Detect articles a French decision applies in a prior wording (« dans sa/leur rédaction antérieure à … », « ancien article … »).
Added 2026-10-12: such links are kept as basis (c) with the interpreted version recorded."""
import json,re,collections,sys
ORD={'premier':0,'première':0,'deuxième':1,'second':1,'seconde':1,'troisième':2,'quatrième':3}
CODE_OF={'fr-cc':'code civil','fr-cpc':'code de procédure civile','fr-cp':'code pénal','fr-cpp':'code de procédure pénale','fr-csp':'code de la santé publique','fr-css':'code de la sécurité sociale','fr-casf':"code de l'action sociale et des familles",'fr-cgi':'code général des impôts','fr-coj':"code de l'organisation judiciaire",'fr-ceseda':"code de l'entrée et du séjour des étrangers",'fr-cpce':"code des procédures civiles d'exécution"}
NUM=r"(?:[LRDA]\.?\s?\*?)?\d+(?:-\d+)*(?:\s(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies|A|B|C))?"
def nn(s): return re.sub(r'[\s.*]','',s).lower()
def prior_targets(txt):
    """return {(code, num): qualifying phrase} for articles interpreted in a prior wording / old numbering"""
    res={}
    txt=re.sub(r'\s+',' ',txt)
    for m in re.finditer(r"articles?\s+((?:"+NUM+r")(?:\s?,\s?(?:alinéa[^,]*,\s?)?(?:"+NUM+r")|\s(?:et|,)\s(?:"+NUM+r")|,?\s(?:alinéas?|al\.)\s[^,;]{1,25}|,\s\d°)*)\s+(?:du|de la|des)\s+(code [^,;:.]{3,60}?)(?=[,;:.]|\s(?:et|dans|le|ce))([^;:]{0,200})",txt):
        lst=[nn(x) for x in re.findall(NUM,m.group(1)) if not re.fullmatch(r'\d°',x)]
        code=m.group(2).strip(); tail=m.group(3)
        q=re.match(r"\s?,?\s?(?:(le|la|ce|les)\s(premier|première|deuxième|second|seconde|troisième|quatrième|dernier|dernière|deux premiers)\s(?:de ces textes|d'entre eux|texte)?\s?,?\s?)?dans (sa|leur) rédaction antérieure",tail)
        if q:
            who=q.group(2); 
            if who is None: tgt=lst if q.group(3)=='leur' or len(lst)==1 else lst[-1:]
            elif who.startswith('derni'): tgt=lst[-1:]
            elif who=='deux premiers': tgt=lst[:2]
            else: tgt=lst[ORD[who]:ORD[who]+1]
            phrase=re.sub(r'\s+',' ',tail[q.start():q.end()+160]).split(' : ')[0].split(';')[0]
            phrase=re.split(r',\s(?:et|ensemble)\s',phrase)[0].strip(' ,')
            for t in tgt: res[(code,t)]=phrase
    for m in re.finditer(r"ancien(?:ne)?s? articles?\s+((?:"+NUM+r")(?:\s(?:et|,)\s(?:"+NUM+r"))*)\s+(?:du|de la)\s+(code [^,;:.]{3,60})",txt):
        for x in re.findall(NUM,m.group(1)): res.setdefault((m.group(2).strip(),nn(x)),'ancien article')
    for m in re.finditer(r"articles?\s+("+NUM+r")\s+ancien(?:ne)?s?\s+(?:du|de la)\s+(code [^,;:.]{3,60})",txt):
        res.setdefault((m.group(2).strip(),nn(m.group(1))),'article ancien')
    return res
def prior_hit(norm, targets):
    """qualifying phrase if the decision interprets `norm` (data id) in a prior wording / former numbering, else ''"""
    parts = norm.split('-', 2)
    if len(parts) < 3:
        return ''
    code = CODE_OF.get(parts[0] + '-' + parts[1])
    if not code:
        return ''
    for (c, t), ph in targets.items():
        if c.lower().startswith(code[:14]) and t == parts[2].lower():
            return ph
    return ''
