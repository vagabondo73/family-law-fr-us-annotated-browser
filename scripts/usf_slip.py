#!/usr/bin/env python3
"""SCOTUS opinions after CAP coverage (U.S. Reports vol. > 572): enumerate every opinion listed on the official
supremecourt.gov 'Opinions of the Court' pages (terms 2013-2025), download the official PDF, extract text, keep
those matching the SCOPE §4.2 patterns -> raw/us/cl_hits/scotus-<docket>.json (same format as seeds). No API quota.
Usage: python3 scripts/usf_slip.py [--terms 13-25]"""
import json, os, re, subprocess, sys, time, urllib.request, html as H
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW
from usf_patterns import match_groups

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
CL = RAW + "/cl_hits"; SD = RAW + "/slip"; os.makedirs(SD, exist_ok=True); os.makedirs(CL, exist_ok=True)
a, b = (sys.argv[sys.argv.index("--terms") + 1] if "--terms" in sys.argv else "13-25").split("-")


def get(u, binary=False):
    for k in range(4):
        try:
            x = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=120).read()
            return x if binary else x.decode("utf-8", "ignore")
        except Exception as e:
            err = e; time.sleep(4 * (k + 1))
    raise err


def rows(term):
    p = f"{SD}/list-{term}.json"
    if os.path.exists(p) and term < int(b):
        return json.load(open(p))
    h = get(f"https://www.supremecourt.gov/opinions/slipopinion/{term}")
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        m = re.search(r"href='(/opinions/[^']+\.pdf(?:#page=\d+)?)'", r)
        if len(tds) < 5 or not m:
            continue
        txt = [re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", t))).strip() for t in tds]
        mm, dd, yy = txt[1].split("/")
        out.append({"date": f"20{yy[-2:]}-{int(mm):02d}-{int(dd):02d}", "docket": txt[2], "name": txt[3],
                    "citation": txt[5] if len(txt) > 5 else "", "pdf_url": "https://www.supremecourt.gov" + m.group(1), "term": term})
    json.dump(out, open(p, "w"), indent=1)
    return out


def main():
    allr = []
    for t in range(int(a), int(b) + 1):
        rs = rows(t); allr += rs; print("term", t, len(rs), flush=True)
    stats = {"listed": len(allr), "hits": 0, "nohit": 0, "fail": 0}
    starts = {}
    for r in allr:
        if "#page=" in r["pdf_url"]:
            base, pg = r["pdf_url"].split("#page=")
            starts.setdefault(base, set()).add(int(pg))
    PD = SD + "/pdf"; os.makedirs(PD, exist_ok=True)

    def text_of(u):
        if "#page=" not in u:
            pdf = get(u, binary=True); tmp = "/tmp/usf_slip_x.pdf"; open(tmp, "wb").write(pdf)
            t = subprocess.run(["pdftotext", tmp, "-"], capture_output=True, text=True).stdout; os.remove(tmp); return t
        base, pg = u.split("#page="); pg = int(pg)
        loc = PD + "/" + base.rsplit("/", 1)[1]
        if not os.path.exists(loc):
            open(loc, "wb").write(get(base, binary=True))
        later = sorted(x for x in starts[base] if x > pg)
        end = (later[0] - 1) if later else pg + 150
        return subprocess.run(["pdftotext", "-f", str(pg), "-l", str(max(pg, end)), loc, "-"], capture_output=True, text=True).stdout
    for r in allr:
        dk = re.sub(r"[^0-9A-Za-z-]", "_", r["docket"].split(",")[0].strip())
        fn = f"{CL}/scotus-{dk}.json"; skip = f"{SD}/nohit-{dk}"
        if os.path.exists(fn) or os.path.exists(skip):
            continue
        v = re.match(r"^(\d+) U\.\s?S\.", r["citation"])
        if v and int(v.group(1)) <= 572:   # already covered by the CAP full-text scan
            continue
        try:
            t = text_of(r["pdf_url"])
        except Exception as e:
            stats["fail"] += 1; print("fail", r["docket"], e, flush=True); continue
        g = match_groups(t)
        if not g:
            open(skip, "w").write(r["name"]); stats["nohit"] += 1; continue
        cit = re.sub(r"\s+", " ", r["citation"]).replace("U. S.", "U.S.")
        cites = [cit] if re.match(r"^\d+ U\.S\. \d+$", cit) else []
        json.dump({"name": re.sub(r"\s*Revisions?\s*:.*$", "", r["name"]).strip(), "date": r["date"], "docket": r["docket"], "citations": cites, "court": "Supreme Court of the United States",
                   "pdf_url": r["pdf_url"], "head_matter": "", "groups": {k: v[:40] for k, v in g.items()}, "text": t, "via": "supremecourt.gov slipopinion list"},
                  open(fn, "w"))
        stats["hits"] += 1; time.sleep(0.5)
    json.dump(stats, open(SD + "/stats.json", "w")); print("done", stats, flush=True)


if __name__ == "__main__":
    main()
