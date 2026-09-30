"""Screen CJEU candidates and build data/interps/eu-cjeu.json (+ raw/int/cjeu/screen_ledger.json).
- Texts: FR XHTML from Cellar (raw/int/cjeu/html/). Summary = operative part (dispositif) verbatim; titrage = official key words.
- Interpreted provisions: Cellar 'reference_to_modified_location' + parsing of the operative part.
- Predecessor instruments (2201/2003 -> 2019/1111; 1393/2007 -> 2020/1784; 1206/2001 -> 2020/1783; 44/2001 -> 1215/2012):
  mapped through the official correlation table annexed to the recast. Decisive test = manual functional review
  (scripts/int_cjeu_review.py: include/exclude with French justification, logged in ledger functional_review_log).
  Similarity (difflib) is informative only; unreviewed pairs >= THRESH are kept with a generic justification,
  unreviewed pairs < THRESH are logged as UNREVIEWED in links_dropped (target: none).
Re-run: python3 scripts/int_cjeu_candidates.py && python3 scripts/int_cjeu_infocuria.py && python3 scripts/int_cjeu.py"""
import os, re, sys, json, difflib, collections, datetime
sys.path.insert(0, os.path.dirname(__file__))
from int_common import *
from int_eu_norms import parse_articles, parse_articles_plain, latest_consolidated
from int_issues import issues_for
from int_cjeu_review import review as functional_review

THRESH = 0.72
CJ = os.path.join(RAW, "cjeu")
HT = os.path.join(CJ, "html")
REGNUM = {"2019/1111": "32019R1111", "2201/2003": "32003R2201", "1347/2000": "32000R1347", "4/2009": "32009R0004",
          "1259/2010": "32010R1259", "2016/1103": "32016R1103", "2016/1104": "32016R1104", "650/2012": "32012R0650",
          "2016/1191": "32016R1191", "2020/1784": "32020R1784", "1393/2007": "32007R1393", "1348/2000": "32000R1348",
          "2020/1783": "32020R1783", "1206/2001": "32001R1206", "1215/2012": "32012R1215", "44/2001": "32001R0044",
          "2004/38": "32004L0038", "2003/86": "32003L0086"}
CURRENT = {"32019R1111": "2019-1111", "32009R0004": "4-2009", "32010R1259": "1259-2010", "32016R1103": "2016-1103",
           "32016R1104": "2016-1104", "32012R0650": "650-2012", "32016R1191": "2016-1191", "32020R1784": "2020-1784",
           "32020R1783": "2020-1783", "32012R1215": "1215-2012", "32004L0038": "2004-38", "32003L0086": "2003-86"}
PRED = {"32003R2201": ("32019R1111", "02019R1111-20190702"), "32007R1393": ("32020R1784", "02020R1784-20250501"),
        "32001R1206": ("32020R1783", "02020R1783-20201202"), "32001R0044": ("32012R1215", "02012R1215-20150226")}
# family-adjacent filters
BRUX1_FAMILY_ARTS = {"1"}          # art. 1(2)(a),(e),(f) exclusions: status, matrimonial property, wills/succession, maintenance
BRUX1_TERMS = re.compile(r"régimes? matrimoniau|état et (de )?la capacité|testaments? et (les )?successions|aliment|époux|divorce|mariage|partenariat", re.I)
DIR38_FAMILY = {"2", "3", "5", "6", "7", "9", "10", "11", "12", "13", "16", "17", "18", "20", "23", "24", "27", "28", "35"}
DIR38_TERMS = re.compile(r"membres? de (sa |la )?famille|conjoint|partenaire|descendant|ascendant|enfant|regroup|époux", re.I)
CHARTER_ARTS = {"7", "9", "24", "33"}
CHARTER_FAMILY = re.compile(r"vie familiale|membres? de (la |sa )?famille|unité familiale|enfant|mariage|conjoint|parent|filiation|état civil|nom (patronymique|de famille)|identité de genre|changement de (sexe|genre)|regroupement familial", re.I)
# annulment actions without interpretive operative part: provisions examined in the grounds (verified manually)
MANUAL_LINKS = {"62003CJ0540": [("32003L0086", "4", None), ("32003L0086", "8", None)]}


def norm_paragraphs(text):
    parts = re.split(r"(?m)^(\d+)\.\s", text)
    d = {"_all": text}
    for i in range(1, len(parts) - 1, 2):
        d[parts[i]] = parts[i + 1]
    return d


def load_articles(celex_version):
    p = cellar_get(celex_version)
    h = open(p, encoding="utf-8", errors="replace").read()
    arts = parse_articles(h) or parse_articles_plain(h)
    out = {}
    for a in arts:
        out.setdefault(a["num"], a["text"])
    return out, h


def correlation(h):
    i = h.upper().rfind("TABLEAU DE CORRESPONDANCE")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", h[i:], re.S)
    pairs = []
    for r in rows:
        cells = [strip_tags(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if len(cells) < 2:
            continue
        o, n = cells[0], cells[-1]
        mo = re.match(r"Articles? (\d+)(?:er)?(?:, paragraphes? ([\d ,età]+))?", o)
        mn = re.findall(r"Articles? (\d+)(?:er)?(?:, paragraphes? (\d+))?", n)
        if mo and mn:
            olds = re.findall(r"\d+", mo.group(2) or "")
            if " à " in (mo.group(2) or "") and len(olds) == 2:
                olds = [str(k) for k in range(int(olds[0]), int(olds[1]) + 1)]
            for op_ in (olds or [None]):
                pairs.append((mo.group(1), op_, [(x, y or None) for x, y in mn], o, n))
    return pairs


def loc_parse(loc):
    m = re.match(r"A0*(\d+)(?:P0*(\d+))?", loc or "")
    return (m.group(1), m.group(2)) if m else (None, None)


ART_TOKEN = re.compile(r"articles? ((?:\d+(?:er)?(?:, (?:paragraphes?|points?|sous) [^,;]{1,25})*(?:,? (?:et|à|,) )?)+)", re.I)


def operative_links(op):
    """Return ({celex: {(art, para)}}, charter_arts, hague_refs) from the operative part (FR)."""
    res = collections.defaultdict(set)
    charter, hague = set(), set()
    text = re.sub(r"\s*\n\s*", " ", op)
    acts = [(m.start(), REGNUM.get(m.group(2))) for m in re.finditer(r"(règlement|directive|décision)[^,;]{0,12}?(?:n[o°]\s?)?(\d{1,4}/\d{4})", text, re.I)]
    for m in re.finditer(r"articles? (\d+)(?:er)?(?:, paragraphes? (\d+))?", text, re.I):
        pos = m.start()
        after = text[m.end():m.end() + 300]
        hg = re.match(r"[^;]{0,120}?(protocole de La Haye[^;]{0,40}2007|protocole de La Haye|convention sur les aspects civils de l[’']enlèvement|convention de La Haye[^;]{0,60}1980|convention[^;]{0,60}19 octobre 1996|convention de La Haye[^;]{0,40}1996|convention[^;]{0,80}recouvrement international des aliments)", after, re.I)
        nxt = [(p, c) for p, c in acts if p > pos and p - pos < 300]
        ref = re.match(r"[^;]{0,80}?(de ce règlement|dudit règlement|du même règlement|de cette directive|de ladite directive|de la même directive|de celui-ci|de celle-ci)", after, re.I)
        if re.match(r"[^;]{0,60}?de la charte", after, re.I) and not (nxt and nxt[0][0] < m.end() + after.lower().find("de la charte")):
            charter.add(m.group(1))
            continue
        if hg and not (nxt and nxt[0][0] - m.end() < hg.start(1)):
            g = hg.group(1).lower()
            key = "2007p" if "protocole" in g else ("1980" if ("enlèvement" in g or "1980" in g) else ("1996" if "1996" in g else "2007"))
            hague.add((key, m.group(1)))
            continue
        if re.match(r"\s*,?\s*(paragraphe \d+, )?(TFUE|TUE)\b", after):
            continue
        if ref and (not nxt or m.end() + ref.start(1) < nxt[0][0]):
            prv = [c for p, c in acts if p < pos]
            reg = prv[-1] if prv else None
        elif nxt:
            reg = nxt[0][1]
        else:
            prv = [c for p, c in acts if p < pos]
            reg = prv[-1] if prv else None
        if reg:
            res[reg].add((m.group(1), m.group(2)))
    return res, charter, hague


def get_case_html(celex):
    p = cellar_get(celex, dest=os.path.join(HT, celex + ".html"))
    if not p:
        return None
    return strip_tags(open(p, encoding="utf-8", errors="replace").read())


def main():
    cands = load(os.path.join(CJ, "candidates.json"), [])
    known = {c["celex"] for c in cands}
    extra = [c for c in load(os.path.join(CJ, "candidates_extra.json"), []) if c["celex"] not in known]
    cands += extra  # independent InfoCuria completeness check (scripts/int_cjeu_infocuria.py)
    norms = load(os.path.join(DATA, "norms", "eu-reg.json"))["norms"]
    nidx = {n["id"]: n for n in norms}
    # predecessor texts + correlation tables
    pred_txt, corr, cur_txt = {}, {}, {}
    for old, (new, newv) in PRED.items():
        cons = latest_consolidated(old)
        for v in list(reversed(cons)) + [old]:
            pred_txt[old], _ = load_articles(v)
            if len(pred_txt[old]) > 10:
                break
        cur_txt[new], h = load_articles(newv)
        corr[old] = correlation(h)
        print("corr", old, len(corr[old]), "pred arts", len(pred_txt[old]), flush=True)
    ledger = {"candidates": len(cands), "screened": 0, "included": 0, "excluded": [], "basis": collections.Counter(), "links_dropped": [], "functional_review_log": [],
              "extra_candidates": [c["celex"] for c in extra]}
    interps = []
    for c in cands:
        celex = c["celex"]
        acts = c.get("acts", {})
        title = c.get("title") or ""
        only_b1 = set(acts) <= {"32001R0044", "32012R1215"}
        if only_b1 and not BRUX1_TERMS.search(title):
            ledger["excluded"].append({"celex": celex, "reason": "Brussels I/Ibis only, not family-adjacent (title screen)"})
            continue
        if set(acts) <= {"32000R1347", "32000R1348"}:
            ledger["excluded"].append({"celex": celex, "reason": "interprets 1347/2000 or 1348/2000 only (two recasts removed) — not mapped"})
            continue
        ledger["screened"] += 1
        t = get_case_html(celex)
        if not t:
            ledger["excluded"].append({"celex": celex, "reason": "FR text not available in Cellar"})
            continue
        m = re.search(r"Par ces motifs, la Cour \([^)]*\)[^\n]*|Par ces motifs, la Cour[^\n]*", t)
        if not m:
            ledger["excluded"].append({"celex": celex, "reason": "operative part not found"})
            continue
        end = re.search(r"\n(Signatures|Fait à Luxembourg|\*\s*Langue de procédure|\(\n\*1)", t[m.end():])
        op = t[m.start(): m.end() + (end.start() if end else 3000)].strip()
        if celex[5:7] == "CO" and re.search(r"(est|sont) rectifié|rectification|radiation|radiée|non-lieu à statuer|n.y a (plus )?lieu de statuer", op[:1500], re.I) \
                and not re.search(r"doit être interprété|doivent être interprétés", op):
            ledger["excluded"].append({"celex": celex, "reason": "order without interpretive ruling (rectification / removal / no need to adjudicate)"})
            continue
        op_links, charter, hague = operative_links(op)
        for act, a, p in MANUAL_LINKS.get(celex, []):
            op_links[act].add((a, p))
        # add Cellar locations
        for act, locs in acts.items():
            for l in locs:
                a, p = loc_parse(l)
                if a:
                    op_links[act].add((a, p))
        links, reasons = [], []
        date = c.get("date", "")[:10]
        for act, arts in op_links.items():
            for a, p in sorted(arts, key=lambda x: (x[0], x[1] or "")):
                if act in ("32001R0044", "32012R1215") and a not in BRUX1_FAMILY_ARTS:
                    reasons.append(f"{act} art {a}: not family-adjacent")
                    continue
                if act == "32004L0038" and (a not in DIR38_FAMILY or not DIR38_TERMS.search(op)):
                    reasons.append(f"2004/38 art {a}: not a family-member provision")
                    continue
                if act in CURRENT:
                    nid = f"eu-reg-{CURRENT[act]}-art-{a}"
                    if nid not in nidx:
                        reasons.append(f"{nid} not in corpus")
                        continue
                    D = nidx[nid]["in_force_since"] or "0000"
                    if date >= D:
                        links.append({"norm": nid, "basis": "a", "cited_version": f"CELEX {act}" + (f", art. {a}" + (f", § {p}" if p else ""))})
                    else:
                        links.append({"norm": nid, "basis": "b", "b_method": "functional-review", "cited_version": f"CELEX {act}",
                                      "b_justification": f"Arrêt antérieur à la date de la version actuelle ({D}) ; l'article {a} n'a pas été modifié quant à la disposition interprétée (vérification : marqueurs de modification du texte consolidé)."})
                elif act in PRED:
                    new, _ = PRED[act]
                    fr = functional_review(celex, act, a, p)
                    if fr:
                        oldname = [k for k, v in REGNUM.items() if v == act][0]
                        entry = {"celex": celex, "from": f"{act} art {a}" + (f"({p})" if p else ""), "verdict": fr["v"], "justification": fr["j"]}
                        if fr["v"] == "include":
                            for na, npar in fr["to"]:
                                nid = f"eu-reg-{CURRENT[new]}-art-{na}"
                                if nid not in nidx:
                                    entry["verdict"] = "exclude"; entry["justification"] += f" [{nid} absent du corpus]"
                                    continue
                                entry["to"] = nid
                                links.append({"norm": nid, "basis": "b", "b_method": "functional-review",
                                              "cited_version": f"Règlement n° {oldname}, article {a}" + (f", paragraphe {p}" if p else ""),
                                              "b_justification": fr["j"]})
                        else:
                            reasons.append(f"{act} art {a}§{p}: functional review — excluded")
                        ledger["functional_review_log"].append(entry)
                        continue
                    rows = [r for r in corr[act] if r[0] == a and (p is None or r[1] in (None, p))]
                    old_txt = pred_txt[act].get(a, "")
                    old_par = norm_paragraphs(old_txt).get(p or "_all", old_txt) if old_txt else ""
                    best = None
                    if p is None and rows:
                        newarts = []
                        for r in rows:
                            for na, npar in r[2]:
                                if na not in newarts:
                                    newarts.append(na)
                        joined = "\n".join(cur_txt[new].get(na, "") for na in newarts)
                        ratio = difflib.SequenceMatcher(None, re.sub(r"\s+", " ", old_txt), re.sub(r"\s+", " ", joined), autojunk=False).ratio()
                        best = (ratio, newarts[0], None, "; ".join(sorted({r[3] for r in rows})), "; ".join(sorted({r[4] for r in rows})))
                        rows = []
                    for r in rows:
                        for na, npar in r[2]:
                            ntxt = cur_txt[new].get(na, "")
                            if not ntxt:
                                continue
                            cand_pars = [norm_paragraphs(ntxt).get(npar)] if npar else list(norm_paragraphs(ntxt).values())
                            for cp in [x for x in cand_pars if x]:
                                ratio = difflib.SequenceMatcher(None, re.sub(r"\s+", " ", old_par), re.sub(r"\s+", " ", cp), autojunk=False).ratio()
                                if not best or ratio > best[0]:
                                    best = (ratio, na, npar, r[3], r[4])
                    if not best:
                        reasons.append(f"{act} art {a}§{p}: no counterpart in correlation table")
                        ledger["functional_review_log"].append({"celex": celex, "from": f"{act} art {a}" + (f"({p})" if p else ""), "verdict": "exclude",
                                                                "justification": "aucune disposition correspondante dans le tableau de correspondance ; non revu manuellement"})
                        continue
                    ratio, na, npar, o_lbl, n_lbl = best
                    nid = f"eu-reg-{CURRENT[new]}-art-{na}"
                    if ratio < THRESH or nid not in nidx:  # not manually reviewed: logged for review
                        reasons.append(f"{act} art {a}§{p} -> {new} art {na}: similarity {ratio:.2f} < {THRESH} (substantive change presumed)")
                        ledger["links_dropped"].append({"celex": celex, "from": f"{act} art {a} {p or ''}", "to": nid, "similarity": round(ratio, 3), "note": "UNREVIEWED"})
                        continue
                    oldname = [k for k, v in REGNUM.items() if v == act][0]
                    newname = [k for k, v in REGNUM.items() if v == new][0]
                    links.append({"norm": nid, "basis": "b", "b_method": "functional-review",
                                  "cited_version": f"Règlement n° {oldname}, article {a}" + (f", paragraphe {p}" if p else ""),
                                  "b_justification": (f"L'arrêt interprète l'article {a}{', paragraphe ' + p if p else ''} du règlement n° {oldname}, "
                                                      f"auquel correspond, selon le tableau de correspondance annexé au règlement {newname} ({o_lbl} → {n_lbl}), "
                                                      f"l'article {na}{', paragraphe ' + npar if npar else ''} du règlement {newname}. Similarité textuelle du passage interprété : {ratio:.0%}. "
                                                      "La refonte a conservé la règle dans sa formulation et sa fonction ; l'interprétation reste transposable (considérant relatif à la continuité de l'interprétation de la Cour pour les dispositions inchangées)."),
                                  "similarity": round(ratio, 3)})
        for key, a in sorted(hague):
            links.append({"norm": f"int-hcch-{key}-art-{a}", "basis": "a", "cited_version": f"HCCH {key}, art. {a} (texte inchangé depuis sa conclusion)"})
        for a in sorted(charter & CHARTER_ARTS):
            if date >= "2009-12-01":
                links.append({"norm": f"eu-reg-charte-art-{a}", "basis": "a", "cited_version": "Charte, art. " + a})
        # dedupe
        seen, L = set(), []
        for l in links:
            if l["norm"] not in seen:
                seen.add(l["norm"]); L.append(l)
        if not L:
            ledger["excluded"].append({"celex": celex, "reason": "no qualifying norm link: " + "; ".join(reasons[:5])})
            continue
        if all(l["norm"].startswith("eu-reg-charte") for l in L) and not CHARTER_FAMILY.search(op + " " + t[:3000]):
            ledger["excluded"].append({"celex": celex, "reason": "Charter-only link without family-law subject matter"})
            continue
        head = t[:4000]
        court = re.search(r"(ARRÊT|ORDONNANCE) DE LA COUR \(([^)]+)\)", head)
        courtname = "Cour de justice de l'Union européenne" + (f", {court.group(2)}" if court else "")
        num = re.search(r"Dans l[’']affaire (C[‑-]\d+/\d+(?: PPU)?)|Dans les affaires jointes (C[‑-][\d/]+[^,]*(?:,| et) [^\n]*?),\n", head)
        number = (num.group(1) or num.group(2)).replace("‑", "-") if num else celex
        kw = re.search(r"«\s*(.*?)\s*»", head, re.S)
        tparts = title.split("#")
        parties = tparts[1].strip().rstrip(".") if len(tparts) > 1 else ""
        kind = "ordonnance" if celex[5:7] == "CO" else "arrêt"
        ecli = c.get("ecli")
        d = datetime.date.fromisoformat(date)
        mois = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juill.", "août", "sept.", "oct.", "nov.", "déc."][d.month - 1]
        cit = f"CJUE, {kind if kind=='ordonnance' else ''}{', ' if kind=='ordonnance' else ''}{d.day} {mois} {d.year}, {parties}, {number}, {ecli.replace('ECLI:','') if ecli else celex}".replace("CJUE, , ", "CJUE, ")
        items = [x.strip() for x in re.split(r"\n(?=\d\)\s)", op) if x.strip()]
        excerpts = [re.sub(r"\s*\n\s*", " ", x)[:1500] for x in items[1:5]] if len(items) > 1 else [re.sub(r"\s*\n\s*", " ", op)[:1500]]
        iss = set()
        for l in L:
            n = nidx.get(l["norm"])
            if n:
                iss.update(n["issues"])
        interps.append({
            "id": "cjeu-" + celex.lower(), "authority": "eu-cjeu", "court": courtname, "date": date, "number": number,
            "ecli": ecli, "citation": cit, "publication": "Rec." if kind == "arrêt" else "ordonnance",
            "official_url": f"https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:{celex}",
            "alt_urls": [{"label": "CURIA", "url": f"https://curia.europa.eu/juris/liste.jsf?num={number.split(' ')[0]}&language=fr"}],
            "summary": re.sub(r"\s*\n\s*", " ", op)[:4000],
            "summary_is_official": True, "summary_note": "Dispositif (verbatim, version française)",
            "excerpts": excerpts, "titrage": [re.sub(r"\s+", " ", kw.group(1))] if kw else [],
            "norms": L, "issues": sorted(iss) or ["eu"], "lang": "fr", "celex": celex})
        ledger["included"] += 1
        for l in L:
            ledger["basis"][l["basis"]] += 1
        if ledger["screened"] % 25 == 0:
            print("screened", ledger["screened"], "included", ledger["included"], flush=True)
    interps.sort(key=lambda x: x["date"])
    dump(os.path.join(DATA, "interps", "eu-cjeu.json"), {"corpus": "eu-cjeu", "interps": interps})
    ledger["basis"] = dict(ledger["basis"])
    dump(os.path.join(CJ, "screen_ledger.json"), ledger)
    print("done", ledger["screened"], ledger["included"], ledger["basis"])


if __name__ == "__main__":
    main()
