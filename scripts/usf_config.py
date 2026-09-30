"""Configuration for the US-federal pipeline (usf_*): norm perimeter (SCOPE §4.2) and issue mapping.

USC entries: (title, section, subdivision-or-None, heading-override-or-None, issues, former_cites)
  subdivision uses uscode.house.gov anchor path, e.g. "a_5" for (a)(5), "g" for (g).
"""

ROOT = "/home/user/workspace/flb"
RAW = ROOT + "/raw/us"

# ---------------------------------------------------------------- USC
USC = []
def add(title, sec, sub=None, issues=(), former=(), heading=None, **kw):
    USC.append(dict(title=str(title), sec=str(sec), sub=sub, issues=list(issues), former=list(former), heading=heading, **kw))

add(1, 7, issues=["us.marriage.recognition"])
add(28, "1738A", issues=["us.jurisdiction.interstate-custody.pkpa"])
add(28, "1738B", issues=["us.support.interstate.ffccsoa"])
add(28, "1738C", issues=["us.marriage.recognition"])
add(28, 1781, issues=["us.international-procedure.evidence-service"])
add(28, 1782, issues=["us.international-procedure.evidence-service"])
for s, former in zip(range(9001, 9012), range(11601, 11612)):
    add(22, s, issues=["us.abduction.icara"], former=[f"42 U.S.C. {former}"])
for s in [14901, 14902, 14911, 14912, 14913, 14914, 14921, 14922, 14923, 14924, 14925,
          14931, 14932, 14941, 14942, 14943, 14944, 14951, 14952, 14953, 14954]:
    add(42, s, issues=["us.adoption.intercountry.iaa"])
add(18, 1204, issues=["us.abduction.criminal.ipkca"])
for s in [9101, 9102, 9103, 9111, 9112, 9113, 9114, 9121, 9122, 9123, 9124, 9125, 9141]:
    add(22, s, issues=["us.abduction.goldman-act"])
for s in ["651", "652", "653", "653a", "654", "654a", "654b", "655", "655a", "656", "657", "658a", "659",
          "659a", "660", "663", "664", "665", "666", "667", "668", "669", "669a", "669b"]:
    add(42, s, issues=["us.support.title-iv-d"])
# tax
add(26, 71, issues=["us.tax.alimony"], status="repealed — continues to govern divorce or separation instruments executed on or before Dec. 31, 2018 (and not modified after that date to adopt the repeal)", note="Repealed by Pub. L. 115-97, title I, §11051, Dec. 22, 2017, effective for instruments executed after Dec. 31, 2018; text shown is the 2017 edition of the Code (last text in force)", edition="2017")
add(26, 215, issues=["us.tax.alimony"], status="repealed — continues to govern divorce or separation instruments executed on or before Dec. 31, 2018 (and not modified after that date to adopt the repeal)", note="Repealed by Pub. L. 115-97, title I, §11051, Dec. 22, 2017, effective for instruments executed after Dec. 31, 2018; text shown is the 2017 edition of the Code (last text in force)", edition="2017")
add(26, 1041, issues=["us.tax.property-transfers"])
add(26, 152, "e", issues=["us.tax.dependency"])
add(26, 24, issues=["us.tax.dependency"])
add(26, 2056, issues=["us.tax.marital-deduction"])
add(26, "2056A", issues=["us.tax.marital-deduction"])
add(26, 2523, issues=["us.tax.marital-deduction"])
add(26, 6015, issues=["us.tax.innocent-spouse"])
add(26, 414, "p", issues=["us.pensions.qdro"])
add(29, 1056, "d", issues=["us.pensions.qdro"])
add(10, 1408, issues=["us.pensions.military"])
for sub in ["b", "c", "e", "f"]:
    add(42, 402, sub, issues=["us.pensions.social-security"])
add(42, 416, issues=["us.pensions.social-security"])
# bankruptcy
add(11, 101, "14A", issues=["us.bankruptcy.dso"])
add(11, 362, "b_2", issues=["us.bankruptcy.automatic-stay"])
add(11, 507, "a_1", issues=["us.bankruptcy.dso"])
add(11, 523, "a_5", issues=["us.bankruptcy.discharge"])
add(11, 523, "a_15", issues=["us.bankruptcy.discharge"])
# immigration / nationality
add(8, 1101, "b", issues=["us.immigration.family"])
add(8, 1151, "b_2", issues=["us.immigration.family"])
add(8, 1154, issues=["us.immigration.family"])
add(8, "1186a", issues=["us.immigration.family"])
add(8, 1401, issues=["us.nationality"])
add(8, 1409, issues=["us.nationality"])
add(8, 1431, issues=["us.nationality"])
add(8, 1433, issues=["us.nationality"])
# DV federal penal
add(18, 2261, issues=["us.domestic-violence.federal-crimes"])
add(18, "2261A", issues=["us.domestic-violence.federal-crimes"])
add(18, 2262, issues=["us.domestic-violence.federal-crimes"])
add(18, 2265, issues=["us.domestic-violence.protection-orders"])
add(18, 922, "g_8", issues=["us.domestic-violence.firearms"])
add(18, 922, "g_9", issues=["us.domestic-violence.firearms"])
add(18, 921, "a_33", issues=["us.domestic-violence.firearms"])  # definition used by 922(g)(9)

# ---------------------------------------------------------------- CFR (whole parts; sections enumerated from eCFR structure)
CFR_PARTS = [
    (22, "94", ["us.abduction.icara"]),
    (22, "96", ["us.adoption.intercountry.iaa"]),
    (22, "97", ["us.adoption.intercountry.iaa"]),
    (22, "98", ["us.adoption.intercountry.iaa"]),
    (22, "99", ["us.adoption.intercountry.iaa"]),
] + [(45, str(p), ["us.support.title-iv-d"]) for p in range(301, 311)]
CFR_SECTIONS = [  # individual sections
    (8, "204.2", ["us.immigration.family"]),
    (8, "204.3", ["us.adoption.intercountry.iaa", "us.immigration.family"]),
] + [(8, f"204.{n}", ["us.adoption.intercountry.iaa", "us.immigration.family"]) for n in range(300, 315)] \
  + [(8, f"216.{n}", ["us.immigration.family"]) for n in range(1, 7)]

# ---------------------------------------------------------------- judge-made rules (us-common)
RULES = [
 ("parental-rights", "Parental rights — fundamental liberty interest in the care, custody and control of children (substantive due process)", ["us.family-rights.parental-rights", "us.family-rights.third-party-visitation"], ["us-const-amend14-s1", "us-const-amend5"]),
 ("unwed-fathers", "Unwed fathers — constitutional protection depends on biological link plus developed parent-child relationship", ["us.family-rights.unwed-fathers"], ["us-const-amend14-s1"]),
 ("tpr-due-process", "Termination of parental rights — procedural due process (clear and convincing evidence; counsel case-by-case; access to appeal)", ["us.family-rights.tpr-procedure"], ["us-const-amend14-s1"]),
 ("family-integrity", "Family integrity and familial association (extended family; foster families; state intervention)", ["us.family-rights.family-integrity"], ["us-const-amend14-s1"]),
 ("marriage-fundamental-right", "Marriage as a fundamental right (due process and equal protection)", ["us.family-rights.marriage-right", "us.family-rights.same-sex-marriage"], ["us-const-amend14-s1"]),
 ("nonmarital-children-ep", "Equal protection — classifications based on nonmarital birth (intermediate scrutiny)", ["us.family-rights.nonmarital-children"], ["us-const-amend14-s1", "us-const-amend5"]),
 ("sex-classifications-family", "Equal protection — sex-based classifications in alimony, support, benefits and citizenship transmission", ["us.family-rights.sex-classifications"], ["us-const-amend14-s1", "us-const-amend5"]),
 ("race-custody", "Race may not be a decisive factor in custody determinations", ["us.family-rights.race-custody"], ["us-const-amend14-s1"]),
 ("access-to-divorce", "Access to divorce and family courts — fees, transcripts, durational residency requirements", ["us.family-rights.access-to-courts"], ["us-const-amend14-s1"]),
 ("personal-jurisdiction-family", "Personal jurisdiction over nonresident family members (minimum contacts; Kulko)", ["us.jurisdiction.personal-jurisdiction"], ["us-const-amend14-s1"]),
 ("divisible-divorce-ffc", "Full faith and credit to divorce decrees; domicile; divisible divorce (status vs. support/property)", ["us.jurisdiction.divisible-divorce", "us.jurisdiction.full-faith-credit"], ["us-const-art4-s1"]),
 ("domestic-relations-exception", "Domestic-relations exception to federal diversity jurisdiction (divorce, alimony, child custody decrees)", ["us.jurisdiction.domestic-relations-exception", "us.jurisdiction.probate-exception"], []),
 ("rooker-feldman", "Rooker-Feldman doctrine — no lower-federal-court review of state-court judgments (family litigation)", ["us.jurisdiction.rooker-feldman"], []),
 ("younger-abstention-family", "Younger abstention in pending state family and child-welfare proceedings", ["us.jurisdiction.younger-abstention"], []),
 ("icara-habitual-residence", "Hague 1980 — habitual residence: totality-of-the-circumstances, fact-driven inquiry (Monasky)", ["us.abduction.icara.habitual-residence"], ["us-usc-22-9003"]),
 ("icara-grave-risk-ameliorative", "Hague 1980 — grave risk (art. 13(1)(b)): ameliorative measures discretionary, not mandatory (Golan)", ["us.abduction.icara.grave-risk"], ["us-usc-22-9003"]),
 ("icara-well-settled", "Hague 1980 — art. 12 one-year period not subject to equitable tolling; 'well settled' exception (Lozano)", ["us.abduction.icara.well-settled"], ["us-usc-22-9003"]),
 ("icara-rights-of-custody", "Hague 1980 — ne exeat right is a 'right of custody' (Abbott)", ["us.abduction.icara.rights-of-custody"], ["us-usc-22-9003"]),
 ("icara-mootness", "Hague 1980 — return of child abroad does not moot appeal (Chafin)", ["us.abduction.icara.appeal-mootness"], ["us-usc-22-9003"]),
 ("federal-preemption-family-property", "Federal benefits law preempts contrary state community-property / family-law allocation", ["us.pensions.federal-benefits-preemption", "us.constitution.preemption"], ["us-const-art6-cl2"]),
 ("civil-contempt-support", "Civil contempt for nonpayment of support — due process safeguards; civil vs. criminal contempt", ["us.support.contempt"], ["us-const-amend14-s1"]),
]
