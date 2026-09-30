"""Enumerate ECtHR candidate judgments from the HUDOC JSON query endpoint (metadata only).
Sets: (1) all judgments v. France on arts 8/12/14/P7-5; (2) Grand Chamber judgments (any respondent) on arts 8/12/14/P7-5;
(3) judgments (any respondent) mentioning the 1980 Hague Child Abduction Convention.
Output raw/int/hudoc/candidates_*.json.  Re-run: python3 scripts/int_hudoc_candidates.py"""
import json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, dump, UA

BASE = "https://hudoc.echr.coe.int/app/query/results"
SEL = "itemid,docname,appno,kpdate,article,conclusion,importance,languageisocode,doctype,ecli,documentcollectionid2,kpthesaurus,respondent,extractedappno,separateopinion"


def q(query, start=0, length=500):
    url = BASE + "?query=" + urllib.parse.quote(query, safe=':"()=') + "&select=" + SEL + "&sort=&start=%d&length=%d" % (start, length)
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            print("retry", i, e, flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError(url)


def all_rows(query):
    out, start = [], 0
    while True:
        d = q(query, start)
        rows = [r["columns"] for r in d["results"]]
        out += rows
        start += len(rows)
        print(query[:80], start, "/", d["resultcount"], flush=True)
        if not rows or start >= d["resultcount"]:
            break
        time.sleep(1)
    return out


JUD = '(doctype="HEJUD" OR doctype="HFJUD")'
SETS = {
    "fra": f'contentsitename:ECHR AND respondent:"FRA" AND {JUD}',
    "gc": f'contentsitename:ECHR AND documentcollectionid2:"GRANDCHAMBER" AND {JUD} AND (article:"8" OR article:"12" OR article:"14" OR article:"P7-5")',
    "hague": f'contentsitename:ECHR AND {JUD} AND ("Hague Convention" OR "Convention de La Haye") AND ("abduction" OR "enlèvement")',
}

if __name__ == "__main__":
    os.makedirs(os.path.join(RAW, "hudoc"), exist_ok=True)
    for k, query in SETS.items():
        rows = all_rows(query)
        dump(os.path.join(RAW, "hudoc", f"candidates_{k}.json"), rows)
        print(k, len(rows))
