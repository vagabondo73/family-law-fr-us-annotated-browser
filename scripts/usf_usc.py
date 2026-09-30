#!/usr/bin/env python3
"""Fetch & parse U.S. Code sections (uscode.house.gov, prelim edition) -> data/norms/us-usc.json.
Re-runnable: cached HTML in raw/us/usc/ (delete a file or pass --refresh to refetch).
D(norm) = enactment date of the latest amending Public Law affecting the section (source credit) or,
for subdivision-level norms, the latest Public Law whose Amendments note targets that subdivision.
"""
import html, json, os, re, sys, time, urllib.request, datetime, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import USC, ROOT, RAW

CACHE = RAW + "/usc"
os.makedirs(CACHE, exist_ok=True)
REFRESH = "--refresh" in sys.argv
UA = {"User-Agent": "Mozilla/5.0 (flb research; family-law annotated browser)"}
MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "June": 6, "July": 7, "Aug": 8, "Sept": 9,
          "Oct": 10, "Nov": 11, "Dec": 12}


def url_for(t, s, ed="prelim"):
    return f"https://uscode.house.gov/view.xhtml?req=granuleid:USC-{ed}-title{t}-section{s}&num=0&edition={ed}"


def get(t, s, ed="prelim"):
    fn = f"{CACHE}/{t}-{s}.html" if ed == "prelim" else f"{CACHE}/{t}-{s}-{ed}.html"
    if os.path.exists(fn) and not REFRESH:
        return open(fn, encoding="utf-8").read()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url_for(t, s, ed), headers=UA)
            data = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
            open(fn, "w", encoding="utf-8").write(data)
            time.sleep(1)
            return data
        except Exception as e:
            print("retry", t, s, e, flush=True)
            time.sleep(5)
    return ""


def strip(h):
    h = re.sub(r"<br[^>]*>", " ", h)
    h = re.sub(r"<[^>]+>", "", h)
    return re.sub(r"[ \t\r\n]+", " ", html.unescape(h)).strip()


def blocks(h):
    out = []
    for m in re.finditer(r"<(h[1-6]|p)\b[^>]*>(.*?)</\1>", h, re.S):
        t = strip(m.group(2))
        if t:
            out.append(t)
    return out


def field(s, name):
    m = re.search(r"<!-- field-start:%s -->(.*?)<!-- field-end:%s -->" % (name, name), s, re.S)
    return m.group(1) if m else ""


def publaws(credit_text):
    """Map 'congress-number' -> ISO date from a source credit."""
    res = {}
    for m in re.finditer(r"Pub\. L\. (\d+)[–-](\d+)((?:(?!Pub\. L\.).)*?)\b(Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec)\.? (\d{1,2}), (\d{4})", credit_text):
        k = f"{m.group(1)}-{m.group(2)}"
        d = datetime.date(int(m.group(6)), MONTHS[m.group(4)], int(m.group(5))).isoformat()
        res.setdefault(k, d)
    return res


def amend_notes(s):
    """Return list of dicts {year, text, publaws:[k], target} from the Amendments note."""
    notes = []; cur = ""
    for m in re.finditer(r"<!-- field-start:amendment-note -->(.*?)<!-- field-end:amendment-note -->", s, re.S):
        year = None
        for b in blocks(m.group(1)):
            if b == "Amendments":
                continue
            ym = re.match(r"(\d{4})[—-]", b)
            if ym:
                year = int(ym.group(1)); b = b[ym.end():]
            pls = [f"{a}-{c}" for a, c in re.findall(r"Pub\. L\. (\d+)[–-](\d+)", b)]
            tm = re.match(r"\s*(Subsecs?\.|Pars?\.|Subpars?\.)\s*([^.]*)\.", b)
            if ym:
                cur = ""
            if tm and tm.group(1).startswith("Subsec"):
                cur = tm.group(0).strip()
            tgt = tm.group(0).strip() if tm else cur  # untargeted paragraphs inherit the preceding Subsec. target
            if not tgt and not re.search(r"amended (this )?section generally|struck out|redesignated|transferred", b):
                tgt = ""
            notes.append(dict(year=year, text=b, publaws=pls, target=tgt))
    return notes


def sub_label(sub):
    return "".join(f"({p})" for p in sub.split("_"))


def target_matches(target, sub):
    """Does an Amendments-note target line concern subdivision sub (e.g. 'a_5')?"""
    if not target:
        return True  # section-wide amendment
    parts = sub.split("_")
    labels = re.findall(r"\(([^)]+)\)", target)
    if target.startswith("Subsec"):
        # e.g. 'Subsec. (a)(5).' or 'Subsecs. (a) to (c).'
        if not labels:
            return True
        first = labels[0]
        if " to " in target and len(labels) >= 2:
            lo, hi = labels[0], labels[1]
            return lo <= parts[0] <= hi if len(lo) == len(hi) == 1 else parts[0] in labels
        if first != parts[0]:
            return False
        rest = labels[1:]
        if len(parts) == 1:
            return True
        if not rest:
            return None  # subsection-level target: refine by paragraph mentions in note text
        return rest[0] == parts[1]
    return None  # Par./Subpar. — resolved relative to previous Subsec. by caller


def section_block(stat, sub):
    """Extract statute HTML for subdivision `sub` using uscode anchors."""
    anchors = [(m.start(), m.group(1)) for m in re.finditer(r'<a name="substructure-location_([^"]+)"', stat)]
    start = None
    for i, (pos, name) in enumerate(anchors):
        if name.lower() == sub.lower():
            start = i; break
    if start is None:
        return None
    endpos = len(stat)
    for pos, name in anchors[start + 1:]:
        if not name.lower().startswith(sub.lower() + "_"):
            endpos = pos; break
    return stat[anchors[start][0]:endpos]


def main():
    norms, gaps = [], []
    for e in USC:
        t, sec, sub = e["title"], e["sec"], e["sub"]
        ed = e.get("edition") or "prelim"
        s = get(t, sec, ed)
        head = re.search(r'<h3 class="section-head">(.*?)</h3>', s, re.S)
        if not head:
            gaps.append(f"{t} U.S.C. {sec}: no section found at uscode.house.gov (omitted)"); continue
        heading = strip(head.group(1))
        heading = re.sub(r"^§\s*\S+\.\s*", "", heading)
        if heading.lower().startswith(("repealed", "omitted", "transferred", "renumbered")) or heading.startswith("["):
            status = "repealed"
        else:
            status = e.get("status") or "in force"
        stat = field(s, "statute")
        if sub:
            blk = section_block(stat, sub)
            if blk is None:
                gaps.append(f"{t} U.S.C. {sec}{sub_label(sub)}: subdivision anchor not found"); continue
            text = "\n\n".join(blocks(blk))
        else:
            text = "\n\n".join(blocks(stat))
        credit = strip(field(s, "sourcecredit"))
        pl = publaws(credit)
        notes = amend_notes(s)
        # D(norm)
        if pl:
            section_last = max(pl.values())
        else:
            section_last = None
        if sub:
            relevant, cur = [], None
            for n in notes:
                tm = target_matches(n["target"], sub)
                if n["target"].startswith("Subsec"):
                    cur = n["target"]
                if tm is None:  # Par. relative to current subsec, or subsection-level target
                    parts = sub.split("_")
                    if n["target"].startswith("Subsec") and re.search(r"in (introductory|concluding) provisions", n["text"]) and not re.search(r"\b[Pp]ars?\. \(", n["text"]):
                        tm = False  # amendment only to the lead-in/flush language of the subsection
                    elif n["target"].startswith("Subsec"):
                        pars = re.findall(r"\b[Pp]ars?\. \(([^)]+)\)", n["text"])
                        tm = (not pars) or parts[1] in pars
                    else:
                        labs = re.findall(r"\(([^)]+)\)", n["target"])
                        cl = re.findall(r"\(([^)]+)\)", cur or "")
                        tm = bool(cl) and cl[0] == parts[0] and bool(labs) and labs[0] == parts[1]
                if tm:
                    relevant.append(n)
            dates = [pl[k] for n in relevant for k in n["publaws"] if k in pl]
            # original enactment of section as floor
            first = min(pl.values()) if pl else None
            d = max(dates) if dates else first
            d_method = "latest Public Law whose Amendments note targets this subdivision (else original enactment)"
        else:
            relevant = notes
            d = section_last
            d_method = "latest Public Law in section source credit"
        ch = re.search(r"<!-- expcite:(.*?) -->", s)
        path = []
        if ch:
            for p in html.unescape(ch.group(1)).split("!@!"):
                p = strip(p)
                if not p.startswith("Sec."):
                    path.append({"label": p})
        former = re.search(r"Section was formerly classified to (?:<[^>]+>)*(section [^<]+)", field(s, "codification-note"))
        nid = f"us-usc-{t}-{sec}".lower() + (("-" + sub.replace("_", "-")).lower() if sub else "")
        num = f"{t} U.S.C. § {sec}" + (sub_label(sub) if sub else "")
        rec = {
            "id": nid, "corpus": "us-usc", "side": "us", "lang": "en", "kind": "section",
            "num": num, "heading": heading + ((" — " + sub_label(sub)) if sub else ""),
            "path": path, "text": text, "in_force_since": d, "status": status,
            "applies_to": ["US"], "official_url": url_for(t, sec, ed),
            "alt_urls": [{"label": "govinfo (USCODE)", "url": f"https://www.govinfo.gov/app/details/USCODE-2023-title{t}"}],
            "source_ids": {"usc": f"{t} USC {sec}" + (sub_label(sub) if sub else ""), "source_credit": credit,
                            "text_sha1": hashlib.sha1(text.encode()).hexdigest()},
            "d_method": d_method,
            "amendments": [{"year": n["year"], "target": n["target"],
                            "publaws": {k: pl.get(k) for k in n["publaws"]}, "note": n["text"][:600]} for n in relevant],
            "issues": e["issues"], "xrefs": [], "interps": [],
        }
        if e.get("note"):
            rec["status_note"] = e["note"]
        if ed != "prelim":
            rec["alt_urls"].insert(0, {"label": "uscode.house.gov (current prelim: repealed)", "url": url_for(t, sec)})
        if e["former"]:
            rec["source_ids"]["former_classification"] = e["former"]
        elif former:
            rec["source_ids"]["former_classification"] = [strip(former.group(1))]
        norms.append(rec)
        print(nid, d, len(text), status, flush=True)
    os.makedirs(ROOT + "/data/norms", exist_ok=True)
    json.dump({"corpus": "us-usc", "generated": datetime.date.today().isoformat(), "norms": norms},
              open(ROOT + "/data/norms/us-usc.json", "w"), indent=2, ensure_ascii=False)
    json.dump(gaps, open(RAW + "/usc_gaps.json", "w"), indent=2)
    print("norms", len(norms), "gaps", gaps)


if __name__ == "__main__":
    main()
