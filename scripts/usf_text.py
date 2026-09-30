#!/usr/bin/env python3
"""Fetch opinion full text for screening/excerpting (never published; only excerpts are stored in data/).
Order: (1) official PDF from CourtListener download_url (ca8.uscourts.gov / supremecourt.gov) via pdftotext;
(2) Caselaw Access Project static bulk (static.case.law) by reporter citation.
Usage: usf_text.py [cluster_ids...]   (default: all candidates flagged by usf_prescreen as needing text)
"""
import json, os, re, sys, time, urllib.request, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW

TD = RAW + "/texts"; CAPD = RAW + "/cap"
os.makedirs(TD, exist_ok=True); os.makedirs(CAPD, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (flb research)"}
REP = {"U.S.": "us", "F.2d": "f2d", "F.3d": "f3d", "F.": "f"}


def http(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def cap_meta(rep, vol):
    fn = f"{CAPD}/{rep}-{vol}.json"
    if os.path.exists(fn):
        return json.load(open(fn))
    try:
        d = json.loads(http(f"https://static.case.law/{rep}/{vol}/CasesMetadata.json"))
    except Exception:
        d = []
    json.dump(d, open(fn, "w"))
    time.sleep(0.3)
    return d


def from_cap(cites):
    for c in cites or []:
        m = re.match(r"(\d+) (U\.S\.|F\.2d|F\.3d|F\.) (\d+)$", c)
        if not m:
            continue
        rep, vol, page = REP[m.group(2)], m.group(1), m.group(3)
        for case in cap_meta(rep, vol):
            if str(case.get("first_page")) == page:
                url = f"https://static.case.law/{rep}/{vol}/cases/{case['file_name']}.json"
                try:
                    d = json.loads(http(url))
                except Exception:
                    continue
                cb = d.get("casebody", {})
                parts = []
                for h in cb.get("head_matter", "") and [cb["head_matter"]] or []:
                    parts.append(h)
                for o in cb.get("opinions", []):
                    parts.append(f"[[OPINION type={o.get('type')} author={o.get('author')}]]\n" + (o.get("text") or ""))
                return "\n\n".join(parts), url
    return None, None


def from_pdf(urls):
    for u in urls or []:
        if not u or not u.lower().endswith(".pdf"):
            continue
        try:
            b = http(u, timeout=90)
            p = "/tmp/usf_op.pdf"; open(p, "wb").write(b)
            t = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True, timeout=60).stdout
            if len(t) > 500:
                return t, u
        except Exception as e:
            print("pdf fail", u, e, flush=True)
    return None, None


def get_text(c):
    cid = str(c["cluster_id"])
    fn = f"{TD}/{cid}.json"
    if os.path.exists(fn):
        return json.load(open(fn))
    t, src = from_pdf(c.get("download_urls"))
    if not t:
        t, src = from_cap(c.get("citation"))
    rec = {"cluster_id": cid, "source": src, "text": t}
    json.dump(rec, open(fn, "w"))
    return rec


def main():
    cands = json.load(open(RAW + "/candidates.json"))
    ids = sys.argv[1:]
    if not ids:
        pre = RAW + "/prescreen.json"
        ids = json.load(open(pre))["need_text"] if os.path.exists(pre) else list(cands)
    ok = 0
    for i, cid in enumerate(ids):
        r = get_text(cands[cid])
        ok += bool(r["text"])
        if i % 20 == 0:
            print(i, len(ids), ok, flush=True)
    print("done", len(ids), ok)


if __name__ == "__main__":
    main()
