"""Control check of the ECtHR metadata filter (France, family matters).
For each French/English family keyword, queries HUDOC (respondent FRA, judgments, full text) and classifies each hit:
included / excluded-by-screen (with reason) / outside article scope (no art. 8/12/14/P7-5 in HUDOC 'article' metadata).
Hits on art. 8 that are neither included nor explicitly excluded are flagged 'unexplained' (should be 0).
Output raw/int/hudoc/kwcheck.json. Re-run: python3 scripts/int_ecthr_kwcheck.py (after int_ecthr.py)."""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, DATA, dump, load
from int_hudoc_candidates import all_rows, JUD
from int_ecthr import touches, arts_of

HD = os.path.join(RAW, "hudoc")
KW = ["enfant", "filiation", "gestation pour autrui", "adoption", "divorce", "autorité parentale", "placement",
      "droit de visite", "enlèvement", "regroupement familial", "custody", "surrogacy", "abduction"]
NAMED = {"Mennesson": "65192/11", "Labassee": "65941/11", "Foulon et Bouvet": "9063/14", "D. c. France (2020)": "11288/18"}


def main():
    interps = load(os.path.join(DATA, "interps", "coe-ecthr.json"))["interps"]
    inc_ids = set()
    inc_apps = set()
    for x in interps:
        inc_ids.add(x["id"].replace("ecthr-", ""))
        for u in x.get("alt_urls", []):
            inc_ids.add(u["url"].split("i=")[-1])
        for a in (x.get("number") or "").split(", "):
            inc_apps.add(a.strip())
    led = load(os.path.join(HD, "screen_ledger.json"))
    exc = {e["itemid"]: e["reason"] for e in led["excluded"]}
    out = {"keywords": {}, "unexplained": [], "named_cases": {}}
    for kw in KW:
        rows = all_rows(f'contentsitename:ECHR AND respondent:"FRA" AND {JUD} AND ("{kw}")')
        c = collections.Counter()
        for r in rows:
            apps = set((r.get("appno") or "").split(";"))
            if r["itemid"] in inc_ids or apps & inc_apps:
                c["included"] += 1
            elif r["itemid"] in exc:
                c["excluded_by_screen"] += 1
            elif not touches(r):
                c["outside_article_scope"] += 1
            else:
                c["unexplained"] += 1
                out["unexplained"].append({"kw": kw, "itemid": r["itemid"], "docname": r["docname"], "article": r.get("article")})
        out["keywords"][kw] = {"hits": len(rows), **c}
        print(kw, out["keywords"][kw], flush=True)
    for n, a in NAMED.items():
        out["named_cases"][n] = {"appno": a, "included": a in inc_apps or any(a in s for s in inc_apps)}
    dump(os.path.join(HD, "kwcheck.json"), out)
    print("unexplained", len(out["unexplained"]))


if __name__ == "__main__":
    main()
