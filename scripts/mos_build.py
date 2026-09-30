#!/usr/bin/env python3
"""Build data/norms/mo-rsmo.json, data/norms/mo-const.json, data/mo-history/<section>.json and the
repeal/transfer ledger from the raw revisor.mo.gov HTML cached by mos_fetch.py.
Usage: python3 scripts/mos_build.py
"""
import os, re, sys, json, html, hashlib, datetime, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from mos_config import *
from mos_issues import rsmo_issues, const_issues
from mop_issues import proc_rsmo_issues

TODAY = datetime.date.today()
# 2007 ICPC re-enactment is contingent (RSMo 210.650) on enactment by 35 states; 18 states as of 5/31/2024
# (Nevada Senate Judiciary exhibit https://www.leg.state.nv.us/Session/83rd2025/Exhibits/Senate/JUD/SJUD896C.pdf) -> the
# 1975 compact text remains operative; the 2007 text is recorded as a pending/contingent version.
CONTINGENT = {"210.620", "210.622", "210.625", "210.635", "210.640"}
CONTINGENT_NOTE = ("Revisor displays the 2007 re-enactment (effective date shown 8/28/2007), but under RSMo 210.650 it takes effect only upon "
                   "enactment of the new compact by no less than 35 states (18 states as of 5/31/2024 per Nevada Senate Judiciary exhibit, "
                   "https://www.leg.state.nv.us/Session/83rd2025/Exhibits/Senate/JUD/SJUD896C.pdf); the prior (1975/1985) text is treated as in force.")
DATA = os.path.join(ROOT, "data")
for d in ["norms", "mo-history", "coverage", "issues"]:
    os.makedirs(os.path.join(DATA, d), exist_ok=True)


def mdy(s):
    m = re.match(r"(\d+)/(\d+)/(\d{4})", s.strip()) if s else None
    return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat() if m else None


MONTHS = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def effdt(h):
    m = re.search(r'id="effdt"[^>]*>(.*?)</span>\s*<a', h, re.S)
    raw = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
    raw = re.sub(r"\s+", " ", raw)
    d = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", raw)
    iso = datetime.date(int(d.group(3)), MONTHS[d.group(2)], int(d.group(1))).isoformat() if d else None
    return raw, iso


def clean(frag):
    frag = re.sub(r"<br\s*/?>", "\n", frag)
    frag = re.sub(r"</(p|tr|h\d|div)>", "\n\n", frag)
    frag = re.sub(r"</t[dh]>", "\t", frag)
    t = html.unescape(re.sub(r"<[^>]+>", "", frag)).replace("\u00ad", "").replace("\xa0", " ")
    t = re.sub(r"[^\S\n]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def parse_section(h):
    out = {}
    out["effdt_raw"], out["effective"] = effdt(h)
    m = re.search(r'<div class="norm"[^>]*>(.*?)</div>\s*</div>\s*<hr>', h, re.S) or re.search(r'<div class="norm"[^>]*>(.*?)<hr>', h, re.S)
    body = m.group(1) if m else ""
    foot = ""
    if '<div class="foot"' in body:
        body, foot = body.split('<div class="foot"', 1)
        foot = foot.split(">", 1)[1]
    # heading = bold span opening the first paragraph: <span class="bold"> 452.375.<span>  </span>Heading — </span>
    hm = re.match(r'\s*<p class="[^"]*norm[^"]*">\s*(<span class="bold">\s*(.*?)<span>[^<]*</span>(.*?)</span>)', body, re.S)
    if not hm:  # constitution / other layouts: bold span without inner spacer span
        hm2 = re.match(r'\s*<p class="[^"]*norm[^"]*">\s*(<span class="bold">(.*?)</span>)', body, re.S)
    heading = ""
    if hm:
        heading = clean(hm.group(3))
        body = body.replace(hm.group(1), "", 1)
    elif hm2:
        raw = clean(hm2.group(2))
        mm = re.match(r"\s*([0-9]+\.[0-9]+\.?|[IVXL]+ Section [0-9()a-z]+\.?)\s*(.*)", raw)
        if mm:
            heading = mm.group(2)
            body = body.replace(hm2.group(1), "", 1)
    heading = re.sub(r"\s*—\s*$", "", heading).strip()
    text = clean(body)
    out["heading"], out["text"] = heading, text
    fps = [clean(p) for p in re.findall(r'<p class="norm">(.*?)</p>', foot, re.S)]
    hist = [p for p in fps if re.match(r"\((L\.|Adopted|RSMo|Amended|CC|Transferred|Repealed|.*\bL\. \d{4})", p)]
    out["history_note"] = hist[0] if hist else (fps[0] if fps else None)
    out["notes"] = [p for p in fps if p != out["history_note"]]
    # links inside body (xrefs)
    out["links"] = sorted(set(re.findall(r'OneSection\.aspx\?section=([0-9]+\.[0-9]+)', body)))
    # versions table
    vers = []
    tbl = h.split("All versions", 1)[1] if "All versions" in h else ""
    for row in re.findall(r"<tr style=\"width:100%;([^\"]*)\">(.*?)</tr>", tbl, re.S):
        style, cells = row
        bm = re.search(r"bid=(\d+)", cells)
        if not bm:
            continue
        tds = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", cells, re.S)]
        vers.append({"bid": bm.group(1), "effective": mdy(tds[1]) if len(tds) > 1 else None,
                     "end": mdy(tds[2]) if len(tds) > 2 else None, "shown": "red" in style,
                     "extra": " ".join(t for t in tds[3:] if t)})
    out["versions"] = vers
    return out


def norm_text(t):
    return re.sub(r"\s+", " ", t or "").strip()


def subsecs(t):
    """split text into numbered subsections '1.', '2.' at paragraph starts"""
    parts, cur, key = {}, [], "0"
    for p in (t or "").split("\n\n"):
        m = re.match(r"(\d+)\.\s", p)
        if m:
            parts[key] = norm_text(" ".join(cur)); cur, key = [], m.group(1)
        cur.append(p)
    parts[key] = norm_text(" ".join(cur))
    return parts


def chapter_meta(ch):
    h = open(os.path.join(RAW, "chapters", f"{ch}.html"), encoding="utf-8", errors="replace").read()
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", h)))
    tm = re.search(r"\| (Title [IVXLC]+ [^|]+?) \|", t)
    cm = re.search(r"\| (Chapter %s [^|]+?) \|" % ch, t)
    return (tm.group(1).strip() if tm else None, cm.group(1).strip() if cm else f"Chapter {ch}",
            hashlib.sha256(h.encode()).hexdigest())


def sec_url(s, bid=None):
    return f"{BASE}/main/OneSection.aspx?section={s}" + (f"&bid={bid}" if bid else "")


def main():
    listing = json.load(open(os.path.join(RAW, "chapter_listing.json")))
    norms, excluded, gaps, hist_count, concurrent = [], [], [], 0, []
    chmeta = {ch: chapter_meta(ch) for ch in listing}
    secs = sorted({r["section"] for ch, rows in listing.items() for r in rows if in_scope(ch, r["section"])}, key=secnum_key)
    ids = {f"mo-rsmo-{s}" for s in secs}
    for s in secs:
        ch = s.split(".")[0]
        p = os.path.join(RAW, "sections", f"{s}__cur.html")
        if not os.path.exists(p):
            gaps.append(f"{s}: current page not fetched"); continue
        h = open(p, encoding="utf-8", errors="replace").read()
        if 'id="effdt"' not in h:
            gaps.append(f"{s}: current page invalid (blocked?)"); continue
        d = parse_section(h)
        today = TODAY.isoformat()
        vers = d["versions"] or [{"bid": None, "effective": d["effective"], "end": None, "shown": True}]
        cands = [v for v in vers if v["effective"] and v["effective"] <= today and (not v["end"] or v["end"] > today)]
        shown = next((v for v in vers if v["shown"]), None)
        curv = shown if shown in cands else (max(cands, key=lambda v: v["effective"]) if cands else None)
        if s in CONTINGENT and len(cands) > 1:
            curv = min(cands, key=lambda v: v["effective"])
        status = "in force" if curv else "not yet in force"
        if curv and shown is not curv and curv["bid"]:
            vp = os.path.join(RAW, "sections", f"{s}__{curv['bid']}.html")
            if os.path.exists(vp) and 'id="effdt"' in open(vp, encoding="utf-8", errors="replace").read():
                d2 = parse_section(open(vp, encoding="utf-8", errors="replace").read())
                d2["versions"] = d["versions"]
                d = d2
            else:
                gaps.append(f"{s}: in-force version bid={curv['bid']} page not fetched"); continue
        if not d["heading"]:
            d["heading"] = next((r["title"] for r in listing[ch] if r["section"] == s and (not curv or r["bid"] == curv["bid"])),
                                next((r["title"] for r in listing[ch] if r["section"] == s), "")).strip()
        low = (d["heading"] + " " + d["text"][:200]).lower()
        if re.match(r"\(?(repealed|transferred)", d["heading"].lower()) or re.match(r"\(?(repealed|transferred)\b", d["text"][:40].lower()):
            status = "repealed" if "repealed" in low else "transferred"
        cur_bid = curv["bid"] if curv else None
        eff = curv["effective"] if curv else d["effective"]
        if status != "in force":
            excluded.append({"section": s, "status": status, "heading": d["heading"], "effective": eff, "url": sec_url(s)})
            continue
        prior, pending = [], []
        cur_sub = subsecs(d["text"])
        for v in d["versions"]:
            if v["bid"] == cur_bid:
                continue
            vp = os.path.join(RAW, "sections", f"{s}__{v['bid']}.html")
            rec = {"effective": v["effective"], "end": v["end"], "bid": v["bid"], "url": sec_url(s, v["bid"])}
            if os.path.exists(vp):
                vh = open(vp, encoding="utf-8", errors="replace").read()
                if 'id="effdt"' in vh:
                    vd = parse_section(vh)
                    rec.update({"heading": vd["heading"], "text": vd["text"], "history_note": vd["history_note"],
                                "effdt_raw": vd["effdt_raw"]})
                    vs = subsecs(vd["text"])
                    rec["identical_to_current"] = norm_text(vd["text"]) == norm_text(d["text"])
                    rec["subsections_changed_vs_current"] = sorted({k for k in set(vs) | set(cur_sub) if vs.get(k) != cur_sub.get(k)}, key=lambda x: int(x))
            if "text" not in rec:
                gaps.append(f"{s}: version bid={v['bid']} ({v['effective']}) text not fetched")
            if v["effective"] and v["effective"] > today:
                rec["note"] = "future version (not yet in force)"
                pending.append(rec)
            elif not v["end"] or v["end"] > today:
                rec["note"] = "concurrent version without end date (contingent / multiple enactment) — see revisor footnote"
                pending.append(rec)
                concurrent.append({"section": s, "current_bid": cur_bid, "current_effective": eff, "other_bid": v["bid"], "other_effective": v["effective"]})
            else:
                prior.append(rec)
        prior.sort(key=lambda r: r["effective"] or "", reverse=True)
        hist_doc = {"section": s, "official_url": sec_url(s), "current": {"effective": eff, "bid": cur_bid, "url": sec_url(s, cur_bid) if cur_bid else sec_url(s)},
                    "versions": prior, "pending_or_concurrent": pending, "generated": TODAY.isoformat()}
        json.dump(hist_doc, open(os.path.join(DATA, "mo-history", f"{s}.json"), "w"), indent=2, ensure_ascii=False)
        hist_count += len(prior)
        title, chap, _ = chmeta[ch]
        path = ([{"label": title, "id": "title-" + title.split()[1].lower()}] if title else []) + [{"label": chap, "id": f"ch-{ch}"}]
        n = {
            "id": f"mo-rsmo-{s}", "corpus": "mo-rsmo", "side": "mo", "lang": "en", "kind": "section", "num": s,
            "heading": d["heading"], "path": path, "text": d["text"], "in_force_since": eff, "status": "in force",
            "applies_to": ["MO"], "official_url": sec_url(s), "alt_urls": ([{"label": "Revisor — this version (bid)", "url": sec_url(s, cur_bid)}] if cur_bid else []),
            "source_ids": {"rsmo": s, "revisor_bid": cur_bid, "effdt_raw": d["effdt_raw"], "history_note": d["history_note"],
                           "history": [{"effective": r["effective"], "end": r["end"], "url": r["url"]} for r in prior],
                           "history_file": f"data/mo-history/{s}.json",
                           "pending": [{"effective": r["effective"], "url": r["url"], "note": r.get("note")} for r in pending],
                           "text_sha256": hashlib.sha256(norm_text(d["text"]).encode()).hexdigest()},
            "revisor_notes": d["notes"],
            "issues": (rsmo_issues(s, d["heading"]) if in_family(ch, s) else []) + (proc_rsmo_issues(s, d["heading"]) if ch in PROC_CHAPTERS else []),
            "xrefs": [f"mo-rsmo-{x}" for x in d["links"] if f"mo-rsmo-{x}" in ids and x != s],
            "interps": [],
            "axes": axes_for(ch, s),
        }
        if s in CONTINGENT:
            n["status_note"] = CONTINGENT_NOTE
        if not n["revisor_notes"]:
            del n["revisor_notes"]
        norms.append(n)
    # repeals/transfers ledger
    rx = open(os.path.join(RAW, "rx.html"), encoding="utf-8", errors="replace").read()
    rx_rows = []
    for s, bid, t in re.findall(r'PageSelect\.aspx\?section=([0-9]+\.[0-9]+)&amp;bid=(\d+)&amp;hl=" style="text-decoration:none;">[^<]*</a>\s*</td>\s*<td[^>]*>(.*?)</td>', rx, re.S):
        ch = s.split(".")[0]
        if in_scope(ch, s):
            txt = clean(t)
            dm = re.search(r"\((\d+/\d+/\d{4})\)\s*$", txt)
            rx_rows.append({"section": s, "note": re.sub(r"\s*\(\d+/\d+/\d{4}\)\s*$", "", txt), "date": mdy(dm.group(1)) if dm else None,
                            "kind": "transferred" if "Transferred" in txt else "repealed", "url": sec_url(s, bid)})
    out = {"corpus": "mo-rsmo", "generated": TODAY.isoformat(), "norms": norms}
    json.dump(out, open(os.path.join(DATA, "norms", "mo-rsmo.json"), "w"), indent=2, ensure_ascii=False)

    # constitution
    cnorms = []
    for art, sec in CONST:
        p = os.path.join(RAW, "const", f"{art}-{sec}.html")
        if not os.path.exists(p):
            gaps.append(f"Const art. {art} § {sec}: not fetched"); continue
        h = open(p, encoding="utf-8", errors="replace").read()
        d = parse_section(h)
        sid = f"{art}    {sec}"
        url = f"{BASE}/main/OneSection.aspx?section={urllib.parse.quote(sid)}&constit=y"
        cnorms.append({
            "id": f"mo-const-{art.lower()}-{sec.lower().replace('(', '').replace(')', '')}", "corpus": "mo-const", "side": "mo", "lang": "en",
            "kind": "section", "num": f"art. {art}, § {sec}", "heading": d["heading"],
            "path": [{"label": "Constitution of Missouri (1945)", "id": "mo-const"}, {"label": f"Article {art}", "id": f"art-{art.lower()}"}],
            "text": d["text"], "in_force_since": d["effective"], "status": "in force", "applies_to": ["MO"], "official_url": url,
            "alt_urls": [], "source_ids": {"mo_const": f"{art}-{sec}", "history_note": d["history_note"], "effdt_raw": d["effdt_raw"],
                                           "text_sha256": hashlib.sha256(norm_text(d["text"]).encode()).hexdigest()},
            "revisor_notes": d["notes"], "issues": const_issues(art, sec), "xrefs": [], "interps": [],
            "axes": ["family", "procedure"] if (art, sec) == ("V", "5") else ["family"]})
    for n in cnorms:
        if n["id"] == "mo-const-i-33":
            n["status_note"] = ("Text remains on the books but is unenforceable to the extent it bars same-sex marriage: "
                                "Obergefell v. Hodges, 576 U.S. 644 (2015) (noted in the revisor's annotation).")
    json.dump({"corpus": "mo-const", "generated": TODAY.isoformat(), "norms": cnorms}, open(os.path.join(DATA, "norms", "mo-const.json"), "w"), indent=2, ensure_ascii=False)

    listed = sum(1 for ch, rows in listing.items() for r in rows if in_scope(ch, r["section"]))
    cov = {"corpus": "mo-rsmo", "norms_expected": len(secs), "norms_done": len(norms), "interps_candidates": 0, "interps_screened": 0,
           "interps_included": 0,
           "method": ("Chapter index pages of revisor.mo.gov (OneChapter.aspx) enumerated programmatically for chapters "
                      + ", ".join(FULL_CHAPTERS) + " (every section; family axis), procedure-axis chapters (SCOPE §4.5) " + ", ".join(PROC_CHAPTERS) + " (every section) and the selected sections/ranges of chapters "
                      + "; ".join(f"{k}: {v}" for k, v in PARTIAL.items())
                      + ". Every section page (OneSection.aspx) fetched; heading, text, Effective date, history note parsed; every prior version "
                        "listed in the 'All versions' table fetched by bid and stored in data/mo-history/<section>.json with text and a "
                        "normalized-text identity flag vs. the current text (for the SCOPE §2(b) test). Repealed/transferred sections are "
                        "taken from revisor rx.aspx and listed below (excluded from norms). Interpretations are handled by the case-law agent."),
           "chapter_listing_rows_in_scope": listed, "prior_versions_stored": hist_count,
           "excluded_not_in_force": excluded, "concurrent_versions": concurrent, "repealed_transferred": rx_rows,
           "gaps": gaps, "updated": TODAY.isoformat(), "id_convention": "mo-rsmo-<section> e.g. mo-rsmo-452.375"}
    json.dump(cov, open(os.path.join(DATA, "coverage", "mo-rsmo.json"), "w"), indent=2, ensure_ascii=False)
    json.dump({"corpus": "mo-const", "norms_expected": len(CONST), "norms_done": len(cnorms), "interps_candidates": 0, "interps_screened": 0,
               "interps_included": 0, "method": "Selected Missouri Constitution sections per SCOPE §4.3 fetched from revisor.mo.gov (constit=y).",
               "gaps": [g for g in gaps if g.startswith("Const")], "updated": TODAY.isoformat()},
              open(os.path.join(DATA, "coverage", "mo-const.json"), "w"), indent=2, ensure_ascii=False)
    print("norms", len(norms), "const", len(cnorms), "excluded", len(excluded), "rx", len(rx_rows), "prior versions", hist_count, "gaps", len(gaps))


if __name__ == "__main__":
    main()
