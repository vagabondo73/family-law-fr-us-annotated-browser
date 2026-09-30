#!/usr/bin/env python3
"""CPC <-> Missouri mapping, quality pass (v2). Full-text pipeline:
  Q  (LLM)  English gist + legal keywords for every CPC article (full article text)      -> raw/mop/v2_q.jsonl
  R  (local) BM25 keyword retrieval over the FULL texts of all Missouri Rules (41-101, 88) and RSMo sections
             (procedure + family chapters); candidates = top-K per article  U  v1 decisions -> raw/mop/v2_cands.json
  M  (LLM)  mapping decision per article from the FULL CPC text and FULL candidate texts  -> raw/mop/v2_m.jsonl
  V  (LLM)  independent verification: sees only the article + the proposed Missouri texts; confirms or downgrades
             the equivalence, gives confidence, verbatim supporting quotes, and grounded notes -> raw/mop/v2_v.jsonl
Quotes returned by V are checked mechanically against the texts in scripts/mop_build.py.
All stages checkpoint & resume. Usage: python3 scripts/mop_map2.py [--workers N] [--stage q|m|v|all] [--redo m|v] [--limit N]
"""
import os, re, sys, json, math, time, hashlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import pplx_sdk

ROOT = "/home/user/workspace/flb"
RAW = os.path.join(ROOT, "raw", "mop")
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 10
STAGE = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "all"
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
REDO = sys.argv[sys.argv.index("--redo") + 1] if "--redo" in sys.argv else ""
QF, MF, VF, CF = (os.path.join(RAW, f) for f in ("v2_q.jsonl", "v2_m.jsonl", "v2_v.jsonl", "v2_cands.json"))
TOPK, MAXC, CAP_ART, CAP_MO, BATCH = 8, 18, 9000, 7000, 3


def jl(p, key):
    out = {}
    if os.path.exists(p):
        for l in open(p):
            try:
                d = json.loads(l)
            except Exception:
                continue
            if d.get("error") and d[key] in out and not out[d[key]].get("error"):
                continue
            out[d[key]] = d
    return out


def run_llm(payload, instr, schema, mt=16384):
    for att in range(3):
        try:
            r = pplx_sdk.llm.extract(items=[json.dumps(payload, ensure_ascii=False)], instruction=instr, output_schema=schema, max_tokens=mt)[0]
            if r.error:
                err = str(r.error)
            else:
                return r.result, None
        except Exception as e:
            err = str(e)
        time.sleep(3 * (att + 1))
    return None, err


def h(t):
    return hashlib.sha1(re.sub(r"\s+", " ", t or "").strip().encode()).hexdigest()[:12]


def norm_ws(t):
    return re.sub(r"\s+", " ", t or "").strip()


def cap(t, n):
    t = norm_ws(t)
    return (t, False) if len(t) <= n else (t[:n].rsplit(" ", 1)[0] + " […]", True)


def load_arts():
    d = json.load(open(os.path.join(RAW, "cpc_articles.json")))
    arts = d["articles"]
    return arts


def load_mo():
    mo = {}
    for c in ("mo-rules", "mo-rsmo"):
        for n in json.load(open(os.path.join(ROOT, "data", "norms", f"{c}.json")))["norms"]:
            if n.get("kind") == "form14-line":
                continue
            mo[n["id"]] = n
    return mo


def mo_label(n):
    return ("Rule " if n["id"].startswith("mo-rules-") else "RSMo ") + n["num"]


# ---------------- BM25 ----------------
STOP = set("""a an the and or of to in on for by with as at from is are be been being was were shall may must not no any all
each such that this these those which who whom whose it its their there than then if when where under upon into within without
other shall be have has had do does done made make court party parties action civil rule rules section sections provided
provision provisions subject pursuant thereof therein hereof herein person persons state missouri rsmo""".split())


def stem(w):
    for suf in ("ations", "ation", "ments", "ment", "ings", "ing", "ies", "ied", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf in ("ies", "ied") else "")
    return w


def toks(t):
    return [stem(w) for w in re.findall(r"[a-z][a-z\-']+", (t or "").lower()) if w not in STOP and len(w) > 2]


class BM25:
    def __init__(self, docs, k1=1.4, b=0.75):
        self.ids = list(docs)
        self.tf = [Counter(docs[i]) for i in self.ids]
        self.dl = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.dl) / len(self.dl)
        df = Counter(w for c in self.tf for w in c)
        N = len(self.ids)
        self.idf = {w: math.log(1 + (N - v + 0.5) / (v + 0.5)) for w, v in df.items()}
        self.k1, self.b = k1, b

    def top(self, q, k):
        qs = Counter(q)
        sc = []
        for j, c in enumerate(self.tf):
            s = 0.0
            for w, qn in qs.items():
                f = c.get(w)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.dl[j] / self.avg)) * (1 + 0.3 * (qn - 1))
            if s > 0:
                sc.append((s, self.ids[j]))
        sc.sort(reverse=True)
        return sc[:k]


# ---------------- prompts ----------------
IQ = ("For EACH French Code de procédure civile article in the input, write in English: 'gist' — one neutral sentence stating what "
      "the article provides; and 'keywords' — 8 to 20 English legal terms (common-law/US civil-procedure vocabulary where an "
      "equivalent exists, e.g. 'summons', 'service of process', 'motion to dismiss', 'statute of limitations', 'default judgment', "
      "'dissolution of marriage', 'child custody', 'appeal', 'garnishment', 'arbitration award') describing the procedural matter. "
      "Base it only on the article text. Return one entry per article with the exact 'num'.")
SQ = {"type": "object", "properties": {"articles": {"type": "array", "items": {"type": "object", "properties": {
    "num": {"type": "string"}, "gist": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}},
    "required": ["num", "gist", "keywords"]}}}, "required": ["articles"]}

IM = ("You map French Code de procédure civile (CPC) articles to Missouri provisions (Supreme Court Rules and RSMo sections). "
      "You receive the FULL text of each CPC article and the FULL text of candidate Missouri provisions. For EACH CPC article decide "
      "which candidates (ONLY ids from 'missouri') govern the same procedural matter, and classify:\n"
      "- equivalent: substantially the same rule for the same matter;\n"
      "- partial: same matter, but covered only in part or with materially different conditions/effects;\n"
      "- functional: a different technique/institution that serves a genuinely comparable procedural function in the same kind of "
      "proceeding (do NOT use it for mere thematic resemblance, general definitions, or French institutional/territorial adaptation rules);\n"
      "- none: no candidate addresses the matter (mo_norms empty). Articles that only adapt the code to overseas territories, "
      "rename French institutions, or organise purely French bodies normally have no counterpart.\n"
      "Choose at most 4 ids, most relevant first. Decide strictly from the texts supplied; never rely on outside knowledge, case law or "
      "numbers not in the texts. note_fr (French) and note_en (English): one or two concise sentences (max ~50 words) stating what "
      "the CPC article provides and how the Missouri provision(s) compare (or why none). Refer to 'Rule 55.27', 'RSMo 516.120', "
      "'art. 56'. Return one entry per CPC article, using the exact 'num'.")
SM = {"type": "object", "properties": {"articles": {"type": "array", "items": {"type": "object", "properties": {
    "num": {"type": "string"}, "mo_norms": {"type": "array", "items": {"type": "string"}},
    "equivalence": {"type": "string", "enum": ["equivalent", "partial", "functional", "none"]},
    "note_fr": {"type": "string"}, "note_en": {"type": "string"}}, "required": ["num", "mo_norms", "equivalence", "note_fr", "note_en"]}}},
    "required": ["articles"]}

IV = ("You are an independent, skeptical reviewer of a proposed comparative-law mapping between French Code de procédure civile "
      "articles and Missouri provisions. For EACH proposal you get the FULL CPC article text, the FULL texts of the proposed Missouri "
      "provisions, the proposed equivalence (equivalent > partial > functional > none) and notes. Using ONLY these texts:\n"
      "1. keep only the Missouri ids that really govern the same matter (subset of the proposed ids);\n"
      "2. set 'equivalence': confirm it or DOWNGRADE it (never upgrade). 'functional' requires a genuinely comparable procedural "
      "function, not thematic resemblance; overseas-adaptation / institution-renaming / purely French organisational articles -> none;\n"
      "3. 'confidence': high | medium | low for your final classification;\n"
      "4. 'cpc_quote': a short VERBATIM excerpt (5-30 words, copied exactly) of the CPC article supporting the comparison; "
      "'mo_quotes': for each kept Missouri id one VERBATIM excerpt (5-30 words, copied exactly from that provision's text);\n"
      "5. 'grounded': true if every statement in the proposed notes is supported by the texts; if not, write corrected note_fr / "
      "note_en (max ~50 words each, grounded in the quotes); otherwise return the proposed notes unchanged;\n"
      "6. 'issue': brief English reason when you downgrade or correct (else empty).\n"
      "For equivalence none, return empty ids/mo_quotes, and a cpc_quote. Return one entry per proposal with the exact 'num'.")
SV = {"type": "object", "properties": {"articles": {"type": "array", "items": {"type": "object", "properties": {
    "num": {"type": "string"}, "mo_norms": {"type": "array", "items": {"type": "string"}},
    "equivalence": {"type": "string", "enum": ["equivalent", "partial", "functional", "none"]},
    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    "cpc_quote": {"type": "string"},
    "mo_quotes": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "quote": {"type": "string"}}, "required": ["id", "quote"]}},
    "grounded": {"type": "boolean"}, "note_fr": {"type": "string"}, "note_en": {"type": "string"}, "issue": {"type": "string"}},
    "required": ["num", "mo_norms", "equivalence", "confidence", "cpc_quote", "mo_quotes", "grounded", "note_fr", "note_en"]}}},
    "required": ["articles"]}


def groups(arts, size):
    g, order = {}, []
    for a in arts:
        k = a["path"][-1]["id"] if a["path"] else a["livre"]
        if k not in g:
            g[k] = []; order.append(k)
        g[k].append(a)
    out = []
    for k in order:
        for i in range(0, len(g[k]), size):
            out.append((f"{k}#{i // size}", g[k][i:i + size]))
    return out


def art_payload(a):
    t, tr = cap(a["text"], CAP_ART)
    return {"num": a["num"], "location": " > ".join(p["label"] for p in a["path"]), "text": t, **({"truncated": True} if tr else {})}


def mo_payload(n):
    t, tr = cap(n.get("text") or "", CAP_MO)
    return {"id": n["id"], "label": mo_label(n), "heading": n.get("heading"), "part_of": " > ".join(p["label"] for p in n.get("path", [])[-2:]),
            "text": t or "(text not available)", **({"truncated": True} if tr else {})}


def pool(fn, todo, path, key):
    with ThreadPoolExecutor(WORKERS) as ex, open(path, "a") as fo:
        for i, rec in enumerate(ex.map(fn, todo)):
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n"); fo.flush()
            if i % 20 == 0:
                print(os.path.basename(path), i, "/", len(todo), rec[key], rec.get("error"), flush=True)


def main():
    arts = load_arts()
    if LIMIT:
        arts = arts[:LIMIT]
    A = {a["num"]: a for a in arts}
    mo = load_mo()
    # ---- Q
    if STAGE in ("q", "all"):
        q = jl(QF, "gid")
        todo = [(gid, ch) for gid, ch in groups(arts, 12) if gid not in q or q[gid].get("error") or set(x["num"] for x in q[gid].get("articles", [])) < set(a["num"] for a in ch)]
        print("Q todo", len(todo), flush=True)

        def fq(x):
            gid, ch = x
            res, err = run_llm({"articles": [{"num": a["num"], "location": " > ".join(p["label"] for p in a["path"]), "text": cap(a["text"], 4000)[0]} for a in ch]}, IQ, SQ, 8192)
            return {"gid": gid, "nums": [a["num"] for a in ch], "articles": (res or {}).get("articles", []), "error": err}
        pool(fq, todo, QF, "gid")
    q = {}
    for d in jl(QF, "gid").values():
        for x in d.get("articles", []):
            q[x["num"]] = x
    # ---- R
    docs = {i: toks((n.get("heading") or "") + " " + (n.get("heading") or "") + " " + " ".join(p["label"] for p in n.get("path", [])[-1:]) + " " + (n.get("text") or "")) for i, n in mo.items()}
    bm = BM25(docs)
    v1 = {}
    if os.path.exists(os.path.join(RAW, "stage2.jsonl")):
        for l in open(os.path.join(RAW, "stage2.jsonl")):
            d = json.loads(l)
            for x in d.get("articles", []):
                v1[x["num"]] = [i for i in x.get("mo_norms", []) if i in mo]
    cands = {}
    for a in arts:
        qa = q.get(a["num"], {})
        qt = toks(" ".join(qa.get("keywords", [])) * 2 + " " + (qa.get("gist") or ""))
        hits = [i for s, i in bm.top(qt, TOPK)] if qt else []
        cands[a["num"]] = {"bm25": hits, "v1": v1.get(a["num"], []), "no_query": not qt}
    json.dump(cands, open(CF, "w"), ensure_ascii=False)
    print("R done; articles without query", sum(1 for c in cands.values() if c["no_query"]), flush=True)
    # ---- M
    if STAGE in ("m", "all"):
        if REDO == "m" and os.path.exists(MF):
            os.rename(MF, MF + f".{int(time.time())}.bak")
        m = jl(MF, "bid")
        todo = [(bid, ch) for bid, ch in groups(arts, BATCH) if bid not in m or m[bid].get("error") or set(x["num"] for x in m[bid].get("articles", [])) < set(a["num"] for a in ch)
                or any(m[bid].get("hashes", {}).get(a["num"], h(a["text"])) != h(a["text"]) for a in ch)]
        print("M todo", len(todo), flush=True)

        def fm(x):
            bid, ch = x
            ids = []
            for a in ch:
                c = cands[a["num"]]
                for i in c["v1"] + c["bm25"]:
                    if i not in ids:
                        ids.append(i)
            # keep the per-article order but cap the union
            if len(ids) > MAXC:
                keep = []
                for rnk in range(TOPK + 4):
                    for a in ch:
                        lst = cands[a["num"]]["v1"] + cands[a["num"]]["bm25"]
                        if rnk < len(lst) and lst[rnk] not in keep:
                            keep.append(lst[rnk])
                ids = keep[:MAXC]
            payload = {"cpc_articles": [art_payload(a) for a in ch], "missouri": [mo_payload(mo[i]) for i in ids]}
            res, err = run_llm(payload, IM, SM)
            out = []
            for r in (res or {}).get("articles", []):
                if r.get("num") in A:
                    r["mo_norms"] = [i for i in r.get("mo_norms", []) if i in ids][:4]
                    if not r["mo_norms"]:
                        r["equivalence"] = "none"
                    out.append(r)
            return {"bid": bid, "nums": [a["num"] for a in ch], "hashes": {a["num"]: h(a["text"]) for a in ch}, "candidates": ids, "articles": out, "error": err}
        pool(fm, todo, MF, "bid")
    # ---- V
    if STAGE in ("v", "all"):
        if REDO == "v" and os.path.exists(VF):
            os.rename(VF, VF + f".{int(time.time())}.bak")
        m = jl(MF, "bid")
        v = jl(VF, "bid")
        todo = [b for b in m.values() if not b.get("error") and (b["bid"] not in v or v[b["bid"]].get("error") or set(v[b["bid"]].get("nums", [])) != set(x["num"] for x in b["articles"]) or v[b["bid"]].get("m_sig", h(json.dumps(b["articles"], sort_keys=True))) != h(json.dumps(b["articles"], sort_keys=True)))]
        print("V todo", len(todo), flush=True)

        def fv(b):
            props = [x for x in b["articles"] if x["num"] in A]
            ids = []
            for x in props:
                for i in x["mo_norms"]:
                    if i not in ids:
                        ids.append(i)
            payload = {"proposals": [{**art_payload(A[x["num"]]), "proposed_mo_norms": x["mo_norms"], "proposed_equivalence": x["equivalence"],
                                      "proposed_note_fr": x["note_fr"], "proposed_note_en": x["note_en"]} for x in props],
                       "missouri": [mo_payload(mo[i]) for i in ids]}
            res, err = run_llm(payload, IV, SV)
            return {"bid": b["bid"], "nums": [x["num"] for x in props], "m_sig": h(json.dumps(b["articles"], sort_keys=True)), "articles": (res or {}).get("articles", []), "error": err}
        pool(fv, todo, VF, "bid")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
