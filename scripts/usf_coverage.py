#!/usr/bin/env python3
"""Write data/sources-us.json and data/coverage/us-*.json from pipeline outputs."""
import json, os, sys, glob, datetime, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import ROOT, RAW, USC, CFR_PARTS, CFR_SECTIONS, RULES

T = datetime.date.today().isoformat()
L = lambda p: json.load(open(p)) if os.path.exists(p) else None
os.makedirs(ROOT + "/data/coverage", exist_ok=True)
norms = {c: L(f"{ROOT}/data/norms/{c}.json")["norms"] for c in ["us-const", "us-usc", "us-cfr", "us-common"]}
interps = {c: L(f"{ROOT}/data/interps/{c}.json")["interps"] for c in ["us-scotus", "us-ca8"]}
stats = L(RAW + "/build_stats.json") or {}
usc_gaps = L(RAW + "/usc_gaps.json") or []
cfr_gaps = L(RAW + "/cfr_gaps.json") or []
screen = [json.loads(l) for l in open(RAW + "/screen.jsonl")]
last = {}
for s in screen:
    last[s["_file"]] = s
cap_s = sum(1 for f in last if "/cap_hits/us-" in f or "scotus-" in f)
slipst = L(RAW + "/slip/stats.json") or {}; boundst = L(RAW + "/slip/bound_stats.json") or {}; ca8b = L(RAW + "/ca8bulk_stats.json") or {}
scan_s = len([x for x in os.listdir(RAW + "/slip") if x.startswith("nohit-")]) + sum(v["cases"] for v in boundst.values())
scan_c = sum(ca8b.values())
ca8_nopdf = [open(RAW + "/ca8_nohit/" + f).read() and f for f in os.listdir(RAW + "/ca8_nohit") if open(RAW + "/ca8_nohit/" + f).read().startswith("no pdf")]
cap_c = len(last) - cap_s
cl_recent = L(RAW + "/cl_recent_candidates.json") or {}
incomplete = L(RAW + "/cl_incomplete.json") or []


def h(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def ab(lst):
    a = sum(1 for r in lst for l in r["norms"] if l["basis"] == "a")
    b = sum(1 for r in lst for l in r["norms"] if l["basis"] == "b")
    return a, b


sources = [
 {"id": "uscode-house", "label": "United States Code (Office of the Law Revision Counsel, prelim edition)", "official": "https://uscode.house.gov/",
  "channel": "http:https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title{T}-section{S}&num=0&edition=prelim", "check": "http-hash",
  "corpora": ["us-usc"], "last_checked": T, "last_version": h([n["source_ids"]["text_sha1"] for n in norms["us-usc"]])},
 {"id": "ecfr", "label": "Electronic Code of Federal Regulations (eCFR, versioner API)", "official": "https://www.ecfr.gov/",
  "channel": "api:https://www.ecfr.gov/api/versioner/v1/full/{date}/title-{T}.xml?part={P}", "check": "api", "corpora": ["us-cfr"],
  "last_checked": T, "last_version": h([n["source_ids"]["text_sha1"] for n in norms["us-cfr"]])},
 {"id": "us-constitution", "label": "Constitution of the United States (National Archives transcription; Constitution Annotated)",
  "official": "https://constitution.congress.gov/constitution/", "channel": "http:https://www.archives.gov/founding-docs/constitution-transcript",
  "check": "http-hash", "corpora": ["us-const"], "last_checked": T, "last_version": h([n["source_ids"]["text_sha1"] for n in norms["us-const"]])},
 {"id": "cap-static", "label": "Caselaw Access Project static bulk (Harvard LIL) — U.S. Reports 1–572, F.2d, F.3d 1–936 (reading channel)",
  "official": "https://static.case.law/", "channel": "http:https://static.case.law/{reporter}/{volume}.zip", "check": "http-hash",
  "corpora": ["us-scotus", "us-ca8"], "last_checked": T, "last_version": "static (frozen dataset)"},
 {"id": "courtlistener-search", "label": "CourtListener REST API v4 search (Free Law Project) — enumeration of SCOTUS >= 2014-06 and CA8 >= 2019",
  "official": "https://www.courtlistener.com/", "channel": "api:https://www.courtlistener.com/api/rest/v4/search/?type=o&court=scotus|ca8&stat_Precedential=on&filed_after=…",
  "check": "api", "corpora": ["us-scotus", "us-ca8"], "last_checked": T, "last_version": str(len(cl_recent)) + " candidates"},
 {"id": "courtlistener-bulk", "label": "CourtListener quarterly bulk data (dockets, opinion-clusters, citations CSV; public S3, no quota)",
  "official": "https://www.courtlistener.com/help/api/bulk-data/", "channel": "http:https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data/{table}-{YYYY-MM-DD}.csv.bz2",
  "check": "http-hash", "corpora": ["us-ca8"], "last_checked": T, "last_version": "2026-06-30 snapshot"},
 {"id": "supremecourt-boundvolumes", "label": "Supreme Court — U.S. Reports bound volumes (PDF) and preliminary prints", "official": "https://www.supremecourt.gov/opinions/USReports.aspx",
  "channel": "http:https://www.supremecourt.gov/opinions/boundvolumes/{vol}BV.pdf", "check": "http-hash", "corpora": ["us-scotus"], "last_checked": T, "last_version": "vols 573-585"},
 {"id": "supremecourt-gov", "label": "Supreme Court of the United States — slip opinions / bound volumes", "official": "https://www.supremecourt.gov/opinions/",
  "channel": "http:https://www.supremecourt.gov/opinions/slipopinion/{term} (lists -> {term}pdf/*.pdf, preliminaryprint/*.pdf#page=N)", "check": "http-hash", "corpora": ["us-scotus"], "last_checked": T, "last_version": None},
 {"id": "loc-usreports", "label": "Library of Congress — United States Reports (vols. 1–578)", "official": "https://www.loc.gov/collections/united-states-reports/",
  "channel": "link:https://www.loc.gov/item/usrep{VVV}{PPP}/", "check": "http-hash", "corpora": ["us-scotus"], "last_checked": T, "last_version": None},
 {"id": "ca8-opinions", "label": "U.S. Court of Appeals for the Eighth Circuit — opinions (PDF)", "official": "https://www.ca8.uscourts.gov/opinions",
  "channel": "http:https://ecf.ca8.uscourts.gov/opndir/{YY}/{MM}/{docket}P.pdf", "check": "http-hash", "corpora": ["us-ca8"], "last_checked": T, "last_version": None},
]
json.dump(sources, open(ROOT + "/data/sources-us.json", "w"), indent=2)

cfr_expected = "all non-reserved sections of " + ", ".join(f"{t} CFR part {p}" for t, p, _ in CFR_PARTS) + " + " + ", ".join(f"{t} CFR {s}" for t, s, _ in CFR_SECTIONS)
led = {
 "us-const": dict(norms_expected=len(norms["us-const"]), norms_done=len(norms["us-const"]), method="Provisions listed in SCOPE §4.2 (Art. I §8 cl.1, Art. II §2 cl.2, Art. IV §1, Art. VI cl.2, Amend. V, Amend. XIV §1); verbatim text from National Archives transcription.", gaps=[]),
 "us-usc": dict(norms_expected=len(USC), norms_done=len(norms["us-usc"]), method="SCOPE §4.2 sections fetched from uscode.house.gov (prelim edition; 26 U.S.C. 71/215 from 2017 edition as last text in force). Very long sections split at the subdivision named in SCOPE (e.g. 8 U.S.C. 1101(b), 11 U.S.C. 523(a)(5)). D(norm) = enactment date of the latest amending Public Law in the source credit (section-level) or latest Public Law whose Amendments note targets the subdivision (subdivision-level; amendments to introductory/flush language excluded).",
                gaps=usc_gaps + ["FRCP 4(f) (Hague Service implementation) not included — rules of court are not in the U.S. Code sections fetched; to add from uscourts.gov",
                                 "Amendment effective dates that differ from enactment dates (e.g. BAPCPA 2005 effective 2005-10-17) are not modelled — enactment date used as D(norm)"]),
 "us-cfr": dict(norms_expected=len(norms["us-cfr"]), norms_done=len(norms["us-cfr"]), method="eCFR versioner API: " + cfr_expected + ". D(norm) = eCFR 'last amended' (versioner amendment_date) when an amendment falls within eCFR history (2017+), else latest Federal Register citation in the section (or part) source note.", gaps=cfr_gaps),
 "us-common": dict(norms_expected=len(RULES), norms_done=len(norms["us-common"]), method="Judge-made federal rules stated with verbatim language of the founding/leading U.S. Supreme Court decisions (rule_sources); D = date of the founding decision.",
                   gaps=[f"{n['id']}: missing rule sources {n['source_ids']['missing_sources']}" for n in norms["us-common"] if n["source_ids"]["missing_sources"]]),
}
for c, d in led.items():
    json.dump({"corpus": c, **d, "interps_candidates": None, "interps_screened": None,
               "interps_included": sum(1 for n in norms[c] for _ in n["interps"]), "updated": T}, open(f"{ROOT}/data/coverage/{c}.json", "w"), indent=2)

common_gaps = [
 "Interpretation link requires >=1 verbatim excerpt verified against the opinion text; screened-relevant decisions without a verifiable excerpt are listed here as gaps.",
 "Summaries are neutral editorial summaries (summary_is_official=false); official syllabi not reproduced.",
 "Screening of candidates (relevance, norm links, issues) is LLM-assisted with instructions in scripts/usf_screen.py; basis-b judgments are LLM-assisted functional reviews (scripts/usf_temporal.py) recorded in b_justification.",
]
for c, key in [("us-scotus", "scotus"), ("us-ca8", "ca8")]:
    a, b = ab(interps[c])
    ne = [x for x in stats.get("no_excerpt", []) if (("/us-" in x or "scotus-" in x) if c == "us-scotus" else ("/f2d-" in x or "/f3d-" in x or "cl-" in x))]
    json.dump({"corpus": c, "norms_expected": None, "norms_done": None,
               "interps_candidates": (cap_s if c == "us-scotus" else cap_c), "interps_screened": (cap_s if c == "us-scotus" else cap_c),
               "opinions_regex_scanned_post_cap": (scan_s if c == "us-scotus" else scan_c),
               "interps_included": len(interps[c]), "links_basis_a": a, "links_basis_b": b,
               "method": ("Exhaustive regex enumeration over the full text of every opinion in U.S. Reports vols. 1–572 (CAP bulk) plus seed list of leading cases, plus every opinion in the official supremecourt.gov bound volumes 573–585 (split per case; scripts/usf_bound.py) and every opinion listed on the official supremecourt.gov 'Opinions of the Court' pages for OT2018–OT2025 (scripts/usf_slip.py), all full-text regex-scanned; patterns in scripts/usf_patterns.py; LLM screening; verbatim excerpt verification; temporal rule (a)/(b)."
                          if c == "us-scotus" else
                          "Exhaustive regex enumeration over the full text of every 8th Cir. opinion in F.2d (vols. 1–999) and F.3d (vols. 1–936, through mid-2019) from the CAP bulk (tables/summary dispositions <150 words skipped), plus every precedential ('Published') 8th Cir. cluster filed >= 2019-01-01 in the CourtListener quarterly bulk data (2026-06-30 snapshot; scripts/usf_bulk.py) not already in F.3d <= 936, text read from the official ecf.ca8.uscourts.gov PDF (docket verified; scripts/usf_ca8bulk.py), full-text regex-scanned; LLM screening; verbatim excerpt verification; temporal rule (a)/(b)."),
               "gaps": common_gaps + [f"no verifiable excerpt: {x}" for x in ne] + (["Full Faith and Credit Clause pattern (family context) added 2026-09-30 after the CAP full-text scan; pre-2014 SCOTUS / pre-2019 CA8 FFC-only family decisions not using the named leading cases may be missed (V. L. v. E. L. added manually)"]) +
                       ([f"CourtListener bulk cluster {x}: official ecf.ca8 PDF not found at the release-month path (not scanned)" for x in ca8_nopdf] if c == "us-ca8" else []) +
                       ([f"temporal review pending (link not yet included): {p['interp']} -> {p['norm']}" for p in (L(RAW + '/temporal_pending.json') or []) if p['interp'].startswith(c)][:200]) +
                       ([f"editorially excluded: {x}" for x in stats.get("excluded_editorial", [])] if c == "us-scotus" else []) +
                       (["8th Cir. opinions before F.2d (Federal Reporter 1st series, pre-1925) not scanned"] if c == "us-ca8" else ["Bound-volume case splitting relies on the 'No. … Argued/Decided' line; cases decided without such a line (e.g. some orders/in-chambers) are not scanned", "OT2025 opinions without a U.S. Reports page yet have no citation (official_url = slip PDF)"]),
               "updated": T}, open(f"{ROOT}/data/coverage/{c}.json", "w"), indent=2)
print("ok", {c: len(v) for c, v in interps.items()})
