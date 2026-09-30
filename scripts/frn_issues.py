"""frn_issues — French issue tree (topical family-law nodes + code hierarchy) and assignment rules.

Topical node: (id, label, rules, children). A rule = (corpora or None, label_regex or None, text_regex or None,
num_ranges or None). A norm gets every matching node; ancestors of matched nodes are dropped (keep most specific).
"""
import re
from frn_lib import in_range

ALL = None


def N(id_, label, rules=(), children=()):
    return {"id": id_, "label": label, "rules": list(rules), "children": list(children)}


def r(corpora=None, lab=None, txt=None, nums=None):
    return (corpora, re.compile(lab, re.I) if lab else None, re.compile(txt, re.I) if txt else None, nums)


CC = ["fr-cc"]
CPC = ["fr-cpc"]

TOPICS = [
    N("fr.dip", "Droit international privé de la famille", [], [
        N("fr.dip.conflits-de-lois", "Conflits de lois", [r(CC, lab=r"Titre préliminaire", nums=[("3", "3")]),
                                                          r(None, lab=r"conflit des lois|loi applicable"),
                                                          r(CC, nums=[("202-1", "202-2"), ("309", "309"), ("311-14", "311-18"), ("370-3", "370-5"), ("515-7-1", "515-7-1")])]),
        N("fr.dip.competence-reconnaissance", "Compétence internationale, reconnaissance et exequatur",
          [r(CPC, lab=r"reconnaissance transfrontalière"), r(CC, nums=[("14", "15")]),
           r(None, txt=r"reconnaissance (et|ou) (l'exécution|l'exequatur)|exequatur|décisions? étrangères?|jugements? étrangers?")]),
        N("fr.dip.notification-preuve", "Notification internationale des actes et obtention des preuves",
          [r(CPC, lab=r"notifications internationales|commissions rogatoires internationales")]),
        N("fr.dip.enlevement-international", "Déplacement illicite international d'enfants",
          [r(None, lab=r"déplacement illicite international"), r(None, txt=r"déplacement illicite international|enlèvement international|non-retour illicite")]),
    ]),
    N("fr.lois-generalites", "Publication, effets et application des lois", [r(CC, lab=r"^Titre préliminaire")]),
    N("fr.droits-civils-personne", "Droits civils et respect du corps humain", [r(CC, lab=r"Titre Ier : Des droits civils")]),
    N("fr.nationalite", "Nationalité française", [r(CC, lab=r"De la nationalité"), r(CPC, lab=r"nationalité"),
                                                  r(None, txt=r"nationalité française")]),
    N("fr.etat-civil", "État civil", [r(CC, lab=r"actes de l'état civil"), r(CPC, lab=r"actes de l'état civil|répertoire civil"),
                                      r(["fr-textes"], txt=r"état civil")], [
        N("fr.etat-civil.nom-prenom", "Nom et prénom", [r(CC, lab=r"Des prénoms|du nom|changement de nom|Du nom"),
                                                       r(CPC, lab=r"prénom|nom"), r(["fr-textes"], txt=r"changement de nom|nom de famille|usage du nom|choix du nom")]),
        N("fr.etat-civil.sexe", "Modification de la mention du sexe", [r(None, lab=r"mention du sexe")]),
    ]),
    N("fr.domicile-absence", "Domicile, absence", [r(CC, lab=r"Du domicile|Des absents|De l'absence"), r(CPC, lab=r"Les absents")]),
    N("fr.mariage", "Mariage", [r(CC, lab=r"Titre V : Du mariage"), r(None, txt=r"\bmariage\b")], [
        N("fr.mariage.conditions", "Conditions du mariage", [r(CC, lab=r"qualités et conditions requises")]),
        N("fr.mariage.formalites", "Formalités de célébration", [r(CC, lab=r"formalités relatives à la célébration|actes de mariage")]),
        N("fr.mariage.oppositions", "Oppositions au mariage", [r(CC, lab=r"oppositions au mariage")]),
        N("fr.mariage.nullite", "Nullité du mariage", [r(CC, lab=r"demandes en nullité de mariage")]),
        N("fr.mariage.obligations-effets", "Obligations naissant du mariage ; devoirs et droits des époux",
          [r(CC, lab=r"obligations qui naissent du mariage|devoirs et des droits respectifs des époux")]),
        N("fr.mariage.dissolution", "Dissolution du mariage", [r(CC, lab=r"dissolution du mariage")]),
        N("fr.mariage.etranger", "Mariage célébré à l'étranger ; mariage des Français à l'étranger", [r(CC, lab=r"mariage (célébré|contracté) (à|en pays) l'étranger|célébrés à l'étranger")]),
        N("fr.mariage.mariage-force-fraude", "Mariage forcé, simulé ou frauduleux",
          [r(["fr-cp", "fr-ceseda"], txt=r"mariage"), r(["fr-ceseda"], lab=r"Mariage contracté")]),
    ]),
    N("fr.divorce", "Divorce et séparation de corps", [r(CC, lab=r"Titre VI : Du divorce"), r(None, txt=r"divorc")], [
        N("fr.divorce.cas", "Cas de divorce", [r(CC, lab=r"Des cas de divorce")]),
        N("fr.divorce.consentement-mutuel", "Divorce par consentement mutuel",
          [r(CC, lab=r"consentement mutuel"), r(CPC, lab=r"consentement mutuel")]),
        N("fr.divorce.procedure", "Procédure du divorce judiciaire",
          [r(CC, lab=r"procédure du divorce"), r(CPC, lab=r"Le divorce et la séparation de corps judiciaires")]),
        N("fr.divorce.consequences-epoux", "Conséquences du divorce pour les époux",
          [r(CC, lab=r"conséquences du divorce pour les époux|date à laquelle se produisent")]),
        N("fr.divorce.prestation-compensatoire", "Prestation compensatoire",
          [r(CC, lab=r"prestations compensatoires"), r(CC, nums=[("270", "281")]), r(None, txt=r"prestation compensatoire")]),
        N("fr.divorce.consequences-enfants", "Conséquences du divorce pour les enfants", [r(CC, lab=r"conséquences du divorce pour les enfants")]),
        N("fr.divorce.separation-de-corps", "Séparation de corps", [r(CC, lab=r"séparation de corps"), r(None, txt=r"séparation de corps")]),
    ]),
    N("fr.filiation", "Filiation", [r(CC, lab=r"Titre VII : De la filiation"), r(CPC, lab=r"filiation"), r(None, txt=r"\bfiliation\b")], [
        N("fr.filiation.etablissement", "Établissement de la filiation", [r(CC, lab=r"établissement de la filiation")]),
        N("fr.filiation.actions", "Actions relatives à la filiation", [r(CC, lab=r"actions relatives à la filiation")]),
        N("fr.filiation.amp-tiers-donneur", "AMP avec tiers donneur (filiation)",
          [r(CC, lab=r"assistance médicale à la procréation"), r(CPC, lab=r"procréation médicalement assistée|assistance médicale")]),
        N("fr.filiation.subsides", "Action à fins de subsides", [r(CC, lab=r"subsides"), r(CPC, lab=r"subsides")]),
    ]),
    N("fr.adoption", "Adoption", [r(CC, lab=r"Titre VIII : De la filiation adoptive"), r(CPC, lab=r"adoption"),
                                 r(["fr-casf"], lab=r"adoption"), r(None, txt=r"\badoption\b|\badopté")], [
        N("fr.adoption.pleniere", "Adoption plénière", [r(CC, lab=r"adoption plénière")]),
        N("fr.adoption.simple", "Adoption simple", [r(CC, lab=r"adoption simple")]),
        N("fr.adoption.internationale", "Adoption internationale ; conflits de lois", [r(None, lab=r"adoption internationale|conflit des lois relatives à la filiation adoptive|Autorité centrale pour l'adoption"),
                                                                                      r(None, txt=r"adoption internationale")]),
        N("fr.adoption.pupilles-etat", "Pupilles de l'État", [r(None, lab=r"pupilles de l'[ÉE]tat"), r(None, txt=r"pupilles? de l'[ÉE]tat")]),
    ]),
    N("fr.obligations-alimentaires", "Obligations alimentaires et contribution à l'entretien des enfants", [
        r(CC, lab=r"Titre V : Du mariage > Chapitre V"), r(CC, nums=[("205", "211")]),
        r(None, txt=r"obligations? alimentaires?|pensions? alimentaires?|créances? alimentaires?|contribution à l'entretien")], [
        N("fr.obligations-alimentaires.contribution-entretien", "Contribution à l'entretien et à l'éducation de l'enfant",
          [r(CC, nums=[("371-2", "371-2"), ("373-2-2", "373-2-5")]), r(None, txt=r"contribution à l'entretien et à l'éducation")]),
        N("fr.obligations-alimentaires.recouvrement", "Recouvrement des pensions alimentaires (paiement direct, recouvrement public)",
          [r(["fr-cpce"], lab=r"paiement direct"), r(["fr-cpce"], txt=r"pension alimentaire|créance alimentaire"),
           r(["fr-textes"], txt=r"recouvrement public des pensions alimentaires|paiement direct")]),
        N("fr.obligations-alimentaires.intermediation-aripa", "Intermédiation financière et ARIPA",
          [r(["fr-css"], lab=r"recouvrement des (créances|pensions) alimentaires|Dispositions relatives au recouvrement des"),
           r(None, txt=r"intermédiation financière")]),
        N("fr.obligations-alimentaires.asf", "Allocation de soutien familial", [r(["fr-css"], lab=r"soutien familial"), r(None, txt=r"allocation de soutien familial")]),
        N("fr.obligations-alimentaires.aide-sociale", "Obligés alimentaires et aide sociale", [r(["fr-casf"], lab=r"Participation et récupération")]),
    ]),
    N("fr.autorite-parentale", "Autorité parentale", [r(CC, lab=r"Titre IX : De l'autorité parentale"), r(CPC, lab=r"autorité parentale"),
                                                     r(None, txt=r"autorité parentale")], [
        N("fr.autorite-parentale.exercice", "Exercice de l'autorité parentale", [r(CC, lab=r"exercice de l'autorité parentale")]),
        N("fr.autorite-parentale.separation-parents", "Exercice par les parents séparés ; résidence de l'enfant",
          [r(CC, lab=r"parents séparés"), r(None, txt=r"résidence alternée|parents séparés")]),
        N("fr.autorite-parentale.assistance-educative", "Assistance éducative", [r(None, lab=r"assistance éducative")]),
        N("fr.autorite-parentale.delegation-retrait", "Délégation, retrait total ou partiel de l'autorité parentale",
          [r(None, lab=r"délégation de l'autorité parentale|retrait total|Délégation, retrait|retrait de l'autorité parentale|déclaration judiciaire de délaissement")]),
        N("fr.autorite-parentale.biens-enfant", "Autorité parentale relativement aux biens de l'enfant (administration légale)",
          [r(CC, lab=r"relativement aux biens de l'enfant"), r(CPC, lab=r"juge des tutelles en matière d'administration légale")]),
        N("fr.autorite-parentale.audition-enfant", "Audition de l'enfant en justice", [r(CPC, lab=r"audition de l'enfant"), r(CC, nums=[("388-1", "388-1")])]),
        N("fr.autorite-parentale.administrateur-ad-hoc", "Administrateur ad hoc", [r(None, lab=r"administrateur ad hoc"), r(None, txt=r"administrateur ad hoc")]),
    ]),
    N("fr.minorite", "Minorité, tutelle des mineurs et émancipation", [r(CC, lab=r"Titre X : De la minorité"), r(CPC, lab=r"protection juridique des mineurs")], [
        N("fr.minorite.tutelle", "Tutelle des mineurs ; gestion du patrimoine du mineur en tutelle", [r(CC, lab=r"De la tutelle|Titre XII : De la gestion du patrimoine")]),
        N("fr.minorite.emancipation", "Émancipation", [r(CC, lab=r"émancipation")]),
    ]),
    N("fr.majorite-capacite", "Majorité et capacité (hors protection des majeurs)", [r(CC, lab=r"Titre XI : De la majorité")]),
    N("fr.pacs-concubinage", "Pacte civil de solidarité et concubinage", [r(CC, lab=r"Titre XIII"), r(None, txt=r"pacte civil de solidarité|concubin")], [
        N("fr.pacs-concubinage.pacs", "Pacte civil de solidarité", [r(CC, lab=r"pacte civil de solidarité")]),
        N("fr.pacs-concubinage.concubinage", "Concubinage", [r(CC, lab=r"Chapitre II : Du concubinage")]),
    ]),
    N("fr.regimes-matrimoniaux", "Régimes matrimoniaux", [r(CC, lab=r"Titre V : Du contrat de mariage et des régimes matrimoniaux"),
                                                         r(CPC, lab=r"droits des époux et les régimes matrimoniaux|régimes matrimoniaux"),
                                                         r(None, txt=r"régimes? matrimoni")], [
        N("fr.regimes-matrimoniaux.dispositions-generales", "Dispositions générales ; contrat de mariage ; changement de régime",
          [r(CC, lab=r"du contrat de mariage et des régimes matrimoniaux > Chapitre Ier")]),
        N("fr.regimes-matrimoniaux.communaute", "Régime de communauté", [r(CC, lab=r"régime en communauté")]),
        N("fr.regimes-matrimoniaux.separation-biens", "Séparation de biens", [r(CC, lab=r"régime de séparation de biens")]),
        N("fr.regimes-matrimoniaux.participation", "Participation aux acquêts", [r(CC, lab=r"participation aux acquêts")]),
        N("fr.regimes-matrimoniaux.regime-primaire", "Régime primaire (devoirs et droits respectifs des époux)", [r(CC, nums=[("212", "226")])]),
    ]),
    N("fr.successions", "Successions", [r(CC, lab=r"Titre Ier : Des successions"), r(CPC, lab=r"successions"), r(None, txt=r"\bsuccessions?\b")], [
        N("fr.successions.devolution", "Ouverture, dévolution, héritiers", [r(CC, lab=r"ouverture des successions|Des qualités requises pour succéder|Des héritiers")]),
        N("fr.successions.conjoint-survivant", "Droits du conjoint successible", [r(CC, lab=r"conjoint successible|conjoint survivant"), r(None, txt=r"conjoint survivant|conjoint successible")]),
        N("fr.successions.option", "Option de l'héritier", [r(CC, lab=r"option de l'héritier")]),
        N("fr.successions.indivision-partage", "Indivision et partage", [r(CC, lab=r"Du partage|régime légal de l'indivision"), r(CC, nums=[("815", "815-18")])]),
        N("fr.successions.vacantes", "Successions vacantes et en déshérence ; administration", [r(CC, lab=r"successions vacantes|administration de la succession")]),
    ]),
    N("fr.liberalites", "Libéralités", [r(CC, lab=r"Titre II : Des libéralités"), r(CPC, lab=r"libéralités")], [
        N("fr.liberalites.reserve-quotite", "Réserve héréditaire, quotité disponible, réduction", [r(CC, lab=r"réserve héréditaire|quotité disponible|réduction")]),
        N("fr.liberalites.donations", "Donations entre vifs", [r(CC, lab=r"donations entre vifs")]),
        N("fr.liberalites.testaments", "Dispositions testamentaires", [r(CC, lab=r"dispositions testamentaires")]),
        N("fr.liberalites.liberalites-partages", "Libéralités-partages", [r(CC, lab=r"libéralités-partages")]),
        N("fr.liberalites.entre-epoux", "Libéralités entre époux (1091-1099-1)", [r(CC, nums=[("1091", "1099-1")])]),
        N("fr.liberalites.graduelles-residuelles", "Libéralités graduelles et résiduelles", [r(CC, lab=r"graduelles|résiduelles")]),
    ]),
    N("fr.indivision", "Indivision conventionnelle", [r(CC, nums=[("1873-1", "1873-18")])]),
    N("fr.contrats-obligations", "Contrats et obligations (conventions matrimoniales et familiales)", [], [
        N("fr.contrats-obligations.contrat", "Le contrat : formation, validité, interprétation, effets", [r(CC, lab=r"Sous-titre Ier : Le contrat")], [
            N("fr.contrats-obligations.contrat.formation", "Formation du contrat", [r(CC, lab=r"formation du contrat > Section 1|La conclusion du contrat")]),
            N("fr.contrats-obligations.contrat.validite", "Validité (consentement, capacité, contenu) ; vices du consentement",
              [r(CC, lab=r"La validité du contrat")]),
            N("fr.contrats-obligations.contrat.nullite-caducite", "Nullité et caducité", [r(CC, lab=r"La nullité|La caducité")]),
            N("fr.contrats-obligations.contrat.interpretation", "Interprétation du contrat", [r(CC, lab=r"L'interprétation du contrat")]),
            N("fr.contrats-obligations.contrat.effets", "Effets du contrat", [r(CC, lab=r"Les effets du contrat")]),
            N("fr.contrats-obligations.contrat.inexecution", "Inexécution du contrat", [r(CC, lab=r"L'inexécution du contrat")]),
        ]),
        N("fr.contrats-obligations.responsabilite-quasi", "Responsabilité extracontractuelle et autres sources", [r(CC, lab=r"Sous-titre II|Sous-titre III")]),
        N("fr.contrats-obligations.regime-general", "Régime général des obligations", [r(CC, lab=r"Titre IV : Du régime général des obligations")]),
        N("fr.contrats-obligations.preuve", "Preuve des obligations", [r(CC, lab=r"Titre IV bis : De la preuve")]),
        N("fr.contrats-obligations.prescription", "Prescription extinctive", [r(CC, nums=[("2219", "2254")])]),
    ]),
    N("fr.violences-familiales", "Violences au sein du couple et de la famille", [
        r(None, txt=r"violences (conjugales|intrafamiliales|au sein du couple|familiales)|violences commises (par|au sein)")], [
        N("fr.violences-familiales.ordonnance-protection", "Ordonnance de protection et mesures civiles",
          [r(CC, lab=r"mesures de protection des victimes de violences"), r(CPC, lab=r"mesures de protection des victimes|ordonnance provisoire de protection immédiate"),
           r(None, txt=r"ordonnance de protection"), r(["fr-cpp"], lab=r"protection européenne")]),
        N("fr.violences-familiales.anti-rapprochement", "Dispositif électronique mobile anti-rapprochement ; téléphone grave danger",
          [r(None, lab=r"anti-rapprochement"), r(None, txt=r"anti-rapprochement|grave danger")]),
        N("fr.violences-familiales.penal", "Infractions de violences et circonstances aggravantes",
          [r(["fr-cp"], lab=r"atteintes volontaires à l'intégrité|harcèlement moral|viol, de l'inceste"), r(["fr-cp"], txt=r"conjoint|concubin|partenaire lié")]),
        N("fr.violences-familiales.procedure-penale", "Procédure pénale et mesures de sûreté",
          [r(["fr-cpp"], txt=r"conjoint|concubin|pacte civil de solidarité|violences")]),
    ]),
    N("fr.penal-famille", "Atteintes aux mineurs et à la famille (droit pénal)", [r(["fr-cp"], lab=r"atteintes aux mineurs et à la famille")], [
        N("fr.penal-famille.abandon-famille", "Abandon de famille", [r(["fr-cp"], lab=r"abandon de famille"), r(None, txt=r"abandon de famille")]),
        N("fr.penal-famille.exercice-autorite-parentale", "Atteintes à l'exercice de l'autorité parentale (non-représentation, soustraction)",
          [r(["fr-cp"], lab=r"atteintes à l'exercice de l'autorité parentale"), r(None, txt=r"non-représentation")]),
        N("fr.penal-famille.filiation-etat-civil", "Atteintes à la filiation et à l'état civil ; bigamie",
          [r(["fr-cp"], lab=r"atteintes à la filiation|atteintes à l'état civil")]),
        N("fr.penal-famille.mise-en-peril-mineurs", "Mise en péril des mineurs", [r(["fr-cp"], lab=r"mise en péril des mineurs")]),
        N("fr.penal-famille.delaissement", "Délaissement de mineur", [r(["fr-cp"], lab=r"délaissement de mineur")]),
    ]),
    N("fr.protection-enfance", "Protection de l'enfance et aide sociale à l'enfance", [r(["fr-casf"], lab=r"Titre II : Enfance")], [
        N("fr.protection-enfance.ase", "Service de l'aide sociale à l'enfance", [r(["fr-casf"], lab=r"aide sociale à l'enfance|Service de l'aide sociale")]),
        N("fr.protection-enfance.origines-personnelles", "Accès aux origines personnelles ; accouchement dans le secret",
          [r(None, lab=r"origines personnelles|accès aux origines"), r(None, txt=r"secret de son identité|origines personnelles|données non identifiantes")]),
        N("fr.protection-enfance.juridictions-mineurs", "Juge des enfants et tribunal pour enfants", [r(["fr-coj"], lab=r"juridictions des mineurs|juge des enfants|tribunal pour enfants")]),
        N("fr.protection-enfance.mineurs-victimes", "Mineurs victimes (procédure)", [r(["fr-cpp"], lab=r"mineurs victimes")]),
    ]),
    N("fr.politique-familiale", "Politique familiale, aide et action sociales en faveur des familles", [r(["fr-casf"], lab=r"Titre Ier : Famille")]),
    N("fr.amp-bioethique", "Assistance médicale à la procréation et bioéthique", [], [
        N("fr.amp-bioethique.amp", "Assistance médicale à la procréation", [r(["fr-csp"], lab=r"Assistance médicale à la procréation"),
                                                                         r(None, txt=r"assistance médicale à la procréation")]),
        N("fr.amp-bioethique.don-gametes", "Don de gamètes ; tiers donneur", [r(["fr-csp"], lab=r"gamètes"), r(None, txt=r"gamètes|tiers donneur")]),
        N("fr.amp-bioethique.principes-corps-humain", "Principes généraux (don d'éléments du corps humain)", [r(["fr-csp"], lab=r"Principes généraux")]),
        N("fr.amp-bioethique.identification-genetique", "Identification par empreintes génétiques", [r(None, txt=r"empreintes génétiques")]),
    ]),
    N("fr.fiscalite-famille", "Fiscalité de la famille", [r(["fr-cgi"])], [
        N("fr.fiscalite-famille.foyer-fiscal", "Foyer fiscal, imposition commune et quotient familial",
          [r(["fr-cgi"], nums=[("6", "6 bis"), ("193", "199")]), r(["fr-cgi"], txt=r"quotient familial|imposition commune|imposés séparément")]),
        N("fr.fiscalite-famille.pensions-prestation", "Pensions alimentaires et prestation compensatoire (IR)",
          [r(["fr-cgi"], nums=[("80 septies", "80 septies"), ("156", "156 bis"), ("199 octodecies", "199 octodecies")]),
           r(["fr-cgi"], txt=r"pension alimentaire|prestation compensatoire")]),
        N("fr.fiscalite-famille.partage", "Droit de partage", [r(["fr-cgi"], nums=[("746", "750 bis")])]),
        N("fr.fiscalite-famille.mutations-titre-gratuit", "Droits de mutation à titre gratuit (successions, donations)",
          [r(["fr-cgi"], nums=[("641", "667"), ("750 ter", "808")]), r(["fr-cgi"], txt=r"mutations? à titre gratuit|succession|donation")]),
        N("fr.fiscalite-famille.solidarite-decharge", "Solidarité fiscale des époux et décharge", [r(["fr-cgi"], nums=[("1691 bis", "1691 bis")])]),
    ]),
    N("fr.protection-sociale-famille", "Protection sociale et famille", [r(["fr-css"])], [
        N("fr.protection-sociale-famille.reversion-veuvage", "Pension de réversion et assurance veuvage",
          [r(["fr-css"], lab=r"réversion|veuvage"), r(["fr-css"], txt=r"réversion|conjoint survivant|veuvage")]),
        N("fr.protection-sociale-famille.prestations-familiales", "Prestations familiales (allocataire, résidence alternée)",
          [r(["fr-css"], lab=r"Prestations familiales"), r(["fr-css"], txt=r"résidence alternée")]),
    ]),
    N("fr.etrangers-famille", "Droit au séjour pour motifs familiaux", [r(["fr-ceseda"])], [
        N("fr.etrangers-famille.citoyens-ue", "Membres de famille des citoyens de l'Union européenne", [r(["fr-ceseda"], lab=r"MEMBRES DE LEUR FAMILLE")]),
        N("fr.etrangers-famille.motif-familial", "Titres de séjour pour motif familial (conjoint, parent d'enfant français)",
          [r(["fr-ceseda"], lab=r"MOTIF FAMILIAL"), r(["fr-ceseda"], txt=r"conjoint de Français|enfant français|parent d'un Français")]),
        N("fr.etrangers-famille.regroupement-familial", "Regroupement et réunification familiale", [r(["fr-ceseda"], lab=r"REGROUPEMENT FAMILIAL|Réunification familiale"),
                                                                                                 r(["fr-ceseda"], txt=r"regroupement familial|réunification familiale")]),
        N("fr.etrangers-famille.violences", "Protection des étrangers victimes de violences familiales", [r(["fr-ceseda"], txt=r"violences (conjugales|familiales)|ordonnance de protection")]),
        N("fr.etrangers-famille.fraude", "Mariage ou reconnaissance d'enfant frauduleux", [r(["fr-ceseda"], lab=r"Mariage contracté ou enfant reconnu")]),
    ]),
    N("fr.organisation-judiciaire", "Organisation judiciaire en matière familiale", [r(["fr-coj"])], [
        N("fr.organisation-judiciaire.jaf", "Juge aux affaires familiales", [r(["fr-coj"], lab=r"affaires familiales"), r(["fr-coj"], txt=r"affaires familiales")]),
        N("fr.organisation-judiciaire.violences-intrafamiliales", "Pôles spécialisés violences intrafamiliales", [r(["fr-coj"], lab=r"violences intrafamiliales")]),
        N("fr.organisation-judiciaire.competences-specialisees", "Tribunaux spécialement désignés (adoption internationale, enlèvement, nationalité)",
          [r(["fr-coj"], txt=r"spécialement désignés?|adoption|déplacement illicite|nationalité")]),
    ]),
    N("fr.procedure-civile-famille", "Procédure civile en matière familiale", [r(CPC)], [
        N("fr.procedure-civile-famille.generale", "Procédure en matière familiale : dispositions générales", [r(CPC, lab=r"procédure en matière familiale > Section I")]),
        N("fr.procedure-civile-famille.autres-procedures-jaf", "Autres procédures relevant du JAF", [r(CPC, lab=r"autres procédures relevant")]),
        N("fr.procedure-civile-famille.regimes-liquidation", "Liquidation et partage des intérêts patrimoniaux des époux", [r(CPC, lab=r"liquidation et le partage des intérêts patrimoniaux|Le fonctionnement, la liquidation")]),
        N("fr.procedure-civile-famille.modes-amiables", "Modes amiables : conciliation, médiation, procédure participative, accord des parties",
          [r(CPC, lab=r"RÉSOLUTION AMIABLE")]),
    ]),
    N("fr.constitution", "Normes constitutionnelles", [r(["fr-const"])], [
        N("fr.constitution.droits-fondamentaux", "Droits fondamentaux (DDHC, Préambule de 1946)", [r(["fr-const"], nums=[("1", "1")]), r(["fr-const"], txt=r"Déclaration de 1789"), r(["fr-const"], nums=[("0", "17")], lab=r"Déclaration"), r(["fr-const"], lab=r"Préambule|1946")]),
        N("fr.constitution.traites", "Traités et droit de l'Union", [r(["fr-const"], nums=[("53", "55"), ("88-1", "88-1")])]),
        N("fr.constitution.controle-constitutionnalite", "Contrôle de constitutionnalité (QPC)", [r(["fr-const"], nums=[("61-1", "62")])]),
        N("fr.constitution.domaine-loi", "Domaine de la loi (état et capacité des personnes, régimes matrimoniaux, successions)", [r(["fr-const"], nums=[("34", "34")])]),
        N("fr.constitution.autorite-judiciaire", "Autorité judiciaire gardienne de la liberté individuelle", [r(["fr-const"], nums=[("66", "66")])]),
    ]),
    N("fr.textes-non-codifies", "Textes non codifiés (lois, ordonnances, décrets, arrêtés, circulaires)", [r(["fr-textes"])]),
]


def iter_nodes(nodes, parent=None):
    for n in nodes:
        yield n, parent
        yield from iter_nodes(n["children"], n)


def _match(rule, norm, labels_str):
    corpora, lab, txt, nums = rule
    if corpora and norm["corpus"] not in corpora:
        return False
    if not corpora and txt and norm["corpus"] == "fr-cc":
        return False  # Code civil: topical nodes follow the official hierarchy, not free-text keywords
    if lab and not lab.search(labels_str):
        return False
    if txt and not txt.search(norm.get("text") or ""):
        return False
    if nums:
        if not any(in_range(norm["num"], lo, hi) for lo, hi in nums):
            return False
    return True


PARENT = {}
for _n, _p in iter_nodes(TOPICS):
    PARENT[_n["id"]] = _p["id"] if _p else None


CORPUS_DEFAULT = {"fr-cc": "fr.lois-generalites", "fr-cpc": "fr.procedure-civile-famille", "fr-coj": "fr.organisation-judiciaire",
                  "fr-casf": "fr.protection-enfance", "fr-csp": "fr.amp-bioethique", "fr-cp": "fr.penal-famille",
                  "fr-cpp": "fr.violences-familiales.procedure-penale", "fr-cgi": "fr.fiscalite-famille", "fr-css": "fr.protection-sociale-famille",
                  "fr-ceseda": "fr.etrangers-famille", "fr-cpce": "fr.obligations-alimentaires.recouvrement", "fr-const": "fr.constitution",
                  "fr-textes": "fr.textes-non-codifies"}


def assign(norm, labels_str):
    hits = set()
    for n, _ in iter_nodes(TOPICS):
        if any(_match(rule, norm, labels_str) for rule in n["rules"]):
            hits.add(n["id"])
    # drop ancestors of more specific hits
    anc = set()
    for h in hits:
        p = PARENT.get(h)
        while p:
            anc.add(p)
            p = PARENT.get(p)
    out = sorted(hits - anc)
    return out or [CORPUS_DEFAULT.get(norm["corpus"], "fr.textes-non-codifies")]


def export_topics(nodes=TOPICS):
    return [{"id": n["id"], "label": n["label"], "children": export_topics(n["children"])} for n in nodes]
