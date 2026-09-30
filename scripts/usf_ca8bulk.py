#!/usr/bin/env python3
"""8th Cir. precedential opinions after CAP coverage (F.3d > 936 / F.4th), enumerated from CourtListener quarterly
bulk data (scripts/usf_bulk.py -> raw/us/bulk_*.jsonl; no API quota). Text is read from the OFFICIAL court PDF
https://ecf.ca8.uscourts.gov/opndir/YY/MM/<docket>P.pdf (docket verified in text); pattern-matching opinions ->
raw/us/cl_hits/cl-<cluster>.json. Resumable.  Usage: python3 scripts/usf_ca8bulk.py [--since 2019-01-01]"""
import json, os, re, subprocess, sys, time, urllib.request, datetime, collections
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW
from usf_patterns import match_groups

SINCE = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else "2019-01-01"
CL = RAW + "/cl_hits"; ND = RAW + "/ca8_nohit"; os.makedirs(ND, exist_ok=True)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def get(u):
    for k in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=90).read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            time.sleep(3 * (k + 1))
        except Exception:
            time.sleep(3 * (k + 1))
    return None


def work(c):
    cid = c["id"]; fn = f"{CL}/cl-{cid}.json"; nf = f"{ND}/{cid}"
    if os.path.exists(fn) or os.path.exists(nf):
        return "cached"
    dks = re.findall(r"\d{2}-\d{4}", c.get("docket_number") or "")
    if not dks:
        open(nf, "w").write("no docket"); return "nodocket"
    d0 = datetime.date.fromisoformat(c["date_filed"])
    for dd in (0, -3, 3, -10, 10, -35, 35):   # file directory = release month; try adjacent months near month edges
        d = d0 + datetime.timedelta(days=dd)
        u = f"https://ecf.ca8.uscourts.gov/opndir/{d:%y}/{d:%m}/{dks[0].replace('-', '')}P.pdf"
        b = get(u)
        if not b or not b.startswith(b"%PDF"):
            continue
        tmp = f"/tmp/usf_ca8_{cid}.pdf"; open(tmp, "wb").write(b)
        t = subprocess.run(["pdftotext", tmp, "-"], capture_output=True, text=True).stdout; os.remove(tmp)
        if dks[0] not in t[:3000]:
            continue
        g = match_groups(t)
        if not g:
            open(nf, "w").write("nohit " + u); return "nohit"
        json.dump({"cluster_id": cid, "name": c["case_name"], "date": c["date_filed"], "docket": ", ".join(dks), "citations": c["cites"],
                   "court": "United States Court of Appeals for the Eighth Circuit", "pdf_url": u,
                   "cl_url": f"https://www.courtlistener.com/opinion/{cid}/{c['slug']}/", "head_matter": "",
                   "groups": {k: v[:40] for k, v in g.items()}, "text": t, "via": "CL bulk data + ecf.ca8 official PDF"}, open(fn, "w"))
        return "hit"
    open(nf, "w").write("no pdf"); return "nopdf"


def main():
    dk = {}
    for l in open(RAW + "/bulk_dockets.jsonl"):
        x = json.loads(l)
        if x["court_id"] == "ca8":
            dk[x["id"]] = x
    cites = collections.defaultdict(list)
    if os.path.exists(RAW + "/bulk_citations.jsonl"):
        for l in open(RAW + "/bulk_citations.jsonl"):
            x = json.loads(l); cites[x["cluster_id"]].append(f"{x['volume']} {x['reporter']} {x['page']}")
    cl = []
    for l in open(RAW + "/bulk_clusters.jsonl"):
        c = json.loads(l)
        if c["docket_id"] not in dk or c["precedential_status"] != "Published" or (c["date_filed"] or "") < SINCE:
            continue
        c["cites"] = cites.get(c["id"], [])
        if any(re.match(r"(\d+) F\.3d", x) and int(x.split()[0]) <= 936 for x in c["cites"]):
            continue   # covered by the CAP full-text scan
        c["docket_number"] = dk[c["docket_id"]]["docket_number"]; cl.append(c)
    print("ca8 published clusters to check", len(cl), flush=True)
    C = collections.Counter()
    with ThreadPoolExecutor(3) as ex:
        for i, st in enumerate(ex.map(work, cl)):
            C[st] += 1
            if i % 100 == 0:
                print(i, dict(C), flush=True)
    json.dump(dict(C), open(RAW + "/ca8bulk_stats.json", "w")); print("done", dict(C), flush=True)


if __name__ == "__main__":
    main()
