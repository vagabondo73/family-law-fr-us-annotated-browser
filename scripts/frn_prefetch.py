#!/usr/bin/env python3
"""Parallel prefetch of dila/textes_juridiques files (TEXT, SCTA, ARTI) listed via scripts/frn_textes.json
into the raw/frn_textes/ cache, so that frn_build.py runs fast.
Usage: python3 scripts/frn_prefetch.py [--refresh]"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frn_build import tj_fetch, parse_text_md, TEXTES_CFG

refresh = "--refresh" in sys.argv
cfg = json.load(open(TEXTES_CFG))
ids = [t["id"] for t in cfg["texts"] if t.get("kind") != "circulaire"]
pool = ThreadPoolExecutor(16)


def get(i):
    try:
        return i, tj_fetch(i, refresh)
    except Exception as e:  # network error: logged, build will retry
        print("fetch error", i, e, flush=True)
        return i, ""


seen, level, n = set(), ids, 0
while level:
    level = [i for i in dict.fromkeys(level) if i not in seen]
    seen.update(level)
    nxt = []
    for i, md in pool.map(get, level):
        if "ARTI" in i or not md:
            continue
        try:
            _, _, items = parse_text_md(md)
        except Exception as e:
            print("parse error", i, e, flush=True)
            continue
        nxt += [it["id"] for it in items]
    n += len(level)
    print("fetched", n, "next level", len(nxt), flush=True)
    level = nxt
print("PREFETCH DONE", n, flush=True)
