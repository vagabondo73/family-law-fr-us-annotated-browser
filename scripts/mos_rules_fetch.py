#!/usr/bin/env python3
"""Fetch Missouri Supreme Court Rules (family-relevant) from courts.mo.gov.
courts.mo.gov returns HTTP 403 to direct/automated HTTP clients (curl, SDK live fetch, cloud browser) and its
banner forbids automated repetitive querying; we therefore read the pages through the Perplexity index copy
(pplx_sdk.content.snippets), a single low-volume pass per run. Page ids on courts.mo.gov are sequential
within a rule (index page id N, subdivisions N+1, N+2 ...).
Output: raw/mo/rules/pages.jsonl (one record per page id)
Usage: python3 scripts/mos_rules_fetch.py [--refresh]
"""
import os, re, sys, json
from concurrent.futures import ThreadPoolExecutor
import pplx_sdk

ROOT = "/home/user/workspace/flb"
OUT = os.path.join(ROOT, "raw", "mo", "rules", "pages.jsonl")
REFRESH = "--refresh" in sys.argv
MISS = os.path.join(ROOT, "raw", "mo", "rules", "pages_missing.jsonl")
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
# rule -> (index page id, first subdivision id, max id to probe)
RULES = {
    "55": (199631, 199632, 199672),
    "74": (199740, 199741, 199758),
    "75": (199759, 199760, 199763),
    "78": (200286, 200287, 200297),
    "84.16": (199775, 199793, 199793),
    "88": (199856, 199857, 199866),
}
Q = ("complete verbatim text of this rule subdivision: every paragraph and lettered subdivision, "
     "the Source note, the adoption/amendment history in parentheses, First Adopted and Most Recently Effective dates")


def fetch(pid):
    url = f"https://www.courts.mo.gov/page.jsp?id={pid}"
    try:
        r = pplx_sdk.content.snippets(query=Q, urls=[url], max_tokens=4096, max_tokens_per_page=4096)
        x = r[0]
        return {"id": pid, "url": url, "text": x.text, "error": x.error}
    except Exception as e:
        return {"id": pid, "url": url, "text": None, "error": str(e)}


def main():
    done = {}
    if os.path.exists(OUT) and not REFRESH:
        for l in open(OUT):
            d = json.loads(l)
            if d.get("text"):
                done[d["id"]] = d
    ids = []
    for rule, (idx, a, b) in RULES.items():
        ids += list(range(a, b + 1))
    # procedure axis (SCOPE §4.5): sweep every page id of the Rules 41-101 block
    sys.path.insert(0, os.path.dirname(__file__))
    from mos_config import RULES_SWEEP
    for a, b in RULES_SWEEP:
        ids += list(range(a, b + 1))
    ids = sorted(set(ids))
    miss = {}
    if os.path.exists(MISS) and not REFRESH:
        for l in open(MISS):
            d = json.loads(l); miss[d["id"]] = d
    todo = [i for i in ids if i not in done and ("--retry-missing" in sys.argv or i not in miss)]
    print("todo", len(todo), flush=True)
    with ThreadPoolExecutor(WORKERS) as ex:
        for k, d in enumerate(ex.map(fetch, todo)):
            if d.get("text"):
                done[d["id"]] = d
                miss.pop(d["id"], None)
            else:
                miss[d["id"]] = d
            print(d["id"], d["error"], (d["text"] or "")[:80].replace("\n", " "), flush=True)
            if k % 50 == 49:
                save(done, miss)
    save(done, miss)


def save(done, miss):
    with open(OUT + ".tmp", "w") as f:
        for i in sorted(done):
            f.write(json.dumps(done[i], ensure_ascii=False) + "\n")
    os.replace(OUT + ".tmp", OUT)
    with open(MISS, "w") as f:
        for i in sorted(miss):
            f.write(json.dumps(miss[i], ensure_ascii=False) + "\n")


FOUT = os.path.join(ROOT, "raw", "mo", "rules", "pages_fetch.jsonl")


def fetch_sitemap_and_combined():
    """courts.mo.gov site map (id=942: every rule subdivision) and each rule's combined page (id=200636&up=<index>), cached copies."""
    sys.path.insert(0, os.path.dirname(__file__))
    from mos_rules_build import RULE_INDEX
    r = pplx_sdk.content.fetch(["https://www.courts.mo.gov/page.jsp?id=942"])
    json.dump([{"url": "https://www.courts.mo.gov/page.jsp?id=942", "content": r[0].content, "error": r[0].error}],
              open(os.path.join(ROOT, "raw", "mo", "rules", "sitemap_fetch.json"), "w"), ensure_ascii=False, indent=1)
    ups = sorted(set(RULE_INDEX.values()))
    res = pplx_sdk.content.fetch([f"https://www.courts.mo.gov/page.jsp?id=200636&up={u}" for u in ups])
    json.dump([{"up": u, "url": x.url, "content": x.content, "error": x.error} for u, x in zip(ups, res)],
              open(os.path.join(ROOT, "raw", "mo", "rules", "combined_fetch.json"), "w"), ensure_ascii=False, indent=1)


def fetch_channel():
    """Second channel: Perplexity cached page copy (pplx_sdk.content.fetch, cache) for every page id of the sweep.
    Fills subdivisions that the snippets channel cannot deliver and the rule index pages (subdivision lists)."""
    sys.path.insert(0, os.path.dirname(__file__))
    from mos_config import RULES_SWEEP, RULES_EXTRA_IDS
    ids = sorted(set(RULES_EXTRA_IDS) | {i for a, b in RULES_SWEEP for i in range(a, b + 1)} | {i for _, (x, a, b) in RULES.items() for i in range(x, b + 1)})
    done = {}
    if os.path.exists(FOUT) and not REFRESH:
        for l in open(FOUT):
            d = json.loads(l); done[d["id"]] = d
    todo = [i for i in ids if i not in done or (("--retry-missing" in sys.argv) and not done[i].get("content"))]
    print("fetch todo", len(todo), flush=True)
    for k in range(0, len(todo), 40):
        chunk = todo[k:k + 40]
        try:
            res = pplx_sdk.content.fetch([f"https://www.courts.mo.gov/page.jsp?id={i}" for i in chunk])
        except Exception as e:
            print("ERR", e, flush=True); continue
        for i, r in zip(chunk, res):
            done[i] = {"id": i, "url": f"https://www.courts.mo.gov/page.jsp?id={i}", "content": r.content, "error": r.error,
                       "is_cached": r.is_cached, "title": r.title}
        with open(FOUT + ".tmp", "w") as f:
            for i in sorted(done):
                f.write(json.dumps(done[i], ensure_ascii=False) + "\n")
        os.replace(FOUT + ".tmp", FOUT)
        print("fetched", k + len(chunk), "/", len(todo), flush=True)


if __name__ == "__main__":
    if "--channel" in sys.argv and sys.argv[sys.argv.index("--channel") + 1] == "fetch":
        fetch_channel()
    elif "--channel" in sys.argv and sys.argv[sys.argv.index("--channel") + 1] == "sitemap":
        fetch_sitemap_and_combined()
    else:
        main()
