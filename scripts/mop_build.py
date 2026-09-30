#!/usr/bin/env python3
"""Assemble data/mapping/cpc-mo.json (SCOPE §4.5) from the v2 quality-pass checkpoints of scripts/mop_map2.py
(raw/mop/v2_m.jsonl = mapping decisions on full texts; raw/mop/v2_v.jsonl = independent verification), the CPC article list
(raw/mop/cpc_articles.json, Tricoteuses LEGI mirror, branch main + future states from branch 'futur') and the Missouri corpora.
Writes the coverage ledger data/coverage/mapping-cpc-mo.json.

Final classification rules (deterministic, applied here):
  * equivalence = verifier's classification, never higher than the mapping pass (equivalent > partial > functional > none);
    mo_norms = ids kept by the verifier (subset of the proposed ids); no ids -> none.
  * 'functional' without high verification confidence -> none (pruned as weak). Livre VI (overseas application) -> none unless the verifier kept a
    counterpart with high confidence and the class is equivalent/partial.
  * verified = verifier returned the article, its verbatim quotes (CPC + every kept Missouri id) are found in the texts, and
    confidence is not low. Notes: the verifier's corrected notes are used when it found the proposed notes not grounded.
FRCP cross-links: from the Missouri Rules' own committee notes ("same as Rule N of the Federal Rules of Civil Procedure",
"Compare: Rule N ...") -> basis "committee_note" (verified, with quote); otherwise from the curated table MO_FRCP ->
basis "editorial" (verified false); the editorial table is not applied to a subdivision whose own committee note names its federal source. Only rules with a page on the FRCP annotated browser are linked.
Usage: python3 scripts/mop_build.py
"""
import os, re, json, datetime
from collections import Counter

ROOT = "/home/user/workspace/flb"
RAW = os.path.join(ROOT, "raw", "mop")
TODAY = datetime.date.today().isoformat()
LF = "https://www.legifrance.gouv.fr/codes/article_lc/"
FRCPB = "https://vagabondo73.github.io/frcp-annotated-browser/content/provision-frcp-{}.html"
RANK = {"none": 0, "functional": 1, "partial": 2, "equivalent": 3}
CORE = ("livre_ier", "livre_ii")

# Editorial Missouri Rule -> FRCP table (structural correspondences; Missouri's 1973 Rules were modelled on the FRCP).
MO_FRCP = {
    "41": ["1"], "41.01": ["1"], "41.05": ["1"], "42": ["2"], "43": ["5"], "43.02": ["5"], "44": ["6"],
    "52.01": ["17"], "52.02": ["17"], "52.04": ["19"], "52.05": ["20"], "52.06": ["21"], "52.07": ["22"], "52.08": ["23"],
    "52.09": ["23.1"], "52.10": ["23.2"], "52.11": ["14"], "52.12": ["24"], "52.13": ["25"],
    "53": ["3"], "54": ["4"],
    "55.01": ["7"], "55.02": ["10"], "55.03": ["11"], "55.025": ["5.2"], "84.015": ["5.2"], "55.04": ["8"], "55.05": ["8"],
    "55.06": ["18"], "55.07": ["8"], "55.08": ["8"], "55.09": ["8"], "55.10": ["8"], "55.11": ["10"], "55.12": ["10"],
    "55.15": ["9"], "55.16": ["9"], "55.18": ["9"], "55.26": ["7"], "55.27": ["12"], "55.28": ["43"], "55.31": ["12"], "55.32": ["13"],
    "55.33": ["15"], "55.34": ["15"], "55.35": ["8"],
    "56": ["26"], "57.01": ["33"], "57.02": ["27"], "57.03": ["30"], "57.04": ["31"], "57.05": ["28"],
    "57.06": ["29"], "57.07": ["32"], "57.08": ["45"], "57.09": ["45"], "58.01": ["34"], "58.02": ["45"],
    "59": ["36"], "60": ["35"], "61": ["37"], "62": ["16"], "66.01": ["42"], "66.02": ["42"], "67": ["41"], "68.01": ["53"],
    "68.02": ["53"], "69.01": ["38"], "69.02": ["38"], "69.03": ["47"], "69.04": ["47"], "69.025": ["47"], "70": ["51"],
    "71": ["48", "49"], "72": ["50"], "73": ["52"],
    "74.01": ["54", "58"], "74.02": ["54"], "74.03": ["77"], "74.04": ["56"], "74.05": ["55"], "74.06": ["60"],
    "76": ["69"], "77": ["54"], "78": ["59"], "79": ["63"], "85": ["64"], "87": ["57"], "90": ["69"], "92": ["65"], "99": ["64"],
}


def nq(t):
    t = (t or "").lower()
    t = re.sub(r"[’‘`´]", "'", t); t = re.sub(r"[“”«»„]", '"', t); t = re.sub(r"[–—‑]", "-", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def wtok(t):
    return re.findall(r"[\w$]+", nq(t))


def match(quote, text):
    """'exact' | 'near' (>=90% of the quote's words found in order within a window of the text) | None"""
    if found(quote, text):
        return "exact"
    q, T = wtok(quote), wtok(text)
    if len(q) < 5:
        return None
    import difflib
    best = 0.0
    idx = [i for i, w in enumerate(T) if w in set(q[:3])]
    for i in idx:
        win = T[max(0, i - 3): i + int(len(q) * 1.4) + 3]
        sm = difflib.SequenceMatcher(None, q, win, autojunk=False)
        best = max(best, sum(b.size for b in sm.get_matching_blocks()) / len(q))
        if best >= 0.999:
            break
    return "near" if best >= 0.9 else None


def found(quote, text):
    q = nq(quote).strip(" .;,:\"'")
    if not q:
        return False
    T = nq(text)
    parts = [p.strip(" .;,:\"'") for p in re.split(r"\s*(?:…|\.\.\.|\[…\]|\[\.\.\.\])\s*", q) if p.strip(" .;,:\"'")]
    return all(p in T for p in parts)


def committee_frcp(mo):
    """Missouri Rule num -> [{rule, quote}] from the Rule's committee notes / text."""
    out = {}
    pat = re.compile(r"(?:Rules?|Rule No\.)\s+(\d+(?:\.\d)?)((?:\s*\([a-z0-9]+\))*)(?:\s*(?:and|,)\s*\d+(?:\.\d)?(?:\s*\([a-z0-9]+\))*)*\s+of the Federal Rules of Civil Procedure")
    for n in mo.values():
        if not n["id"].startswith("mo-rules-"):
            continue
        for src, t in (("committee_note", " ".join(n.get("committee_notes") or [])), ("rule_text", n.get("text") or "")):
          for m in pat.finditer(t):
            seg = m.group(0)
            for r in re.findall(r"(?<![\d.])(\d+(?:\.\d)?)(?=\s*(?:\(|and|,|\s+of the Federal))", seg):
                s = max(0, m.start() - 60)
                out.setdefault(n["num"], [])
                if r not in [x["rule"] for x in out[n["num"]]]:
                    out[n["num"]].append({"rule": r, "source": src, "quote": re.sub(r"\s+", " ", t[s:m.end()]).strip()})
    return out


def frcp_for(ids, avail, cn):
    out = []
    for i in ids:
        if not i.startswith("mo-rules-"):
            continue
        num = i[len("mo-rules-"):]
        seen = [x["rule"] for x in out]
        for c in cn.get(num, []):
            if c["rule"] in avail and c["rule"] not in seen:
                out.append({"rule": c["rule"], "url": FRCPB.format(c["rule"]), "via": i, "basis": c["source"], "verified": True, "evidence": c["quote"]})
                seen.append(c["rule"])
        for r in ([] if cn.get(num) else (MO_FRCP.get(num) or MO_FRCP.get(num.split(".")[0]) or [])):
            if r in avail and r not in seen:
                out.append({"rule": r, "url": FRCPB.format(r), "via": i, "basis": "editorial", "verified": False})
                seen.append(r)
    return out


def jl(p, key):
    out = {}
    if os.path.exists(p):
        for l in open(p):
            d = json.loads(l)
            if d.get("error") and d[key] in out and not out[d[key]].get("error"):
                continue
            out[d[key]] = d
    return out


def main():
    ca = json.load(open(os.path.join(RAW, "cpc_articles.json")))
    arts, head = ca["articles"], ca.get("mirror_head")
    avail = set(json.load(open(os.path.join(RAW, "frcp_rules.json")))["rules"])
    mo = {}
    for c in ("mo-rules", "mo-rsmo"):
        for n in json.load(open(os.path.join(ROOT, "data", "norms", f"{c}.json")))["norms"]:
            mo[n["id"]] = n
    cn = committee_frcp(mo)
    M, V = {}, {}
    for b in jl(os.path.join(RAW, "v2_m.jsonl"), "bid").values():
        if not b.get("error"):
            for x in b["articles"]:
                M[x["num"]] = x
    for b in jl(os.path.join(RAW, "v2_v.jsonl"), "bid").values():
        if not b.get("error"):
            for x in b["articles"]:
                V[x["num"]] = x
    entries, gaps, missing, unver = [], [], [], []
    cnt, prune = Counter(), Counter()
    for a in arts:
        liv, core = a["livre"], a["livre"] in CORE
        m, v = M.get(a["num"]), V.get(a["num"])
        if m is None:
            missing.append(a["num"]); continue
        prop_ids = [i for i in m.get("mo_norms", []) if i in mo]
        prop_eq = m["equivalence"] if prop_ids else "none"
        note_fr, note_en, revised = m.get("note_fr"), m.get("note_en"), False
        if v:
            ids = [i for i in prop_ids if i in set(v.get("mo_norms", []))]
            eq = v.get("equivalence", prop_eq)
            if RANK.get(eq, 0) > RANK[prop_eq]:
                eq = prop_eq
            conf = v.get("confidence", "low")
            if not v.get("grounded", True) and v.get("note_fr") and v.get("note_en"):
                note_fr, note_en, revised = v["note_fr"], v["note_en"], True
            qmo = {q.get("id"): q.get("quote") for q in v.get("mo_quotes", []) if isinstance(q, dict)}
            cpc_m = match(v.get("cpc_quote"), a["text"])
            mo_m = {i: (match(qmo.get(i), mo[i].get("text") or "") if qmo.get(i) else None) for i in ids}
            cpc_ok, mo_ok = bool(cpc_m), {i: bool(x) for i, x in mo_m.items()}
        else:
            ids, eq, conf, cpc_ok, mo_ok, qmo, cpc_m, mo_m = prop_ids, prop_eq, "low", False, {}, {}, None, {}
        if not ids:
            eq = "none"
        pruned = None
        if eq == "functional" and conf != "high":
            pruned = f"weak functional match (verification confidence {conf})"
        if liv == "livre_vi" and eq != "none" and not (conf == "high" and eq in ("equivalent", "partial")):
            pruned = "Livre VI overseas-application article: no genuine counterpart established"
        if pruned:
            prune[pruned] += 1
            eq = "none"
        if eq == "none" and ids:
            if pruned:
                note_fr = f"Pas d'équivalent retenu en droit du Missouri (rapprochement écarté : {('correspondance seulement fonctionnelle, confiance insuffisante' if 'functional' in pruned else 'disposition d’application outre-mer sans homologue')})."
                note_en = f"No Missouri counterpart retained ({pruned})."
            ids = []
        if not core and eq == "none":
            cnt[(liv, "screened-none")] += 1
            continue
        verified = bool(v) and cpc_ok and all(mo_ok.get(i) for i in ids) and conf != "low"
        if not verified:
            unver.append(a["num"])
        e = {"cpc_article": a["num"], "cpc_legiarti": a["legiarti"], "cpc_url": a.get("cpc_url"), "legifrance_url": LF + a["legiarti"],
             "cpc_livre": liv, "cpc_path": [p["label"] for p in a["path"]], "cpc_in_force_since": a["debut"],
             "mo_norms": ids, "mo_axes": sorted({ax for i in ids for ax in mo[i].get("axes", [])}),
             "equivalence": eq, "confidence": conf, "verified": verified, "note_fr": note_fr, "note_en": note_en,
             "frcp": frcp_for(ids, avail, cn),
             "verification": {"cpc_quote": (v or {}).get("cpc_quote"), "cpc_quote_found": cpc_ok, "cpc_quote_match": cpc_m,
                              "mo_quotes": [{"id": i, "quote": qmo.get(i), "found": mo_ok.get(i, False), "match": mo_m.get(i)} for i in ids],
                              "proposed": {"mo_norms": prop_ids, "equivalence": prop_eq},
                              **({"downgraded_from": prop_eq} if RANK[eq] < RANK[prop_eq] else {}),
                              **({"verifier_equivalence": v.get("equivalence")} if v else {}),
                              **({"pruned": pruned} if pruned else {}), **({"notes_revised_by_verifier": True} if revised else {}),
                              **({"issue": v.get("issue")} if v and v.get("issue") else {})},
             "annotation_method": "LLM-assisted on full texts (mapping pass + independent verification pass with verbatim quotes checked mechanically); not individually human-reviewed"}
        if a.get("fin", "2999") < "2999-01-01":
            e["cpc_version_ends"] = a["fin"]
            e["cpc_successors"] = [{k: s[k] for k in ("date", "legiarti", "debut") if k in s} | ({"removed": True} if s.get("removed") else {}) for s in a.get("successors", [])[:1]]
        if not a.get("cpc_url"):
            gaps.append(f"art. {a['num']}: no page on the CPC annotated browser index (cpc_url null)")
        entries.append(e)
        cnt[(liv, eq)] += 1
    for x in missing:
        gaps.append(f"art. {x}: no mapping decision — re-run scripts/mop_map2.py")
    fut = ca.get("future_states", [])
    ending = ca.get("versions_ending_before_2999", [])
    byfin = Counter(next(a["fin"] for a in arts if a["num"] == n) for n in ending)
    out = {"mapping": "cpc-mo", "generated": TODAY, "axis": "procedure",
           "description": "Article-to-rule correspondences between the French Code de procédure civile and Missouri civil procedure (Supreme Court Rules 41–101; RSMo chapters 506–517, 525; family-law RSMo chapters and Rule 88 where relevant). SCOPE §4.5.",
           "sources": {"cpc": f"https://git.tricoteuses.fr/codes/code_de_procedure_civile.git (branch main @ {head}; future states from branch futur)",
                       "cpc_browser": "https://vagabondo73.github.io/cpc-annotated-browser/content/index.html",
                       "frcp_browser": "https://vagabondo73.github.io/frcp-annotated-browser/content/index.html"},
           "equivalence_scale": {"equivalent": "substantially the same rule for the same matter", "partial": "same matter, covered in part or with materially different conditions/effects",
                                 "functional": "different technique/institution serving a genuinely comparable procedural function", "none": "no Missouri counterpart in the corpora"},
           "confidence_scale": "verifier's confidence in the final classification: high | medium | low",
           "entries": entries}
    os.makedirs(os.path.join(ROOT, "data", "mapping"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data", "mapping", "cpc-mo.json"), "w"), indent=2, ensure_ascii=False)
    core_total = sum(1 for a in arts if a["livre"] in CORE)
    mo_used = Counter(i for e in entries for i in e["mo_norms"])
    proc_ids = [i for i, n in mo.items() if "procedure" in n.get("axes", [])]
    fr = [f for e in entries for f in e["frcp"]]
    cov = {"corpus": "mapping-cpc-mo", "norms_expected": core_total, "norms_done": sum(1 for e in entries if e["cpc_livre"] in CORE),
           "interps_candidates": 0, "interps_screened": 0, "interps_included": 0,
           "cpc_mirror": {"branch_main_head": head, "note": "Tricoteuses commit dates are entry-into-force dates: main HEAD 64a5dcb (dated 2026-05-07, décret n° 2026-337) is the latest state in force on the build date; the repository's 2026-09-22 update concerns branch 'futur' (future states), which is read for successor versions.",
                          "future_states": [{k: f[k] for k in ("date", "commit", "subject")} | {"modified": len(f["modified"]), "added": f["added"], "removed": f["removed"]} for f in fut]},
           "cpc_articles_in_force": len(arts), "livres_i_ii_articles": core_total,
           "livres_iii_vi_articles_screened": sum(1 for a in arts if a["livre"] not in CORE and a["num"] not in missing),
           "livres_iii_vi_entries_with_counterpart": sum(1 for e in entries if e["cpc_livre"] not in CORE),
           "entries": len(entries), "by_livre_equivalence": {f"{k[0]}:{k[1]}": v for k, v in sorted(cnt.items())},
           "equivalence_totals": dict(Counter(e["equivalence"] for e in entries)),
           "confidence_totals": dict(Counter(e["confidence"] for e in entries)),
           "verified_true": sum(1 for e in entries if e["verified"]), "verified_false": sum(1 for e in entries if not e["verified"]),
           "downgraded_by_verifier": sum(1 for e in entries if "downgraded_from" in e["verification"] and "pruned" not in e["verification"]),
           "quotes_near_verbatim": sum(1 for e in entries if e["verification"].get("cpc_quote_match") == "near") + sum(1 for e in entries for q in e["verification"]["mo_quotes"] if q.get("match") == "near"),
           "notes_revised_by_verifier": sum(1 for e in entries if e["verification"].get("notes_revised_by_verifier")),
           "pruned": dict(prune),
           "frcp_links": len(fr), "frcp_links_committee_note": sum(1 for f in fr if f["basis"] == "committee_note"), "frcp_links_rule_text": sum(1 for f in fr if f["basis"] == "rule_text"), "frcp_links_editorial": sum(1 for f in fr if f["basis"] == "editorial"),
           "missouri_procedure_norms": len(proc_ids), "missouri_procedure_norms_mapped": sum(1 for i in proc_ids if i in mo_used),
           "cpc_versions_changing": {"count": len(ending), "by_end_date": dict(byfin), "articles": ending,
                                     "refresh": "scripts/mos_check.py re-runs mop_cpc_articles.py + mop_map2.py + mop_build.py for these articles once their end date is reached (first: 2026-10-01, décret n° 2026-683: 20 modified, 456-1 added, 1549 removed)."},
           "method": ("CPC texts from the Tricoteuses LEGI mirror (state in force on the build date); successors from branch futur. "
                      "Q: English gist/keywords per article (LLM). R: BM25 keyword retrieval over the FULL texts of all Missouri Rules and RSMo sections "
                      "(top 8) plus the v1 candidates. M: mapping decision on FULL CPC and Missouri texts (≤3 articles, ≤18 candidates per call; texts capped at 9,000/7,000 chars). "
                      "V: independent verification pass (only the article and proposed provisions): confirm/downgrade, confidence, verbatim quotes, grounded notes; "
                      "quotes checked mechanically (exact after normalisation, or 'near' = ≥90% of the quote's words in order within one passage). Pruning and verified flag per scripts/mop_build.py docstring. FRCP: committee-note basis vs editorial."),
           "gaps": gaps + [f"{len(unver)} entries verified=false (verifier confidence low, quote not found verbatim, or verifier output missing) — listed in 'unverified'",
                           "Notes are LLM-generated from the texts and checked by a second LLM pass and a mechanical quote check, not individually human-reviewed.",
                           "fr-cpc (another agent's file) not edited: JAF cross-links to cpc-annotated-browser pages are available here via cpc_url."],
           "unverified": unver, "updated": TODAY}
    json.dump(cov, open(os.path.join(ROOT, "data", "coverage", "mapping-cpc-mo.json"), "w"), indent=2, ensure_ascii=False)
    print(json.dumps({k: cov[k] for k in ("norms_expected", "norms_done", "entries", "livres_iii_vi_entries_with_counterpart", "equivalence_totals", "confidence_totals", "verified_true", "verified_false", "downgraded_by_verifier", "pruned", "frcp_links", "frcp_links_committee_note", "missouri_procedure_norms_mapped")}, ensure_ascii=False), "missing", len(missing))


if __name__ == "__main__":
    main()
