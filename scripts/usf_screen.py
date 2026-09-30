#!/usr/bin/env python3
"""LLM-assisted screening of candidate opinions (raw/us/cap_hits + raw/us/cl_hits).
For each candidate: build keyword-in-context windows around the matched patterns, ask the LLM whether the opinion
interprets/applies an included norm or judge-made rule, which ones, issues, a neutral summary and 1-3 excerpts
copied from the windows. Excerpts are later verified verbatim (usf_build.py). Checkpoint: raw/us/screen.jsonl
"""
import glob, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW, ROOT, RULES
import pplx_sdk

OUT = RAW + "/screen.jsonl"
BATCH = 12

USC = {n["id"]: n["heading"] for n in json.load(open(ROOT + "/data/norms/us-usc.json"))["norms"]}
CFR = {n["id"]: n["heading"] for n in json.load(open(ROOT + "/data/norms/us-cfr.json"))["norms"]}
CONST = {n["id"]: n["heading"] for n in json.load(open(ROOT + "/data/norms/us-const.json"))["norms"]}
COMMON = {f"us-common-{r[0]}": r[1] for r in RULES}


def ids(prefix, d=USC):
    return [k for k in d if k.startswith(prefix)]


C = ["us-const-amend14-s1", "us-const-amend5"]
GN = {
 "icara": ids("us-usc-22-90") + ids("us-cfr-22-94", CFR) + [k for k in COMMON if "icara" in k] + ["us-common-younger-abstention-family", "us-const-art6-cl2"],
 "pkpa": ["us-usc-28-1738a", "us-const-art4-s1", "us-common-divisible-divorce-ffc"],
 "ffccsoa": ["us-usc-28-1738b", "us-const-art4-s1"],
 "doma": ["us-usc-1-7", "us-usc-28-1738c", "us-const-amend5", "us-common-marriage-fundamental-right"],
 "evidence-service": ["us-usc-28-1781", "us-usc-28-1782"],
 "iaa": ids("us-usc-42-149"),
 "ipkca": ["us-usc-18-1204"],
 "goldman": ids("us-usc-22-91"),
 "title-iv-d": ids("us-usc-42-65") + ids("us-usc-42-66") + ["us-const-art1-s8-cl1"],
 "tax-alimony": ["us-usc-26-71", "us-usc-26-215"],
 "tax-1041": ["us-usc-26-1041"],
 "tax-dependency": ["us-usc-26-152-e", "us-usc-26-24"],
 "tax-marital-deduction": ["us-usc-26-2056", "us-usc-26-2056a", "us-usc-26-2523"],
 "tax-6015": ["us-usc-26-6015"],
 "qdro": ["us-usc-29-1056-d", "us-usc-26-414-p", "us-common-federal-preemption-family-property"],
 "usfspa": ["us-usc-10-1408", "us-common-federal-preemption-family-property"],
 "social-security-spouse": ids("us-usc-42-402") + ["us-usc-42-416"] + C,
 "bankruptcy-dso": ids("us-usc-11-"),
 "imm-family": ["us-usc-8-1101-b", "us-usc-8-1151-b-2", "us-usc-8-1154", "us-usc-8-1186a"] + ids("us-cfr-8-", CFR) + C,
 "nationality": ["us-usc-8-1401", "us-usc-8-1409", "us-usc-8-1431", "us-usc-8-1433"] + C + ["us-common-sex-classifications-family", "us-common-nonmarital-children-ep"],
 "dv-federal": ["us-usc-18-2261", "us-usc-18-2261a", "us-usc-18-2262", "us-usc-18-2265"],
 "dv-firearms": ["us-usc-18-922-g-8", "us-usc-18-922-g-9", "us-usc-18-921-a-33"],
 "domestic-relations-exception": ["us-common-domestic-relations-exception"],
 "rooker-feldman-family": ["us-common-rooker-feldman"],
 "younger-family": ["us-common-younger-abstention-family"],
 "parental-rights": C + ["us-common-parental-rights", "us-common-unwed-fathers", "us-common-tpr-due-process", "us-common-family-integrity"],
 "marriage-right": C + ["us-common-marriage-fundamental-right"],
 "pj-family": ["us-common-personal-jurisdiction-family", "us-const-amend14-s1"],
 "ffc-judgments-family": ["us-const-art4-s1", "us-common-divisible-divorce-ffc", "us-usc-28-1738a", "us-usc-28-1738b"],
 "federal-preemption-family": ["us-common-federal-preemption-family-property", "us-const-art6-cl2", "us-usc-10-1408", "us-usc-29-1056-d"],
 "nonmarital-children-ep": C + ["us-common-nonmarital-children-ep", "us-common-unwed-fathers"],
 "sex-classifications-family": C + ["us-common-sex-classifications-family"],
 "contempt-support": ["us-common-civil-contempt-support", "us-const-amend14-s1"],
 "access-divorce": ["us-common-access-to-divorce", "us-common-tpr-due-process", "us-const-amend14-s1"],
}
HAGUE = {"icara": "int-hcch-1980-art<N> (Hague Child Abduction Convention 1980, e.g. int-hcch-1980-art3, -art12, -art13, -art20)",
         "evidence-service": "int-hcch-1965-art<N> (Hague Service Convention) or int-hcch-1970-art<N> (Hague Evidence Convention)",
         "iaa": "int-hcch-1993-art<N> (Hague Intercountry Adoption Convention)"}
ALL = {**USC, **CFR, **CONST, **COMMON}
ISSUES = []
def _walk(n):
    ISSUES.append((n["id"], n["label"])); [_walk(c) for c in n["children"]]
for n in json.load(open(ROOT + "/data/issues/us.json"))["nodes"]:
    _walk(n)

INSTRUCTION = """You screen U.S. judicial opinions (U.S. Supreme Court or U.S. Court of Appeals for the Eighth Circuit) for a
family-law annotated code. Each item gives case metadata, CANDIDATE_NORMS (ids + headings), ISSUES (ids + labels) and
WINDOWS: verbatim passages from the opinion around the matched citations/keywords.
Decide whether the MAJORITY / COURT opinion actually interprets, construes, or applies (as part of its reasoning or holding)
at least one candidate norm or judge-made rule. A mere string citation, background mention, or a citation only in a dissent
does NOT qualify.
(1) Candidate STATUTES, REGULATIONS and TREATIES (U.S.C., C.F.R., Hague conventions) are included in the code as such: ANY
    genuine interpretation or application of them qualifies, whatever the subject of the dispute (e.g. 28 U.S.C. 1782 or the
    Hague Service Convention in a commercial case; 26 U.S.C. 6015 in any tax case; 18 U.S.C. 922(g)(8)/(9) or 921(a)(33) in
    any criminal case).
(2) CONSTITUTIONAL provisions qualify only when applied to a family-law question (marriage, parenthood, custody, child
    welfare, support, family benefits, family immigration/citizenship, domestic violence, divorce/judgment recognition).
(3) JUDGE-MADE RULES (us-common-*) qualify when the court articulates or applies the rule; for doctrines of general
    application (Rooker-Feldman, Younger abstention, personal jurisdiction) require a family-law context, EXCEPT when the
    item is marked "leading_case": true (the founding/leading decision establishing the doctrine), which qualifies.
For 42 U.S.C. 416 only its family-status definitions (subsections (a)-(h): spouse, wife, husband, widow(er), divorced
spouse, child, stepchild, family status under state intestacy law) count; disability ((i)) and other definitions do NOT.
Abortion-regulation questions are outside the perimeter (not relevant), unless another candidate norm is interpreted.
Return:
- relevant: true/false
- norms: list of candidate norm ids interpreted/applied (only ids from CANDIDATE_NORMS; for Hague conventions you may also
  use the int-hcch pattern given in HAGUE_IDS with the specific article numbers actually interpreted)
- provisions: the precise subdivision(s) construed, as cited by the court (e.g. "22 U.S.C. § 9003(e)(2)(A)", "art. 13(b)")
- issues: 1-3 ids from ISSUES (most specific applicable)
- summary: 1-3 neutral English sentences stating what the court held on the norm/rule
- excerpts: 1-3 passages COPIED CHARACTER-FOR-CHARACTER from WINDOWS (contiguous, 120-700 characters each) that state the
  court's interpretation/holding on the norm. Do not paraphrase, do not join non-contiguous text, do not add ellipses.
- reason: one short sentence."""

SCHEMA = {"type": "object", "properties": {
    "relevant": {"type": "boolean"},
    "norms": {"type": "array", "items": {"type": "string"}},
    "provisions": {"type": "array", "items": {"type": "string"}},
    "issues": {"type": "array", "items": {"type": "string"}},
    "summary": {"type": "string"},
    "excerpts": {"type": "array", "items": {"type": "string"}},
    "reason": {"type": "string"}}, "required": ["relevant", "norms", "issues", "summary", "excerpts"]}


SMALL = os.environ.get("USF_SMALL") == "1"  # retry mode for items whose LLM response failed to decode


def windows(rec, width=900, cap=11000):
    if SMALL:
        width, cap = 450, 4500
    t = rec["text"]
    spans = []
    for g, sp in rec["groups"].items():
        for s, e in sp[:6]:
            spans.append((max(0, s - width), min(len(t), e + width)))
    spans.sort()
    if not spans or rec.get("seed"):
        spans.insert(0, (0, min(len(t), 7000)))  # opening of the opinion (syllabus / statement of holding)
        spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    out, total = [], 0
    for s, e in merged:
        seg = t[s:e]
        out.append(seg); total += len(seg)
        if total > cap:
            break
    return out


def item(rec):
    cand = []
    for g in rec["groups"]:
        cand += GN.get(g, [])
    cand = list(dict.fromkeys(cand))
    iss_prefix = set()
    for c in cand:
        iss_prefix.add(c)
    hague = {g: HAGUE[g] for g in rec["groups"] if g in HAGUE}
    catalog = {c: ALL.get(c, "")[:110] for c in cand}
    if len(catalog) > 60:  # compact CFR lists
        catalog = {c: v[:60] for c, v in catalog.items()}
    return json.dumps({"case": rec["name"], "court": rec["court"], "date": rec["date"], "citations": rec["citations"],
                       "matched_groups": list(rec["groups"]), "leading_case": bool(rec.get("seed")), "CANDIDATE_NORMS": catalog, "HAGUE_IDS": hague,
                       "ISSUES": {i: l for i, l in ISSUES}, "WINDOWS": windows(rec)}, ensure_ascii=False)


def load_records():
    recs = []
    for d in ["cap_hits", "cl_hits"]:
        for fn in sorted(glob.glob(f"{RAW}/{d}/*.json")):
            r = json.load(open(fn)); r["_file"] = fn
            recs.append(r)
    return recs


def main():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            done.add(json.loads(line)["_file"])
    if "--rescreen" in sys.argv:  # re-run items previously judged not relevant (after instruction change)
        prev = {}
        for line in open(OUT):
            d = json.loads(line); prev[d["_file"]] = d
        STAT = {"icara", "pkpa", "ffccsoa", "doma", "evidence-service", "iaa", "ipkca", "goldman", "title-iv-d", "tax-alimony", "tax-1041",
                "tax-dependency", "tax-marital-deduction", "tax-6015", "qdro", "usfspa", "social-security-spouse", "bankruptcy-dso",
                "imm-family", "nationality", "dv-federal", "dv-firearms"}
        done = {f for f, d in prev.items() if d.get("relevant")}
        recs = [r for r in load_records() if r["_file"] in prev and r["_file"] not in done and (r.get("seed") or set(r["groups"]) & STAT)]
    else:
        recs = [r for r in load_records() if r["_file"] not in done]
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    if only:
        recs = [r for r in recs if any(o in r["_file"] for o in only)]
    print("to screen", len(recs), flush=True)
    import concurrent.futures as cf, threading
    lock = threading.Lock()

    def work(b):
        try:
            res = pplx_sdk.llm.extract(items=[item(r) for r in b], instruction=INSTRUCTION, output_schema=SCHEMA, max_tokens=16384)
        except Exception as e:
            print("batch error", e, flush=True); return 0
        with lock, open(OUT, "a") as f:
            for r, x in zip(b, res):
                if x.error:
                    print("err", r["_file"], x.error, flush=True); continue
                f.write(json.dumps({"_file": r["_file"], "name": r["name"], "date": r["date"], **x.result}, ensure_ascii=False) + "\n")
        return len(b)

    batches = [recs[i:i + BATCH] for i in range(0, len(recs), BATCH)]
    n = 0
    with cf.ThreadPoolExecutor(int(os.environ.get("USF_THREADS", "4"))) as ex:
        for k in ex.map(work, batches):
            n += k; print(n, "/", len(recs), flush=True)


if __name__ == "__main__":
    main()
