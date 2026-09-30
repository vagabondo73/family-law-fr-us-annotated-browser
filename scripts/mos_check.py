#!/usr/bin/env python3
"""Daily source check for the Missouri corpora (mo-rsmo, mo-const, mo-rules).

- RSMo: re-reads every chapter index page on revisor.mo.gov; the 'http-hash' is the SHA-256 of the normalized
  in-scope section rows (section|bid|listed date|title) — stable against page chrome. Any new/removed section,
  new bid or new listed date is flagged; flagged sections are re-fetched and their text hash compared with
  data/norms/mo-rsmo.json. Also flags pending (future-effective) versions whose effective date has arrived.
- Constitution: section pages re-fetched; text hash compared.
- Rules: courts.mo.gov rule pages read via the index copy (pplx_sdk.content.snippets); hash of the extracted
  rule text + 'Most Recently Effective' date compared; the 'Orders For Rules' page is checked for new orders
  mentioning Rules 55/74/75/78/84/88 or Form 14.
Writes data/sources-mo.json (last_checked/last_version) and raw/mo/check_report.json; exit code 1 if changes found.
CPC (mapping-cpc-mo): compares the Tricoteuses main HEAD with raw/mop/cpc_articles.json and flags CPC article versions whose
  end date has arrived (e.g. the 59 versions ending 2026-10-01 / 2026-12-31 / 2027-01-01 / 2029-06-30); unless --no-refresh it then
  re-runs mop_cpc_articles.py --pull, mop_map2.py (only batches whose article text changed) and mop_build.py.
Usage: python3 scripts/mos_check.py [--init] [--no-rules] [--no-cpc] [--no-refresh]
  --init      record current state as baseline without flagging
Rebuild after a flagged change: python3 scripts/mos_fetch.py --refresh && python3 scripts/mos_build.py &&
  python3 scripts/mos_rules_fetch.py --refresh && python3 scripts/mos_rules_build.py
"""
import os, re, sys, json, hashlib, datetime, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from mos_config import *
import mos_fetch
from mos_build import parse_section, norm_text
import pplx_sdk

NOW = datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
TODAY = datetime.date.today().isoformat()
SRC = os.path.join(ROOT, "data", "sources-mo.json")
INIT = "--init" in sys.argv


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default


def main():
    sources = {s["id"]: s for s in load(SRC, [])}
    norms = {n["num"]: n for n in load(os.path.join(ROOT, "data", "norms", "mo-rsmo.json"), {"norms": []})["norms"]}
    report = {"checked": NOW, "changes": [], "errors": []}
    tmp = os.path.join(RAW, "check"); os.makedirs(tmp, exist_ok=True)
    # --- RSMo chapters
    pairs = [(f"{BASE}/main/OneChapter.aspx?chapter={ch}", os.path.join(tmp, f"ch{ch}.html")) for ch in all_chapters()]
    got = mos_fetch.get_many(pairs, force=True)
    flagged = set()
    for ch in all_chapters():
        url, p = pairs[all_chapters().index(ch)]
        h = got.get(p)
        sid = f"rsmo-ch-{ch}"
        if not h:
            report["errors"].append(f"{sid}: fetch failed"); continue
        rows = [r for r in (dict(section=s, bid=b, title=re.sub(r"<[^>]+>", "", t).strip()) for s, b, t in mos_fetch.ROW_RE.findall(h)) if in_scope(ch, r["section"])]
        canon = "\n".join(f"{r['section']}|{r['bid']}|{re.sub(r'\s+', ' ', r['title'])}" for r in rows)
        ver = sha(canon)
        old = sources.get(sid, {})
        rec = {"id": sid, "label": f"RSMo Chapter {ch} (Revisor of Statutes)", "official": url, "channel": "http:" + url,
               "check": "http-hash", "corpora": ["mo-rsmo"], "last_checked": NOW, "last_version": ver,
               "rows": {r["section"]: r["bid"] for r in rows}}
        if old.get("last_version") and old["last_version"] != ver and not INIT:
            prev = old.get("rows", {})
            cur = rec["rows"]
            for s in sorted(set(prev) | set(cur), key=secnum_key):
                if prev.get(s) != cur.get(s):
                    kind = "new section" if s not in prev else ("section removed from index" if s not in cur else "new version (bid) listed")
                    report["changes"].append({"source": sid, "section": s, "kind": kind, "old_bid": prev.get(s), "new_bid": cur.get(s),
                                              "url": f"{BASE}/main/OneSection.aspx?section={s}"})
                    flagged.add(s)
        sources[sid] = rec
    # pending versions whose effective date has arrived
    for s, n in norms.items():
        for pv in n.get("source_ids", {}).get("pending", []):
            if pv.get("effective") and pv["effective"] <= TODAY and (pv.get("note") or "").startswith("future"):
                report["changes"].append({"source": "rsmo", "section": s, "kind": "pending version now effective", "effective": pv["effective"], "url": pv["url"]})
                flagged.add(s)
    # re-fetch flagged sections, compare text hash
    if flagged:
        fp = [(f"{BASE}/main/OneSection.aspx?section={s}", os.path.join(tmp, f"{s}.html")) for s in sorted(flagged)]
        g = mos_fetch.get_many(fp, force=True)
        for (u, p), s in zip(fp, sorted(flagged)):
            if g.get(p):
                d = parse_section(g[p])
                newh = sha(norm_text(d["text"]))
                oldh = norms.get(s, {}).get("source_ids", {}).get("text_sha256")
                report["changes"].append({"source": "rsmo", "section": s, "kind": "text check", "effective": d["effective"],
                                          "text_changed": newh != oldh, "old_in_force_since": norms.get(s, {}).get("in_force_since")})
    # --- Constitution
    cn = {n["source_ids"]["mo_const"]: n for n in load(os.path.join(ROOT, "data", "norms", "mo-const.json"), {"norms": []})["norms"]}
    cp = [(f"{BASE}/main/OneSection.aspx?section={urllib.parse.quote(f'{a}    {s}')}&constit=y", os.path.join(tmp, f"const-{a}-{s}.html")) for a, s in CONST]
    g = mos_fetch.get_many(cp, force=True)
    for (u, p), (a, s) in zip(cp, CONST):
        sid = f"mo-const-{a}-{s}"
        if not g.get(p):
            report["errors"].append(f"{sid}: fetch failed"); continue
        d = parse_section(g[p]); ver = sha(norm_text(d["text"]) + "|" + str(d["effective"]))
        old = sources.get(sid, {})
        if old.get("last_version") and old["last_version"] != ver and not INIT:
            report["changes"].append({"source": sid, "kind": "constitution text/effective changed", "effective": d["effective"], "url": u})
        sources[sid] = {"id": sid, "label": f"Missouri Constitution art. {a} § {s}", "official": u, "channel": "http:" + u, "check": "http-hash",
                        "corpora": ["mo-const"], "last_checked": NOW, "last_version": ver}
    # --- Rules
    if "--no-rules" not in sys.argv:
        import mos_rules_fetch as rf, mos_rules_build as rb
        pages = []
        for rule, (idx, a, b) in rf.RULES.items():
            pages += list(range(a, b + 1))
        pages += [128693]
        res = {}
        for i in range(0, len(pages), 10):
            chunk = pages[i:i + 10]
            try:
                r = pplx_sdk.content.snippets(query=rf.Q, urls=[f"https://www.courts.mo.gov/page.jsp?id={x}" for x in chunk], max_tokens=16384, max_tokens_per_page=4096)
                for x, pid in zip(r, chunk):
                    res[pid] = x.text
            except Exception as e:
                report["errors"].append(f"rules snippets {chunk[0]}..: {e}")
        for pid, t in res.items():
            if not t:
                continue
            sid = f"courts-mo-page-{pid}"
            if pid == 128693:
                lines = sorted(l.strip() for l in t.split("\n") if re.search(r"Rules? (4[1-9]|[5-9]\d|10[01])\b|\b(4[1-9]|[5-9]\d|10[01])\.\d|Form (No\. )?14", l))
                ver = sha("\n".join(lines))
                label, corp = "Missouri Courts — Orders For Rules (entries for Rules 41–101 and Form 14)", "mo-rules"
            else:
                d = rb.parse_page(t)
                if not d:
                    continue
                ver = sha(re.sub(r"\s+", " ", d["text"]) + "|" + str(d["most_recently_effective"]))
                label, corp = f"Supreme Court Rule {d['num']}", "mo-rules"
            old = sources.get(sid, {})
            if old.get("last_version") and old["last_version"] != ver and not INIT:
                report["changes"].append({"source": sid, "kind": "rule page changed", "url": f"https://www.courts.mo.gov/page.jsp?id={pid}"})
            sources[sid] = {"id": sid, "label": label, "official": f"https://www.courts.mo.gov/page.jsp?id={pid}",
                            "channel": "pplx_sdk.content.snippets (index copy; courts.mo.gov 403 to automated clients)", "check": "http-hash",
                            "corpora": [corp], "last_checked": NOW, "last_version": ver}
    # --- Procedure axis: rule combined pages (every subdivision heading + effective date) and new Missouri Bar order PDFs
    if "--no-rules" not in sys.argv:
        from mos_rules_build import RULE_INDEX
        ups = sorted(set(RULE_INDEX.values()))
        try:
            res = pplx_sdk.content.fetch([f"https://www.courts.mo.gov/page.jsp?id=200636&up={u}" for u in ups])
        except Exception as e:
            res = []; report["errors"].append(f"combined pages: {e}")
        for u, x in zip(ups, res):
            if not x.content:
                continue
            canon = "\n".join(re.findall(r"^## .+$|Most Recently Effective: \*\*\s*\n*\s*.+$", x.content, re.M))
            sid = f"courts-mo-rule-combined-{u}"; ver = sha(canon); old = sources.get(sid, {})
            if old.get("last_version") and old["last_version"] != ver and not INIT:
                report["changes"].append({"source": sid, "kind": "rule subdivision list / effective dates changed", "url": f"https://www.courts.mo.gov/page.jsp?id=200636&up={u}"})
            sources[sid] = {"id": sid, "label": f"Supreme Court Rule (index page {u}) — all subdivisions", "official": f"https://www.courts.mo.gov/page.jsp?id=200636&up={u}",
                            "channel": "pplx_sdk.content.fetch (Perplexity cached copy)", "check": "http-hash", "corpora": ["mo-rules"], "last_checked": NOW, "last_version": ver}
        odir = os.path.join(RAW, "rules", "orders")
        known = sorted(int(f[:-4]) for f in os.listdir(odir) if re.fullmatch(r"\d+\.pdf", f)) if os.path.isdir(odir) else [3190]
        import subprocess
        for k in range(known[-1] + 1, known[-1] + 25):
            u = f"{MOBAR_ORDERS}{k}.pdf"; fp = os.path.join(odir, f"{k}.pdf")
            subprocess.run(["curl", "-s", "-m", "20", "-o", fp, u])
            if os.path.exists(fp) and open(fp, "rb").read(4) == b"%PDF":
                t = subprocess.run(["pdftotext", fp, "-"], capture_output=True, text=True).stdout[:3000]
                if re.search(r"\b(4[1-9]|[5-9]\d|10[01])\.\d", t) and not INIT:
                    report["changes"].append({"source": "mobar-orders", "kind": "new Supreme Court order touching Rules 41-101 — add to ORDERS_OVERLAY", "url": u})
            elif os.path.exists(fp):
                os.remove(fp)
    # Form 14 order attachments (Missouri Bar copies) — hash of the PDF bytes
    for f in ["3093", "3093a", "3093b"]:
        u = f"https://images.magnetmail.net/images/clients/MOBAR/attach/Orders/{f}.pdf"
        p = os.path.join(RAW, "rules", f"mobar_{f}.pdf")
        sid = f"mo-form-14-order-{f}"
        ver = hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
        sources[sid] = {"id": sid, "label": f"Civil Procedure Form No. 14 — order of March 4, 2025 (eff. Jan. 1, 2026), attachment {f}", "official": "https://www.courts.mo.gov/page.jsp?id=128693",
                        "channel": "http:" + u, "check": "http-hash", "corpora": ["mo-rules"], "last_checked": NOW, "last_version": ver}
    # CPC side of data/mapping/cpc-mo.json: Tricoteuses mirror HEAD + CPC versions whose end date has arrived
    if "--no-cpc" not in sys.argv:
        import subprocess
        ca_p = os.path.join(ROOT, "raw", "mop", "cpc_articles.json")
        ca = load(ca_p, {})
        head = subprocess.run(["git", "ls-remote", "https://git.tricoteuses.fr/codes/code_de_procedure_civile.git", "refs/heads/main"], capture_output=True, text=True).stdout.split("\t")[0]
        due = sorted(a["num"] for a in ca.get("articles", []) if a.get("fin", "2999") <= TODAY)
        sources["cpc-tricoteuses-main"] = {"id": "cpc-tricoteuses-main", "label": "Code de procédure civile — Tricoteuses LEGI mirror, branch main (state in force)",
                                           "official": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070716/", "channel": "git:https://git.tricoteuses.fr/codes/code_de_procedure_civile.git#main",
                                           "check": "git-head", "corpora": ["mapping-cpc-mo"], "last_checked": NOW, "last_version": head or ca.get("mirror_head")}
        if not INIT and ((head and head != (ca.get("mirror_head") or "").split()[0] and "branch futur" not in (ca.get("mirror_head") or "")) or due):
            report["changes"].append({"source": "cpc-tricoteuses-main", "kind": "CPC mirror advanced or article versions reached their end date", "head": head, "due_articles": due})
            if "--no-refresh" not in sys.argv:
                for cmd in (["python3", "scripts/mop_cpc_articles.py", "--pull"], ["python3", "scripts/mop_map2.py", "--workers", "6"], ["python3", "scripts/mop_build.py"]):
                    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
                    report.setdefault("cpc_refresh", []).append({"cmd": " ".join(cmd), "rc": r.returncode, "tail": r.stdout[-300:]})
    json.dump(sorted(sources.values(), key=lambda s: s["id"]), open(SRC, "w"), indent=2, ensure_ascii=False)
    json.dump(report, open(os.path.join(RAW, "check_report.json"), "w"), indent=2, ensure_ascii=False)
    print(json.dumps({"changes": len(report["changes"]), "errors": report["errors"][:10]}, indent=1))
    sys.exit(1 if report["changes"] and not INIT else 0)


if __name__ == "__main__":
    main()
