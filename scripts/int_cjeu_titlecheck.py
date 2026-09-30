"""OPTIONAL / SLOW (full-text title scan on Cellar; may exceed the SPARQL endpoint limits — first attempt 2026-09-30 did not return within 5 min). Completeness cross-check: CJEU works whose title mentions an included regulation number but which are not in candidates.json.
Re-run: python3 scripts/int_cjeu_titlecheck.py  (writes raw/int/cjeu/titlecheck.json)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from int_common import sparql, RAW, dump
NUMS = ["2201/2003", "2019/1111", "1347/2000", "4/2009", "650/2012", "1259/2010", "2016/1103", "2016/1104", "2003/86", "1393/2007", "2020/1784", "1206/2001", "2020/1783", "2016/1191"]
out = {}
cands = {x["celex"] for x in json.load(open(os.path.join(RAW, "cjeu", "candidates.json")))}
for n in NUMS:
    q = '''PREFIX cdm:<http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?celex WHERE { ?e cdm:expression_title ?t . FILTER(CONTAINS(STR(?t),"%s")) ?e cdm:expression_belongs_to_work ?w . ?w cdm:resource_legal_id_celex ?celex . FILTER(REGEX(STR(?celex),"^6[0-9]{4}C[JO]")) }''' % n
    try:
        r = sparql(q)
        s = sorted({x["celex"] for x in r})
        out[n] = {"found": len(s), "missing_from_candidates": [c for c in s if c not in cands]}
    except Exception as e:
        out[n] = {"error": str(e)}
    print(n, out[n] if "error" in out[n] else (out[n]["found"], out[n]["missing_from_candidates"]), flush=True)
dump(os.path.join(RAW, "cjeu", "titlecheck.json"), out)
