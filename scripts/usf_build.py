#!/usr/bin/env python3
"""Assemble interps (us-scotus, us-ca8), judge-made rules (us-common), norm back-links, coverage ledgers.
Inputs: data/norms/us-{usc,cfr,const}.json, raw/us/screen.jsonl (+ cap_hits/cl_hits texts), raw/us/temporal.jsonl.
Temporal rule (SCOPE §2): link basis 'a' if decision date >= D(norm); else only if raw/us/temporal.jsonl holds a
functional-review / text-identity verdict that the interpreted language is identical in wording and function ('b');
otherwise the link is dropped (pending links are written to raw/us/temporal_pending.json for usf_temporal.py)."""
import glob, json, os, re, sys, datetime, urllib.request, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import ROOT, RAW, RULES
from usf_canon import CANON

TODAY = datetime.date.today().isoformat()
N = {}
for c in ["us-usc", "us-cfr", "us-const"]:
    for n in json.load(open(f"{ROOT}/data/norms/{c}.json"))["norms"]:
        n["interps"] = []
        N[n["id"]] = n
ISS = set()
def _w(n):
    ISS.add(n["id"]); [_w(c) for c in n["children"]]
for n in json.load(open(ROOT + "/data/issues/us.json"))["nodes"]:
    _w(n)

HCCH_D = {"1980": "1988-07-01", "1965": "1969-02-10", "1970": "1972-10-07", "1993": "2008-04-01"}
HCCH_RE = re.compile(r"^int-hcch-(1965|1970|1980|1993)-art(\d+[a-z]?)$")

RULE_SOURCES = {
 "parental-rights": ["262 U.S. 390", "268 U.S. 510", "321 U.S. 158", "406 U.S. 205", "530 U.S. 57"],
 "unwed-fathers": ["405 U.S. 645", "434 U.S. 246", "441 U.S. 380", "463 U.S. 248", "491 U.S. 110"],
 "tpr-due-process": ["452 U.S. 18", "455 U.S. 745", "519 U.S. 102"],
 "family-integrity": ["431 U.S. 494", "431 U.S. 816"],
 "marriage-fundamental-right": ["388 U.S. 1", "434 U.S. 374", "482 U.S. 78", "576 U.S. 644"],
 "nonmarital-children-ep": ["391 U.S. 68", "430 U.S. 762", "486 U.S. 456"],
 "sex-classifications-family": ["440 U.S. 268", "421 U.S. 7", "582 U.S. 47"],
 "race-custody": ["466 U.S. 429"],
 "access-to-divorce": ["401 U.S. 371", "419 U.S. 393", "519 U.S. 102"],
 "personal-jurisdiction-family": ["436 U.S. 84", "345 U.S. 528", "495 U.S. 604"],
 "divisible-divorce-ffc": ["317 U.S. 287", "325 U.S. 226", "334 U.S. 541", "354 U.S. 416", "334 U.S. 343"],
 "domestic-relations-exception": ["62 U.S. 582", "136 U.S. 586", "504 U.S. 689", "547 U.S. 293"],
 "rooker-feldman": ["263 U.S. 413", "460 U.S. 462", "544 U.S. 280"],
 "younger-abstention-family": ["401 U.S. 37", "442 U.S. 415", "571 U.S. 69"],
 "icara-habitual-residence": ["589 U.S. 68"], "icara-grave-risk-ameliorative": ["596 U.S. 666"],
 "icara-well-settled": ["572 U.S. 1"], "icara-rights-of-custody": ["560 U.S. 1"], "icara-mootness": ["568 U.S. 165"],
 "federal-preemption-family-property": ["439 U.S. 572", "453 U.S. 210", "454 U.S. 46", "490 U.S. 581", "581 U.S. 214", "569 U.S. 483", "481 U.S. 619"],
 "civil-contempt-support": ["485 U.S. 624", "564 U.S. 431"],
}
# Decisions screened as relevant but excluded by editorial review (outside the SCOPE §4 perimeter or overruled)
EXCLUDE = {
 "410 U.S. 113": "abortion regulation — outside perimeter; overruled by Dobbs v. Jackson Women's Health Org., 597 U.S. 215 (2022)",
 "410 U.S. 179": "abortion regulation — outside perimeter; framework overruled by Dobbs (2022)",
 "402 U.S. 62": "abortion statute vagueness — outside perimeter",
 "428 U.S. 52": "abortion regulation (parental consent) — outside perimeter; Roe/Casey framework overruled by Dobbs (2022)",
 "443 U.S. 622": "abortion (parental consent) — outside perimeter; framework overruled by Dobbs (2022)",
 "450 U.S. 398": "abortion (parental notice) — outside perimeter; framework overruled by Dobbs (2022)",
 "497 U.S. 417": "abortion (parental notice) — outside perimeter; framework overruled by Dobbs (2022)",
 "405 U.S. 438": "contraception access of unmarried persons — outside family-law perimeter",
 "450 U.S. 464": "criminal statutory rape — outside perimeter",
 "467 U.S. 253": "juvenile pretrial detention — outside perimeter",
 "462 U.S. 669": "Title VII pregnancy benefits — outside perimeter",
 "511 U.S. 127": "jury selection (Batson) — outside perimeter",
 "427 U.S. 160": "42 U.S.C. 1981 private school admissions — outside perimeter",
 "413 U.S. 756": "Establishment Clause — outside perimeter",
 "457 U.S. 202": "public education of undocumented children — outside perimeter",
 "468 U.S. 609": "freedom of association (Jaycees) — outside perimeter",
 "390 U.S. 629": "obscenity / minors — outside perimeter",
 "415 U.S. 709": "ballot filing fees — outside perimeter",
 "503 U.S. 594": "state taxation of military retirement pay — not a family-law question",
 "486 U.S. 825": "ERISA welfare-plan garnishment — not a family-law question",
 "579 U.S. 582": "abortion regulation — outside perimeter; framework overruled by Dobbs (2022)",
 "372 U.S. 144": "loss of nationality as punishment — outside perimeter",
 "363 U.S. 603": "termination of social security benefits of deportees — outside perimeter",
 "435 U.S. 647": "visa-holder domicile for tuition — outside perimeter",
 "377 U.S. 163": "loss of nationality of naturalized citizens — outside perimeter",
}

RULE_D_FROM = {k: v[0] for k, v in RULE_SOURCES.items()}  # D = date of the first (founding) rule source


# ------------------------------------------------------------------ helpers
def fold(s):
    s = s.replace("\u00ad", "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    return s


def build_index(text):
    """alphanumeric-only lowercase stream + map to original indices (robust to whitespace, dash, quote and
    reporter-spacing differences); the excerpt finally stored is the ORIGINAL source span."""
    out, idx = [], []
    for i, ch in enumerate(text):
        if ch.isalnum():
            out.append(ch.lower()); idx.append(i)
    return "".join(out), idx


def verify(ex, text, cache):
    if "ix" not in cache:
        cache["ix"] = build_index(text)
    ns, idx = cache["ix"]
    q = "".join(ch.lower() for ch in ex if ch.isalnum())
    if len(q) < 45:
        return None
    k = ns.find(q)
    if k < 0:
        return None
    start, end = idx[k], idx[k + len(q) - 1] + 1
    # extend to include trailing closing punctuation/quote present in the requested excerpt
    while end < len(text) and text[end] in ".,;:”\"')]’" and len(ex) and not ex.rstrip()[-1].isalnum():
        end += 1
        if text[end - 1] in ".;:":
            break
    orig = text[start:end]
    orig = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", orig)
    orig = re.sub(r"\s+", " ", orig).strip()
    return orig


def evidence_ok(nid, text):
    """The opinion text must actually cite the section (guards against LLM mis-linking, e.g. reporter page numbers)."""
    n = N.get(nid)
    if not n or n["corpus"] == "us-const":
        return True
    if n["corpus"] == "us-usc":
        sec = n["source_ids"]["usc"].split()[2].split("(")[0]
        alts = [sec] + [f.split()[-1] for f in n["source_ids"].get("former_classification", [])]
        return any(re.search(r"(?:§|U\.\s?S\.\s?C\.(?:\s?A\.)?|[Ss]ection)\s*§?\s*" + re.escape(a) + r"(?![0-9])", text) for a in alts)
    if n["corpus"] == "us-cfr":
        sec = n["source_ids"]["cfr"].split()[-1]
        return re.search(re.escape(sec) + r"(?![0-9])", text) is not None
    return True


def year(d):
    return (d or "")[:4]


def cite_parts(c):
    m = re.match(r"(\d+) (U\.S\.|F\.2d|F\.3d|F\.4th) (\d+)$", c)
    return m.groups() if m else None


URLCACHE_F = RAW + "/ca8_urls.json"
URLCACHE = json.load(open(URLCACHE_F)) if os.path.exists(URLCACHE_F) else {}


def head_ok(u):
    if u in URLCACHE:
        return URLCACHE[u]
    try:
        req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (flb research)"})
        ok = urllib.request.urlopen(req, timeout=30).status == 200
    except Exception:
        ok = False
    URLCACHE[u] = ok
    return ok


def ca8_official(docket, date):
    """ecf.ca8.uscourts.gov/opndir/YY/MM/<docket digits>P.pdf (opinions posted since 1995)"""
    if not docket or not date or date < "1995-01-01":
        return None
    m = re.search(r"(\d{2})-(\d{3,4})", docket)
    if not m:
        return None
    num = m.group(1) + m.group(2)
    y, mo = int(date[:4]), int(date[5:7])
    for dy, dm in [(y, mo), (y + (mo == 12), 1 if mo == 12 else mo + 1), (y - (mo == 1), 12 if mo == 1 else mo - 1)]:
        u = f"https://ecf.ca8.uscourts.gov/opndir/{str(dy)[2:]}/{dm:02d}/{num}P.pdf"
        if head_ok(u):
            return u
    return None


# ------------------------------------------------------------------ load screening
def load_screen():
    res = {}
    for line in open(RAW + "/screen.jsonl"):
        d = json.loads(line); res[d["_file"]] = d
    return res


def main():
    screen = load_screen()
    temporal = {}
    if os.path.exists(RAW + "/temporal.jsonl"):
        for line in open(RAW + "/temporal.jsonl"):
            d = json.loads(line)
            # conservative override: interpretations of predecessor provisions (other Code / former text) are not 'identical in wording'
            if d.get("identical") and re.search(r"1939 Code|\(1939\)|predecessor|formerly codified|interpreted former|former \d+ U\.S\.C", d.get("justification", "")):
                d["identical"] = False; d["override"] = "predecessor provision"
            temporal[(d["interp"], d["norm"])] = d
    interps = {"us-scotus": {}, "us-ca8": {}}
    pending, stats = [], {"screened": 0, "relevant": 0, "no_excerpt": [], "dropped_links": 0, "a": 0, "b": 0, "excluded_changed": 0}
    by_cite = {}
    for fn, s in screen.items():
        stats["screened"] += 1
        if not s.get("relevant"):
            continue
        rec = json.load(open(fn))
        court = "us-scotus" if ("Supreme" in (rec.get("court") or "") or rec.get("rep") == "us") else "us-ca8"
        cites = rec.get("citations") or []
        if rec.get("rep") == "us" and not any(" U.S. " in c for c in cites):
            cites = [f"{rec['vol']} U.S. {int(rec['file'].split('-')[0])}"] + cites
        if court == "us-scotus":
            off = [c for c in cites if " U.S. " in c]
        else:
            off = [c for c in cites if re.search(r" F\.(2d|3d|4th) ", c)]
        cp = cite_parts(off[0]) if off else None
        date = rec.get("date")
        if off and off[0] in EXCLUDE:
            stats.setdefault("excluded_editorial", []).append(f"{rec['name']}, {off[0]}: {EXCLUDE[off[0]]}"); continue
        if court == "us-scotus" and cp and int(cp[2]) >= 1301:
            stats.setdefault("excluded_editorial", []).append(f"{rec['name']}, {off[0]}: in-chambers opinion of a single Justice"); continue
        rec["docket"] = re.sub(r"^(Nos?\.\s*)+", "", (rec.get("docket") or "").strip()) or None
        if cp:
            iid = f"{court}-{cp[0]}-{cp[1].replace('.', '').lower()}-{cp[2]}".replace("-us-", "-") if court == "us-scotus" else f"{court}-{cp[0]}-{cp[1].replace('.', '').lower()}-{cp[2]}"
        else:
            dk = re.sub(r"[^0-9a-z-]", "", (rec.get("docket") or "").lower().replace(" ", ""))[:30]
            iid = f"{court}-{dk}-{date}"
        if iid in by_cite:  # duplicate (CAP + CourtListener overlap): keep the first
            continue
        cache = {}
        exs = []
        for e in CANON.get(off[0] if off else "", []):
            v = verify(e, rec["text"], cache)
            if v:
                exs.append(v)
            else:
                stats.setdefault("canon_unverified", []).append(f"{off[0]}: {e[:60]}")
        for e in s.get("excerpts", [])[:4]:
            v = verify(e, rec["text"], cache)
            if v and v not in exs:
                exs.append(v)
        if not exs:
            stats["no_excerpt"].append(f"{rec.get('name')} ({date}) {fn}")
            continue
        stats["relevant"] += 1
        # official URL
        alt = []
        if court == "us-scotus":
            if cp and int(cp[0]) <= 578:
                official = f"https://www.loc.gov/item/usrep{int(cp[0]):03d}{int(cp[2]):03d}/"
                if rec.get("pdf_url"):
                    alt.append({"label": "Supreme Court (PDF)", "url": rec["pdf_url"]})
            else:
                official = rec.get("pdf_url")
            if cp:
                alt.append({"label": "CourtListener", "url": f"https://www.courtlistener.com/c/U.S./{cp[0]}/{cp[2]}/"})
            cit = f"{rec['name']}, {off[0] if off else 'No. ' + str(rec.get('docket'))} ({year(date)})"
            number = rec.get("docket")
        else:
            official = rec.get("pdf_url") or ca8_official(rec.get("docket"), date)
            if cp:
                cl = f"https://www.courtlistener.com/c/{cp[1]}/{cp[0]}/{cp[2]}/"
                if official:
                    alt.append({"label": "CourtListener", "url": cl})
                else:
                    official = cl
            elif rec.get("cl_url") and not official:
                official = rec["cl_url"]
            elif rec.get("cl_url"):
                alt.append({"label": "CourtListener", "url": rec["cl_url"]})
            cit = f"{rec['name']}, {off[0] if off else 'No. ' + str(rec.get('docket'))} (8th Cir. {year(date)})"
            number = rec.get("docket")
        if rec.get("cap_url"):
            alt.append({"label": "Caselaw Access Project (text)", "url": rec["cap_url"]})
        # norm links + temporal rule
        links = []
        for nid in dict.fromkeys(s.get("norms", [])):
            nid = nid.strip().lower()
            hm = HCCH_RE.match(nid)
            if hm:
                D = HCCH_D[hm.group(1)]
            elif nid.startswith("us-common-"):
                continue  # handled below
            elif nid in N:
                if not evidence_ok(nid, rec["text"]):
                    stats["dropped_links"] += 1; continue
                D = N[nid]["in_force_since"]
            else:
                stats["dropped_links"] += 1; continue
            if not D or (date and date >= D):
                links.append({"norm": nid, "basis": "a"}); stats["a"] += 1
            else:
                t = temporal.get((iid, nid))
                if t is not None and t.get("D") and t["D"] != D:
                    t = None  # norm amended again since the review -> review again
                if t is None:
                    pending.append({"interp": iid, "norm": nid, "date": date, "D": D, "file": fn, "provisions": s.get("provisions", []),
                                    "excerpts": exs, "name": rec["name"]})
                elif t.get("identical"):
                    links.append({"norm": nid, "basis": "b", "b_method": t.get("method", "functional-review"),
                                  "b_justification": t["justification"]}); stats["b"] += 1
                else:
                    stats["excluded_changed"] += 1
        # Hague 1980 applied in an ICARA petition: also link 22 U.S.C. 9003 when the opinion cites it (or former 42 U.S.C. 11603)
        if any(l["norm"].startswith("int-hcch-1980") for l in links) and not any(l["norm"] == "us-usc-22-9003" for l in links) \
                and evidence_ok("us-usc-22-9003", rec["text"]):
            links.append({"norm": "us-usc-22-9003", "basis": "a" if date >= N["us-usc-22-9003"]["in_force_since"] else "b"}); stats["a"] += 1
        rule_links = [x.strip().lower() for x in s.get("norms", []) if x.strip().lower().startswith("us-common-")]
        rec_out = {
            "id": iid, "authority": court,
            "court": "Supreme Court of the United States" if court == "us-scotus" else "United States Court of Appeals for the Eighth Circuit",
            "date": date, "number": number, "ecli": None, "citation": cit, "publication": "published",
            "official_url": official, "alt_urls": alt,
            "summary": s.get("summary", "").strip(), "summary_is_official": False,
            "excerpts": exs[:3], "titrage": [], "norms": links,
            "provisions": s.get("provisions", []),
            "issues": [i for i in s.get("issues", []) if i in ISS], "lang": "en",
            "_rules": rule_links, "_cite": off[0] if off else None, "_file": fn,
        }
        by_cite[iid] = rec_out
        interps[court][iid] = rec_out
    # ---------------------------------------------------------- judge-made rules
    cite2id = {r["_cite"]: r["id"] for r in by_cite.values() if r["_cite"]}
    rules = []
    for key, heading, issues, xrefs in RULES:
        rid = f"us-common-{key}"
        srcs = [cite2id.get(c) for c in RULE_SOURCES.get(key, [])]
        missing = [c for c, i in zip(RULE_SOURCES.get(key, []), srcs) if not i]
        srcs = [i for i in srcs if i]
        dates = [by_cite[i]["date"] for i in srcs]
        D = by_cite[cite2id[RULE_D_FROM[key]]]["date"] if RULE_D_FROM[key] in cite2id else (min(dates) if dates else None)
        quotes = []
        for i in srcs:
            r = by_cite[i]
            quotes.append(f"“{r['excerpts'][0]}” ({r['citation']})")
        rules.append({"id": rid, "corpus": "us-common", "side": "us", "lang": "en", "kind": "judge-made-rule", "num": key,
                      "heading": heading, "path": [{"label": "Federal judge-made rules (U.S. Supreme Court)"}],
                      "summary_rule": heading + ". " + " ".join(quotes), "rule_sources": srcs,
                      "in_force_since": D, "status": "in force", "applies_to": ["US"],
                      "official_url": by_cite[srcs[0]]["official_url"] if srcs else None, "alt_urls": [],
                      "source_ids": {"leading_cases": RULE_SOURCES.get(key, []), "missing_sources": missing},
                      "d_method": "date of the founding U.S. Supreme Court decision of the rule (first rule source)",
                      "issues": issues, "xrefs": xrefs, "interps": []})
    R = {r["id"]: r for r in rules}
    for court in interps:
        for iid, r in interps[court].items():
            for rid, rr in R.items():  # a rule source always interprets (establishes) its rule
                if iid in rr["rule_sources"] and rid not in r["_rules"]:
                    r["_rules"].append(rid)
            for rid in r.pop("_rules"):
                if rid not in R:
                    continue
                D = R[rid]["in_force_since"]
                if iid in R[rid]["rule_sources"] or not D or r["date"] >= D:
                    r["norms"].append({"norm": rid, "basis": "a"}); stats["a"] += 1
                else:
                    t = temporal.get((iid, rid))
                    if t is None:
                        pending.append({"interp": iid, "norm": rid, "date": r["date"], "D": D, "file": r["_file"], "provisions": r["provisions"],
                                        "excerpts": r["excerpts"], "name": r["citation"]})
                    elif t.get("identical"):
                        r["norms"].append({"norm": rid, "basis": "b", "b_method": "functional-review", "b_justification": t["justification"]}); stats["b"] += 1
                    else:
                        stats["excluded_changed"] += 1
    # drop interps with no qualifying link; fill issues fallback; back-links
    out = {}
    allnorms = {**N, **R}
    for court in interps:
        lst = []
        for iid, r in sorted(interps[court].items(), key=lambda x: (x[1]["date"] or "")):
            if not r["norms"]:
                continue
            if not r["issues"]:
                iss = []
                for l in r["norms"]:
                    iss += allnorms.get(l["norm"], {}).get("issues", [])
                r["issues"] = list(dict.fromkeys(iss))[:3] or (["us.abduction.icara"] if l["norm"].startswith("int-hcch-1980") else [])
            for l in r["norms"]:
                if l["norm"] in allnorms:
                    allnorms[l["norm"]]["interps"].append(iid)
            for k in ["_cite", "_file"]:
                r.pop(k, None)
            lst.append(r)
        out[court] = lst
        json.dump({"corpus": court, "generated": TODAY, "interps": lst}, open(f"{ROOT}/data/interps/{court}.json", "w"), indent=2, ensure_ascii=False)
    for c in ["us-usc", "us-cfr", "us-const"]:
        d = json.load(open(f"{ROOT}/data/norms/{c}.json"))
        for n in d["norms"]:
            n["interps"] = sorted(set(N[n["id"]]["interps"]))
        json.dump(d, open(f"{ROOT}/data/norms/{c}.json", "w"), indent=2, ensure_ascii=False)
    json.dump({"corpus": "us-common", "generated": TODAY, "norms": rules}, open(f"{ROOT}/data/norms/us-common.json", "w"), indent=2, ensure_ascii=False)
    json.dump(pending, open(RAW + "/temporal_pending.json", "w"), indent=1)
    json.dump(URLCACHE, open(URLCACHE_F, "w"))
    stats["pending_temporal"] = len(pending)
    stats["included"] = {k: len(v) for k, v in out.items()}
    json.dump(stats, open(RAW + "/build_stats.json", "w"), indent=1)
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in stats.items()}))


if __name__ == "__main__":
    os.makedirs(ROOT + "/data/interps", exist_ok=True)
    main()
