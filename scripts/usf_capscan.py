#!/usr/bin/env python3
"""Exhaustive candidate enumeration over the Caselaw Access Project static bulk (static.case.law):
U.S. Reports vols 1-572 (SCOTUS through 2014) and F.2d 1-999 / F.3d 1-936 (8th Cir. opinions through mid-2019).
Each volume zip is streamed, 8th Cir./SCOTUS opinions are regex-screened (usf_patterns), hits are saved to
raw/us/cap_hits/<rep>-<vol>-<file>.json (full text kept only in raw/ for excerpting). Checkpoint: raw/us/capscan_done.txt
Usage: usf_capscan.py [us|f2d|f3d ...]
"""
import io, json, os, sys, time, zipfile, urllib.request, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW
from usf_patterns import match_groups

HD = RAW + "/cap_hits"; os.makedirs(HD, exist_ok=True)
DONE = RAW + "/capscan_done.txt"
RANGES = {"us": range(1, 573), "f2d": range(1, 1000), "f3d": range(1, 937)}
COURT = {"us": None, "f2d": "8th Cir.", "f3d": "8th Cir."}


def fetch(url):
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (flb research)"})
            return urllib.request.urlopen(req, timeout=120).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(3)
        except Exception:
            time.sleep(3)
    raise RuntimeError("fetch failed " + url)


def scan(rep, vol):
    b = fetch(f"https://static.case.law/{rep}/{vol}.zip")
    if b is None:
        return rep, vol, 0, 0
    z = zipfile.ZipFile(io.BytesIO(b))
    n = hits = 0
    for name in z.namelist():
        if not name.endswith(".json") or "/json/" not in "/" + name:
            continue
        d = json.loads(z.read(name))
        if COURT[rep] and d.get("court", {}).get("name_abbreviation") != COURT[rep]:
            continue
        n += 1
        if (d.get("analysis") or {}).get("word_count", 1000) < 150:
            continue  # table entries / summary dispositions without opinion
        ops = d.get("casebody", {}).get("opinions", [])
        text = "\n\n".join(f"[[OPINION type={o.get('type')} author={o.get('author')}]]\n{o.get('text','')}" for o in ops)
        g = match_groups(text)
        if not g:
            continue
        hits += 1
        rec = {"cap_id": d["id"], "name": d.get("name_abbreviation"), "name_full": d.get("name"), "date": d.get("decision_date"),
               "docket": d.get("docket_number"), "citations": [c["cite"] for c in d.get("citations", [])],
               "court": d.get("court", {}).get("name"), "rep": rep, "vol": vol, "file": d.get("file_name"),
               "cap_url": f"https://static.case.law/{rep}/{vol}/cases/{d.get('file_name')}.json",
               "groups": {k: v[:40] for k, v in g.items()}, "head_matter": d.get("casebody", {}).get("head_matter", ""), "text": text}
        json.dump(rec, open(f"{HD}/{rep}-{vol}-{d.get('file_name')}.json", "w"))
    return rep, vol, n, hits


def main():
    reps = sys.argv[1:] or ["us", "f3d", "f2d"]
    done = set(open(DONE).read().split()) if os.path.exists(DONE) else set()
    todo = [(r, v) for r in reps for v in RANGES[r] if f"{r}-{v}" not in done]
    print("todo", len(todo), flush=True)
    with cf.ThreadPoolExecutor(4) as ex, open(DONE, "a") as fd:
        futs = {ex.submit(scan, r, v): (r, v) for r, v in todo}
        for f in cf.as_completed(futs):
            r, v = futs[f]
            try:
                _, _, n, h = f.result()
                fd.write(f"{r}-{v}\n"); fd.flush()
                if h:
                    print(r, v, n, h, flush=True)
            except Exception as e:
                print("ERR", r, v, e, flush=True)


if __name__ == "__main__":
    main()
