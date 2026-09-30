#!/usr/bin/env python3
"""Write data/issues/us.json (English issue tree for the U.S. federal side)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from usf_config import ROOT

T = [
 ("us.constitution", "U.S. Constitution — structural provisions", [
   ("us.constitution.due-process", "Due process (Fifth / Fourteenth Amendments)"),
   ("us.constitution.equal-protection", "Equal protection (incl. Fifth Amendment equal-protection component)"),
   ("us.constitution.federalism", "Federalism; Spending Clause conditions (Title IV-D)"),
   ("us.constitution.treaties", "Treaties: Treaty Clause, self-execution, Supremacy"),
   ("us.constitution.preemption", "Federal preemption of state family law")]),
 ("us.family-rights", "Constitutional family rights (judge-made doctrine)", [
   ("us.family-rights.parental-rights", "Parental rights — substantive due process (care, custody and control)"),
   ("us.family-rights.unwed-fathers", "Unwed fathers — biological link and developed relationship"),
   ("us.family-rights.tpr-procedure", "Termination of parental rights & child-welfare proceedings — procedural due process"),
   ("us.family-rights.third-party-visitation", "Grandparent / third-party visitation"),
   ("us.family-rights.family-integrity", "Family integrity, extended family & familial association"),
   ("us.family-rights.marriage-right", "Marriage as a fundamental right"),
   ("us.family-rights.same-sex-marriage", "Same-sex marriage and equal recognition"),
   ("us.family-rights.nonmarital-children", "Classifications based on nonmarital birth (illegitimacy)"),
   ("us.family-rights.sex-classifications", "Sex-based classifications in family, support and benefits law"),
   ("us.family-rights.race-custody", "Race and custody determinations"),
   ("us.family-rights.access-to-courts", "Access to divorce and family courts (fees, transcripts, residency)"),
   ("us.family-rights.immigration-family", "Family rights in immigration and nationality law")]),
 ("us.marriage", "Marriage — federal law", [
   ("us.marriage.recognition", "Federal definition and interstate recognition of marriage (1 U.S.C. 7; 28 U.S.C. 1738C)")]),
 ("us.jurisdiction", "Jurisdiction, recognition and federal courts in family matters", [
   ("us.jurisdiction.full-faith-credit", "Full faith and credit — divorce, custody, adoption, support judgments"),
   ("us.jurisdiction.divisible-divorce", "Divisible divorce; ex parte divorce and domicile"),
   ("us.jurisdiction.personal-jurisdiction", "Personal jurisdiction over nonresident parents/spouses (Kulko)"),
   ("us.jurisdiction.domestic-relations-exception", "Domestic-relations exception to federal jurisdiction"),
   ("us.jurisdiction.probate-exception", "Probate exception (related)"),
   ("us.jurisdiction.rooker-feldman", "Rooker-Feldman doctrine in family litigation"),
   ("us.jurisdiction.younger-abstention", "Younger abstention and other abstention in family cases"),
   ("us.jurisdiction.interstate-custody", "Interstate custody jurisdiction", [
     ("us.jurisdiction.interstate-custody.pkpa", "Parental Kidnaping Prevention Act (28 U.S.C. 1738A)")])]),
 ("us.abduction", "International child abduction", [
   ("us.abduction.icara", "Hague 1980 Convention / ICARA (22 U.S.C. 9001 ff.)", [
     ("us.abduction.icara.habitual-residence", "Habitual residence"),
     ("us.abduction.icara.rights-of-custody", "Rights of custody, ne exeat rights, exercise of custody"),
     ("us.abduction.icara.wrongful-removal", "Wrongful removal or retention; date of retention"),
     ("us.abduction.icara.grave-risk", "Grave risk of harm / intolerable situation (art. 13(1)(b)); ameliorative measures"),
     ("us.abduction.icara.well-settled", "One-year period and 'well settled' exception (art. 12)"),
     ("us.abduction.icara.consent-acquiescence", "Consent and acquiescence (art. 13(1)(a))"),
     ("us.abduction.icara.child-objection", "Child's objection / age and maturity (art. 13)"),
     ("us.abduction.icara.human-rights", "Fundamental principles / human rights (art. 20)"),
     ("us.abduction.icara.procedure", "Procedure: jurisdiction, burdens of proof, evidence, provisional remedies, abstention"),
     ("us.abduction.icara.fees", "Costs and fees (22 U.S.C. 9007)"),
     ("us.abduction.icara.appeal-mootness", "Appeals, stays and mootness after return"),
     ("us.abduction.icara.access", "Access (visitation) rights under art. 21")]),
   ("us.abduction.criminal", "Criminal law of international parental kidnapping", [
     ("us.abduction.criminal.ipkca", "International Parental Kidnapping Crime Act (18 U.S.C. 1204)")]),
   ("us.abduction.goldman-act", "Goldman Act — diplomatic measures (22 U.S.C. 9101 ff.)")]),
 ("us.adoption", "Adoption — federal", [
   ("us.adoption.intercountry", "Intercountry adoption", [
     ("us.adoption.intercountry.iaa", "Intercountry Adoption Act & Hague 1993 (42 U.S.C. 14901 ff.; 22 CFR 96–99)")])]),
 ("us.support", "Child and spousal support — federal", [
   ("us.support.title-iv-d", "Title IV-D child support program (42 U.S.C. 651–669b; 45 CFR 301–310)"),
   ("us.support.interstate", "Interstate and international support", [
     ("us.support.interstate.ffccsoa", "Full Faith and Credit for Child Support Orders Act (28 U.S.C. 1738B)")]),
   ("us.support.contempt", "Enforcement by contempt — due process")]),
 ("us.tax", "Federal tax aspects of family law", [
   ("us.tax.alimony", "Alimony and separate maintenance (26 U.S.C. 71, 215 — pre-2019 instruments)"),
   ("us.tax.property-transfers", "Transfers between spouses / incident to divorce (26 U.S.C. 1041)"),
   ("us.tax.dependency", "Dependency and child tax credit for divorced parents (26 U.S.C. 152(e), 24)"),
   ("us.tax.marital-deduction", "Estate and gift tax marital deduction; QDOT"),
   ("us.tax.innocent-spouse", "Innocent-spouse relief (26 U.S.C. 6015)")]),
 ("us.pensions", "Pensions and federal benefits on divorce", [
   ("us.pensions.qdro", "ERISA anti-alienation & qualified domestic relations orders"),
   ("us.pensions.military", "Uniformed Services Former Spouses' Protection Act (10 U.S.C. 1408)"),
   ("us.pensions.social-security", "Social Security spousal, divorced-spouse and child benefits"),
   ("us.pensions.federal-benefits-preemption", "Preemption of state family law by federal benefit statutes")]),
 ("us.bankruptcy", "Bankruptcy and family obligations", [
   ("us.bankruptcy.dso", "Domestic support obligations — definition and priority"),
   ("us.bankruptcy.discharge", "Nondischargeability (11 U.S.C. 523(a)(5), (a)(15))"),
   ("us.bankruptcy.automatic-stay", "Automatic stay exceptions for family proceedings (362(b)(2))")]),
 ("us.immigration", "Immigration — family-based", [
   ("us.immigration.family", "Family-based immigration: spouses, children, adoption, conditional residence, marriage fraud")]),
 ("us.nationality", "Nationality — acquisition by birth abroad and derivation"),
 ("us.domestic-violence", "Domestic violence — federal", [
   ("us.domestic-violence.federal-crimes", "Interstate domestic violence, stalking, protection-order violations"),
   ("us.domestic-violence.protection-orders", "Full faith and credit to protection orders (18 U.S.C. 2265)"),
   ("us.domestic-violence.firearms", "Firearms prohibitions (18 U.S.C. 922(g)(8), (g)(9); 921(a)(33))")]),
 ("us.international-procedure", "International civil procedure", [
   ("us.international-procedure.evidence-service", "Hague Service & Evidence Conventions; 28 U.S.C. 1781–1782")]),
]


def node(t):
    nid, label = t[0], t[1]
    kids = t[2] if len(t) > 2 else []
    return {"id": nid, "label": label, "children": [node(k) for k in kids]}


def all_ids():
    out = []
    def walk(n):
        out.append(n["id"]); [walk(c) for c in n["children"]]
    for t in T:
        walk(node(t))
    return out


if __name__ == "__main__":
    json.dump({"side": "us", "lang": "en", "nodes": [node(t) for t in T]}, open(ROOT + "/data/issues/us.json", "w"), indent=2)
    print(len(all_ids()))
