#!/usr/bin/env python3
"""Fetch CFR parts/sections from the eCFR API -> data/norms/us-cfr.json.
D(norm) = latest of (eCFR versioner amendment_date for the section, latest Federal Register date in the section
[CITA] note, or — when the section has no CITA — the part [SOURCE] note).
"""
import html, json, os, re, sys, time, urllib.request, datetime, gzip, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import CFR_PARTS, CFR_SECTIONS, ROOT, RAW

CACHE = RAW + "/cfr"; os.makedirs(CACHE, exist_ok=True)
REFRESH = "--refresh" in sys.argv
API = "https://www.ecfr.gov/api/versioner/v1"
MON = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"])}
MON.update({"Sep": 9, "Jun": 6, "Jul": 7, "March": 3, "April": 4, "January": 1, "February": 2, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12})


def get(url, fn):
    path = f"{CACHE}/{fn}"
    if os.path.exists(path) and not REFRESH:
        return open(path, encoding="utf-8").read()
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip", "User-Agent": "flb-research"})
    for a in range(3):
        try:
            r = urllib.request.urlopen(req, timeout=90); b = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                b = gzip.decompress(b)
            s = b.decode("utf-8"); open(path, "w", encoding="utf-8").write(s); time.sleep(0.5); return s
        except Exception as e:
            print("retry", url, e, flush=True); time.sleep(4)
    return ""


def strip(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", h))).strip()


def fr_dates(s):
    out = []
    for m in re.finditer(r"FR \d+, ((?:Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec|Jun|Jul|Sep)[a-z]*)\.? (\d{1,2}), (\d{4})", s):
        mo = MON.get(m.group(1)) or MON.get(m.group(1)[:3])
        try:
            out.append(datetime.date(int(m.group(3)), mo, int(m.group(2))).isoformat())
        except Exception:
            pass
    return out


def main():
    titles = json.loads(get(API + "/titles.json", "titles.json"))["titles"]
    asof = {t["number"]: t["up_to_date_as_of"] for t in titles}
    norms, gaps = [], []
    work = [(t, p, iss, None) for t, p, iss in CFR_PARTS]
    for t, sec, iss in CFR_SECTIONS:
        work.append((t, sec.split(".")[0], iss, sec))
    parts_done = {}
    for t, part, iss, only in work:
        key = (t, part)
        if key not in parts_done:
            xml = get(f"{API}/full/{asof[t]}/title-{t}.xml?part={part}", f"t{t}-p{part}.xml")
            ver = get(f"{API}/versions/title-{t}.json?part={part}", f"t{t}-p{part}-versions.json")
            try:
                vers = json.loads(ver)["content_versions"]
            except Exception:
                vers = []
            parts_done[key] = (xml, vers)
        xml, vers = parts_done[key]
        if not xml:
            gaps.append(f"{t} CFR part {part}: fetch failed"); continue
        partsrc = re.search(r"<SOURCE>(.*?)</SOURCE>", xml, re.S)
        partsrc = strip(partsrc.group(1)) if partsrc else ""
        heads = re.findall(r'<DIV5 N="[^"]+" TYPE="PART"[^>]*>\s*<HEAD>(.*?)</HEAD>', xml, re.S)
        parthead = strip(heads[0]) if heads else f"Part {part}"
        subpart = None
        for m in re.finditer(r'<DIV6 N="([^"]+)" TYPE="SUBPART"[^>]*>\s*<HEAD>(.*?)</HEAD>|<DIV8 N="([^"]+)" TYPE="SECTION"[^>]*>(.*?)</DIV8>', xml, re.S):
            if m.group(1):
                subpart = strip(m.group(2)); continue
            sec, body = m.group(3), m.group(4)
            if only and sec != only:
                continue
            head = strip(re.search(r"<HEAD>(.*?)</HEAD>", body, re.S).group(1))
            cita = re.search(r"<CITA[^>]*>(.*?)</CITA>", body, re.S)
            cita = strip(cita.group(1)) if cita else ""
            body2 = re.sub(r"<CITA[^>]*>.*?</CITA>", "", body, flags=re.S)
            body2 = re.sub(r"<HEAD>.*?</HEAD>", "", body2, count=1, flags=re.S)
            paras = [strip(p) for p in re.findall(r"<(?:P|FP|HD1|HD2|HD3)[^>]*>(.*?)</(?:P|FP|HD1|HD2|HD3)>", body2, re.S)]
            text = "\n\n".join(p for p in paras if p)
            vd = [v["amendment_date"] for v in vers if v.get("identifier") == sec and not v.get("removed")]
            fd = fr_dates(cita) if cita else fr_dates(partsrc)
            base = min([v["amendment_date"] for v in vers] or ["0000"])
            vd_real = [x for x in vd if x != base]  # eCFR versioner baseline (start of eCFR history) is not an amendment
            if vd_real:
                d = max(vd_real)  # eCFR 'last amended' (amendment effective date)
                dm = "eCFR versioner amendment_date"
            elif fd:
                d = max(fd); dm = "latest Federal Register citation in section/part source note (pre-eCFR-history)"
            else:
                d = max(vd) if vd else None; dm = "eCFR versioner baseline date (no earlier data)"
            reserved = "[Reserved]" in head or not text
            if reserved and not text:
                continue
            heading = re.sub(r"^§\s*[\d.a-z]+\s*", "", head)
            path = [{"label": f"Title {t} CFR"}, {"label": parthead}] + ([{"label": subpart}] if subpart else [])
            nid = f"us-cfr-{t}-{sec}".lower().replace(".", "-")
            norms.append({
                "id": nid, "corpus": "us-cfr", "side": "us", "lang": "en", "kind": "section",
                "num": f"{t} C.F.R. § {sec}", "heading": heading, "path": path, "text": text,
                "in_force_since": d, "status": "in force", "applies_to": ["US"],
                "official_url": f"https://www.ecfr.gov/current/title-{t}/part-{part}/section-{sec}",
                "alt_urls": [{"label": "govinfo (CFR annual edition)", "url": f"https://www.govinfo.gov/app/collection/cfr"}],
                "source_ids": {"cfr": f"{t} CFR {sec}", "cita": cita or None, "part_source": None if cita else partsrc,
                                "ecfr_as_of": asof[t], "text_sha1": hashlib.sha1(text.encode()).hexdigest()},
                "d_method": dm,
                "issues": iss, "xrefs": [], "interps": []})
        print(t, part, len(norms), flush=True)
    json.dump({"corpus": "us-cfr", "generated": datetime.date.today().isoformat(), "norms": norms},
              open(ROOT + "/data/norms/us-cfr.json", "w"), indent=2, ensure_ascii=False)
    json.dump(gaps, open(RAW + "/cfr_gaps.json", "w"), indent=2)
    print("norms", len(norms), gaps)


if __name__ == "__main__":
    main()
