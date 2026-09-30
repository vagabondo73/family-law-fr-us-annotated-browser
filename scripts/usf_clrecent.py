#!/usr/bin/env python3
"""Enumerate opinions NOT covered by the CAP bulk (SCOTUS filed >= 2014-06-01; CA8 filed >= 2019-01-01) through the
CourtListener REST v4 search API (anonymous, precedential only, <=1 req/3 s), download the official PDF
(download_url: supremecourt.gov / media.ca8.uscourts.gov), regex-screen (usf_patterns) -> raw/us/cl_hits/.
Query pages are cached in raw/us/cl_queries/ (resume-safe; incomplete queries are not cached)."""
import json, os, sys, time, subprocess, urllib.parse, urllib.request, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW
from usf_patterns import match_groups
from usf_candidates import fetch, QDIR

CL = RAW + "/cl_hits"; os.makedirs(CL, exist_ok=True)
PH = [
 ['"Hague Convention"', '"International Child Abduction"', '"ICARA"', '"1738A"', '"1738B"', '"1738C"', '"Parental Kidnaping"', '"Intercountry Adoption"', '"International Parental Kidnapping"', '"Goldman"'],
 ['"Title IV-D"', '"IV-D"', '"child support obligation"', '"qualified domestic relations order"', '"QDRO"', '"1056(d)"', '"414(p)"', '"Former Spouses"', '"divorce decree"', '"dissolution decree"'],
 ['"523(a)(5)"', '"523(a)(15)"', '"domestic support obligation"', '"362(b)(2)"', '"marital deduction"', '"innocent spouse"', '"6015"', '"1041"', '"152(e)"', '"alimony"'],
 ['"1186a"', '"1154"', '"immediate relative"', '"marriage fraud"', '"sham marriage"', '"1401"', '"1409"', '"1431"', '"1433"', '"Child Citizenship Act"'],
 ['"922(g)(8)"', '"922(g)(9)"', '"921(a)(33)"', '"misdemeanor crime of domestic violence"', '"2261"', '"2261A"', '"2262"', '"2265"', '"interstate domestic violence"', '"1782"'],
 ['"domestic relations exception"', '"domestic-relations exception"', '"Rooker-Feldman"', '"Younger abstention"', '"parental rights"', '"child custody"', '"familial association"', '"right to marry"', '"same-sex marriage"', '"Obergefell"'],
 ['"Troxel"', '"Santosky"', '"Kulko"', '"Ankenbrandt"', '"nonmarital"', '"illegitimate"', '"Hague Service Convention"', '"Hague Evidence Convention"', '"divorced wife"', '"stepchild"'],
]
SCOPE = [("scotus", "2014-06-01"), ("ca8", "2019-01-01")]
BASE = "https://www.courtlistener.com/api/rest/v4/search/"


def run(court, after, q):
    h = hashlib.sha1(f"recent|{court}|{after}|{q}".encode()).hexdigest()[:16]
    fn = f"{QDIR}/recent-{court}-{h}.json"
    if os.path.exists(fn):
        return json.load(open(fn))["results"]
    url = BASE + "?" + urllib.parse.urlencode({"type": "o", "court": court, "q": q, "stat_Precedential": "on", "filed_after": after, "order_by": "dateFiled desc"})
    res, pages = [], 0
    while url and pages < 60:
        d = fetch(url); pages += 1; time.sleep(3)
        if not d:
            print("INCOMPLETE", court, q[:50], flush=True); return None
        for r in d.get("results", []):
            res.append({k: r.get(k) for k in ["cluster_id", "caseName", "citation", "dateFiled", "docketNumber", "absolute_url", "status", "court_id"]} |
                       {"download_urls": [o.get("download_url") for o in r.get("opinions", []) if o.get("download_url")]})
        url = d.get("next")
    json.dump({"court": court, "q": q, "results": res}, open(fn, "w"))
    print(court, len(res), q[:60], flush=True)
    return res


def pdftext(u):
    u = u.replace("://media.ca8.uscourts.gov/", "://ecf.ca8.uscourts.gov/")  # media host not reachable from sandbox; same files
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (flb research)"})
    b = urllib.request.urlopen(req, timeout=120).read()
    p = "/tmp/usf_recent.pdf"; open(p, "wb").write(b)
    return subprocess.run(["pdftotext", p, "-"], capture_output=True, text=True).stdout


def main():
    cands = {}
    for court, after in SCOPE:
        for ph in PH:
            res = run(court, after, " OR ".join(ph))
            for r in res or []:
                if r.get("status") not in (None, "Published", "Precedential"):
                    continue
                cands[str(r["cluster_id"])] = r
    json.dump(cands, open(RAW + "/cl_recent_candidates.json", "w"), indent=1)
    print("candidates", len(cands), flush=True)
    nohit = 0
    for cid, r in cands.items():
        fn = f"{CL}/cl-{cid}.json"; skip = f"{RAW}/cl_nohit/{cid}"
        if os.path.exists(fn) or os.path.exists(skip):
            continue
        urls = [u for u in r["download_urls"] if u and u.lower().endswith(".pdf")]
        if not urls:
            print("no pdf", cid, r["caseName"], flush=True); continue
        try:
            t = pdftext(urls[0]); time.sleep(0.5)
        except Exception as e:
            print("pdf fail", cid, e, flush=True); continue
        g = match_groups(t)
        if not g:
            os.makedirs(f"{RAW}/cl_nohit", exist_ok=True); open(skip, "w").write(r["caseName"] or ""); nohit += 1; continue
        court = "Supreme Court of the United States" if r["court_id"] == "scotus" else "United States Court of Appeals for the Eighth Circuit"
        json.dump({"cluster_id": cid, "name": r["caseName"], "date": r["dateFiled"], "docket": r["docketNumber"], "citations": r["citation"] or [],
                   "court": court, "pdf_url": urls[0].replace("://media.ca8.uscourts.gov/", "://ecf.ca8.uscourts.gov/"), "cl_url": "https://www.courtlistener.com" + (r["absolute_url"] or ""),
                   "groups": {k: v[:40] for k, v in g.items()}, "head_matter": "", "text": t}, open(fn, "w"))
    print("done; no-hit", nohit)


if __name__ == "__main__":
    main()
