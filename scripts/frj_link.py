# -*- coding: utf-8 -*-
"""Link indexed decisions (CASS / JADE / CONSTIT) to perimeter norms and apply the temporal rule (SCOPE §2).
Phase 1 (--phase=1): compute candidate links, write work/frj/need_versions.txt.
Phase 2 (--phase=2): evaluate basis a/b with LEGI version histories (work/frj/legi cache) and write
work/frj/links_<src>.jsonl (all evaluated links incl. excluded ones with reason)."""
import os, re, sys, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from frj_common import *

PHASE = next((a.split("=")[1] for a in sys.argv if a.startswith("--phase=")), "1")
CIV = {"CHAMBRE_CIVILE_1", "CHAMBRE_CIVILE_2", "ASSEMBLEE_PLENIERE", "CHAMBRE_MIXTE", "AVIS", "CHAMBRE_CIVILE", "CHAMBRES_REUNIES"}
CRIM = {"CHAMBRE_CRIMINELLE"}
OTHER_CH = {"CHAMBRE_CIVILE_3", "CHAMBRE_COMMERCIALE", "CHAMBRE_SOCIALE"}
STRONG = {"cass": {"vu", "liens", "sommaire", "titrage", "motif"},
          "jade": {"liens", "sommaire", "titrage", "motif"},
          "constit": {"objet", "dispositif", "motif", "sommaire", "titrage", "text"}}


FAMILY_TITLE = (r"famil|mariage|\bmarié|conjoint|couples?\b|filiation|paternit|maternit|adopt(?!ion\s+(?:de|du|des|d')\s*(?:la\s+|l')?(?:partie|loi|texte|projet|ordonnance|mesures?|amendements?|dispositions?))|\bparent|divorce|"
                r"séparation de corps|succession|héritier|réserve héréditaire|donation|libéralit|testament|nom de famille|nom d'usage|"
                r"changement de nom|prénom|nationalit|bioéthique|procréation|gestation|embryon|pacte civil|concubin|pension alimentaire|"
                r"prestation compensatoire|violences conjugales|violences au sein du couple|violences intrafamiliales|réversion|état civil|regroupement familial|"
                r"veuv|orphelin|tutelle|curatelle|émancipation|inceste|non-représentation|abandon de famille|"
                r"autorité parentale|droit de visite|interruption volontaire|contraception|régime matrimonial|indivision|"
                r"mutations? à titre gratuit|droits de mutation|liens familiaux")


def family_core(corpus, num, path):
    """Core family-law norms (screened for all chambers)."""
    if corpus == "fr-cc":
        m = re.match(r"(\d+)", num)
        b = int(m.group(1)) if m else -1
        return path.startswith("livre_ier") or 720 <= b <= 1099 or 1387 <= b <= 1581 or b == 1873
    if corpus == "fr-cpc":
        return path.startswith("livre_iii/titre_ier") or path.startswith("livre_iii/titre_ii/") or path.startswith("livre_iii/titre_iii")
    return corpus in ("fr-casf", "fr-csp", "fr-cgi", "fr-css", "fr-ceseda", "fr-cpce", "fr-coj", "fr-cp", "fr-cpp", "fr-textes")


def load_perimeter(cat, mode="union"):
    """union: norm-agent files ∪ own definition (used for linking, robust to later norm-file changes);
    canonical: norm-agent files when present, else own definition (used for the published output)."""
    nf = perimeter_from_norm_files()
    per = {}
    for corpus, arts in cat.items():
        own = {n for n, a in arts.items() if a["perimeter"]}
        if corpus in nf:
            theirs = {n for n, a in arts.items() if a["id"] in nf[corpus]}
            per[corpus] = (theirs | own) if mode == "union" else theirs
        else:
            per[corpus] = own
    return per, sorted(nf)


def scope_of(src, d):
    """Return None if decision out of screened set, else 'civ'|'crim'|'other'|'ce'|'cc'."""
    if "error" in d:
        return None
    if src == "cass":
        f = d.get("formation", "")
        if f in CIV:
            return "civ"
        if f in CRIM:
            return "crim"
        if f in OTHER_CH:
            return "other"
        if f == "" and re.search(r"Assemblée plénière|Chambre mixte|avis", d.get("titre", ""), re.I):
            return "civ"
        return None
    if src == "jade":
        if not re.match(r"Conseil d.[ÉE]tat", d.get("juridiction", "")):
            return None
        if d.get("publi_recueil") not in ("A", "B"):
            return None
        return "ce"
    if src == "constit":
        return "cc" if d.get("nature") in ("DC", "QPC") else None
    return None


def expand(cat_sorted, corpus, c):
    """Expand 'X à Y' ranges using catalog order."""
    if "range_from" not in c:
        return [c["num"]]
    lst = cat_sorted.get(corpus, [])
    try:
        i, j = lst.index(c["range_from"]), lst.index(c["num"])
    except ValueError:
        return [c["num"]]
    if 0 <= j - i <= 40:
        return lst[i + 1:j + 1]
    return [c["num"]]


def candidate_links(src, d, cat, per, cat_sorted):
    sc = scope_of(src, d)
    if not sc:
        return sc, []
    out = []
    ancien = [c for c in d["cites"] if c.get("ancien")]
    for c in d["cites"]:
        corpus = c["corpus"]
        if corpus not in cat:
            continue
        if corpus == "fr-const" and src != "constit":
            continue
        nums = expand(cat_sorted, corpus, c) if corpus != "fr-textes" else [c["num"] if c["num"] in cat[corpus] else c.get("texte_alt", "")]
        for num in nums:
            if num not in per.get(corpus, ()):
                continue
            a = cat[corpus][num]
            if sc == "crim" and corpus not in ("fr-cp", "fr-cpp"):
                continue
            if sc == "other" and not family_core(corpus, num, a["path"]):
                out.append({"norm": a["id"], "corpus": corpus, "num": num, "status": "excluded", "reason": "chambre-hors-perimetre-matiere"})
                continue
            strong = bool(set(c["sources"]) & STRONG[src])
            L = {"norm": a["id"], "corpus": corpus, "num": num, "sources": c["sources"], "n": c["n"]}
            for f in ("alineas", "redaction", "devenu"):
                if f in c:
                    L[f] = c[f]
            if c.get("ancien"):
                L.update(status="excluded", reason="ancienne-numerotation")
            elif not strong:
                L.update(status="excluded", reason="mention-faible")
            else:
                L["status"] = "candidate"
            if c.get("devenu"):
                L["ancien_nums"] = [x["num"] for x in ancien if x["corpus"] == corpus]
            out.append(L)
    if src == "constit":
        tt = d.get("titre", "")
        subj = re.findall(r"\[(.*?)\]", tt)
        fam = re.search(FAMILY_TITLE, " ".join(subj) if subj else tt, re.I)
        other = any(L["status"] == "candidate" and L["corpus"] != "fr-const" for L in out)
        for L in out:
            if L["corpus"] == "fr-const" and L["status"] == "candidate":
                if set(L.get("sources", [])) <= {"vu", "objet"}:
                    L.update(status="excluded", reason="mention-procedurale")
                elif not (fam or other):
                    L.update(status="excluded", reason="hors-perimetre-matiere")
    # dedupe by norm keeping best status
    best = {}
    rank = {"candidate": 0, "excluded": 1}
    for L in out:
        k = L["norm"]
        if k not in best or rank[L["status"]] < rank[best[k]["status"]]:
            best[k] = L
    return sc, list(best.values())


# ---------------- temporal rule ----------------
def paras_of(html_text):
    t = re.sub(r"</p>|<br\s*/?>|</div>|\n\s*\n", "\n", html_text or "")
    t = clean_xml_text(t)
    return [normalize_for_compare(p) for p in t.split("\n") if normalize_for_compare(p)]


NOMINAL = [("tribunaux de grande instance", "tribunaux judiciaires"), ("tribunal de grande instance", "tribunal judiciaire"),
           ("nouveau code de procedure civile", "code de procedure civile"),
           ("greffier en chef", "directeur des services de greffe judiciaires"),
           ("code de la famille et de l'aide sociale", "code de l'action sociale et des familles")]


def nominal(paras):
    out = []
    for p in paras:
        for a, b in NOMINAL:
            p = p.replace(a, b)
        out.append(p)
    return out


def paras_orig(html_text):
    t = re.sub(r"</p>|<br\s*/?>|</div>|\n\s*\n", "\n", html_text or "")
    t = clean_xml_text(t)
    return [norm_ws(p) for p in t.split("\n") if normalize_for_compare(p)]


def version_at(versions, date):
    for v in versions:
        if v.get("debut") and v.get("fin") and v["debut"] <= date < v["fin"]:
            return v
    return None


def get_ver(vid):
    p = f"{WORK}/legi/{vid}.json"
    return json.load(open(p)) if os.path.exists(p) else None


def fr_date(iso):
    y, m, dd = iso.split("-")
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"][int(m) - 1]
    return f"{'1er' if dd == '01' else int(dd)} {mois} {y}"


def ngrams(words, n=8):
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def evaluate(L, date, cat, dec_text_fn, dc=False):
    """Return updated L with basis/b_method/b_justification or status excluded."""
    a = cat[L["corpus"]][L["num"]]
    D = a["debut"]
    cur = get_ver(a["legiarti"])
    target = None
    why_target = "version en vigueur à la date de la décision"
    red = L.get("redaction")
    vers = (cur or {}).get("versions") or []
    if red and red.get("date") and vers:
        rd = red["date"]
        if red["kind"].startswith("anterieure"):
            target = version_at(vers, rd)
            why_target = f"rédaction antérieure ({red['text']})"
        elif red["kind"] in ("issue", "resultant"):
            cands = sorted([v for v in vers if v.get("debut") and v["debut"] >= rd], key=lambda v: v["debut"])
            target = cands[0] if cands else None
            why_target = f"rédaction visée ({red['text']})"
        else:
            target = version_at(vers, rd)
            why_target = f"rédaction visée ({red['text']})"
    if dc and vers and (not red or not red.get("date")):
        # DC review happens before promulgation: the interpreted text is the version created by the loi déférée
        import datetime as _dt
        lim = (_dt.date.fromisoformat(date) + _dt.timedelta(days=400)).isoformat()
        cands = sorted([v for v in vers if v.get("debut") and date < v["debut"] <= lim], key=lambda v: v["debut"])
        if cands:
            target = cands[0]
            why_target = "rédaction issue de la loi déférée, entrée en vigueur après la décision"
    if L.get("devenu"):
        # interpreted text = old article (former numbering) in force just before the current version
        olds = []
        for on in L.get("ancien_nums", []):
            oa = cat[L["corpus"]].get(on)
            ocur = get_ver(oa["legiarti"]) if oa else None
            if ocur:
                ov = version_at(ocur.get("versions") or [], (D or "2999-01-01"))
                # version in force the day before D
                ov = next((v for v in ocur.get("versions") or [] if v.get("fin") == D), None) or ov
                if ov:
                    olds.append((on, ov))
        if not cur or not olds:
            L.update(status="excluded", reason="devenu-version-inconnue")
            return L
        ctext = paras_of(cur.get("text_html"))
        for on, ov in olds:
            ovr = get_ver(ov["id"])
            if ovr and paras_of(ovr.get("text_html")) == ctext and ctext:
                L.update(status="included", basis="a" if date >= D else "b", cited_version=ov["id"],
                         b_method="text-identical",
                         b_justification=(f"La décision applique l'ancien article {on} ({ov['id']}, en vigueur du {fr_date(ov['debut'])} au {fr_date(ov['fin'])}), "
                                          f"devenu l'article {L['num']} ; comparaison automatisée : texte identique, après normalisation, à la version actuelle ({a['legiarti']})."))
                if L["basis"] == "a":
                    L.pop("b_method"); L["note"] = L.pop("b_justification")
                return L
        L.update(status="excluded", reason="devenu-texte-different")
        return L
    if target is None:
        if date >= D:
            L.update(status="included", basis="a", cited_version=a["legiarti"])
            return L
        if not cur:
            L.update(status="excluded", reason="historique-indisponible")
            return L
        target = version_at(vers, date)
        if target is None:
            L.update(status="excluded", reason="aucune-version-a-la-date")
            return L
    if target["id"] == a["legiarti"]:
        L.update(status="included", basis="a" if date >= D else "b", cited_version=a["legiarti"])
        if L["basis"] == "b":
            L.update(b_method="text-identical", b_justification=(f"La version interprétée ({why_target}) est la version actuellement en vigueur ({a['legiarti']}, depuis le {fr_date(D)}) : "
                                                                 "texte identique par construction."))
        return L
    tv = get_ver(target["id"])
    if not tv or not cur:
        L.update(status="excluded", reason="historique-indisponible")
        return L
    old, new = paras_of(tv.get("text_html")), paras_of(cur.get("text_html"))
    basis = "a" if date >= D else "b"
    vdesc = f"{target['id']}, en vigueur du {fr_date(target['debut'])} au {fr_date(target['fin'])}"
    if old and old == new:
        L.update(status="included", basis=basis, cited_version=target["id"], b_method="text-identical",
                 b_justification=(f"Version interprétée : {vdesc} ({why_target}). Comparaison automatisée : texte identique, après normalisation "
                                  f"(casse, accents, espaces, ponctuation), à la version actuelle {a['legiarti']} en vigueur depuis le {fr_date(D)}."))
        if basis == "a":
            L.pop("b_method"); L["note"] = L.pop("b_justification")
        return L
    if old and nominal(old) == nominal(new):
        L.update(status="included", basis=basis, cited_version=target["id"], b_method="functional-review",
                 b_justification=(f"Version interprétée : {vdesc} ({why_target}). La seule différence avec la version actuelle {a['legiarti']} "
                                  f"(en vigueur depuis le {fr_date(D)}) est une substitution terminologique sans portée normative "
                                  f"(par ex. « tribunal de grande instance » devenu « tribunal judiciaire » par la loi n° 2019-222 du 23 mars 2019, "
                                  f"« nouveau code de procédure civile » devenu « code de procédure civile ») : la règle interprétée est identique "
                                  f"dans sa lettre et sa fonction."))
        if basis == "a":
            L.pop("b_method"); L["note"] = L.pop("b_justification")
        return L
    old, new = nominal(old), nominal(new)
    newset = set(new)
    unchanged = [i for i, p in enumerate(old) if p in newset]
    changed = [i for i, p in enumerate(old) if p not in newset]
    added = [p for p in new if p not in set(old)]
    al = L.get("alineas")
    keep_idx = None
    method_note = ""
    if al and old:
        idx = []
        for x in al:
            i = (x - 1) if x > 0 else len(old) + x
            idx.append(i)
        if all(0 <= i < len(old) for i in idx) and all(i in unchanged for i in idx):
            keep_idx = idx
            method_note = "alinéa(s) expressément visé(s) par la décision"
        else:
            L.update(status="excluded", reason="alinea-vise-modifie")
            return L
    elif old and unchanged:
        txt = dec_text_fn()
        w = normalize_for_compare(txt).split()
        g = ngrams(w)
        def hits(p):
            return len(ngrams(p.split()) & g)
        hu = [i for i in unchanged if hits(old[i]) > 0]
        hc = [i for i in changed if hits(old[i]) > 0]
        ha = [p for p in added if hits(p) > 0]
        if hu and not hc and not ha:
            keep_idx = hu
            method_note = "alinéa(s) repris textuellement dans la décision (concordance de séquences de 8 mots)"
        else:
            L.update(status="excluded", reason="texte-modifie")
            return L
    else:
        L.update(status="excluded", reason="texte-modifie")
        return L
    als = ", ".join(str(i + 1) for i in keep_idx)
    po = paras_orig(tv.get("text_html"))
    quote = (po[keep_idx[0]] if len(po) == len(old) else old[keep_idx[0]])[:160]
    L.update(status="included", basis=basis, cited_version=target["id"], b_method="functional-review", alineas_interpretes=[i + 1 for i in keep_idx],
             b_justification=(f"Version interprétée : {vdesc} ({why_target}). Le texte de l'article a été modifié depuis, mais l'alinéa {als} "
                              f"interprété ({method_note} ; début : « {quote}… ») figure à l'identique dans la version actuelle {a['legiarti']} "
                              f"(en vigueur depuis le {fr_date(D)}) ; les modifications portent sur {len(changed)} autre(s) alinéa(s) "
                              f"et n'affectent ni la lettre ni la fonction de la règle appliquée par la décision."))
    return L


def dec_fulltext(src, d):
    p = f"{RAW}/{d['path']}"
    try:
        x = open(p, encoding="utf-8").read()
    except Exception:
        return ""
    m = re.search(r"<CONTENU>(.*?)</CONTENU>", x, re.S)
    body = clean_xml_text(m.group(1)) if m else ""
    return body + "\n" + "\n".join(d.get("ana", []))


def main():
    cat = load_catalog()
    per, nf = load_perimeter(cat)
    cat_sorted = {c: sorted(arts, key=num_key) for c, arts in cat.items()}
    need = set()
    stats = {}
    for src in ("cass", "jade", "constit"):
        ip = f"{WORK}/{src}_index.jsonl"
        if not os.path.exists(ip):
            continue
        st = collections.Counter()
        outf = open(f"{WORK}/links_{src}.jsonl", "w") if PHASE == "2" else None
        for line in open(ip):
            d = json.loads(line)
            sc, links = candidate_links(src, d, cat, per, cat_sorted)
            if sc is None:
                st["hors_champ"] += 1
                continue
            st["screened"] += 1
            st[f"screened_{sc}"] += 1
            if not links:
                continue
            st["candidates"] += 1
            date = d.get("date_dec", "")
            cache = {}
            def txt():
                if "t" not in cache:
                    cache["t"] = dec_fulltext(src, d)
                return cache["t"]
            for L in links:
                if L["status"] != "candidate":
                    continue
                a = cat[L["corpus"]][L["num"]]
                if PHASE == "1":
                    if date < a["debut"] or L.get("redaction") or L.get("devenu") or src == "constit":
                        need.add(a["legiarti"])
                        for on in L.get("ancien_nums", []):
                            if on in cat[L["corpus"]]:
                                need.add(cat[L["corpus"]][on]["legiarti"])
                else:
                    evaluate(L, date, cat, txt, dc=(src == "constit" and d.get("nature") == "DC"))
            if PHASE == "2":
                inc = [L for L in links if L["status"] == "included"]
                weak = ("mention-faible", "chambre-hors-perimetre-matiere", "ancienne-numerotation")
                st["linked"] += 1 if any(L["status"] == "included" or L.get("reason") not in weak for L in links) else 0
                for L in links:
                    st[f"link_{L['status']}"] += 1
                    if L["status"] == "excluded":
                        st[f"excl_{L['reason']}"] += 1
                    elif L["status"] == "included":
                        st[f"basis_{L['basis']}"] += 1
                        if L.get("b_method"):
                            st[f"bmethod_{L['b_method']}"] += 1
                if inc:
                    st["included"] += 1
                outf.write(json.dumps({"src": src, "id": d["id"], "scope": sc, "date": date, "links": links}, ensure_ascii=False) + "\n")
        if outf:
            outf.close()
        stats[src] = dict(st)
        print(src, dict(st), flush=True)
    if PHASE == "1":
        open(f"{WORK}/need_versions.txt", "w").write("\n".join(sorted(need)) + "\n")
        print("need versions", len(need))
    else:
        json.dump({"stats": stats, "perimeter_from_norm_files": nf,
                   "perimeter_sizes": {c: len(v) for c, v in per.items()}}, open(f"{WORK}/link_stats.json", "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
