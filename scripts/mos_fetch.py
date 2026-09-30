#!/usr/bin/env python3
"""Fetch RSMo chapter pages, current section pages and all prior-version pages from revisor.mo.gov.
Resumable: raw HTML cached under raw/mo/. Re-run with --refresh to re-download chapter + current pages
(prior versions are immutable and never re-downloaded).
Usage: python3 scripts/mos_fetch.py [--refresh] [--workers 4]
"""
import os, re, sys, time, json, html, hashlib, urllib.request, urllib.parse
import pplx_sdk
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from mos_config import *

REFRESH = "--refresh" in sys.argv
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
os.makedirs(os.path.join(RAW, "chapters"), exist_ok=True)
os.makedirs(os.path.join(RAW, "sections"), exist_ok=True)
os.makedirs(os.path.join(RAW, "const"), exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (flb research; family-law annotated browser)"}


def valid(data, path):
    if not data or len(data) < 2000 or "Blocked" in data[:20000] and "effdt" not in data:
        return False
    if "/sections/" in path or "/const/" in path:
        return 'id="effdt"' in data
    return True


def get(url, path, force=False, tries=3):
    """Single fetch: cached file -> pplx_sdk (return_html) -> urllib fallback."""
    return get_many([(url, path)], force, tries).get(path)


def get_many(pairs, force=False, tries=3, batch=25):
    """Batch fetch [(url, path)] via pplx_sdk.content.fetch(return_html=True); cache to path.
    revisor.mo.gov blocks bursty direct clients by IP (302 -> /main/Block.aspx), so the SDK channel is primary."""
    out, todo = {}, []
    for u, p in pairs:
        if not force and os.path.exists(p):
            d = open(p, encoding="utf-8", errors="replace").read()
            if valid(d, p):
                out[p] = d
                continue
        todo.append((u, p))
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        for t in range(tries):
            pending = [(u, p) for u, p in chunk if p not in out]
            if not pending:
                break
            try:
                res = pplx_sdk.content.fetch([u for u, _ in pending], return_html=True, cache_enabled=False)
                for (u, p), r in zip(pending, res):
                    d = r.raw_html
                    if valid(d, p):
                        open(p, "w", encoding="utf-8").write(d)
                        out[p] = d
                    else:
                        print("BAD", u, r.error, flush=True)
            except Exception as e:
                print("ERR", e, flush=True)
            time.sleep(2 * t)
        print("batch", i + len(chunk), "/", len(todo), flush=True)
    for u, p in todo:
        if p not in out and "--direct" in sys.argv:
            try:
                d = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf-8", "replace")
                if valid(d, p):
                    open(p, "w", encoding="utf-8").write(d); out[p] = d
            except Exception as e:
                print("ERR direct", u, e, flush=True)
    return out


ROW_RE = re.compile(r'PageSelect\.aspx\?section=([0-9.]+)&amp;bid=(\d+)&amp;hl=" style="text-decoration:none;">[^<]*</a>\s*</td>\s*<td[^>]*>(.*?)</td>', re.S)
VER_RE = re.compile(r'PageSelect\.aspx\?section=([^&"]+)&amp;bid=(\d+)(?:&amp;constit=y)?" style="text-decoration:none;">[^<]*</a>\s*</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>', re.S)


def chapter_rows(ch, force):
    h = get(f"{BASE}/main/OneChapter.aspx?chapter={ch}", os.path.join(RAW, "chapters", f"{ch}.html"), force)
    rows = []
    for s, b, t in ROW_RE.findall(h or ""):
        txt = html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
        m = re.search(r"\((\d+/\d+/\d{4})\)\s*$", txt)
        rows.append({"section": s, "bid": b, "title": re.sub(r"\s*\(\d+/\d+/\d{4}\)\s*$", "", txt), "date": m.group(1) if m else None})
    return rows


def main():
    listing = {}
    tasks = []
    for ch in all_chapters():
        rows = chapter_rows(ch, REFRESH)
        print(ch, len(rows), flush=True)
        listing[ch] = rows
    json.dump(listing, open(os.path.join(RAW, "chapter_listing.json"), "w"), indent=1)
    secs = sorted({r["section"] for ch, rows in listing.items() for r in rows if in_scope(ch, r["section"])}, key=secnum_key)
    print("sections in scope", len(secs), flush=True)

    pairs = [(f"{BASE}/main/OneSection.aspx?section={s}", os.path.join(RAW, "sections", f"{s}__cur.html")) for s in secs]
    got = get_many(pairs, REFRESH)
    cur = {s: got.get(p) for s, (u, p) in zip(secs, pairs)}
    vers = []
    for s, h in cur.items():
        if not h:
            continue
        for sec, bid, eff, end in VER_RE.findall(h):
            vers.append((s, bid))

    print("version pages", len(vers), flush=True)
    get_many([(f"{BASE}/main/OneSection.aspx?section={s}&bid={bid}", os.path.join(RAW, "sections", f"{s}__{bid}.html")) for s, bid in vers])
    # Constitution
    for art, sec in CONST:
        sid = f"{art}    {sec}"
        u = f"{BASE}/main/OneSection.aspx?section={urllib.parse.quote(sid)}&constit=y"
        get(u, os.path.join(RAW, "const", f"{art}-{sec}.html"), REFRESH)
    # Repeals & transfers table
    get(f"{BASE}/main/rx.aspx", os.path.join(RAW, "rx.html"), REFRESH)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
