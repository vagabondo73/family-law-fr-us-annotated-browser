"""Enumerate CJEU candidates (judgments CJ, orders CO) linked to the included EU family instruments and their
predecessors via Cellar: (i) case-law_interpretes_resource_legal (with article location), (ii) work_cites_work.
Output raw/int/cjeu/candidates.json.  Re-run: python3 scripts/int_cjeu_candidates.py"""
import os, sys, re, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from int_common import sparql, RAW, dump

ACTS = ["32019R1111", "32003R2201", "32000R1347", "32009R0004", "32010R1259", "32016R1103", "32016R1104", "32012R0650",
        "32016R1191", "32020R1784", "32007R1393", "32000R1348", "32020R1783", "32001R1206", "32012R1215", "32001R0044",
        "32004L0038", "32003L0086"]
X = "^^<http://www.w3.org/2001/XMLSchema#string>"


def main():
    out = collections.defaultdict(lambda: {"acts": {}, "via": set()})
    for a in ACTS:
        for prop, via in (("case-law_interpretes_resource_legal", "interpretes"), ("work_cites_work", "cites")):
            rows = sparql(f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX ann: <http://publications.europa.eu/ontology/annotation#>
SELECT DISTINCT ?cc ?loc WHERE {{ ?act cdm:resource_legal_id_celex "{a}"{X} . ?case cdm:{prop} ?act .
 ?case cdm:resource_legal_id_celex ?cc . FILTER(REGEX(STR(?cc), "^6[0-9]{{4}}C[JOAB]"))
 OPTIONAL {{ ?ax owl:annotatedSource ?case ; owl:annotatedProperty cdm:{prop} ; owl:annotatedTarget ?act ; ann:reference_to_modified_location ?loc }} }}""")
            for r in rows:
                cc = r["cc"]
                # map summaries/communications (CA/CB) to the judgment/order celex
                cc = re.sub(r"^(6\d{4})CA", r"\1CJ", cc)
                cc = re.sub(r"^(6\d{4})CB", r"\1CO", cc)
                d = out[cc]
                d["via"].add(via)
                locs = d["acts"].setdefault(a, [])
                if r.get("loc") and via == "interpretes" and r["loc"] not in locs:
                    locs.append(r["loc"])
            print(a, prop, len(rows), flush=True)
    # metadata
    cands = {}
    celexes = sorted(out)
    for i in range(0, len(celexes), 60):
        chunk = celexes[i:i + 60]
        vals = " ".join(f'"{c}"{X}' for c in chunk)
        rows = sparql(f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?cc ?date ?ecli ?title WHERE {{ VALUES ?cc {{ {vals} }} ?w cdm:resource_legal_id_celex ?cc .
 OPTIONAL {{ ?w cdm:work_date_document ?date }} OPTIONAL {{ ?w cdm:case-law_ecli ?ecli }}
 OPTIONAL {{ ?e cdm:expression_belongs_to_work ?w ; cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/FRA> ; cdm:expression_title ?title }} }}""")
        for r in rows:
            c = cands.setdefault(r["cc"], {"celex": r["cc"]})
            for k in ("date", "ecli", "title"):
                if r.get(k) and not c.get(k):
                    c[k] = r[k]
    res = []
    for cc in celexes:
        c = cands.get(cc, {"celex": cc})
        c["acts"] = out[cc]["acts"]
        c["via"] = sorted(out[cc]["via"])
        res.append(c)
    dump(os.path.join(RAW, "cjeu", "candidates.json"), res)
    print("candidates", len(res))


if __name__ == "__main__":
    main()
