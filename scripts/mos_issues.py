#!/usr/bin/env python3
"""Missouri issue tree (data/issues/mo.json) + deterministic issue assignment for RSMo, Constitution and Rules.
Run directly to (re)write data/issues/mo.json."""
import os, re, json

T = [
    ("mo.constitution", "Missouri Constitution", [
        ("equal-rights", "Natural rights, equality under the law"), ("due-process", "Due process of law"),
        ("marriage", "Marriage definition (art. I § 33) and Obergefell"), ("rulemaking", "Supreme Court rulemaking power")]),
    ("mo.marriage", "Marriage", [
        ("formation", "Nature of marriage; solemnization and officiants"), ("license", "Marriage license, recording, fees"),
        ("validity", "Prohibited, void and bigamous marriages; same-sex marriage policy"),
        ("records", "Marriage records and certificates"), ("children-legitimation", "Children born before marriage"),
        ("marital-agreements", "Marriage contracts / antenuptial agreements (form, recording, notice)"),
        ("spousal-property", "Property rights of married persons; separate property; tenancy by the entirety"),
        ("agreement-enforceability", "Validity and enforceability of antenuptial and postnuptial agreements (judge-made)")]),
    ("mo.dissolution", "Dissolution of marriage and legal separation", [
        ("grounds-procedure", "Grounds, petition, venue, residence, irretrievable breakdown"),
        ("temporary-orders", "Temporary orders, restraining orders, insurance"),
        ("separation-agreements", "Separation agreements and unconscionability review (452.325)"),
        ("property-division", "Division of marital property and debts; separate property"),
        ("transmutation-commingling", "Transmutation, commingling, source-of-funds rule (judge-made)"),
        ("maintenance", "Maintenance (spousal support) and alimony"),
        ("attorney-fees", "Costs and attorney's fees"),
        ("judgment", "Judgment of dissolution/legal separation; name; effect; enforcement of decree"),
        ("modification", "Modification of maintenance and support"),
        ("older-provisions", "Older separate-maintenance / married persons' provisions (452.025–452.250)"),
        ("education-programs", "Parent education sessions, resolution fund, handbook")]),
    ("mo.custody", "Child custody, parenting time and visitation", [
        ("best-interests", "Custody determination, best-interests factors, joint custody, parenting plans"),
        ("visitation", "Visitation / parenting time; neutral exchange"),
        ("third-party", "Third-party and grandparent visitation/custody"),
        ("relocation", "Relocation of the child"),
        ("modification", "Modification of custody"),
        ("domestic-violence", "Domestic violence and abuse in custody determinations"),
        ("gal-investigation", "Guardian ad litem, investigations, child's wishes"),
        ("military", "Military service and deployment (incl. Uniform Deployed Parents Custody and Visitation Act 452.1200 ff.)"),
        ("international-abduction", "Risk of international abduction; enforcement by law enforcement"),
        ("records-access", "Parental access to records")]),
    ("mo.uccjea", "UCCJEA (452.700–452.930): jurisdiction and enforcement of custody determinations", [
        ("general", "General provisions, definitions, international application"),
        ("jurisdiction", "Initial, exclusive continuing, modification and emergency jurisdiction; inconvenient forum"),
        ("enforcement", "Registration, recognition and enforcement; warrants; Hague Convention enforcement")]),
    ("mo.child-support", "Child support", [
        ("determination", "Determination, factors, Form 14 presumption (452.340; Rule 88.01)"),
        ("duration-emancipation", "Duration, emancipation, post-secondary education"),
        ("payment-withholding", "Payment through clerk/payment center; income withholding"),
        ("medical-support", "Health benefit plan / medical support orders"),
        ("administrative", "Family Support Division; administrative establishment and modification"),
        ("enforcement", "Enforcement: liens, garnishment, license suspension, passport, credit reporting"),
        ("state-debt-assignment", "Assignment of support rights; state debt; public assistance"),
        ("stepparent", "Stepparent support duty")]),
    ("mo.uifsa", "UIFSA (454.1500–454.1730): interstate and international support", [
        ("jurisdiction", "Jurisdiction, continuing exclusive jurisdiction, controlling order"),
        ("procedure", "Tribunals, proceedings, evidence, communications"),
        ("registration-enforcement", "Registration and enforcement of foreign orders; income withholding"),
        ("modification", "Registration for modification; modification of other-state/foreign orders"),
        ("hague-convention", "Support proceedings under the 2007 Hague Child Support Convention (Art. 7)"),
        ("rendition-general", "Rendition; uniformity; general")]),
    ("mo.paternity", "Parentage / paternity (Uniform Parentage Act 210.817–210.854)", [
        ("presumptions", "Presumptions of paternity and rebuttal"),
        ("acknowledgment", "Voluntary acknowledgment of paternity"),
        ("actions", "Paternity actions: standing, limitations, parties, genetic testing, evidence"),
        ("judgment-support", "Judgment, support, custody and parenting plan in paternity cases"),
        ("set-aside", "Setting aside paternity/support judgments"),
        ("assisted-reproduction", "Artificial insemination")]),
    ("mo.adoption", "Adoption", [
        ("petition-procedure", "Petition, jurisdiction, venue, GAL, hearing and decree"),
        ("consent", "Consent to adoption and cases where consent is not required"),
        ("investigation-placement", "Placement, investigations, home studies, postplacement"),
        ("effects", "Consequences of adoption"),
        ("records", "Adoption records, confidentiality, birth certificates, adoptee rights"),
        ("foreign-interstate", "Adoptions under laws of other states or countries; interstate compacts (ICPC, adoption assistance)"),
        ("subsidy", "Subsidies and adoption funds")]),
    ("mo.tpr", "Termination of parental rights (211.442–211.487)", [
        ("grounds", "Grounds and consent/voluntary termination"), ("procedure", "Petition, service, hearings, GAL, orders")]),
    ("mo.child-protection", "Child protection", [
        ("abuse-reporting", "Child abuse and neglect reporting and investigation (210.109 ff.)"),
        ("protective-custody", "Protective custody; juvenile court jurisdiction"),
        ("gal", "Guardian ad litem in abuse/neglect proceedings"),
        ("safe-haven", "Safe place for newborns")]),
    ("mo.protection-orders", "Orders of protection", [
        ("adult-abuse", "Adult Abuse Act: definitions, petitions, ex parte and full orders, relief"),
        ("child-protection-orders", "Child Protection Orders Act (455.500 ff.)"),
        ("foreign-orders", "Foreign orders of protection — full faith and credit"),
        ("enforcement", "Law enforcement response, arrest, violation penalties"),
        ("services", "Shelters, commissions, programs, fatality review")]),
    ("mo.criminal", "Family-related crimes", [
        ("domestic-assault", "Domestic assault (565.072–565.076); definitions"),
        ("custody-interference", "Interference with custody, parental kidnapping, child abduction (565.150–565.160)")]),
    ("mo.vital-records", "Vital records", [
        ("birth", "Birth certificates, parentage entries, court-ordered certificates"),
        ("marriage-divorce", "Marriage and dissolution records"),
        ("amendment", "Amendment of certificates; certified copies")]),
    ("mo.succession", "Probate — surviving spouse and children", [
        ("intestacy", "Intestate succession; parent-child relationship; posthumous children"),
        ("spousal-bars", "Waiver/bar of spousal rights (misconduct, contract, abandonment)"),
        ("elective-share", "Elective share; gifts in fraud of marital rights"),
        ("marital-agreement-waiver", "Waiver of right of election and statutory rights by agreement (474.120, 474.220)"),
        ("omitted-spouse-children", "Omitted spouse and children"),
        ("allowances", "Exempt property, support allowance, homestead allowance"),
        ("revocation-divorce", "Revocation of will provisions by divorce")]),
    ("mo.contracts", "Contract formalities and limitations", [
        ("statute-of-frauds", "Statute of frauds (432.010) — agreements in consideration of marriage"),
        ("limitations", "Limitations periods (516.100–516.120)"),
        ("judgments-presumption", "Presumption of payment of judgments / revival (516.350)"),
        ("interpretation", "Contract interpretation principles applied to marital agreements (judge-made)"),
        ("equitable-doctrines", "Equitable doctrines (estoppel, laches, unclean hands) in family matters (judge-made)")]),
    ("mo.conflicts", "Conflict of laws and recognition", [
        ("foreign-judgments-comity", "Recognition of foreign-country divorce/custody/support judgments; comity"),
        ("choice-of-law", "Choice of law (Restatement (Second) Conflict of Laws §§ 187–188 as adopted)")]),
    ("mo.procedure", "Civil procedure in family matters (Supreme Court Rules)", [
        ("pleadings-motions", "Pleadings, motions and hearings (Rule 55)"),
        ("judgments", "Judgments and relief from judgment (Rule 74)"),
        ("control-of-judgment", "Trial court control of judgments (Rule 75)"),
        ("post-trial", "New trial and after-trial motions (Rule 78)"),
        ("appellate-opinions", "Appellate opinions, memoranda and orders (Rule 84.16)"),
        ("child-support-guidelines", "Rule 88.01 and Civil Procedure Form No. 14"),
        ("mediation", "Mediation of custody and visitation (Rule 88.02–88.08)"),
        ("self-represented", "Self-represented litigants (Rule 88.09)")]),
]


def tree():
    nodes = []
    for nid, label, kids in T:
        nodes.append({"id": nid, "label": label, "children": [{"id": f"{nid}.{k}", "label": l, "children": []} for k, l in kids]})
    return {"side": "mo", "lang": "en", "nodes": nodes}


def n(s):
    ch, sec = s.split(".")
    return int(ch), int(sec)


def rng(s, a, b):
    return n(a) <= n(s) <= n(b)


def rsmo_issues(s, heading):
    h = (heading or "").lower()
    ch, k = n(s)
    out = []
    if ch == 451:
        if k in (10, 100, 110, 115, 120):
            out.append("mo.marriage.formation")
        if k in (40, 80, 90, 120, 130, 150, 151):
            out.append("mo.marriage.license")
        if k in (20, 22, 30):
            out.append("mo.marriage.validity")
        if k in range(170, 211):
            out.append("mo.marriage.records")
        if k == 160:
            out.append("mo.marriage.children-legitimation")
        if k in (220, 230, 240):
            out.append("mo.marriage.marital-agreements")
        if k >= 250:
            out.append("mo.marriage.spousal-property")
    elif ch == 452:
        if k < 300:
            out.append("mo.dissolution.older-provisions")
            if k in (75, 80, 110, 130):
                out.append("mo.dissolution.maintenance")
        elif k in (300, 305, 310, 311, 312, 314, 320):
            out.append("mo.dissolution.grounds-procedure")
        elif k in (315, 317, 318):
            out.append("mo.dissolution.temporary-orders")
        elif k == 325:
            out.append("mo.dissolution.separation-agreements")
        elif k == 330:
            out.append("mo.dissolution.property-division")
        elif k == 335:
            out.append("mo.dissolution.maintenance")
        elif 340 <= k <= 347:
            out.append("mo.child-support.determination")
            if k in (340,):
                out.append("mo.child-support.duration-emancipation")
            if k in (345,):
                out.append("mo.child-support.payment-withholding")
        elif k == 350:
            out.append("mo.child-support.payment-withholding")
        elif k == 354:
            out += ["mo.dissolution.modification", "mo.dissolution.attorney-fees"]
        elif k == 355:
            out.append("mo.dissolution.attorney-fees")
        elif k in (360, 365):
            out.append("mo.dissolution.judgment")
        elif k in (370, 371):
            out.append("mo.dissolution.modification")
        elif k == 372 or 552 <= k <= 610:
            out.append("mo.dissolution.education-programs")
        elif k == 374:
            out.append("mo.paternity.actions")
        elif k == 375:
            out += ["mo.custody.best-interests", "mo.custody.domestic-violence"]
        elif k == 376 or k == 430:
            out.append("mo.custody.records-access")
        elif k == 377:
            out.append("mo.custody.relocation")
        elif k == 380:
            out.append("mo.custody.best-interests")
        elif k in (385, 390, 423):
            out.append("mo.custody.gal-investigation")
        elif k in (395, 405, 415, 420):
            out.append("mo.custody.best-interests")
        elif k in (400, 404):
            out.append("mo.custody.visitation")
            if k == 400:
                out.append("mo.custody.domestic-violence")
        elif k in (402, 403):
            out.append("mo.custody.third-party")
        elif k in (410, 411):
            out.append("mo.custody.modification")
        elif k in (412, 413, 416) or 1200 <= k <= 1258:
            out.append("mo.custody.military")
        elif k in (425, 426):
            out.append("mo.custody.international-abduction")
        elif 700 <= k <= 930:
            if k <= 735 or k >= 920:
                out.append("mo.uccjea.general")
            elif k <= 845:
                out.append("mo.uccjea.jurisdiction" if k <= 790 or k in (800, 845) else "mo.uccjea.enforcement")
            else:
                out.append("mo.uccjea.enforcement")
            if k in (795, 805, 810, 815):
                out.append("mo.uccjea.enforcement")
    elif ch == 453:
        if k in (40, 50, 30) or "consent" in h:
            out.append("mo.adoption.consent")
        if k in (5, 10, 11, 12, 20, 25, 60, 61, 80, 101, 140, 150, 160, 315):
            out.append("mo.adoption.petition-procedure")
        if k in (14, 15, 26, 70, 75, 77, 102, 110, 350):
            out.append("mo.adoption.investigation-placement")
        if k == 90:
            out.append("mo.adoption.effects")
        if k in (100, 120, 121):
            out.append("mo.adoption.records")
        if k in (170, 500, 503):
            out.append("mo.adoption.foreign-interstate")
        if k in (65, 72, 73, 74, 153, 600, 650):
            out.append("mo.adoption.subsidy")
        if k == 400:
            out.append("mo.child-support.stepparent")
        if k in (11, 40):
            out.append("mo.tpr.grounds")
    elif ch == 454:
        if 1500 <= k <= 1730:
            if k in range(1680, 1717):
                out.append("mo.uifsa.hague-convention")
            elif 1515 <= k <= 1545:
                out.append("mo.uifsa.jurisdiction")
            elif 1548 <= k <= 1608:
                out.append("mo.uifsa.procedure")
            elif 1611 <= k <= 1653:
                out.append("mo.uifsa.registration-enforcement")
            elif 1656 <= k <= 1677:
                out.append("mo.uifsa.modification")
            else:
                out.append("mo.uifsa.rendition-general")
        elif 600 <= k <= 700:
            out.append("mo.child-support.medical-support")
        elif 1000 <= k <= 1031 or 505 <= k <= 528 or k in (511, 512, 520):
            out.append("mo.child-support.enforcement")
        elif 530 <= k <= 565:
            out.append("mo.child-support.payment-withholding")
        elif 440 <= k <= 500:
            out.append("mo.child-support.administrative")
            if k in (465, 450, 455):
                out.append("mo.child-support.state-debt-assignment")
            if k == 485:
                out.append("mo.paternity.actions")
        elif k in (410, 415, 455):
            out.append("mo.child-support.state-debt-assignment")
        else:
            out.append("mo.child-support.administrative")
        if "withhold" in h and "mo.child-support.payment-withholding" not in out:
            out.append("mo.child-support.payment-withholding")
        if k == 1050:
            out = ["mo.child-support.determination"]
    elif ch == 455:
        if 500 <= k <= 549:
            out.append("mo.protection-orders.child-protection-orders")
            if k == 538:
                out.append("mo.protection-orders.enforcement")
        elif 200 <= k <= 305 or k == 560:
            out.append("mo.protection-orders.services")
        elif k == 67:
            out.append("mo.protection-orders.foreign-orders")
        elif k in (80, 83, 85, 95):
            out.append("mo.protection-orders.enforcement")
        else:
            out.append("mo.protection-orders.adult-abuse")
        if k == 90:
            out.append("mo.protection-orders.foreign-orders")
    elif ch == 210:
        if 817 <= k <= 854:
            if k == 822:
                out.append("mo.paternity.presumptions")
            elif k == 823:
                out.append("mo.paternity.acknowledgment")
            elif k == 824:
                out.append("mo.paternity.assisted-reproduction")
            elif k in (841, 842, 843, 845, 847, 853):
                out.append("mo.paternity.judgment-support")
            elif k == 854:
                out.append("mo.paternity.set-aside")
            else:
                out.append("mo.paternity.actions")
        elif 109 <= k <= 183:
            out.append("mo.child-protection.gal" if k == 160 else ("mo.child-protection.protective-custody" if k == 125 else "mo.child-protection.abuse-reporting"))
        elif 620 <= k <= 650:
            out.append("mo.adoption.foreign-interstate")
        elif k == 950:
            out.append("mo.child-protection.safe-haven")
    elif ch == 211:
        if k == 31:
            out.append("mo.child-protection.protective-custody")
        elif k in (444, 447):
            out += ["mo.tpr.grounds", "mo.tpr.procedure"] if k == 447 else ["mo.tpr.grounds"]
        else:
            out.append("mo.tpr.procedure")
    elif ch == 193:
        if k in (185, 195, 205):
            out.append("mo.vital-records.marriage-divorce")
        elif k in (215, 255):
            out.append("mo.vital-records.amendment")
        else:
            out.append("mo.vital-records.birth")
        if k in (87, 215):
            out.append("mo.paternity.acknowledgment")
        if k in (125, 128, 135):
            out.append("mo.adoption.records")
    elif ch == 474:
        if k <= 100:
            out.append("mo.succession.intestacy")
        elif k in (110, 130, 140):
            out.append("mo.succession.spousal-bars")
        elif k == 120:
            out += ["mo.succession.spousal-bars", "mo.succession.marital-agreement-waiver"]
        elif k in (150, 155, 160, 163, 170, 180, 190, 200, 230):
            out.append("mo.succession.elective-share")
        elif k == 220:
            out += ["mo.succession.elective-share", "mo.succession.marital-agreement-waiver"]
        elif k in (235, 240):
            out.append("mo.succession.omitted-spouse-children")
        elif 250 <= k <= 300:
            out.append("mo.succession.allowances")
        elif k == 420:
            out.append("mo.succession.revocation-divorce")
    elif ch == 432:
        out += ["mo.contracts.statute-of-frauds", "mo.marriage.marital-agreements"]
    elif ch == 516:
        out.append("mo.contracts.judgments-presumption" if k == 350 else "mo.contracts.limitations")
    elif ch == 565:
        out.append("mo.criminal.domestic-assault" if k <= 76 else "mo.criminal.custody-interference")
    if s in ("452.720", "452.790", "452.795", "453.170", "454.1512", "454.1665", "454.1701"):
        out.append("mo.conflicts.foreign-judgments-comity")
    if s in ("454.1554", "454.1641"):
        out.append("mo.conflicts.choice-of-law")
    if not out:
        out.append({451: "mo.marriage", 452: "mo.dissolution", 453: "mo.adoption", 454: "mo.child-support", 455: "mo.protection-orders"}.get(ch, "mo"))
    return list(dict.fromkeys(out))


def const_issues(art, sec):
    return {("I", "2"): ["mo.constitution.equal-rights"], ("I", "10"): ["mo.constitution.due-process"],
            ("I", "33"): ["mo.constitution.marriage", "mo.marriage.validity"], ("V", "5"): ["mo.constitution.rulemaking", "mo.procedure"]}.get((art, sec), ["mo.constitution"])


def rule_issues(num):
    if num.startswith("55."):
        return ["mo.procedure.pleadings-motions"]
    if num == "74.14":
        return ["mo.procedure.judgments", "mo.conflicts.foreign-judgments-comity"]
    if num.startswith("74."):
        return ["mo.procedure.judgments"]
    if num.startswith("75."):
        return ["mo.procedure.control-of-judgment"]
    if num.startswith("78."):
        return ["mo.procedure.post-trial"]
    if num.startswith("84."):
        return ["mo.procedure.appellate-opinions"]
    if num == "88.01" or num.startswith("form-14"):
        return ["mo.procedure.child-support-guidelines", "mo.child-support.determination"]
    if num == "88.09":
        return ["mo.procedure.self-represented"]
    if num.startswith("88."):
        return ["mo.procedure.mediation", "mo.custody.best-interests"]
    return ["mo.procedure"]


if __name__ == "__main__":
    p = "/home/user/workspace/flb/data/issues/mo.json"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(tree(), open(p, "w"), indent=2, ensure_ascii=False)
    print("wrote", p, sum(1 + len(x["children"]) for x in tree()["nodes"]), "nodes")
