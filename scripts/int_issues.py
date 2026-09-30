"""Issue tree for side 'eu-int' (data/issues/eu-int.json) + article-range mapping helpers."""
import os, sys, re
sys.path.insert(0, os.path.dirname(__file__))
from int_common import DATA, dump

T = lambda i, l, c=None: {"id": i, "label": l, "children": c or []}
TREE = [
    T("eu", "Droit de l'Union européenne — droit international privé de la famille", [
        T("eu.scope", "Champ d'application et définitions"),
        T("eu.matrimonial", "Matière matrimoniale (divorce, séparation de corps, annulation)", [
            T("eu.matrimonial.jurisdiction", "Compétence en matière matrimoniale")]),
        T("eu.parental-responsibility", "Responsabilité parentale", [
            T("eu.parental-responsibility.jurisdiction", "Compétence — résidence habituelle de l'enfant, prorogation, transfert"),
            T("eu.parental-responsibility.provisional", "Mesures provisoires et conservatoires"),
            T("eu.parental-responsibility.hearing-child", "Audition de l'enfant")]),
        T("eu.abduction", "Enlèvement international d'enfants (complément à la Convention de La Haye de 1980)"),
        T("eu.lis-pendens", "Litispendance, connexité et vérification de la compétence"),
        T("eu.recognition", "Reconnaissance et exécution des décisions, actes authentiques et accords"),
        T("eu.cooperation", "Coopération entre autorités centrales"),
        T("eu.maintenance", "Obligations alimentaires (règlement 4/2009)", [
            T("eu.maintenance.jurisdiction", "Compétence en matière d'obligations alimentaires"),
            T("eu.maintenance.applicable-law", "Loi applicable (Protocole de La Haye de 2007)"),
            T("eu.maintenance.recognition", "Reconnaissance, force exécutoire et exécution"),
            T("eu.maintenance.cooperation", "Assistance juridique et autorités centrales")]),
        T("eu.divorce-law", "Loi applicable au divorce et à la séparation de corps (Rome III)"),
        T("eu.property-regimes", "Régimes matrimoniaux (règlement 2016/1103)", [
            T("eu.property-regimes.jurisdiction", "Compétence"),
            T("eu.property-regimes.applicable-law", "Loi applicable et choix de loi"),
            T("eu.property-regimes.recognition", "Reconnaissance et exécution")]),
        T("eu.partnerships", "Effets patrimoniaux des partenariats enregistrés (règlement 2016/1104)"),
        T("eu.successions", "Successions (règlement 650/2012)", [
            T("eu.successions.jurisdiction", "Compétence"),
            T("eu.successions.applicable-law", "Loi applicable"),
            T("eu.successions.recognition", "Reconnaissance, actes authentiques et transactions"),
            T("eu.successions.certificate", "Certificat successoral européen")]),
        T("eu.public-documents", "Documents publics — dispense de légalisation (règlement 2016/1191)"),
        T("eu.procedure", "Procédure civile transfrontière", [
            T("eu.procedure.service", "Signification et notification des actes"),
            T("eu.procedure.evidence", "Obtention des preuves"),
            T("eu.procedure.brussels-i-bis", "Bruxelles I bis — exclusions familiales et accords matrimoniaux"),
            T("eu.procedure.judicial-cooperation", "Base juridique — art. 81, § 3, TFUE (droit de la famille)")]),
        T("eu.family-migration", "Libre circulation et regroupement familial (directives 2004/38 et 2003/86)"),
        T("eu.fundamental-rights", "Charte des droits fondamentaux (art. 7, 9, 24, 33)"),
    ]),
    T("int", "International instruments (HCCH, UN, Council of Europe, CIEC, bilateral France–United States)", [
        T("int.status", "Status tables — France / United States / EU"),
        T("int.procedure", "International civil procedure", [
            T("int.procedure.apostille", "Legalisation — Apostille Convention 1961"),
            T("int.procedure.service", "Service of documents abroad — Hague 1965"),
            T("int.procedure.evidence", "Taking of evidence abroad — Hague 1970"),
            T("int.procedure.judgments", "Recognition of foreign judgments — Hague 2019")]),
        T("int.abduction", "International child abduction", [
            T("int.abduction.hague-1980", "Hague 1980 Child Abduction Convention"),
            T("int.abduction.luxembourg-1980", "European Custody Convention (Luxembourg 1980)")]),
        T("int.child-protection", "Parental responsibility and child protection (Hague 1961/1996; CoE contact & children's rights)"),
        T("int.adoption", "Intercountry adoption (Hague 1993; CoE 1967/2008)"),
        T("int.maintenance", "Maintenance / child support (Hague 1956, 1958, 1973, 2007; UN 1956 New York)"),
        T("int.adults", "Protection of adults (Hague 2000)"),
        T("int.marriage", "Marriage, divorce and matrimonial property (Hague 1970/1978; UN 1962)"),
        T("int.successions", "Wills and successions (Hague 1961 form of testamentary dispositions)"),
        T("int.civil-status", "Civil status (CIEC conventions)"),
        T("int.human-rights", "Human-rights treaties — family provisions (ICCPR, CRC, CEDAW)"),
        T("int.domestic-violence", "Violence against women and domestic violence (Istanbul Convention)"),
        T("int.echr", "European Convention on Human Rights — family matters", [
            T("int.echr.family-life", "Respect for family life (Art. 8) — general"),
            T("int.echr.filiation", "Filiation, origins, paternity/maternity"),
            T("int.echr.filiation.surrogacy", "Surrogacy (GPA) and recognition of parent–child ties"),
            T("int.echr.assisted-reproduction", "Assisted reproduction"),
            T("int.echr.adoption", "Adoption"),
            T("int.echr.parental-responsibility", "Custody, residence, contact"),
            T("int.echr.child-protection", "Placement of children in public care"),
            T("int.echr.migration", "Expulsion, family reunification and family life"),
            T("int.echr.marriage", "Right to marry (Art. 12)"),
            T("int.echr.divorce", "Divorce and separation"),
            T("int.echr.succession", "Inheritance and discrimination (Art. 14)"),
            T("int.echr.civil-status", "Name and civil status"),
            T("int.echr.domestic-violence", "Domestic violence — positive obligations"),
            T("int.echr.spousal-equality", "Equality between spouses (P7-5)")]),
        T("int.bilateral", "Bilateral France–United States agreements (consular, social security, tax, child support)", [
            T("int.bilateral.consular", "Consular Convention 1966 — civil status, successions, guardianship of nationals"),
            T("int.bilateral.social-security", "Social Security Agreement 1987 — survivors' and family benefits"),
            T("int.bilateral.tax", "Tax conventions — estates, inheritances, gifts; income")]),
    ]),
]

# article ranges per instrument short id -> issue ids
RANGES = {
    "2019-1111": [((1, 2), "eu.scope"), ((3, 6), "eu.matrimonial.jurisdiction"), ((7, 14), "eu.parental-responsibility.jurisdiction"),
                  ((15, 15), "eu.parental-responsibility.provisional"), ((16, 16), "eu.parental-responsibility.jurisdiction"),
                  ((17, 20), "eu.lis-pendens"), ((21, 21), "eu.parental-responsibility.hearing-child"), ((22, 29), "eu.abduction"),
                  ((30, 75), "eu.recognition"), ((76, 84), "eu.cooperation")],
    "2003-2201": [((1, 2), "eu.scope"), ((3, 7), "eu.matrimonial.jurisdiction"), ((8, 9), "eu.parental-responsibility.jurisdiction"),
                  ((10, 11), "eu.abduction"), ((12, 15), "eu.parental-responsibility.jurisdiction"), ((16, 19), "eu.lis-pendens"),
                  ((20, 20), "eu.parental-responsibility.provisional"), ((21, 52), "eu.recognition"), ((53, 58), "eu.cooperation")],
    "4-2009": [((1, 2), "eu.scope"), ((3, 14), "eu.maintenance.jurisdiction"), ((15, 15), "eu.maintenance.applicable-law"),
               ((16, 43), "eu.maintenance.recognition"), ((44, 63), "eu.maintenance.cooperation")],
    "650-2012": [((1, 3), "eu.scope"), ((4, 19), "eu.successions.jurisdiction"), ((20, 38), "eu.successions.applicable-law"),
                 ((39, 61), "eu.successions.recognition"), ((62, 73), "eu.successions.certificate")],
    "2016-1103": [((1, 3), "eu.scope"), ((4, 19), "eu.property-regimes.jurisdiction"), ((20, 35), "eu.property-regimes.applicable-law"),
                  ((36, 60), "eu.property-regimes.recognition")],
}


def issues_for(sid, num, default):
    try:
        n = int(re.match(r"\d+", str(num)).group())
    except Exception:
        return default
    for (a, b), iss in RANGES.get(sid, []):
        if a <= n <= b:
            return [iss]
    return default


def write_tree():
    dump(os.path.join(DATA, "issues", "eu-int.json"), {"side": "eu-int", "lang": "fr",
         "lang_note": "Libellés en français pour les nœuds eu.* ; English labels for int.* nodes",
         "nodes": TREE})


if __name__ == "__main__":
    write_tree()
