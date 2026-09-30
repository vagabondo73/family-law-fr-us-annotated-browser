#!/usr/bin/env python3
"""Enumerate The Missouri Bar's copies of Supreme Court of Missouri rule orders (news.mobar.org/order-<n>/) and keep those
touching Rules 41-101; download their order PDFs (Missouri Bar copies). Output raw/mo/rules/mobar_orders.json + PDFs.
Usage: python3 scripts/mop_orders_fetch.py [first last]"""
import os, re, sys, json, subprocess
import pplx_sdk
ROOT = "/home/user/workspace/flb"
RAW = os.path.join(ROOT, "raw", "mo", "rules")
OUT = os.path.join(RAW, "mobar_orders.json")
a, b = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (3080, 3200)
done = json.load(open(OUT)) if os.path.exists(OUT) else {}
todo = [f"https://news.mobar.org/order-{i}/" for i in range(a, b + 1) if f"https://news.mobar.org/order-{i}/" not in done]
for k in range(0, len(todo), 40):
    chunk = todo[k:k + 40]
    res = pplx_sdk.content.fetch(chunk, return_html=True)
    for u, r in zip(chunk, res):
        h = r.raw_html or ""
        c = r.content or ""
        t = re.search(r"# (Supreme Court of Missouri order[^\n]*)", c)
        od = re.search(r"Order dated ([A-Z][a-z]+\.? \d{1,2}, \d{4})", c)
        ed = re.search(r"Effective(?: date)?:?\s*\**\s*([A-Z][a-z]+\.? \d{1,2}, \d{4})", c)
        pdfs = sorted(set(re.findall(r'href="([^"]+\.pdf)"', h)))
        done[u] = {"url": u, "error": r.error, "title": t.group(1).strip() if t else (r.title or None), "order_dated": od.group(1) if od else None,
                   "effective": ed.group(1) if ed else None, "pdfs": pdfs, "content": c[:4000]}
    json.dump(done, open(OUT, "w"), indent=1, ensure_ascii=False)
    print("fetched", k + len(chunk), flush=True)
civ = {u: d for u, d in done.items() if d.get("title") and re.search(r"\b(4[1-9]|[5-9]\d|10[01])\.\d", d["title"] or "")}
for u, d in civ.items():
    for p in d["pdfs"]:
        fn = os.path.join(RAW, "mobar_" + os.path.basename(p))
        if not os.path.exists(fn):
            subprocess.run(["curl", "-sL", "-o", fn, p if p.startswith("http") else "https://news.mobar.org" + p], timeout=60)
    print(u, "|", d["title"], "|", d["order_dated"], "|", d["effective"], "|", d["pdfs"])
