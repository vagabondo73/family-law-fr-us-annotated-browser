#!/usr/bin/env python3
"""Generate scripts/frn_textes.json (curated list of non-codified French texts in force).

Inputs: raw/frn_textes/screen_rows.json (LEGI title-keyword candidates, état from the
dila/textes_juridiques mirror), plus a manual list of reform laws / ordonnances whose
autonomous (non-modifying) articles remain in force. Re-run after re-screening candidates.
"""
import json, os, re, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = json.load(open(os.path.join(ROOT, "raw/frn_textes/screen_rows.json")))

EXC = re.compile(r"attributions|Haut Conseil|composition|prorogation du mandat|prolongation du mandat|contribution financière des départements|néonicotinoïdes|changement de nom (de|d'un|des) (communes?|établissement|l'exploitant)|affiliation|recrutement|indemnit|élection|comité|concours|normes comptables|pêche|médaille|charte d'audit|financement (exceptionnel )?de l'Etat|libéralités consenties aux (associations|Etats)|Fondation du patrimoine|conjoints de fonctionnaires|régime indemnitaire|agents contractuels|marins|militaires|bâtonniers|épargne salariale|conditions adaptées pour le bénéfice|délais d'adoption des comptes|famille olympique|usure|expérimentation des dotations|seuil d'affiliation|langue française|connaissance de l'histoire|tests linguistiques|diplômes et certifications|comparabilité|recherche sur l'embryon|vétérinaires|personnels du ministère|professionnels libéraux|exploitation|travailleurs indépendants|substances actives|Nouvelle-Calédonie|Wallis|Mayotte|conservation des hypothèques|privilèges|dotations globales|bordereau|formation des cadres|formation dans le domaine|commissions administratives|Conseil national de la protection de l'enfance|Conseil supérieur de l'adoption|déconcentration|chef d'exploitation|données à caractère personnel par les organismes|allocation de remplacement|congé de maternité ou d'adoption|revalorisation|montant majoré|prise en compte forfaitaire|curatelle|majeurs protégés|mesure de protection|mandataires judiciaires|protection juridique des majeurs|bonnes pratiques cliniques|biovigilance|code européen unique des tissus|marqueurs infectieux|autoconservation|procédés biologiques|critères de compétence des praticiens|sages-femmes"
                 r"|échelonnement indiciaire|correspondances entre les emplois|budget|réglementations techniques|aliénation|rapport d'activité|rapports? annuels?|compensation des heures|notation des fonctionnaires|commissions d'appel d'offres|taux de promotion|contrôle financier|bilan social|prime de restructuration|restructuration de certains services|plan d'urgence gaz|comptabilité générale|équidés|contingents annuels|carte sanitaire|indice de besoins|moyenne générale|organisation interne|traitement automatisé|t[ée]l[ée]-?servi|répertoire national d'identification|centres d'aide par le travail|gestion budgétaire|changement de noms? de (communes|département)|importation et à l'exportation|agents non titulaires|médecins d|rachat de cotisations|prélèvement sur les ressources|ex-r[ée]gime local|rattachement des membres de la famille|signalement d'un incident|déléguant|montants maximaux|tarifs r[èé]glementés|établissements recevant des mineurs|allocation (pour jeune enfant|d'adoption|parentale d'éducation)|carte nationale d'identité|seuil de garantie|document d'évaluation|stimulation ovarienne|conditions de formation et d'expérience des praticiens|réfugiés et apatrides d'un système|lettre adressée par le médecin|accès télématique|échanges par voie électronique|frais de gestion des immeubles|modalités exceptionnelles|remboursement de congé|centres? d'aide|conseil de famille des pupilles|fiabilité, de sécurité et d'intégrité du registre|compensation des besoins|calendrier de déploiement|création du secrétariat général", re.I)
# manual exclusions after reading titles (not family law, or adult protection = out of scope)
DROP = {"006062905", "005630799", "005631025", "005632099", "005634948", "005957326", "006051259", "006056259", "027722475",
        "023571598", "045643504", "049690983", "049863458", "050657038", "048884310", "048551862",
        "006055787", "018882322", "005765491", "006061618", "006080290", "005620459", "024751060",
        "028309219", "026772792", "005628851", "043944322", "006062706", "005624421", "037358154"}

MANUAL = [  # (LEGITEXT, title-short, optional keyword filter for omnibus laws)
    ("LEGITEXT000006068521", "Loi n° 75-618 du 11 juillet 1975 (recouvrement public des pensions alimentaires)", None),
    ("LEGITEXT000005628705", "Loi n° 99-944 du 15 novembre 1999 (PACS)", None),
    ("LEGITEXT000005631757", "Loi n° 2001-1135 du 3 décembre 2001 (conjoint survivant)", None),
    ("LEGITEXT000005632380", "Loi n° 2002-304 du 4 mars 2002 (nom de famille)", None),
    ("LEGITEXT000005632381", "Loi n° 2002-305 du 4 mars 2002 (autorité parentale)", None),
    ("LEGITEXT000005773380", "Loi n° 2004-439 du 26 mai 2004 (divorce)", None),
    ("LEGITEXT000006053518", "Loi n° 2006-399 du 4 avril 2006 (violences au sein du couple)", None),
    ("LEGITEXT000006055596", "Loi n° 2007-293 du 5 mars 2007 (protection de l'enfance)", None),
    ("LEGITEXT000022455660", "Loi n° 2010-769 du 9 juillet 2010 (violences faites aux femmes)", None),
    ("LEGITEXT000027416452", "Loi n° 2013-404 du 17 mai 2013 (mariage pour tous)", None),
    ("LEGITEXT000032205870", "Loi n° 2016-297 du 14 mars 2016 (protection de l'enfant)", None),
    ("LEGITEXT000039696403", "Loi n° 2019-1480 du 28 décembre 2019 (violences au sein de la famille)", None),
    ("LEGITEXT000043886035", "Loi n° 2021-1017 du 2 août 2021 (bioéthique)", None),
    ("LEGITEXT000045134301", "Loi n° 2022-140 du 7 février 2022 (protection des enfants)", None),
    ("LEGITEXT000043404965", "Loi n° 2021-478 du 21 avril 2021 (mineurs, crimes et délits sexuels, inceste)", None),
    ("LEGITEXT000049164013", "Loi n° 2024-120 du 19 février 2024 (droit à l'image des enfants)", None),
    ("LEGITEXT000049291811", "Loi n° 2024-233 du 18 mars 2024 (enfants victimes de violences intrafamiliales)", None),
    ("LEGITEXT000029333373", "Loi n° 2014-873 du 4 août 2014 (égalité réelle)", r"pension|alimentaire|divorc|conjoint|parent|enfant|violence|famil"),
    ("LEGITEXT000033423670", "Loi n° 2016-1547 du 18 novembre 2016 (J21)", r"divorc|pacte civil|état civil|mariage|filiation|nom|prénom|famil|enfant|parent"),
    ("LEGITEXT000038262498", "Loi n° 2019-222 du 23 mars 2019 (LPJ)", r"divorc|séparation de corps|pension|alimentaire|famil|enfant|parent|état civil|mariage"),
    ("LEGITEXT000030249581", "Loi n° 2015-177 du 16 février 2015 (simplification, droit de la famille)", r"famil|enfant|divorc|parent|succession|mariage|filiation"),
    ("LEGITEXT000037286909", "Loi n° 2018-703 du 3 août 2018 (violences sexuelles et sexistes)", r"mineur|enfant|famil|conjoint|inceste"),
    ("LEGITEXT000024961879", "Loi n° 2011-1862 du 13 décembre 2011 (répartition des contentieux)", r"famil|divorc|enfant|pacte civil|succession|mariage|adoption"),
    ("LEGITEXT000020606377", "Loi n° 2009-526 du 12 mai 2009 (simplification)", r"famil|divorc|enfant|pacte civil|succession|mariage|adoption|filiation"),
]

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def mkslug(title):
    m = re.match(r"\s*(Loi|LOI|Décret|Ordonnance|Arrêté|Decret)\s*(?:n°\s*([0-9-]+))?\s*du\s*([0-9]+(?:er)?\s+\w+\s+[0-9]{4})", title, re.I)
    if m:
        nat = slugify(m.group(1)); num = m.group(2)
        return "%s-%s" % (nat, num) if num else "%s-%s" % (nat, slugify(m.group(3)))
    return slugify(title)[:60]

TOPIC = [  # title regex -> issue ids (validated against frn_issues tree by frn_build)
    (r"livret de famille|état civil|actes? de l'état civil|naissance|prénom|décès", "fr.etat-civil"),
    (r"nationalit|naturalisation", "fr.nationalite"),
    (r"mariage", "fr.mariage"),
    (r"divorce|séparation de corps|prestation compensatoire|276-4", "fr.divorce"),
    (r"filiation|nom de famille|choix du nom|changement de nom|accouchement", "fr.filiation"),
    (r"adoption|pupilles", "fr.adoption"),
    (r"pensions? alimentaires?|obligation d'entretien|soutien familial|impayés|intermédiation", "fr.obligations-alimentaires"),
    (r"autorité parentale|audition de l'enfant|droit de visite|espace de rencontre|conventions parentales|sortie du territoire|visite en présence d'un tiers|parentalité|image des enfants", "fr.autorite-parentale"),
    (r"pacte civil|PACS|partenaire|concubin", "fr.pacs-concubinage"),
    (r"régimes? matrimoniaux|conjoint du chef d'entreprise", "fr.regimes-matrimoniaux"),
    (r"succession|conjoint survivant|libéralit|900-2", "fr.successions"),
    (r"violence|anti-rapprochement|ordonnance de protection|victimes", "fr.violences-familiales"),
    (r"protection de l'enfance|enfance délinquante|protection des enfants|protection de l'enfant|jeunes majeurs|pris en charge par l'aide sociale", "fr.protection-enfance"),
    (r"procréation|gamètes|bioéthique|tiers donneur|AMP", "fr.amp-bioethique"),
    (r"enlèvement|retour|règlements européens|droit de l'Union européenne|Autorité centrale|internationale", "fr.dip"),
    (r"juge aux affaires familiales|tribunaux|juridictions|procédure civile|pôles spécialisés", "fr.procedure-civile-famille"),
    (r"visas", "fr.etrangers-famille"),
]

def topics(title):
    out = [iid for rx, iid in TOPIC if re.search(rx, title, re.I)]
    return out or ["fr.textes-non-codifies"]

sel, excl = [], []
for r in rows:
    if r["etat"] not in ("VIGUEUR", "VIGUEUR_DIFF", "MODIFIE"):
        excl.append({"id": r["id"], "reason": "état " + r["etat"]}); continue
    if EXC.search(r["title"]) or r["id"][-9:] in DROP:
        excl.append({"id": r["id"], "reason": "hors champ (titre)", "title": r["title"][:160]}); continue
    sel.append(r)
# de-duplicate same act listed twice (keep latest start date)
by = {}
for r in sel:
    k = mkslug(r["title"])
    if k not in by or r["debut"] > by[k]["debut"]:
        by[k] = r
texts, seen = [], set()
for k, r in sorted(by.items()):
    texts.append({"id": r["id"], "slug": k, "short": r["title"][:120], "title": r["title"], "issues": topics(r["title"])})
    seen.add(r["id"])
for tid, short, flt in MANUAL:
    if tid in seen: continue
    e = {"id": tid, "slug": mkslug(short), "short": short, "issues": topics(short)}
    if flt: e["filter"] = flt
    texts.append(e)
CIRC = [
    {"kind": "circulaire", "id": "circ-42386", "slug": "circulaire-2017-01-26-divorce-consentement-mutuel",
     "title": "Circulaire du 26 janvier 2017 de présentation des dispositions en matière de divorce par consentement mutuel et de succession issues de la loi n° 2016-1547 du 18 novembre 2016 de modernisation de la justice du XXIe siècle",
     "date": "2017-01-26", "official_url": "https://www.legifrance.gouv.fr/circulaire/id/42386", "issues": ["fr.divorce"]},
    {"kind": "circulaire", "id": "circ-45058", "slug": "circulaire-2020-09-23-violences-conjugales",
     "title": "Circulaire du 23 septembre 2020 relative à la politique pénale en matière de lutte contre les violences conjugales",
     "date": "2020-09-23", "number": "CRIM-2020-19/E1", "official_url": "https://www.legifrance.gouv.fr/circulaire/id/45058", "issues": ["fr.violences-familiales"]},
]
cfg = {"method": "Candidats: titres LEGI (index table_des_matieres du miroir dila/textes_juridiques) filtrés par mots-clés famille; "
                  "exclusion des textes non VIGUEUR et des textes hors champ (liste EXC/DROP de scripts/frn_textes_config.py); "
                  "ajout manuel des lois de réforme; pour chaque texte, seuls les articles autonomes en vigueur sont ingérés "
                  "(articles modificatifs exclus : leur contenu est consolidé dans les codes).",
       "screened": {"candidates": len(rows), "selected": len(texts), "excluded": len(excl)},
       "excluded": excl, "texts": texts + CIRC}
json.dump(cfg, open(os.path.join(ROOT, "scripts/frn_textes.json"), "w"), ensure_ascii=False, indent=1)
print(len(rows), "candidates ->", len(texts), "texts +", len(CIRC), "circulaires")
