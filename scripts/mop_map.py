#!/usr/bin/env python3
"""CPC <-> Missouri article-to-rule mapping (SCOPE §4.5), LLM-assisted and grounded in the texts.
Stage 1 (per CPC section group): choose the Missouri units (Supreme Court Rule or RSMo chapter) that could govern the
         same matter, from a unit catalog.
Stage 2 (per group): given the CPC article texts and the heading + opening text of every subdivision/section of the chosen
         units, decide per article: mo_norms (ids from the supplied list only), equivalence, note_fr, note_en.
Checkpoints: raw/mop/stage1.jsonl, raw/mop/stage2.jsonl (resume; --redo-stage2 to recompute stage 2).
Assembly: python3 scripts/mop_build.py
Usage: python3 scripts/mop_map.py [--limit N] [--workers 6]
"""
import os, re, sys, json, hashlib
from concurrent.futures import ThreadPoolExecutor
import pplx_sdk

ROOT = "/home/user/workspace/flb"
RAW = os.path.join(ROOT, "raw", "mop")
S1 = os.path.join(RAW, "stage1.jsonl")
S2 = os.path.join(RAW, "stage2.jsonl")
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
MAXG = 12  # articles per LLM item

RSMO_CHAPTER_TITLES = {}


def load_mo():
    rules = json.load(open(os.path.join(ROOT, "data", "norms", "mo-rules.json")))["norms"]
    rsmo = json.load(open(os.path.join(ROOT, "data", "norms", "mo-rsmo.json")))["norms"]
    units = {}
    for n in rules:
        if n["kind"] != "rule":
            continue
        r = n["num"].split(".")[0]
        u = units.setdefault(f"rule-{r}", {"id": f"rule-{r}", "label": n["path"][-1]["label"], "norms": []})
        u["norms"].append(n)
    for n in rsmo:
        ch = n["num"].split(".")[0]
        u = units.setdefault(f"ch-{ch}", {"id": f"ch-{ch}", "label": "RSMo " + n["path"][-1]["label"], "norms": []})
        u["norms"].append(n)
    return units


def cpc_groups():
    arts = json.load(open(os.path.join(RAW, "cpc_articles.json")))["articles"]
    groups, order = {}, []
    for a in arts:
        key = a["path"][-1]["id"] if a["path"] else a["livre"]
        if key not in groups:
            groups[key] = []; order.append(key)
        groups[key].append(a)
    items = []
    for k in order:
        g = groups[k]
        for i in range(0, len(g), MAXG):
            chunk = g[i:i + MAXG]
            items.append({"gid": f"{k}#{i // MAXG}", "path": " > ".join(p["label"] for p in chunk[0]["path"]), "articles": chunk})
    return items


def jl(p):
    out = {}
    if os.path.exists(p):
        for l in open(p):
            try:
                d = json.loads(l); out[d["gid"]] = d
            except Exception:
                pass
    return out


I1 = ("You are a comparative civil procedure expert (French Code de procédure civile vs. Missouri civil procedure). "
      "Given a group of French CPC articles (with their location in the code) and a catalog of Missouri units "
      "(Supreme Court Rules 41-101 and RSMo chapters), list the ids of up to 5 Missouri units whose provisions could govern "
      "the same procedural matter as at least one of the CPC articles. Return an empty list when nothing in the catalog deals "
      "with that matter (e.g. French institutions with no Missouri analogue). Use only ids from the catalog.")
SC1 = {"type": "object", "properties": {"units": {"type": "array", "items": {"type": "string"}}}, "required": ["units"]}

I2 = ("You map French Code de procédure civile (CPC) articles to Missouri provisions (Supreme Court Rules and RSMo sections). "
      "For EACH CPC article in the input, decide which of the supplied Missouri provisions (ONLY ids from 'missouri' list) "
      "correspond to it, and classify the correspondence:\n"
      "- equivalent: the Missouri provision states substantially the same rule for the same procedural matter;\n"
      "- partial: it covers the same matter but only in part, or with materially different conditions/effects;\n"
      "- functional: it uses a different technique/institution to achieve a comparable procedural function;\n"
      "- none: no supplied Missouri provision addresses the matter (mo_norms must then be empty).\n"
      "Choose at most 4 ids, most relevant first. Base the decision strictly on the texts supplied; do not rely on or cite "
      "anything not in the texts, do not invent content, case law or numbers. Write note_fr (French) and note_en (English), each "
      "one or two concise sentences (max ~45 words) stating what the CPC article provides and how the Missouri provision(s) "
      "compare (or why there is no counterpart). Refer to Missouri provisions as 'Rule 55.27' or 'RSMo 516.120' and to CPC "
      "articles as 'art. 56'. Return one entry per CPC article, using the exact 'num' given.")
SC2 = {"type": "object", "properties": {"articles": {"type": "array", "items": {"type": "object", "properties": {
    "num": {"type": "string"}, "mo_norms": {"type": "array", "items": {"type": "string"}},
    "equivalence": {"type": "string", "enum": ["equivalent", "partial", "functional", "none"]},
    "note_fr": {"type": "string"}, "note_en": {"type": "string"}}, "required": ["num", "mo_norms", "equivalence", "note_fr", "note_en"]}}},
    "required": ["articles"]}


def short(t, n):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " …"


def run_llm(item, instr, schema, mt=16384):
    try:
        r = pplx_sdk.llm.extract(items=[json.dumps(item, ensure_ascii=False)], instruction=instr, output_schema=schema, max_tokens=mt)[0]
        if r.error:
            return None, str(r.error)
        return r.result, None
    except Exception as e:
        return None, str(e)


def main():
    units = load_mo()
    catalog = [{"id": u["id"], "label": u["label"],
                "contents": short("; ".join(n["num"] + " " + (n["heading"] or "") for n in u["norms"]), 400)} for u in units.values()]
    items = cpc_groups()
    if LIMIT:
        items = items[:LIMIT]
    s1 = jl(S1)
    todo = [it for it in items if it["gid"] not in s1 or s1[it["gid"]].get("error")]
    print("groups", len(items), "stage1 todo", len(todo), flush=True)

    def f1(it):
        payload = {"cpc_group": it["path"], "cpc_articles": [{"num": a["num"], "text": short(a["text"], 500)} for a in it["articles"]],
                   "missouri_catalog": catalog}
        res, err = run_llm(payload, I1, SC1, 4096)
        return {"gid": it["gid"], "units": [u for u in (res or {}).get("units", []) if u in units][:5], "error": err}

    with ThreadPoolExecutor(WORKERS) as ex, open(S1, "a") as fo:
        for k, d in enumerate(ex.map(f1, todo)):
            fo.write(json.dumps(d, ensure_ascii=False) + "\n"); fo.flush(); s1[d["gid"]] = d
            if k % 20 == 0:
                print("s1", k, d["gid"], d["units"], d["error"], flush=True)

    s2 = {} if "--redo-stage2" in sys.argv else jl(S2)
    todo = [it for it in items if it["gid"] not in s2 or s2[it["gid"]].get("error")]
    print("stage2 todo", len(todo), flush=True)

    def f2(it):
        us = s1.get(it["gid"], {}).get("units", [])
        cands = []
        for u in us:
            for n in units[u]["norms"]:
                cands.append({"id": n["id"], "heading": n["heading"], "text": short(n.get("text") or "", 450)})
        arts = [{"num": a["num"], "text": short(a["text"], 1400)} for a in it["articles"]]
        if not cands:
            return {"gid": it["gid"], "units": us, "articles": [{"num": a["num"], "mo_norms": [], "equivalence": "none", "note_fr": None, "note_en": None,
                                                                   "auto": "no-candidate-unit"} for a in it["articles"]], "error": None}
        payload = {"cpc_group": it["path"], "cpc_articles": arts, "missouri": cands}
        res, err = run_llm(payload, I2, SC2, 16384)
        valid = {c["id"] for c in cands}
        out = []
        for x in (res or {}).get("articles", []):
            x["mo_norms"] = [i for i in x.get("mo_norms", []) if i in valid][:4]
            if not x["mo_norms"]:
                x["equivalence"] = "none"
            out.append(x)
        return {"gid": it["gid"], "units": us, "articles": out, "error": err,
                "cand_hash": hashlib.sha256(json.dumps(sorted(valid)).encode()).hexdigest()[:12]}

    with ThreadPoolExecutor(WORKERS) as ex, open(S2, "a") as fo:
        for k, d in enumerate(ex.map(f2, todo)):
            fo.write(json.dumps(d, ensure_ascii=False) + "\n"); fo.flush()
            if k % 10 == 0:
                print("s2", k, d["gid"], len(d["articles"]), d["error"], flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
