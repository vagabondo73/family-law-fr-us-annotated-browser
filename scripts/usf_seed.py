#!/usr/bin/env python3
"""Seed list of leading U.S. Supreme Court family-law decisions (guarantees inclusion in screening even when the regex
enumeration misses them, e.g. because the doctrine's later name does not appear in the founding case).
Vol <= 572: text from CAP static; later volumes: supremecourt.gov slip-opinion PDF (official) -> raw/us/cl_hits/."""
import json, os, re, sys, subprocess, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import RAW
from usf_text import cap_meta, http
from usf_patterns import match_groups

SEEDS = [
 ("62 U.S. 582", ["domestic-relations-exception"]), ("136 U.S. 586", ["domestic-relations-exception"]),
 ("280 U.S. 379", ["domestic-relations-exception"]), ("504 U.S. 689", ["domestic-relations-exception"]),
 ("547 U.S. 293", ["domestic-relations-exception"]), ("125 U.S. 190", ["marriage-right"]),
 ("262 U.S. 390", ["parental-rights"]), ("268 U.S. 510", ["parental-rights"]), ("321 U.S. 158", ["parental-rights"]),
 ("405 U.S. 645", ["parental-rights"]), ("406 U.S. 205", ["parental-rights"]), ("431 U.S. 494", ["parental-rights"]),
 ("431 U.S. 816", ["parental-rights"]), ("434 U.S. 246", ["parental-rights"]), ("441 U.S. 380", ["parental-rights", "sex-classifications-family"]),
 ("442 U.S. 584", ["parental-rights"]), ("452 U.S. 18", ["parental-rights"]), ("455 U.S. 745", ["parental-rights"]),
 ("463 U.S. 248", ["parental-rights"]), ("466 U.S. 429", ["parental-rights"]), ("491 U.S. 110", ["parental-rights"]),
 ("519 U.S. 102", ["access-divorce", "parental-rights"]), ("530 U.S. 57", ["parental-rights"]), ("489 U.S. 189", ["parental-rights"]),
 ("545 U.S. 748", ["parental-rights", "dv-federal"]), ("388 U.S. 1", ["marriage-right"]), ("381 U.S. 479", ["marriage-right"]),
 ("401 U.S. 371", ["access-divorce"]), ("419 U.S. 393", ["access-divorce"]), ("434 U.S. 374", ["marriage-right"]),
 ("482 U.S. 78", ["marriage-right"]), ("570 U.S. 744", ["doma", "marriage-right"]),
 ("391 U.S. 68", ["nonmarital-children-ep"]), ("391 U.S. 73", ["nonmarital-children-ep"]), ("406 U.S. 164", ["nonmarital-children-ep"]),
 ("409 U.S. 535", ["nonmarital-children-ep"]), ("430 U.S. 762", ["nonmarital-children-ep"]), ("439 U.S. 259", ["nonmarital-children-ep"]),
 ("456 U.S. 91", ["nonmarital-children-ep"]), ("462 U.S. 1", ["nonmarital-children-ep"]), ("486 U.S. 456", ["nonmarital-children-ep"]),
 ("452 U.S. 1", ["nonmarital-children-ep", "parental-rights"]), ("427 U.S. 495", ["nonmarital-children-ep", "social-security-spouse"]),
 ("421 U.S. 7", ["sex-classifications-family"]), ("440 U.S. 268", ["sex-classifications-family"]), ("450 U.S. 455", ["sex-classifications-family"]),
 ("430 U.S. 199", ["sex-classifications-family", "social-security-spouse"]), ("420 U.S. 636", ["sex-classifications-family", "social-security-spouse"]),
 ("533 U.S. 53", ["nationality", "sex-classifications-family"]), ("523 U.S. 420", ["nationality", "sex-classifications-family"]),
 ("430 U.S. 787", ["imm-family", "nonmarital-children-ep"]), ("566 U.S. 541", ["social-security-spouse"]),
 ("317 U.S. 287", ["ffc-judgments-family"]), ("325 U.S. 226", ["ffc-judgments-family"]), ("334 U.S. 541", ["ffc-judgments-family"]),
 ("334 U.S. 343", ["ffc-judgments-family"]), ("334 U.S. 378", ["ffc-judgments-family"]), ("340 U.S. 581", ["ffc-judgments-family"]),
 ("354 U.S. 416", ["ffc-judgments-family"]), ("345 U.S. 528", ["ffc-judgments-family", "pj-family"]), ("356 U.S. 604", ["ffc-judgments-family"]),
 ("371 U.S. 187", ["ffc-judgments-family"]), ("330 U.S. 610", ["ffc-judgments-family"]), ("218 U.S. 1", ["ffc-judgments-family"]),
 ("436 U.S. 84", ["pj-family"]), ("495 U.S. 604", ["pj-family"]), ("484 U.S. 174", ["pkpa"]),
 ("263 U.S. 413", ["rooker-feldman-family"]), ("460 U.S. 462", ["rooker-feldman-family"]), ("544 U.S. 280", ["rooker-feldman-family"]),
 ("546 U.S. 459", ["rooker-feldman-family"]), ("401 U.S. 37", ["younger-family"]), ("442 U.S. 415", ["younger-family"]),
 ("571 U.S. 69", ["younger-family"]), ("560 U.S. 1", ["icara"]), ("572 U.S. 1", ["icara"]), ("568 U.S. 165", ["icara"]),
 ("486 U.S. 694", ["evidence-service"]), ("482 U.S. 522", ["evidence-service"]), ("542 U.S. 241", ["evidence-service"]),
 ("520 U.S. 329", ["title-iv-d"]), ("564 U.S. 431", ["contempt-support"]), ("485 U.S. 624", ["contempt-support"]),
 ("481 U.S. 619", ["federal-preemption-family"]), ("475 U.S. 851", ["title-iv-d"]), ("520 U.S. 833", ["qdro", "federal-preemption-family"]),
 ("532 U.S. 141", ["qdro", "federal-preemption-family"]), ("555 U.S. 285", ["qdro"]), ("490 U.S. 581", ["usfspa"]),
 ("453 U.S. 210", ["federal-preemption-family"]), ("439 U.S. 572", ["federal-preemption-family"]), ("454 U.S. 46", ["federal-preemption-family"]),
 ("569 U.S. 483", ["federal-preemption-family"]), ("339 U.S. 655", ["federal-preemption-family"]), ("369 U.S. 663", ["federal-preemption-family"]),
 ("520 U.S. 93", ["tax-marital-deduction"]), ("555 U.S. 415", ["dv-firearms"]), ("572 U.S. 157", ["dv-firearms"]),
 ("542 U.S. 1", ["domestic-relations-exception", "parental-rights"]),
]
PDF = [  # (name, date, U.S. cite or None, docket, official PDF, groups)
 ("Obergefell v. Hodges", "2015-06-26", "576 U.S. 644", "14-556", "https://www.supremecourt.gov/opinions/14pdf/14-556_3204.pdf", ["marriage-right"]),
 ("Pavan v. Smith", "2017-06-26", "582 U.S. 563", "16-992", "https://www.supremecourt.gov/opinions/16pdf/16-992_868c.pdf", ["marriage-right"]),
 ("Howell v. Howell", "2017-05-15", "581 U.S. 214", "15-1031", "https://www.supremecourt.gov/opinions/16pdf/15-1031_hejm.pdf", ["usfspa", "federal-preemption-family"]),
 ("Water Splash, Inc. v. Menon", "2017-05-22", "581 U.S. 271", "16-254", "https://www.supremecourt.gov/opinions/16pdf/16-254_5iel.pdf", ["evidence-service"]),
 ("Monasky v. Taglieri", "2020-02-25", "589 U.S. 68", "18-935", "https://www.supremecourt.gov/opinions/19pdf/18-935_new_fd9g.pdf", ["icara"]),
 ("Golan v. Saada", "2022-06-15", "596 U.S. 666", "20-1034", "https://www.supremecourt.gov/opinions/21pdf/20-1034_b8dg.pdf", ["icara"]),
 ("ZF Automotive US, Inc. v. Luxshare, Ltd.", "2022-06-13", "596 U.S. 619", "21-401", "https://www.supremecourt.gov/opinions/21pdf/21-401_2cp3.pdf", ["evidence-service"]),
 ("Boechler, P.C. v. Commissioner", "2022-04-21", "596 U.S. 199", "20-1472", "https://www.supremecourt.gov/opinions/21pdf/20-1472_6j37.pdf", ["tax-6015"]),
 ("United States v. Rahimi", "2024-06-21", "602 U.S. 680", "22-915", "https://www.supremecourt.gov/opinions/23pdf/22-915_8o6b.pdf", ["dv-firearms"]),
 ("Department of State v. Muñoz", "2024-06-21", "602 U.S. 899", "23-334", "https://www.supremecourt.gov/opinions/23pdf/23-334_e18f.pdf", ["imm-family", "marriage-right"]),
]


def cap_case(cite):
    vol, _, page = cite.split()
    for c in cap_meta("us", vol):
        if str(c.get("first_page")) == page:
            return c, f"https://static.case.law/us/{vol}/cases/{c['file_name']}.json"
    return None, None


def main():
    hd = RAW + "/cap_hits"; cl = RAW + "/cl_hits"; os.makedirs(cl, exist_ok=True)
    miss = []
    for cite, groups in SEEDS:
        c, url = cap_case(cite)
        if not c:
            miss.append(cite); continue
        fn = f"{hd}/us-{cite.split()[0]}-{c['file_name']}.json"
        if os.path.exists(fn):
            r = json.load(open(fn))
            for g in groups:
                r["groups"].setdefault(g, [])
            r["seed"] = True
            json.dump(r, open(fn, "w")); continue
        d = json.loads(http(url)); ops = d["casebody"]["opinions"]
        text = "\n\n".join(f"[[OPINION type={o.get('type')} author={o.get('author')}]]\n{o.get('text','')}" for o in ops)
        g = match_groups(text)
        for x in groups:
            g.setdefault(x, [])
        rec = {"cap_id": d["id"], "name": d.get("name_abbreviation"), "name_full": d.get("name"), "date": d.get("decision_date"),
               "docket": d.get("docket_number"), "citations": [x["cite"] for x in d.get("citations", [])],
               "court": d["court"]["name"], "rep": "us", "vol": int(cite.split()[0]), "file": d["file_name"], "cap_url": url,
               "groups": g, "head_matter": d["casebody"].get("head_matter", ""), "text": text, "seed": True}
        json.dump(rec, open(fn, "w"))
    for name, date, cite, dk, pdf, groups in PDF:
        fn = f"{cl}/scotus-{dk}.json"
        if os.path.exists(fn):
            continue
        p = "/tmp/usf_seed.pdf"
        try:
            open(p, "wb").write(http(pdf, 120))
        except Exception as e:
            miss.append(f"{name} {pdf} {e}"); continue
        text = subprocess.run(["pdftotext", p, "-"], capture_output=True, text=True).stdout
        g = match_groups(text)
        for x in groups:
            g.setdefault(x, [])
        json.dump({"name": name, "date": date, "docket": dk, "citations": [cite] if cite else [], "court": "Supreme Court of the United States",
                   "pdf_url": pdf, "groups": g, "head_matter": "", "text": text, "seed": True}, open(fn, "w"))
    print("missing", miss)


if __name__ == "__main__":
    main()
