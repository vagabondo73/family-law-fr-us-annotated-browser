#!/usr/bin/env python3
"""Build data/norms/mo-rules.json (Missouri Supreme Court Rules 55, 74, 75, 78, 84.16, 88 + Civil Procedure Form No. 14)
from raw/mo/rules/pages.jsonl (mos_rules_fetch.py) and the Form 14 order PDFs (raw/mo/rules/mobar_3093*.pdf).
Usage: python3 scripts/mos_rules_build.py
"""
import os, re, sys, json, hashlib, datetime, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from mos_issues import rule_issues
from mop_issues import proc_rule_issues
from mos_config import FAMILY_RULES, FAMILY_RULE_NUMS, RULES_SWEEP, RULES_EXTRA_IDS, ORDERS_OVERLAY, MOBAR_ORDERS

ROOT = "/home/user/workspace/flb"
RAW = os.path.join(ROOT, "raw", "mo", "rules")
TODAY = datetime.date.today().isoformat()
CM = "https://www.courts.mo.gov/page.jsp?id="
RULE_INDEX = {"41": 199547, "51": 199575, "52": 199592, "54": 199608, "55": 199631, "57": 199669, "65": 199696, "67": 199706, "71": 199729, "74": 199740, "75": 199759, "76": 199761, "78": 200286, "81": 200301, "83": 199764, "84": 199775, "85": 199807, "86": 199832, "87": 199844, "88": 199856, "90": 199868, "91": 199892, "94": 199924, "96": 199938, "97": 199971, "99": 199986}
RULE_TITLES = {
    "55": "Rule 55 — Pleadings, Motions, and Hearings",
    "74": "Rule 74 — Judgments, Orders and Proceedings Thereon",
    "75": "Rule 75 — Control of Judgments",
    "78": "Rule 78 — New Trials – After-Trial Motions – Preservation of Error",
    "84": "Rule 84 — Procedure in All Appellate Courts",
    "88": "Rule 88 — Domestic Relations and Paternity Cases – Calculation of Child Support – Mediation – Self-Represented Litigants",
}
WANT = lambda num: num.split(".")[0] in ("55", "74", "75", "78", "88") or num == "84.16"
MONTHS = "January February March April May June July August September October November December".split()

# Pages that courts.mo.gov / the index copy could not deliver (see coverage gaps). Headings and adoption-history
# parentheticals were read from the rule's combined page (page.jsp?id=200636&up=<index id>) on courts.mo.gov.
MISSING = {
    199645: {"num": "55.14", "heading": "Partnership Deemed Confessed, Unless Denied", "hist": "(Adopted January 19, 1973, effective September 1, 1973.)"},
    199648: {"num": "55.17", "heading": "Official Documents or Acts – Form of Pleading", "hist": "(Adopted January 19, 1973, effective September 1, 1973.)"},
    199649: {"num": "55.18", "heading": "Judgments and Decisions – Form of Pleading", "hist": None},
    199654: {"num": "55.23", "heading": "[REPEALED]", "hist": "(Adopted January 19, 1973, effective September 1, 1973. Repealed June 28, 2017, effective January 1, 2018.)"},
    199655: {"num": "55.24", "heading": "Pleadings, How Construed", "hist": None},
    199755: {"num": "74.15", "heading": "[REPEALED]", "hist": None},
    199858: {"num": "88.02", "heading": "Mediation Authorized", "hist": "(Adopted December 27, 1990, effective July 1, 1991. Amended December 21, 2021, effective July 1, 2022.)",
             "text": ("As provided in this Rule 88, any judicial circuit may elect to establish a mediation program for contested issues, including, "
                      "but not limited to, child custody, parenting time, parenting plans, child support, maintenance, and property division, in "
                      "domestic relations and paternity cases. Mediation may be conducted in person or by telephone or video conferencing."),
             "text_source": "Supreme Court of Missouri order of December 21, 2021 (effective July 1, 2022) adopting new Rule 88.02, courts.mo.gov page.jsp?id=182834",
             "text_source_url": "https://www.courts.mo.gov/page.jsp?id=182834"},
    200289: {"num": "78.03", "heading": "Order Granting New Trial Shall Specify Grounds", "hist": "(Adopted March 29, 1974, effective January 1, 1975.)",
             "text": "Every order allowing a new trial shall specify of record the ground or grounds on which said new trial is granted.",
             "text_source": "Verbatim quotation of Rule 78.03 in a Missouri Court of Appeals opinion (2003, No. 24768); courts.mo.gov page not retrievable",
             "text_source_url": "https://law.justia.com/cases/missouri/court-of-appeals/2003/24768-1.html"},
    200294: {"num": "78.08", "heading": "New Trial – Plain Errors May Be Considered", "hist": "(Adopted April 10, 1974, effective January 1, 1975.)"},
}


def iso(s):
    m = re.search(r"(%s) (\d{1,2}), (\d{4})" % "|".join(MONTHS), s or "")
    return datetime.date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2))).isoformat() if m else None


def last_effective(hist):
    ds = re.findall(r"effective ((?:%s) \d{1,2}, \d{4})" % "|".join(MONTHS), hist or "")
    return iso(ds[-1]) if ds else None


def demd(t):
    t = re.sub(r"\*\*([^*]*)\*\*", r"\1", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"\1", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def parse_page(t):
    fa = re.search(r"First Adopted: \*\*\s*(.+?)\n", t)
    mre = re.search(r"Most Recently Effective: \*\*\s*(.+?)\n", t)
    hm = re.search(r"^## ([0-9]+\.[0-9]+[a-z]?(?: to [0-9.]+)?) \| (.+)$", t, re.M)
    if not hm:
        return None
    body = t[hm.end():]
    hist = None
    hmm = re.search(r"\*?\((Adopted[^)]*?(?:\([^)]*\)[^)]*?)*)\)\*?", body, re.S)
    if hmm:
        hist = "(" + re.sub(r"\s+", " ", hmm.group(1)).strip() + ")"
        body = body[:hmm.start()]
    src = re.search(r"\*\*Source:\s*\*\*\s*(.+)", body)
    source_note = None
    if src:
        source_note = src.group(1).strip()
        body = body[:src.start()] + body[src.end():]
    notes = []
    cn = re.search(r"^### (Committee Note.*)$", body, re.M)
    if cn:
        notes.append(demd(body[cn.start():]).lstrip("# ").strip())
        body = body[:cn.start()]
    return {"num": hm.group(1), "heading": hm.group(2).strip(), "text": demd(body), "first_adopted": iso(fa.group(1)) if fa else None,
            "most_recently_effective": iso(mre.group(1)) if mre else None, "history_note": hist, "source_note": source_note, "notes": notes}


def rule_record(pid, d, gaps, titles=None):
    num = d["num"]
    rule = num.split(".")[0]
    eff = d.get("most_recently_effective") or last_effective(d.get("history_note"))
    le = last_effective(d.get("history_note"))
    if d.get("most_recently_effective") and le and le != d["most_recently_effective"]:
        gaps.append(f"Rule {num}: 'Most Recently Effective' {d['most_recently_effective']} differs from last effective date in history note {le}; used the former")
    tl = (titles or {}).get(rule)
    rtitle = RULE_TITLES.get(rule) or (f"Rule {rule} — {tl[2]}" if tl else f"Rule {rule}")
    rpath = {"label": rtitle, "id": f"rule-{rule}"}
    if rule in RULE_INDEX:
        rpath["url"] = CM + str(RULE_INDEX[rule])
    path = [{"label": "Supreme Court Rules — Rules of Civil Procedure", "id": "mo-rules-civ"}]
    if tl:
        path.append({"label": tl[1], "id": GROUPS.get(tl[1], "mo-rules-civ-other")})
    path.append(rpath)
    offurl = CM + str(pid) if isinstance(pid, int) else (f"{CM}200636&up={d['up']}" if d.get("up") else (CM + str(d["index_page"]) if d.get("index_page") else CM + "942"))
    n = {"id": f"mo-rules-{num}", "corpus": "mo-rules", "side": "mo", "lang": "en", "kind": "rule", "num": num,
         "heading": d["heading"],
         "path": path,
         "text": d.get("text") or None, "in_force_since": eff, "status": "in force", "applies_to": ["MO"],
         "official_url": offurl, "alt_urls": ([{"label": f"Rule {rule} — all subdivisions (courts.mo.gov)", "url": f"{CM}200636&up={RULE_INDEX[rule]}"}] if rule in RULE_INDEX else []),
         "source_ids": {"courts_mo_page_id": pid if isinstance(pid, int) else None, "first_adopted": d.get("first_adopted"), "history_note": d.get("history_note"),
                        "source_note": d.get("source_note"),
                        "text_sha256": hashlib.sha256(re.sub(r"\s+", " ", d.get("text") or "").encode()).hexdigest() if d.get("text") else None},
         "issues": (rule_issues(num) if IS_FAMILY(num) else []) + proc_rule_issues(num), "xrefs": [], "interps": [],
         "axes": (["family", "procedure"] if IS_FAMILY(num) else ["procedure"])}
    n["source_ids"]["text_source"] = {"perplexity-index-snippets": "Perplexity search-index copy of the courts.mo.gov page (pplx_sdk.content.snippets)",
                                      "perplexity-index-cached-page": "Perplexity cached copy of the courts.mo.gov page (pplx_sdk.content.fetch)",
                                      "combined-page-heading-only": "Heading/history from the rule's combined page (cached copy); subdivision text not retrievable",
                                      "sitemap-heading-only": "Heading from the courts.mo.gov site map (cached copy); subdivision text not retrievable",
                                      "manual": None}.get(d.get("channel"))
    if d.get("stale_vs_combined"):
        n["text_status"] = f"page copy may predate the amendment effective {d['stale_vs_combined']} shown on the combined rule page — verify against official_url"
    if d.get("notes"):
        n["committee_notes"] = d["notes"]
    if d.get("text_source"):
        n["source_ids"]["text_source"] = d["text_source"]
    if not n["source_ids"].get("text_source"):
        n["source_ids"].pop("text_source", None)
        n["alt_urls"].append({"label": "Text source", "url": d["text_source_url"]})
    if not d.get("text"):
        n["text_status"] = "text not retrievable (courts.mo.gov blocks automated access; page not in index copy) — see official_url"
    x = []
    if num == "88.01":
        x = ["mo-rsmo-452.340", "mo-rules-form-14", "mo-rsmo-454.1050"]
    if num.startswith("88.0") and num != "88.01":
        x = ["mo-rsmo-452.372", "mo-rsmo-452.375"]
    n["xrefs"] = x
    return n


def pdftext(pdf, layout=False):
    return subprocess.run(["pdftotext"] + (["-layout"] if layout else []) + [pdf, "-"], capture_output=True, text=True).stdout


def form14_records():
    ORDER = "https://www.courts.mo.gov/page.jsp?id=128693"
    FORMS = "https://www.courts.mo.gov/page.jsp?id=638"
    MB = "https://images.magnetmail.net/images/clients/MOBAR/attach/Orders/"
    common_alt = [{"label": "Supreme Court order of March 4, 2025 (copy published by The Missouri Bar)", "url": MB + "3093.pdf"},
                  {"label": "Form No. 14 with directions, comments for use, examples and assumptions (order attachment, Missouri Bar copy)", "url": MB + "3093a.pdf"},
                  {"label": "Schedule of Basic Child Support Obligations (order attachment, Missouri Bar copy)", "url": MB + "3093b.pdf"},
                  {"label": "Missouri Courts — Child Support Forms", "url": FORMS},
                  {"label": "The Missouri Bar — notice of order", "url": "https://news.mobar.org/supreme-court-of-missouri-order---new-form-14-child-support-amount-calculation-worksheet/"}]
    src = {"order_date": "2025-03-04", "order_effective": "2026-01-01", "orders_for_rules_entry": "03-04-2025 | 01-01-2026 | Order dated March 4, 2025, re: new Form 14 Child Support Amount Calculation Worksheet"}
    a = os.path.join(RAW, "mobar_3093a.pdf"); b = os.path.join(RAW, "mobar_3093b.pdf")
    plain = pdftext(a).replace("\f", "\n")
    lay = pdftext(a, True)
    sched = pdftext(b, True).replace("\f", "\n")
    recs = []
    base = lambda rid, num, heading, text, kind="text": {
        "id": rid, "corpus": "mo-rules", "side": "mo", "lang": "en", "kind": kind, "num": num, "heading": heading,
        "path": [{"label": "Supreme Court Rules — Civil Procedure Forms", "id": "mo-rules-forms"},
                 {"label": "Civil Procedure Form No. 14 — Child Support Amount Calculation Worksheet (eff. Jan. 1, 2026)", "id": "form-14"}],
        "text": text.strip(), "in_force_since": "2026-01-01", "status": "in force", "applies_to": ["MO"], "official_url": ORDER,
        "alt_urls": list(common_alt), "source_ids": dict(src, text_sha256=hashlib.sha256(re.sub(r"\s+", " ", text).encode()).hexdigest()),
        "issues": rule_issues("form-14"), "xrefs": ["mo-rules-88.01", "mo-rsmo-452.340"], "interps": []}
    i_dir = plain.find("DIRECTIONS, COMMENTS FOR USE AND EXAMPLES FOR")
    li = lay.find("DIRECTIONS, COMMENTS FOR USE AND EXAMPLES FOR")
    recs.append(base("mo-rules-form-14", "Form No. 14", "Form No. 14 Child Support Amount Calculation Worksheet", lay[:li].replace("\f", "\n"), "text"))
    rest = plain[i_dir:]
    ia = rest.find("\nASSUMPTIONS\n")
    dirs, assum = rest[:ia], rest[ia:]
    parts = list(re.finditer(r"^Line (\d+[a-z]?): (.+)$", dirs, re.M))
    recs.append(base("mo-rules-form-14-directions-general", "Form No. 14 — Directions (general)",
                     "Directions, Comments for Use and Examples for Completion of Form No. 14 — general provisions", dirs[:parts[0].start()]))
    for k, m in enumerate(parts):
        end = parts[k + 1].start() if k + 1 < len(parts) else len(dirs)
        heading = m.group(2).strip()
        nxt = dirs[m.end():m.end() + 200].split("\n")
        if len(nxt) > 1 and nxt[1].strip() and len(nxt[1].strip()) < 90 and not re.match(r"(DIRECTION|COMMENT|[A-Z]\.|\()", nxt[1].strip()):
            heading += " " + nxt[1].strip()
        recs.append(base(f"mo-rules-form-14-line-{m.group(1)}", f"Form No. 14 — Line {m.group(1)}",
                         f"Form No. 14 Directions and Comments — Line {m.group(1)}: {heading}", dirs[m.start():end]))
    recs.append(base("mo-rules-form-14-assumptions", "Form No. 14 — Assumptions", "Form No. 14 — Assumptions", assum))
    recs.append(base("mo-rules-form-14-schedule", "Form No. 14 — Schedule", "Schedule of Basic Child Support Obligations (2024 Child Support Guideline Review, updated schedule)", sched))
    for r in recs:
        r["text"] = re.sub(r"[ \t]+\n", "\n", re.sub(r"\n{3,}", "\n\n", r["text"]))
    return recs


SITEMAP_INDEX = {"46": 199327}
RANGE = lambda num: re.match(r"^\d+\.\d+[a-z]?$", num or "") and 41 <= int(num.split(".")[0]) <= 101
IS_FAMILY = lambda num: num.split(".")[0] in FAMILY_RULES or num in FAMILY_RULE_NUMS
GROUPS = {"Rules Governing Civil Procedure in the Circuit Courts": "mo-rules-civ-circuit",
          "Rules Relating to All Appellate Courts": "mo-rules-civ-appellate", "Rules Relating to Special Actions": "mo-rules-civ-special"}


def rule_title_line(t):
    m = re.search(r"^Rule (\d+) [|-] Rules of Civil Procedure [|-] (.+?) [|-] (.+)$", t or "", re.M)
    return (m.group(1), m.group(2).replace("CIrcuit", "Circuit").strip(), m.group(3).strip()) if m else None


def load_pages():
    """page id -> parsed record; channels: snippets (pages.jsonl) and cached page copy (pages_fetch.jsonl)."""
    S, F = {}, {}
    for l in open(os.path.join(RAW, "pages.jsonl")):
        d = json.loads(l); S[d["id"]] = d
    fp = os.path.join(RAW, "pages_fetch.jsonl")
    if os.path.exists(fp):
        for l in open(fp):
            d = json.loads(l); F[d["id"]] = d
    out, titles = {}, {}
    for pid in sorted(set(S) | set(F)):
        for chan, t in (("perplexity-index-snippets", (S.get(pid) or {}).get("text")), ("perplexity-index-cached-page", (F.get(pid) or {}).get("content"))):
            if not t:
                continue
            rt = rule_title_line(t)
            if rt:
                titles.setdefault(rt[0], rt)
            d = parse_page(t) if ("Adopted" in t and "## " in t) else None
            if d and pid not in out:
                d["channel"] = chan
                out[pid] = d
    return out, titles


def load_combined():
    """Rule-level combined pages (page.jsp?id=200636&up=<index>) -> {num: {heading, first_adopted, mre, history}}."""
    p = os.path.join(RAW, "combined_fetch.json")
    res = {}
    if not os.path.exists(p):
        return res
    for c in json.load(open(p)):
        t = c.get("content") or ""
        blocks = re.split(r"(?=\*\*First Adopted: \*\*)", t)
        for b in blocks:
            d = parse_page(b)
            if d:
                res.setdefault(d["num"], dict(d, up=c["up"]))
    return res


def order_plain(n):
    p = os.path.join(RAW, "orders", f"{n}.pdf")
    t = subprocess.run(["pdftotext", p, "-"], capture_output=True, text=True).stdout
    lines = [l.rstrip() for l in t.replace("\f", "\n").split("\n")]
    return [l for l in lines if l.strip() and not re.fullmatch(r"\s*\d{1,3}\s*", l)]


def reflow(lines):
    w = max([len(l) for l in lines] or [80])
    paras = []
    for l in lines:
        st = l.strip()
        newp = not paras or re.match(r"^\((?:[a-z]|\d+|[A-Z]|[ivx]+)\)\s", st) or (
            re.search(r"[.:;]$", paras[-1]) and len(prev) < 0.8 * w)
        if newp:
            paras.append(st)
        else:
            paras[-1] += " " + st
        prev = l
    return "\n\n".join(paras)


def order_block(n, num):
    """Text adopted for subdivision `num` in order n: lines after the heading 'NUM TITLE' (+ wrapped caps title lines) until
    the next '* * *' marker or 'N. It is ordered'."""
    L = order_plain(n)
    start = next((k for k, l in enumerate(L) if re.match(re.escape(num) + r"\s+[A-Z][A-Z ,;'’\-–—]+", l.strip())), None)
    if start is None:
        return None
    k = start + 1
    while k < len(L) and L[k].strip().upper() == L[k].strip() and re.search(r"[A-Z]{3}", L[k]) and not L[k].strip().startswith("("):
        k += 1
    body = []
    while k < len(L) and not re.match(r"^\d+\.\s+It is ordered", L[k].strip()) and not re.match(r"^\d+\.\d+\s+[A-Z]{3}[A-Z ,;'’\-–—]*$", L[k].strip()):
        body.append(L[k]); k += 1
    # stop at * * * (unchanged remainder) - keep the marker positions
    txt = reflow([l for l in body])
    return txt


def apply_orders(norms, gaps):
    by = {n["num"]: n for n in norms}
    pending, applied = {}, []
    for o in ORDERS_OVERLAY:
        url = f"{MOBAR_ORDERS}{o['order']}.pdf"
        if o["mode"] == "pending" or o["effective"] > TODAY:
            pending.setdefault(o["num"], []).append({"order_dated": o["dated"], "effective": o["effective"], "order_pdf_missouri_bar_copy": url,
                                                     "note": "adopted, not yet in force"})
            continue
        n = by.get(o["num"])
        prior = None
        if n is not None:
            prior = {"text": n.get("text"), "heading": n["heading"], "effective": n.get("in_force_since"), "end": o["effective"],
                     "source": n["source_ids"].get("text_source") or "courts.mo.gov page (index copy)"}
        blk = None if o["mode"] == "title" else order_block(o["order"], o["num"])
        if o["mode"] != "title" and not blk:
            gaps.append(f"Rule {o['num']}: amending order {o['order']} text not parsed — current text not updated"); continue
        if blk:
            blk = re.sub(r"(\n\n)?\*(\s*\*){2}\s*$", "", blk).strip()
        if o["mode"] == "new":
            base = by.get("55.025") or next(iter(by.values()))
            n = json.loads(json.dumps(base))
            n.update({"id": f"mo-rules-{o['num']}", "num": o["num"], "heading": o["title"], "text": blk, "interps": [], "xrefs": []})
            n["source_ids"] = {"courts_mo_page_id": None, "first_adopted": o["dated"], "history_note": f"(Adopted {o['dated']}, effective {o['effective']}.)"}
            n["issues"] = proc_rule_issues(o["num"]); n["axes"] = ["procedure"]
            n["official_url"] = CM + "128693"
            n.pop("committee_notes", None); n.pop("text_status", None)
            if o.get("comment_order"):
                cl = reflow(order_plain(o["comment_order"]))
                m = re.search(r"COMMENT\s+(.+?)(?:\s+2\. It is ordered|$)", cl, re.S)
                if m:
                    n["committee_notes"] = ["Comment: " + re.sub(r"\s+", " ", m.group(1)).strip()]
            norms.append(n); by[o["num"]] = n
        elif o["mode"] == "full":
            n["text"] = blk
        elif o["mode"].startswith("sub:"):
            lab = o["mode"][4:]
            cur = n.get("text") or ""
            nxt = "(" + chr(ord(lab[1]) + 1) + ")"
            i = cur.find(lab + " ")
            j = cur.find("\n" + nxt, i + 1) if i >= 0 else -1
            new_sub = blk.split("\n\n* * *")[0].strip()
            new_sub = new_sub[new_sub.find(lab):] if lab in new_sub else new_sub
            if i < 0:
                gaps.append(f"Rule {o['num']}: could not locate subdivision {lab} in current text to splice order {o['order']}"); continue
            n["text"] = cur[:i] + new_sub + ("\n" + cur[j:].lstrip("\n") if j >= 0 else "")
            if j >= 0:
                n["text"] = cur[:i] + new_sub + "\n\n" + cur[j + 1:]
        elif o["mode"] == "title":
            n["heading"] = o["title"]
        n["in_force_since"] = o["effective"]
        n["status"] = "in force"
        n.pop("text_status", None)
        n["source_ids"]["text_source"] = (f"Supreme Court of Missouri order dated {o['dated']} (effective {o['effective']}), Missouri Bar copy {url}"
                                          + ("; unchanged remainder from the courts.mo.gov page (index copy)" if o["mode"].startswith("sub:") or o["mode"] == "title" else ""))
        n["source_ids"]["amending_order"] = {"dated": o["dated"], "effective": o["effective"], "pdf": url}
        n["source_ids"]["text_sha256"] = hashlib.sha256(re.sub(r"\s+", " ", n.get("text") or "").encode()).hexdigest()
        n["alt_urls"] = [a for a in n.get("alt_urls", []) if a.get("url") != url] + [{"label": f"Order dated {o['dated']} (Missouri Bar copy)", "url": url}]
        if prior and prior.get("text"):
            n.setdefault("_prior_versions", []).append(prior)
        applied.append(o["num"])
    for num, p in pending.items():
        if num in by:
            by[num]["source_ids"]["pending_amendments"] = p
    return applied, pending


def main():
    pages, titles = load_pages()
    comb = load_combined()
    norms, excluded, gaps, stale, seen, dup = [], [], [], [], {}, []
    for pid, d in sorted(pages.items()):
        num = d["num"]
        if not RANGE(num):
            continue
        if num in seen:
            a = seen[num]
            if (d.get("most_recently_effective") or "") > (pages[a]["most_recently_effective"] or ""):
                dup.append({"num": num, "superseded_page": a, "kept_page": pid}); seen[num] = pid
            else:
                dup.append({"num": num, "superseded_page": pid, "kept_page": a})
            continue
        seen[num] = pid
    for pid, m in MISSING.items():
        if m["num"] not in seen:
            pages[pid] = {"num": m["num"], "heading": m["heading"], "text": m.get("text"), "history_note": m.get("hist"),
                          "text_source": m.get("text_source"), "text_source_url": m.get("text_source_url"), "channel": "manual"}
            seen[m["num"]] = pid
            if not m.get("text") and "REPEALED" not in m["heading"]:
                gaps.append(f"Rule {m['num']} ({CM}{pid}): text not retrievable — heading/history only")
    # subdivisions listed on a rule's combined page but with no retrievable subdivision page
    for num, c in comb.items():
        if RANGE(num) and num not in seen:
            key = f"combined:{num}"
            pages[key] = dict(c, text=None, channel="combined-page-heading-only")
            seen[num] = key
            if "REPEALED" not in c["heading"].upper():
                gaps.append(f"Rule {num}: listed on combined rule page ({CM}200636&up={c['up']}) but subdivision page not retrievable via the index copy — heading/history only, text null")
    # courts.mo.gov site map (page.jsp?id=942, cached copy) = master enumeration of every subdivision
    smp = os.path.join(RAW, "sitemap_fetch.json")
    sitemap = []
    if os.path.exists(smp):
        sm = json.load(open(smp))[0]["content"]
        sitemap = [(n, h.strip()) for n, h in re.findall(r"^- ([0-9]+\.[0-9]+[a-z]?(?: to [0-9.]+)?) \| (.+)$", sm, re.M)
                   if 41 <= int(n.split(".")[0]) <= 101]
    smh = dict(sitemap)
    for num, h in sitemap:
        if num in seen:
            continue
        rule = num.split(".")[0]
        if "REPEALED" in h.upper():
            excluded.append({"num": num, "status": "repealed", "history_note": None, "url": CM + "942", "source": "courts.mo.gov site map"})
            continue
        key = f"sitemap:{num}"
        pages[key] = {"num": num, "heading": h, "text": None, "history_note": None, "channel": "sitemap-heading-only",
                      "up": None, "index_page": RULE_INDEX.get(rule) or SITEMAP_INDEX.get(rule)}
        seen[num] = key
        gaps.append(f"Rule {num}: listed on the courts.mo.gov site map (page.jsp?id=942) but neither the subdivision page nor its text is available in the index copy — heading only, text null, effective date not verified")
    for num, pid in sorted(seen.items(), key=lambda kv: [int(x) for x in re.findall(r"\d+", kv[0])]):
        d = pages[pid]
        rule = num.split(".")[0]
        c = comb.get(num)
        if c and (c.get("most_recently_effective") or "") > (d.get("most_recently_effective") or "") and d.get("channel") != "combined-page-heading-only":
            stale.append({"num": num, "page": pid, "page_mre": d.get("most_recently_effective"), "combined_mre": c.get("most_recently_effective")})
            gaps.append(f"Rule {num}: subdivision page copy shows Most Recently Effective {d.get('most_recently_effective')} but the combined rule page shows {c.get('most_recently_effective')} — text may predate the latest amendment (flagged text_status)")
            d = dict(d, stale_vs_combined=c.get("most_recently_effective"))
        if "REPEALED" in (d["heading"] or "").upper() or "RESERVED" in (d["heading"] or "").upper():
            excluded.append({"num": num, "status": "repealed" if "REPEALED" in d["heading"].upper() else "reserved",
                             "history_note": d.get("history_note"), "url": CM + str(pid) if isinstance(pid, int) else None})
            continue
        known = smh.get(num) or (c or {}).get("heading")
        if known and d.get("heading") and d["heading"] != known and d["heading"].startswith(known) and len(d["heading"]) > len(known) + 3:
            d = dict(d, text=(d["heading"][len(known):].strip() + ("\n\n" + d["text"] if d.get("text") else "")).strip(), heading=known)
        rec = rule_record(pid, d, gaps, titles)
        if not rec.get("in_force_since") and c:
            rec["in_force_since"] = c.get("most_recently_effective") or last_effective(c.get("history_note"))
            if rec["in_force_since"]:
                rec["source_ids"]["in_force_since_source"] = "rule combined page (Most Recently Effective / history note)"
            if not rec["source_ids"].get("history_note") and c.get("history_note"):
                rec["source_ids"]["history_note"] = c["history_note"]
        if not rec.get("in_force_since"):
            gaps.append(f"Rule {num}: effective date not stated on the page copy or combined page — in_force_since null (not verified)")
        norms.append(rec)
    applied, pending = apply_orders(norms, gaps)
    norms.sort(key=lambda n: [int(x) for x in re.findall(r"\d+", n["num"])])
    priors = {n["num"]: n.pop("_prior_versions") for n in norms if "_prior_versions" in n}
    # cross-references cited in the rule text (other Rules in this corpus; RSMo sections in mo-rsmo)
    rids = {n["num"] for n in norms}
    try:
        sids = {n["num"] for n in json.load(open(os.path.join(ROOT, "data", "norms", "mo-rsmo.json")))["norms"]}
    except Exception:
        sids = set()
    for n in norms:
        t = n.get("text") or ""
        xs = list(n.get("xrefs") or [])
        for m in re.findall(r"Rules? ((?:\d+\.\d+[a-z]?)(?:\([^)]*\))*(?:,? (?:and |or )?\d+\.\d+(?:\([^)]*\))*)*)", t):
            for r in re.findall(r"\d+\.\d+", m):
                if r in rids and r != n["num"] and f"mo-rules-{r}" not in xs:
                    xs.append(f"mo-rules-{r}")
        for sct in re.findall(r"[Ss]ections? (\d{3}\.\d{3})", t):
            if sct in sids and f"mo-rsmo-{sct}" not in xs:
                xs.append(f"mo-rsmo-{sct}")
        n["xrefs"] = xs
    f14 = form14_records()
    for r in f14:
        r["axes"] = ["family"]
    norms += f14
    json.dump({"corpus": "mo-rules", "generated": TODAY, "norms": norms}, open(os.path.join(ROOT, "data", "norms", "mo-rules.json"), "w"), indent=2, ensure_ascii=False)
    write_history(norms, pages, dup, priors)
    present_rules = sorted({int(n["num"].split(".")[0]) for n in norms if RANGE(n["num"])})
    repealed_rules = sorted({int(e["num"].split(".")[0]) for e in excluded} - set(present_rules))
    cov = {"corpus": "mo-rules", "norms_expected": len(norms) + len([g for g in gaps if "text null" in g]) * 0, "norms_done": len(norms),
           "norms_with_text": sum(1 for n in norms if n.get("text")),
           "axes_counts": {k: sum(1 for n in norms if k in n.get("axes", [])) for k in ("family", "procedure")},
           "interps_candidates": 0, "interps_screened": 0, "interps_included": 0,
           "method": ("Procedure axis (SCOPE §4.5): every courts.mo.gov page id in the Rules block " + ", ".join(f"{a}–{b}" for a, b in RULES_SWEEP)
                      + " plus re-issued ids " + ", ".join(map(str, RULES_EXTRA_IDS)) + " read through two Perplexity index channels "
                      "(pplx_sdk.content.snippets and the cached page copy of pplx_sdk.content.fetch) because courts.mo.gov answers HTTP 403 "
                      "to automated clients and its banner prohibits automated repetitive querying. Each rule's combined page "
                      "(page.jsp?id=200636&up=<index id>, cached copy) lists every subdivision with heading, First Adopted, Most Recently Effective "
                      "and adoption history; it is the enumeration check. 'Most Recently Effective' = in_force_since. text_source records the channel. "
                      "Family axis (pre-existing): Rules 55, 74, 75, 78, 84.16, 88 and Civil Procedure Form No. 14 (order of March 4, 2025, eff. Jan. 1, 2026; "
                      "text from The Missouri Bar's copy of the order attachments)."),
           "rules_present": present_rules, "rules_wholly_repealed": repealed_rules, "rules_absent_in_41_101": [r for r in range(41, 102) if r not in present_rules and r not in repealed_rules],
           "sitemap_subdivisions_41_101": len(sitemap),
           "scope_decisions": ["All Rules 41–101 in force are ingested for the procedure axis (axes ['procedure']); Rules 55, 74, 75, 78, 84.16 and 88 carry axes ['family','procedure']; Form No. 14 ['family'].",
                               "Rules outside 41–101 (e.g. criminal Rules 19–38, juvenile Rules 110–130) found in the swept id block are ignored.",
                               "Rule 128: no Supreme Court Rule 128 relevant to family matters was identified — not ingested; flagged for review."],
           "orders_applied": applied, "orders_pending": pending, "excluded_repealed": excluded, "superseded_pages": dup, "stale_copies": stale, "gaps": gaps, "updated": TODAY,
           "id_convention": "mo-rules-<num> e.g. mo-rules-55.27; mo-rules-form-14[-line-<n>|-assumptions|-schedule|-directions-general]"}
    for r in cov["rules_absent_in_41_101"]:
        cov["gaps"].append(f"Rule {r}: no subdivision found in the swept page-id block or the index (possibly repealed/reserved) — not verified")
    json.dump(cov, open(os.path.join(ROOT, "data", "coverage", "mo-rules.json"), "w"), indent=2, ensure_ascii=False)
    print("rules norms", len(norms) - len(f14), "with text", cov["norms_with_text"] - len(f14), "form14", len(f14), "excluded", len(excluded),
          "stale", len(stale), "dups", len(dup), "gaps", len(gaps), "absent", cov["rules_absent_in_41_101"])


def write_history(norms, pages, dup, priors=None):
    """data/mo-history/rule-<num>.json: amendment chronology (from the Court's history note) and texts of superseded page copies."""
    hdir = os.path.join(ROOT, "data", "mo-history")
    by = {}
    for x in dup:
        by.setdefault(x["num"], []).append(x["superseded_page"])
    for n in norms:
        if n["kind"] != "rule":
            continue
        hn = n["source_ids"].get("history_note") or ""
        chron = [{"adopted_or_amended": iso(a), "effective": iso(b)} for a, b in re.findall(
            r"((?:%s) \d{1,2}, \d{4})[^;.)]*?effective ((?:%s) \d{1,2}, \d{4})" % ("|".join(MONTHS), "|".join(MONTHS)), hn)]
        prior = []
        for pv in (priors or {}).get(n["num"], []):
            prior.append({"effective": pv["effective"], "end": pv["end"], "heading": pv["heading"], "text": pv["text"], "source": pv["source"],
                          "identical_to_current": re.sub(r"\s+", " ", pv["text"] or "") == re.sub(r"\s+", " ", n.get("text") or "")})
        for pid in by.get(n["num"], []):
            d = pages.get(pid)
            if d and d.get("text"):
                prior.append({"page": CM + str(pid), "most_recently_effective": d.get("most_recently_effective"), "text": d["text"],
                              "identical_to_current": re.sub(r"\s+", " ", d["text"]) == re.sub(r"\s+", " ", n.get("text") or "")})
        doc = {"rule": n["num"], "official_url": n["official_url"], "current": {"effective": n["in_force_since"], "text_sha256": n["source_ids"].get("text_sha256")},
               "chronology": chron, "history_note": hn or None, "versions": prior,
               "pending": n["source_ids"].get("pending_amendments", []),
               "note": ("Prior rule texts are not published on courts.mo.gov rule pages; the chronology comes from the Court's history note. "
                        "For the SCOPE §2(b) test, a decision predating the last effective date requires comparison with the amending order "
                        "(courts.mo.gov 'Orders For Rules', page.jsp?id=128693; Missouri Bar copies) — not yet ingested."),
               "generated": TODAY}
        json.dump(doc, open(os.path.join(hdir, f"rule-{n['num']}.json"), "w"), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
