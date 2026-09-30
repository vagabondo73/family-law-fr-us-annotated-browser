#!/usr/bin/env python3
"""Temporal rule (b) review for links where decision date < D(norm) (raw/us/temporal_pending.json, from usf_build.py).
Evidence given to the reviewer: current text, post-decision amendment notes (USC 'Amendments' notes / CFR source note),
the provision(s) the court construed, verified excerpts, and quoted passages from the excerpts that occur verbatim in the
current text (automatic text-identity check). Output raw/us/temporal.jsonl {interp, norm, identical, method, justification}."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import ROOT, RAW
import pplx_sdk

N = {}
for c in ["us-usc", "us-cfr", "us-const", "us-common"]:
    fn = f"{ROOT}/data/norms/{c}.json"
    if os.path.exists(fn):
        for n in json.load(open(fn))["norms"]:
            N[n["id"]] = n
OUT = RAW + "/temporal.jsonl"

INSTRUCTION = """You apply a temporal rule for an annotated legal code. A court decision was issued BEFORE the date D on which
the current version of the norm took effect (last amendment). The decision may be kept only if the language it interpreted is
IDENTICAL IN WORDING AND FUNCTION to the current text (amendments elsewhere in the section/subsection, renumbering, or purely
technical changes that do not touch the interpreted language are harmless). If the interpreted language was changed in
substance after the decision (or you cannot tell from the evidence that it was not), answer identical=false.
For judge-made rules (id us-common-*), D is the date of the leading Supreme Court decision; answer identical=true only if the
earlier decision states/applies the rule consistently with the current formulation given in RULE.
Return identical (bool), method ("text-identical" when the quoted interpreted language appears verbatim in the current text
and no later amendment touched it; otherwise "functional-review"), and justification: 1-3 English sentences naming the
provision interpreted and why it is (or is not) identical in wording and function to the current text."""
SCHEMA = {"type": "object", "properties": {"identical": {"type": "boolean"}, "method": {"type": "string", "enum": ["text-identical", "functional-review"]},
                                            "justification": {"type": "string"}}, "required": ["identical", "method", "justification"]}


def quotes_in_current(excerpts, text):
    t = re.sub(r"\s+", " ", text or "")
    out = []
    for e in excerpts:
        for q in re.findall(r"[\"“]([^\"”]{30,400})[\"”]", e):
            q2 = re.sub(r"\s+", " ", q).strip()
            if q2 and q2 in t:
                out.append(q2)
    return out


def item(p):
    n = N.get(p["norm"], {})
    y = int((p["date"] or "0000")[:4])
    am = [a for a in n.get("amendments", []) if (a.get("year") or 0) >= y]
    return json.dumps({"decision": p["name"], "decision_date": p["date"], "norm": p["norm"], "norm_num": n.get("num"), "D": p["D"],
                       "current_text": (n.get("text") or "")[:5000], "RULE": n.get("summary_rule", "")[:2500] if p["norm"].startswith("us-common") else None,
                       "amendments_after_decision": [{"year": a["year"], "target": a["target"], "note": a["note"][:400]} for a in am][:40],
                       "cfr_source_note": (n.get("source_ids") or {}).get("cita") or (n.get("source_ids") or {}).get("part_source"),
                       "provisions_construed": p.get("provisions"), "excerpts": p["excerpts"],
                       "quoted_language_found_verbatim_in_current_text": quotes_in_current(p["excerpts"], n.get("text"))}, ensure_ascii=False)


def main():
    pend = json.load(open(RAW + "/temporal_pending.json"))
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT):
            d = json.loads(l); done.add((d["interp"], d["norm"], d.get("D")))
    pend = [p for p in pend if (p["interp"], p["norm"], p["D"]) not in done and (p["interp"], p["norm"], None) not in done]
    print("pending", len(pend), flush=True)
    for i in range(0, len(pend), 15):
        b = pend[i:i + 15]
        res = pplx_sdk.llm.extract(items=[item(p) for p in b], instruction=INSTRUCTION, output_schema=SCHEMA, max_tokens=16384)
        with open(OUT, "a") as f:
            for p, r in zip(b, res):
                if r.error:
                    print("err", p["interp"], r.error, flush=True); continue
                f.write(json.dumps({"interp": p["interp"], "norm": p["norm"], "D": p["D"], **r.result}, ensure_ascii=False) + "\n")
        print(i + len(b), flush=True)


if __name__ == "__main__":
    main()
