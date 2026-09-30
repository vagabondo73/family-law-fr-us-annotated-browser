"""Cross-validate interp->norm links for the int/eu corpora, back-fill norm.interps, write coverage ledgers
and data/sources-int.json. Re-run (after any int_* builder): python3 scripts/int_link.py"""
import os, sys, json, glob, datetime, hashlib, collections
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, DATA, dump, load

TODAY = datetime.date.today().isoformat()
MINE = ["eu-reg", "int-hcch", "int-un", "int-coe", "int-ciec", "int-bilateral"]
INTERPS = ["eu-cjeu", "coe-ecthr"]


def h(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16] if os.path.exists(path) else None


def main():
    norms = {c: load(os.path.join(DATA, "norms", c + ".json")) for c in MINE}
    idx = {n["id"]: n for c in MINE for n in norms[c]["norms"]}
    for n in idx.values():
        n["interps"] = []
    dropped = []
    stats = {}
    for c in INTERPS:
        p = os.path.join(DATA, "interps", c + ".json")
        d = load(p)
        keep = []
        for it in d["interps"]:
            ok = []
            for l in it["norms"]:
                if l["norm"] in idx:
                    ok.append(l)
                    idx[l["norm"]]["interps"].append(it["id"])
                else:
                    dropped.append({"interp": it["id"], "norm": l["norm"], "reason": "norm id not in corpus"})
            it["norms"] = ok
            if ok:
                keep.append(it)
            else:
                dropped.append({"interp": it["id"], "reason": "no remaining norm link — interp removed"})
        d["interps"] = keep
        dump(p, d)
        stats[c] = {"n": len(keep), "basis": dict(collections.Counter(l["basis"] for it in keep for l in it["norms"])),
                    "interps_with_b": sum(1 for it in keep if any(l["basis"] == "b" for l in it["norms"])),
                    "interps_a_only": sum(1 for it in keep if all(l["basis"] == "a" for l in it["norms"]))}
    for c in MINE:
        for n in norms[c]["norms"]:
            n["interps"] = sorted(set(n["interps"]))
        dump(os.path.join(DATA, "norms", c + ".json"), norms[c])
    dump(os.path.join(RAW, "link_dropped.json"), dropped)

    # ---- coverage ledgers
    eul = load(os.path.join(RAW, "eu_norms_ledger.json"), [])
    tl = load(os.path.join(RAW, "treaties_ledger.json"), {})
    bg = load(os.path.join(RAW, "bilateral_gaps.json"), [])
    cj = load(os.path.join(RAW, "cjeu", "screen_ledger.json"), {})
    hd = load(os.path.join(RAW, "hudoc", "screen_ledger.json"), {})
    tc = load(os.path.join(RAW, "cjeu", "titlecheck.json"), {})
    cnt = lambda c: sum(1 for n in norms[c]["norms"] if n["kind"] != "text")
    inst = lambda c: sum(1 for n in norms[c]["norms"] if n["kind"] == "text")
    excl = tl.get("excluded", [])
    cov = {
        "eu-reg": {"norms_expected": cnt("eu-reg"), "method": "Cellar (publications.europa.eu) — latest consolidated version ≤ today of each act (FR XHTML via /resource/celex/<CELEX>), one record per article; in_force_since = entry into force of the base act or of the last amending act (▼M markers); applicable_since recorded separately. Acts: 2019/1111, 4/2009, 1259/2010, 2016/1103, 2016/1104, 650/2012, 2016/1191, 2020/1784, 2020/1783, 1215/2012 (family-relevant arts), 2004/38 (family-member arts), 2003/86, Charter arts 7, 9, 24, 33, TFEU art 81.",
                   "gaps": ["Directive 2003/86 has no consolidated version on Cellar; original OJ text used (plain-text fallback parse).",
                            "Council Decision 2009/941/EC (EU approval of the 2007 Hague Protocol) and Decision 2011/432/EU not ingested as norms (acts of accession; see int-hcch status_detail).",
                            "Regulation 2016/1191 and 2016/1103/1104 consolidated versions predate any later corrigenda — checked by scripts/int_status_check.py."],
                   },
        "int-hcch": {"norms_expected": cnt("int-hcch"), "method": "HCCH status tables (hcch.net status-table/?cid=N) parsed for France, United States and EU rows; full text of every convention/protocol in force for France and/or the US from hcch.net full-text pages (EN; FR for France-only instruments, other language as text_<lang>), one record per article, stop at the testimonium. Instruments only signed (1985 Trusts; 2005 and 2019 for the US) or excluding family matters (2005, 2019) get a status record only.",
                     "gaps": [x["instrument"] + " — excluded: " + x["reason"] for x in excl if x["instrument"].startswith("HCCH")]},
        "int-un": {"norms_expected": cnt("int-un"), "method": "UN Treaty Collection status pages (ViewDetails mtdsg_no) parsed for FR/US/EU; texts: UNTC certified true copies (PDF, English section) aligned with OHCHR text; family-relevant articles only for general covenants (ICCPR 23-24, ICESCR 10, CEDAW 16, CRPD 23); full text for CRC, its OP-AC and OP-SC, and the 1956 New York Maintenance Convention.",
                   "gaps": tl.get("gaps", [])[:0] + [g for g in tl.get("gaps", []) if g.startswith("int-un")] +
                           ["CRC: 7 articles (1, 4, 5, 29, 38, 39, 54) taken from the UNTC certified-copy PDF text layer (OCR) with manual correction of obvious OCR marks; other 47 from the OHCHR text.",
                            "1962 Consent to Marriage Convention: the only copy available (UNTC PDF) has an unreliable OCR layer and OHCHR is behind a bot wall — status record only, no article text.",
                            "OP-CRC communications procedure (2011): status record only (France party; procedural, no substantive family articles).",
                            "Convention on the Nationality of Married Women (1957, XVI-2): excluded — neither France nor the US is a party."]},
        "int-coe": {"norms_expected": cnt("int-coe"), "method": "CoE Treaty Office charts of signatures and ratifications (coe.int full-list, read via browser; saved raw/int/coe/status_browser.json); texts from rm.coe.int / echr.coe.int official PDFs: ECHR arts 8, 12, 14; Protocol 7 art 5; ETS 105, ETS 160, CETS 210 in full. Status-only: ETS 058, 085, 166 (signed by France only), ETS 043 (Chapter II only for France), ETS 062/097 (procedure, information on foreign law).",
                    "gaps": [x["instrument"] + " — excluded: " + x["reason"] for x in excl if "ETS" in x["instrument"]] +
                            ["General entry-into-force dates of ETS 043/062/097/058/085/166 not recorded (not on the saved chart pages); FR dates recorded.",
                             "ETS 105/160/210 texts: English authentic text; French text not ingested."]},
        "int-ciec": {"norms_expected": cnt("int-ciec"), "method": "ciec1.org convention pages (list pages 1-2, 35 instruments): France row of each status table parsed; French text parsed per article for every instrument ratified by France; signed-only → status record; others → excluded (ledger). The United States is not a CIEC member.",
                     "gaps": ["Convention n°18: France ratified 14/05/1986; the CIEC table shows no entry-into-force date for France — in_force_since null.",
                              "CIEC pages append an explanatory report: article text cut at the first repeated article number / 'Seul l'original français fait foi' marker (see raw/int/treaties_ledger.json ciec_truncated).",
                              "CIEC statuses are as published by the CIEC secretariat (not an official treaty depositary in every case; the depositary is the Swiss Federal Council) — to be cross-checked on the Swiss FDFA depositary lists."] +
                             [x["instrument"] + " — excluded: " + x["reason"] for x in excl if x["instrument"].startswith(("Convention (n°", "Protocole"))]},
        "int-bilateral": {"norms_expected": cnt("int-bilateral"), "method": "U.S. Department of State, Treaties in Force 2026 (France section) for the list and entry-into-force dates; texts: Consular Convention 1966 from UNTS vol. 700 (English text), Social Security Agreement 1987 from ssa.gov (HTML rendered via browser; list markers reconstructed from <ol> numbering).",
                          "gaps": bg + ["Child-support reciprocity: no bilateral instrument listed in TIF 2026; record points to Hague 2007 (in force FR/US since 2017-01-01) — no declaration date invented.",
                                        "Consular Convention: protocol and exchange of letters not ingested."]},
    }
    for c, v in cov.items():
        dump(os.path.join(DATA, "coverage", c + ".json"), {"corpus": c, "norms_expected": v["norms_expected"], "norms_done": cnt(c), "instrument_records": inst(c),
                                                             "interps_candidates": 0, "interps_screened": 0, "interps_included": 0,
                                                             "method": v["method"], "gaps": v["gaps"], "updated": TODAY})
    ic = load(os.path.join(RAW, "cjeu", "infocuria_check.json"), {})
    frl = cj.get("functional_review_log", [])
    fr_inc = sorted({(e["celex"], e["from"]) for e in frl if e["verdict"] == "include"})
    fr_exc = [e for e in frl if e["verdict"] == "exclude"]
    unrev = [d for d in cj.get("links_dropped", []) if d.get("note") == "UNREVIEWED"]
    extra_inc = [c for c in cj.get("extra_candidates", []) if c in {it["celex"] for it in load(os.path.join(DATA, "interps", "eu-cjeu.json"))["interps"]}]
    dump(os.path.join(DATA, "coverage", "eu-cjeu.json"), {
        "corpus": "eu-cjeu", "norms_expected": 0, "norms_done": 0, "interps_candidates": cj.get("candidates"), "interps_screened": cj.get("screened"),
        "interps_included": stats["eu-cjeu"]["n"], "basis_links": stats["eu-cjeu"]["basis"], "interps_with_basis_b": stats["eu-cjeu"]["interps_with_b"],
        "method": "Candidates: (1) Cellar SPARQL — case-law works (CJ/CO) with cdm:case-law_interpretes_resource_legal or cdm:work_cites_work to the included acts and their predecessors (2201/2003, 1347/2000, 1393/2007, 1348/2000, 1206/2001, 44/2001); (2) independent check: InfoCuria (official CURIA search back-end) exact-phrase full-text search per instrument number, Court of Justice, with a second pass listing all decisions of every matched case (scripts/int_cjeu_infocuria.py); decisions missing from (1) added (raw/int/cjeu/candidates_extra.json). Screening: French text of each judgment/order from Cellar; operative part parsed for article references; orders without interpretive ruling (rectification, removal) excluded; Brussels I/Ibis only art 1 (family exclusions); Directive 2004/38 only family-member provisions; Charter arts 7/9/24/33 only alongside an included act. Basis a if decision >= D(current article). Predecessor provisions: decisive test = manual functional review of old vs new provision, the recast correlation table and recital 3 of 2019/1111 (scripts/int_cjeu_review.py) — include as basis b with specific French justification or exclude with logged reason (raw/int/cjeu/screen_ledger.json functional_review_log); difflib similarity is informative only. summary = operative part verbatim; titrage = official keywords.",
        "completeness_check": {"infocuria_per_term": ic.get("per_term"), "cases_matched": ic.get("cases_matched"), "decisions_found": ic.get("decisions_found"),
                               "already_in_cellar_candidates": ic.get("already_candidates"), "added": ic.get("missing_added_to_candidates_extra"),
                               "added_and_included": extra_inc},
        "functional_review": {"pairs_included": len(fr_inc), "pairs_excluded": len(fr_exc),
                              "excluded": [{"celex": e["celex"], "from": e["from"], "reason": e["justification"][:300]} for e in fr_exc]},
        "gaps": ([f"{len(unrev)} predecessor links below similarity 0.72 not manually reviewed: " + ", ".join(sorted({d['celex'] + ' ' + d['from'].strip() for d in unrev}))] if unrev else []) +
                ["InfoCuria check not run for 44/2001, 1215/2012 and 2004/38 (hundreds of non-family decisions); their family-adjacent subset rests on the Cellar candidate set and the title/term screen."] +
                ([f"InfoCuria judgments/orders without CELEX: {ic.get('judgments_or_orders_without_celex')}"] if ic.get("judgments_or_orders_without_celex") else []),
        "updated": TODAY})
    kw = load(os.path.join(RAW, "hudoc", "kwcheck.json"), {})
    dump(os.path.join(DATA, "coverage", "coe-ecthr.json"), {
        "corpus": "coe-ecthr", "norms_expected": 0, "norms_done": 0,
        "interps_candidates": {"fra_art8_12_14_p7": 2356, "grand_chamber_art8_12_14_p7": 363, "hague_1980_mentions": 167},
        "interps_screened": hd.get("screened"), "interps_included": stats["coe-ecthr"]["n"], "basis_links": stats["coe-ecthr"]["basis"],
        "method": "HUDOC JSON query endpoint (hudoc.echr.coe.int/app/query/results): (1) judgments against France with violation/no-violation on arts 8, 12, 14, P7-5; (2) Grand Chamber judgments on those articles; (3) judgments mentioning the Hague 1980 Convention. Metadata pre-filter (importance, doctype) then text screen of the judgment body (HUDOC conversion endpoint): included if KP thesaurus 'Respect for family life', art 12 / P7-5, 'family life' in the conclusion, or family-term score ≥ 25; Hague cases need ≥ 3 substantive Hague mentions. All links basis a (ECHR article text unchanged since 1953; Hague 1980 text unchanged). summary = HUDOC official conclusion metadata verbatim; excerpts = operative provisions.",
        "filter_check": {"method": "HUDOC full-text keyword queries (respondent FRA, judgments) — each hit classified included / excluded by screen / outside article scope (no art 8, 12, 14, P7-5 in HUDOC metadata) / unexplained (scripts/int_ecthr_kwcheck.py)",
                         "keywords": kw.get("keywords"), "named_cases": kw.get("named_cases"),
                         "unexplained_reviewed": sorted({u["docname"] for u in kw.get("unexplained", [])}),
                         "unexplained_verdict": "all reviewed manually: art. 8 private life / home / correspondence (interceptions, searches, DNA, registers) or other rights — no family-life issue; correctly outside"},
        "gaps": ["Family matters decided against France only under art 6 (e.g. length of custody proceedings) or art 3/5 are outside the article scope set by SCOPE §4.4 (arts 8/12/14/P7-5) and not included (counted as outside_article_scope in filter_check).",
                 "Decisions (inadmissibility) and Committee judgments of importance 4 against France were screened only if tagged on the included articles.",
                 "Family-life cases in the migration/prison context are included where the Court examined family life (issue int.echr.migration).",
                 "Issue classification of ECtHR items is keyword-based (see scripts/int_ecthr.py classify()).",
                 f"{sum(1 for it in load(os.path.join(DATA, 'interps', 'coe-ecthr.json'))['interps'] if not it['excerpts'])} items without a parsed operative-part excerpt (summary = HUDOC conclusion only).",
                 "Hague-set items with no identifiable Hague article are linked to the instrument record int-hcch-1980."],
        "updated": TODAY})

    # ---- sources registry
    S = []
    add = lambda i, label, off, ch, chk, corp, ver: S.append({"id": i, "label": label, "official": off, "channel": ch, "check": chk, "corpora": corp, "last_checked": TODAY, "last_version": ver})
    for n in norms["eu-reg"]["norms"]:
        pass
    eul_acts = eul.get("acts", eul) if isinstance(eul, dict) else eul
    for a in (eul_acts if isinstance(eul_acts, list) else []):
        cel = a.get("act")
        ver = a.get("consolidated_used")
        if cel:
            add(f"eurlex-{cel}", f"EUR-Lex / Cellar — {cel} (consolidated {ver})", f"https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:{ver or cel}",
                "sparql:https://publications.europa.eu/webapi/rdf/sparql (latest consolidated version) + http://publications.europa.eu/resource/celex/<CELEX>", "api", ["eu-reg"], ver)
    for key, cid, *_ in __import__("int_treaties").HCCH:
        add(f"hcch-status-{cid}", f"HCCH status table cid={cid} ({key})", f"https://www.hcch.net/en/instruments/conventions/status-table/?cid={cid}",
            f"http:https://www.hcch.net/en/instruments/conventions/status-table/?cid={cid}", "http-hash", ["int-hcch"], h(os.path.join(RAW, "hcch", f"st_{cid}.html")))
    for key, mt, ch, *_ in __import__("int_treaties").UN:
        add(f"untc-{mt}", f"UN Treaty Collection status {mt} ({key})", f"https://treaties.un.org/Pages/ViewDetails.aspx?src=TREATY&mtdsg_no={mt}&chapter={ch}&clang=_en",
            "http", "http-hash", ["int-un"], h(os.path.join(RAW, "un", f"{mt}.html")))
    add("coe-treaty-office", "Council of Europe Treaty Office — charts of signatures and ratifications", "https://www.coe.int/en/web/conventions/full-list",
        "browser (cloud) — coe.int blocks non-browser clients", "http-hash", ["int-coe"], h(os.path.join(RAW, "coe", "status_browser.json")))
    add("ciec", "Commission internationale de l'état civil — conventions et états des signatures", "https://ciec1.org/", "http:https://ciec1.org/convention/<slug>/", "http-hash", ["int-ciec"], h(os.path.join(RAW, "ciec", "ciec.json")))
    add("state-tif-2026", "U.S. Department of State — Treaties in Force 2026", "https://www.state.gov/wp-content/uploads/2026/06/Treaties-in-Force-2026.pdf", "http", "http-hash", ["int-bilateral", "int-hcch"], h(os.path.join(RAW, "texts", "tif2026_france.txt")))
    add("ssa-france", "SSA — U.S.-French Social Security Agreement", "https://www.ssa.gov/international/Agreement_Texts/french.html", "browser", "http-hash", ["int-bilateral"], h(os.path.join(RAW, "texts", "ssa-fr.html")))
    add("cellar-cjeu", "Cellar — CJEU case law interpreting included acts", "https://eur-lex.europa.eu/", "sparql:https://publications.europa.eu/webapi/rdf/sparql", "api", ["eu-cjeu"], h(os.path.join(RAW, "cjeu", "candidates.json")))
    add("hudoc", "HUDOC — European Court of Human Rights case law", "https://hudoc.echr.coe.int/", "api:https://hudoc.echr.coe.int/app/query/results", "api", ["coe-ecthr"], h(os.path.join(DATA, "interps", "coe-ecthr.json")))
    dump(os.path.join(DATA, "sources-int.json"), S)
    print("links dropped", len(dropped), stats, "sources", len(S))


if __name__ == "__main__":
    main()
