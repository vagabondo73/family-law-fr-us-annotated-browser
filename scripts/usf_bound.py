#!/usr/bin/env python3
"""SCOTUS decisions in U.S. Reports vols. 573-585 (after CAP coverage, before the supremecourt.gov slip-opinion
lists used by usf_slip.py): download the official bound volumes (supremecourt.gov/opinions/boundvolumes/<vol>BV.pdf),
split into cases at each first page carrying the 'No. ... Argued/Decided' line, keep cases matching the SCOPE §4.2
patterns -> raw/us/cl_hits/scotus-<docket>.json. Usage: python3 scripts/usf_bound.py [--vols 573-585]"""
import json, os, re, subprocess, sys, time, urllib.request, datetime
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW
from usf_patterns import match_groups

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
CL = RAW + "/cl_hits"; PD = RAW + "/slip/pdf"; os.makedirs(PD, exist_ok=True)
a, b = (sys.argv[sys.argv.index("--vols") + 1] if "--vols" in sys.argv else "573-585").split("-")
MON = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
DOCK = re.compile(r"(?m)^Nos?\.\s+(\d+[–-]\d+|\d+,\s*Orig\.|\d+A\d+)[^\n]{0,200}?\n?\s*(?:Argued|Submitted|Decided|Reargued)[^\n]*", re.S)
DEC = re.compile(r"Decided\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})")
SMALL = {"v.", "of", "and", "the", "for", "in", "on", "et", "al.", "de", "ex", "rel."}


def tc(s):
    out = []
    for w in s.split():
        lw = w.lower()
        if lw in SMALL and out:
            out.append(lw)
        elif re.fullmatch(r"[A-Z]\.([A-Z]\.)+,?", w) or w in ("LLC", "L.L.C.", "LP", "U.S.", "USA", "FCC", "EPA", "NLRB", "INS", "IRS"):
            out.append(w)
        elif w.startswith("MC") and len(w) > 3:
            out.append("Mc" + w[2:].capitalize())
        else:
            out.append("-".join(p[:1].upper() + p[1:].lower() for p in w.split("-")))
    return " ".join(out)


def get(u, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 100000:
        return
    for k in range(4):
        try:
            data = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=600).read()
            open(dest, "wb").write(data); return
        except Exception as e:
            err = e; time.sleep(10 * (k + 1))
    raise err


def pnum(page):
    for ln in [l.strip() for l in page.split("\n") if l.strip()][:3]:
        if "TERM" in ln or "Cite as" in ln:
            continue
        m = re.match(r"^(\d{1,4})\b", ln) or re.search(r"\b(\d{1,4})$", ln)
        if m:
            return int(m.group(1))
    return None


def main():
    stats = {}
    for vol in range(int(a), int(b) + 1):
        url = f"https://www.supremecourt.gov/opinions/boundvolumes/{vol}BV.pdf"
        loc = f"{PD}/{vol}BV.pdf"
        get(url, loc)
        txt = subprocess.run(["pdftotext", loc, "-"], capture_output=True, text=True).stdout
        pages = txt.split("\f")
        starts = []
        for i, pg in enumerate(pages):
            head = pg[:1500]
            m = DOCK.search(head)
            if m:
                n = pnum(pg)
                if n is None and i + 1 < len(pages) and pnum(pages[i + 1]):
                    n = pnum(pages[i + 1]) - 1
                if n and (not starts or n > starts[-1][1]):
                    starts.append((i, n, m))
        hits = 0
        for k, (i, n, m) in enumerate(starts):
            j = starts[k + 1][0] if k + 1 < len(starts) else min(len(pages), i + 150)
            chunk = "\f".join(pages[i:j])
            dk = re.sub(r"[–\s]", "-", m.group(1)).replace(",-Orig.", "-orig").replace(",Orig.", "-orig")
            fn = f"{CL}/scotus-{dk}.json"
            if os.path.exists(fn):
                continue
            g = match_groups(chunk)
            if not g:
                continue
            d = DEC.search(chunk[:6000])
            date = datetime.date(int(d.group(3)), MON[d.group(1)], int(d.group(2))).isoformat() if d else None
            # short caption = running head of the following (even) page, e.g. '645 OBERGEFELL v. HODGES'
            name = None
            if i + 1 < len(pages):
                for ln in [l.strip() for l in pages[i + 1].split("\n") if l.strip()][:3]:
                    ln2 = re.sub(r"^\d+\s+|\s+\d+$", "", ln)
                    if " v. " in ln2 or ln2.startswith("IN RE") or ln2.startswith("EX PARTE"):
                        name = tc(ln2); break
            if not name:   # caption on the first page: between the TERM line and the lower-court line
                mm = re.search(r"TERM, \d{4}\s*\n(?:\s*Syllabus\s*\n)?\s*(.+?)\n\s*(?:certiorari|on writ|appeal|on application|on petition|on bill)", pages[i], re.S | re.I)
                if mm:
                    cap = re.sub(r"\s+", " ", mm.group(1))
                    sides = [re.split(r",", x)[0].replace(" et al.", "").replace(" ET AL.", "").strip() for x in cap.split(" v. ", 1)]
                    if len(sides) == 2 and all(sides):
                        name = tc(" v. ".join(sides))
            if not name:
                mm = re.search(r"\n([A-Z][A-Z .,'&\-]+ v\. [A-Z][A-Z .,'&\-]+)", chunk[:3000])
                name = tc(re.sub(r",? ET AL\.", "", mm.group(1)).split(",")[0]) if mm else f"No. {m.group(1)}"
            name = re.sub(r"^(\d+\s+)?(Syllabus|Per Curiam|PER CURIAM)\s+", "", name)
            json.dump({"name": name, "date": date, "docket": m.group(1).replace("–", "-"), "citations": [f"{vol} U.S. {n}"],
                       "court": "Supreme Court of the United States", "pdf_url": f"{url}#page={i + 1}", "head_matter": "",
                       "groups": {k2: v[:40] for k2, v in g.items()}, "text": chunk, "via": "supremecourt.gov bound volume"}, open(fn, "w"))
            hits += 1
        stats[vol] = {"cases": len(starts), "hits": hits}
        print(vol, stats[vol], flush=True)
    json.dump(stats, open(RAW + "/slip/bound_stats.json", "w"))


if __name__ == "__main__":
    main()
