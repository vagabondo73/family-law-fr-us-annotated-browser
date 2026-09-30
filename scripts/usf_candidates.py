#!/usr/bin/env python3
"""Enumerate candidate opinions (SCOTUS + CA8, precedential) from CourtListener REST v4 search (anonymous).
Output: raw/us/candidates.json  {cluster_id: {meta..., hits:[query-keys]}}  (checkpointed per query in raw/us/cl_queries/)
Be polite: <=1 req/s.
"""
import json, os, sys, time, urllib.parse, urllib.request, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW

QDIR = RAW + "/cl_queries"; os.makedirs(QDIR, exist_ok=True)
REFRESH = "--refresh" in sys.argv


def cite(t, s):
    return f'("{t} U.S.C. § {s}" OR "{t} U.S.C. {s}" OR "{t} U.S.C. §{s}" OR "{t} U.S.C. §§ {s}")'


Q = {}
# group key -> list of queries.  group keys are used later to link candidates to norms.
Q["icara"] = ['"International Child Abduction Remedies Act"', '"Hague Convention" AND (abduction OR "wrongfully removed" OR "wrongful removal" OR "wrongful retention")',
              cite(42, 11601), cite(42, 11603), cite(42, 11604), cite(42, 11607), cite(22, 9003), cite(22, 9001), cite(22, 9007), '"ICARA"']
Q["pkpa"] = ['"Parental Kidnaping Prevention Act"', '"Parental Kidnapping Prevention Act"', '"1738A"']
Q["ffccsoa"] = ['"1738B"', '"Full Faith and Credit for Child Support Orders"']
Q["doma"] = ['"1738C"', '"Defense of Marriage Act"', '"Respect for Marriage Act"', cite(1, 7)]
Q["evidence-service"] = ['"1782"', '"1781"', '"Hague Service Convention"', '"Hague Evidence Convention"']
Q["iaa"] = ['"Intercountry Adoption Act"', cite(42, 14901), cite(42, 14952), cite(42, 14954), '"Hague Adoption Convention"']
Q["ipkca"] = ['"International Parental Kidnapping Crime Act"', '"International Parental Kidnaping Crime Act"', cite(18, 1204)]
Q["goldman"] = ['"Goldman International Child Abduction"', cite(22, 9101), cite(22, 9111)]
Q["title-iv-d"] = ['"Title IV-D"', '"IV-D"'] + [cite(42, s) for s in ["651", "652", "653", "653a", "654", "654a", "654b", "655", "656", "657", "658a", "659", "659a", "660", "663", "664", "665", "666", "667", "668", "669", "669b"]] + ['"Child Support Recovery Act"', '"Deadbeat Parents Punishment Act"']
Q["tax-alimony"] = ['alimony AND ("section 71" OR "§ 71(" OR "section 215" OR "§ 215")', '"26 U.S.C. § 71"', '"26 U.S.C. § 215"']
Q["tax-1041"] = ['"1041" AND (spouse OR divorce)']
Q["tax-dependency"] = ['"152(e)"', 'dependency exemption AND divorce', '"child tax credit"']
Q["tax-marital-deduction"] = ['"marital deduction"', '"2056"', '"2523"', '"2056A"', '"qualified domestic trust"']
Q["tax-6015"] = ['"6015"', '"innocent spouse"']
Q["qdro"] = ['"qualified domestic relations order"', '"QDRO"', '"1056(d)"', '"414(p)"']
Q["usfspa"] = ['"Uniformed Services Former Spouses"', cite(10, 1408)]
Q["social-security-spouse"] = [cite(42, 402) + ' AND (wife OR husband OR spouse OR widow OR widower OR divorced)', cite(42, 416) + ' AND (wife OR husband OR spouse OR widow OR child)', '"divorced wife"', '"surviving divorced"']
Q["bankruptcy-dso"] = ['"523(a)(5)"', '"523(a)(15)"', '"domestic support obligation"', '"362(b)(2)"', '"507(a)(1)"', '"101(14A)"', '"523(a)(5)(B)"']
Q["imm-family"] = ['"1186a"', '"1154(c)"', '"1154(a)"', '"1101(b)(1)"', '"1101(b)(2)"', '"1151(b)(2)"', '"immediate relative" AND (spouse OR child OR marriage)', '"sham marriage"', '"conditional permanent resident"', '"marriage fraud"']
Q["nationality"] = [cite(8, 1401), cite(8, 1409), cite(8, 1431), cite(8, 1433), '"Child Citizenship Act"', '"1401(a)(7)"', '"1409(a)"']
Q["dv-federal"] = [cite(18, 2261), cite(18, "2261A"), cite(18, 2262), cite(18, 2265), '"interstate domestic violence"', '"interstate stalking"', '"2261A"']
Q["dv-firearms"] = ['"922(g)(8)"', '"922(g)(9)"', '"921(a)(33)"', '"misdemeanor crime of domestic violence"']
Q["domestic-relations-exception"] = ['"domestic relations exception"', '"domestic-relations exception"', 'Ankenbrandt', '"Barber v. Barber"', '"In re Burrus"']
Q["rooker-feldman-family"] = ['"Rooker-Feldman" AND (custody OR divorce OR "child support" OR "parental rights" OR adoption OR dissolution)']
Q["younger-family"] = ['Younger AND abstention AND (custody OR divorce OR "child support" OR "parental rights" OR "juvenile court")', '"Moore v. Sims"']
Q["parental-rights"] = ['"parental rights" AND "due process"', '"Troxel v. Granville"', '"Santosky v. Kramer"', '"Stanley v. Illinois"', '"Meyer v. Nebraska"', '"Pierce v. Society of Sisters"', '"Lehr v. Robertson"', '"Quilloin v. Walcott"', '"Lassiter v. Department of Social Services"', '"familial association"']
Q["marriage-right"] = ['"right to marry"', '"Loving v. Virginia"', '"Zablocki v. Redhail"', '"Obergefell"', '"same-sex marriage"']
Q["pj-family"] = ['"Kulko"', '"May v. Anderson"']
Q["ffc-judgments-family"] = ['"full faith and credit" AND (divorce OR custody OR adoption OR alimony OR "child support")', '"Williams v. North Carolina"', '"Estin v. Estin"', '"Sherrer v. Sherrer"']
Q["federal-preemption-family"] = ['"community property" AND preempt*', '"Hisquierdo"', '"McCarty v. McCarty"', '"Hillman v. Maretta"', '"Egelhoff"', '"Boggs v. Boggs"', '"Ridgway v. Ridgway"']
Q["nonmarital-children-ep"] = ['illegitimate AND "equal protection"', '"nonmarital children"', '"Trimble v. Gordon"', '"Clark v. Jeter"']
Q["contempt-support"] = ['"Turner v. Rogers"', '"Hicks v. Feiock"', '"civil contempt" AND "child support"']
Q["access-divorce"] = ['"Boddie v. Connecticut"', '"Sosna v. Iowa"', '"M.L.B. v. S.L.J."']

COURTS = ["scotus ca8"]  # one combined query per search string
INCOMPLETE = []
BASE = "https://www.courtlistener.com/api/rest/v4/search/"


def fetch(url):
    for a in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "flb-research (family law annotated browser)"})
            r = urllib.request.urlopen(req, timeout=60)
            return json.loads(r.read())
        except urllib.error.HTTPError as e:
            ra = e.headers.get("Retry-After") if e.headers else None
            wait = int(ra) + 2 if ra and ra.isdigit() else (60 * (a + 1) if e.code == 429 else 5)
            print("HTTP", e.code, "wait", wait, flush=True); time.sleep(wait)
        except Exception as e:
            print("ERR", e, flush=True); time.sleep(5)
    return None


def run_query(court, q):
    h = hashlib.sha1(f"{court}|{q}".encode()).hexdigest()[:16]
    fn = f"{QDIR}/{court.replace(' ', '+')}-{h}.json"
    if os.path.exists(fn) and not REFRESH:
        return json.load(open(fn))["results"]
    url = BASE + "?" + urllib.parse.urlencode({"type": "o", "court": court, "q": q, "stat_Precedential": "on", "order_by": "dateFiled desc"})
    res = []
    pages = 0
    while url and pages < 40:
        d = fetch(url); pages += 1
        time.sleep(3.0)
        if not d:
            print("INCOMPLETE (not cached)", court, q[:60], flush=True)
            INCOMPLETE.append(q)
            return res
        for r in d.get("results", []):
            res.append({k: r.get(k) for k in ["cluster_id", "caseName", "caseNameFull", "citation", "dateFiled", "docketNumber",
                                             "absolute_url", "status", "court_id", "citeCount"]} |
                       {"download_urls": [o.get("download_url") for o in r.get("opinions", []) if o.get("download_url")],
                        "snippet": " ".join((o.get("snippet") or "") for o in r.get("opinions", []))[:800]})
        url = d.get("next")
    json.dump({"court": court, "q": q, "count": len(res), "results": res}, open(fn, "w"), indent=1)
    print(court, q[:70], len(res), flush=True)
    return res


def main():
    cands = {}
    for g, qs in Q.items():
        for q in qs:
            for court in COURTS:
                for r in run_query(court, q):
                    if r.get("status") not in (None, "Published", "Precedential"):
                        continue
                    c = cands.setdefault(str(r["cluster_id"]), dict(r, groups=[], queries=[]))
                    if g not in c["groups"]:
                        c["groups"].append(g)
                    c["queries"].append(q)
    json.dump(cands, open(RAW + "/candidates.json", "w"), indent=1)
    json.dump(INCOMPLETE, open(RAW + "/cl_incomplete.json", "w"), indent=1)
    from collections import Counter
    print("candidates", len(cands), Counter(c["court_id"] for c in cands.values()))


if __name__ == "__main__":
    main()
