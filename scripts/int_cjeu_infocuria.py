"""Independent CJEU completeness check (does not depend on Cellar SPARQL).
Queries the official InfoCuria search back-end (infocuriaws.curia.europa.eu/elastic-connector/search, the service
behind https://infocuria.curia.europa.eu) with an exact-phrase full-text search per instrument number, Court of
Justice only, and collects every judgment/order (CELEX 6yyyyCJnnnn / 6yyyyCOnnnn) whose text contains the phrase.
Compares with raw/int/cjeu/candidates.json and writes:
  raw/int/cjeu/infocuria_hits.json      all hits per term
  raw/int/cjeu/candidates_extra.json    decisions missing from candidates (merged by int_cjeu.py)
  raw/int/cjeu/infocuria_check.json     summary (per-term totals, missing, gaps)
Re-run: python3 scripts/int_cjeu_infocuria.py && python3 scripts/int_cjeu.py
Note: Brussels I/Ibis (44/2001, 1215/2012) and directive 2004/38 are NOT full-text checked (hundreds of non-family
decisions; the family-adjacent subset is bounded by the Cellar screen) — recorded as a bounded-scope note."""
import os, re, sys, json, subprocess, time
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, load, dump

CJ = os.path.join(RAW, "cjeu")
API = "https://infocuriaws.curia.europa.eu/elastic-connector/search"
TERMS = {  # phrase -> CELEX of the act (a phrase is searched exactly, in all indexed languages/metadata)
    "2201/2003": "32003R2201", "2019/1111": "32019R1111", "1347/2000": "32000R1347",
    "règlement (CE) no 4/2009": "32009R0004", "règlement (CE) n° 4/2009": "32009R0004", "Regulation (EC) No 4/2009": "32009R0004",
    "1259/2010": "32010R1259", "2016/1103": "32016R1103", "2016/1104": "32016R1104", "650/2012": "32012R0650",
    "2016/1191": "32016R1191", "1393/2007": "32007R1393", "2020/1784": "32020R1784", "1348/2000": "32000R1348",
    "1206/2001": "32001R1206", "2020/1783": "32020R1783", "2003/86": "32003L0086",
}


def query(term, page, size=100):
    body = {"searchTerm": f'"{term}"', "multiSearchTerms": [],
            "sortTermList": [{"sortDirection": "DESC", "sortTerm": "AFF_NUM", "sortSourceTab": "affair"}],
            "pagination": {"pageNumber": page, "pageSize": size, "from": page * size, "to": (page + 1) * size},
            "language": "FR", "tabName": "affair", "isAllTabsRequest": False, "ecli": "", "publishedId": "",
            "usualName": "", "logicDocId": "", "repJurExpand": True,
            "filtersValue": [{"field": "jurisdiction", "values": ["C"], "valuesWithFullHierarchy": ["C"]}],
            "advancedFiltersValue": [], "isSearchExact": True, "searchSources": ["document", "metadata"]}
    for k in range(3):
        r = subprocess.run(["curl", "-s", "-m", "60", "-X", "POST", API, "-H", "Content-Type: application/json",
                            "-H", "Origin: https://infocuria.curia.europa.eu", "-A", "Mozilla/5.0",
                            "-d", json.dumps(body, ensure_ascii=False)], capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except Exception:
            time.sleep(3)
    return None


def usual(content):
    for d in content.get("usualNameML") or []:
        if "fr" in d:
            return d["fr"].strip()
    return ""


def main():
    cands = {c["celex"] for c in load(os.path.join(CJ, "candidates.json"), [])}
    hits, per_term, noncelex = {}, {}, []
    affairs = {}  # publishedId -> set(acts) for every matched case (second pass lists all its decisions)
    for term, act in TERMS.items():
        page, n_aff, tot = 0, 0, None
        while True:
            d = query(term, page)
            if not d:
                per_term[term] = {"error": "query failed"}
                break
            tot = d.get("totalHits", 0)
            for h in d.get("searchHits", []):
                n_aff += 1
                pid = h["content"].get("publishedId")
                affairs.setdefault(pid, set()).add(act)
                docs = ((h.get("innerHits") or {}).get("document") or {}).get("searchHits") or []
                for x in docs:
                    c = x.get("content", {})
                    cx = c.get("celex") or ""
                    if re.fullmatch(r"6\d{4}C[JO]\d{4}", cx):
                        e = hits.setdefault(cx, {"celex": cx, "case": pid, "date": c.get("docDate"), "ecli": c.get("ecli") or None,
                                                 "docType": c.get("docType"), "acts": {}, "terms": [], "name": usual(h["content"])})
                        e["acts"].setdefault(act, [])
                        if term not in e["terms"]:
                            e["terms"].append(term)
                    elif c.get("docTypeCode") in ("ARRET", "ORD", "ORDONNANCE", "ORD_REC") and not cx:
                        noncelex.append({"case": pid, "docType": c.get("docType"), "date": c.get("docDate")})
            page += 1
            if page * 100 >= tot:
                break
        per_term[term] = per_term.get(term) or {"cases_matching": tot, "cases_read": n_aff}
        print(term, per_term[term], flush=True)
    # second pass: matched cases for which no judgment/order was returned among the matching documents
    have = {v["case"] for v in hits.values()}
    second = []
    for pid, acts in sorted(affairs.items()):
        if pid in have or not pid:
            continue
        d = query(pid, 0, 20)
        for h in (d or {}).get("searchHits", []):
            if h["content"].get("publishedId") != pid:
                continue
            for x in ((h.get("innerHits") or {}).get("document") or {}).get("searchHits") or []:
                c = x.get("content", {})
                cx = c.get("celex") or ""
                if re.fullmatch(r"6\d{4}C[JO]\d{4}", cx) and cx not in hits:
                    hits[cx] = {"celex": cx, "case": pid, "date": c.get("docDate"), "ecli": c.get("ecli") or None,
                                "docType": c.get("docType"), "acts": {a: [] for a in acts}, "terms": ["second-pass (case matched)"], "name": usual(h["content"])}
                    second.append(cx)
    print("second pass added", len(second), "from", len([p for p in affairs if p not in have]), "cases", flush=True)
    missing = [v for k, v in sorted(hits.items()) if k not in cands]
    dump(os.path.join(CJ, "infocuria_hits.json"), hits)
    dump(os.path.join(CJ, "candidates_extra.json"), [
        {"celex": m["celex"], "date": m["date"], "ecli": m["ecli"], "title": "#" + m.get("name", ""), "acts": m["acts"], "source": "InfoCuria full-text: " + "; ".join(m["terms"])}
        for m in missing])
    dump(os.path.join(CJ, "infocuria_check.json"), {
        "method": "InfoCuria exact-phrase full-text search per instrument number, Court of Justice, all documents; judgments/orders with CELEX",
        "endpoint": API, "per_term": per_term, "cases_matched": len(affairs), "second_pass_added": second, "decisions_found": len(hits), "already_candidates": len(hits) - len(missing),
        "missing_added_to_candidates_extra": [m["celex"] for m in missing],
        "judgments_or_orders_without_celex": noncelex,
        "not_checked": "44/2001, 1215/2012, 2004/38 (full-text volume; family subset bounded by Cellar screen)"})
    print("found", len(hits), "missing", len(missing))


if __name__ == "__main__":
    main()
