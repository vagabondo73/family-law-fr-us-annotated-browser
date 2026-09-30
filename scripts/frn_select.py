"""frn_select — selection rules (SCOPE §4.1) and issue assignment for French norm corpora.

Each corpus: repo (Tricoteuses mirror dir under raw/), LEGITEXT, label, select(a) -> bool.
`a` has: num, path (list of {label,id}), text. Helpers below build `labels` (joined path labels).
"""
import re
from frn_lib import in_range, num_key

TODAY_NOTE = "Sélection par plages d'articles (SCOPE §4.1), intitulés de sections et mots-clés du texte."


def labels(a):
    return " > ".join(p["label"] for p in a["path"])


def R(num, *ranges, prefix=None):
    for r in ranges:
        lo, hi = r if isinstance(r, tuple) else (r, r)
        if in_range(num, lo, hi, prefix=prefix):
            return True
    return False


def rx(pattern):
    return re.compile(pattern, re.I)


# ---------------------------------------------------------------- Code civil
def sel_cc(a):
    n, L = a["num"], labels(a)
    top = a["path"][0]["id"] if a["path"] else ""
    if top == "titre_preliminaire":
        return True
    if top == "livre_ier":
        # Adult protection is OUT of the domestic perimeter (SCOPE §4): keep Titre XI ch. I (majorité, 414-414-3)
        # and the marriage/PACS rules for protected adults (460-462); drop the rest of 415-495-9.
        if R(n, ("415", "495-9")) and not R(n, ("460", "462")):
            return False
        return True
    if top == "livre_iii":
        return R(n, ("720", "892"), ("893", "1099-1"), ("1100", "1231-7"), ("1304", "1352-9"),
                 ("1353", "1386-1"), ("1387", "1581"), ("815", "815-18"), ("1873-1", "1873-18"),
                 ("2219", "2254"), ("1832-1", "1832-1"))
    return False


# ---------------------------------------------------------------- CPC
CPC_T1_EXCL = rx(r"mandat de protection future|majeurs? protégés?|habilitation familiale|sauvegarde de justice"
                 r"|Dispositions relatives aux majeurs|mesure d'accompagnement|préalablement à la saisine du juge des tutelles")


def sel_cpc(a):
    n, L = a["num"], labels(a)
    if L.startswith("Livre III"):
        if re.search(r"Titre Ier : Les personnes", L):
            return not CPC_T1_EXCL.search(L)
        if re.search(r"Titre III : Les régimes matrimoniaux", L):
            return True
        return False
    if re.search(r"Titre IX bis : L'audition de l'enfant", L):
        return True
    if re.search(r"La reconnaissance transfrontalière", L):
        return True
    if re.search(r"Règles particulières aux notifications internationales", L):
        return True
    if re.search(r"Les commissions rogatoires internationales", L):
        return True
    if L.startswith("Livre V : LA RÉSOLUTION AMIABLE"):
        return True
    return False


# ---------------------------------------------------------------- COJ
FAM_KW = (r"affaires familiales|violences intrafamiliales|droit de la famille|déplacement illicite international"
          r"|enlèvement international|adoption|obligations? alimentaires?|pensions? alimentaires?|état des personnes"
          r"|nationalité|divorce|filiation|autorité parentale|pacte civil de solidarité|régimes? matrimoni|successions"
          r"|assistance éducative|juge des enfants|ordonnance de protection")
COJ_HEAD = rx(r"affaires familiales|violences intrafamiliales|droit de la famille|juge des enfants|tribunal pour enfants"
              r"|juridictions des mineurs")


def sel_coj(a):
    L = labels(a)
    if COJ_HEAD.search(L) and not re.search(r"cour d'assises des mineurs", L, re.I):
        return True
    return bool(re.search(FAM_KW, a["text"], re.I))


# ---------------------------------------------------------------- CASF
CASF_HEAD = rx(r"Titre Ier : Famille|Titre II : Enfance|Institutions compétentes en matière de protection de l'enfance"
               r"|accès aux origines|Autorité centrale pour l'adoption|Participation et récupération")


def sel_casf(a):
    L = labels(a)
    if re.search(r"^Partie [^>]*> Livre V", L):
        return False
    return bool(CASF_HEAD.search(L))


# ---------------------------------------------------------------- CSP
CSP_HEAD = rx(r"Assistance médicale à la procréation|Don et utilisation de gamètes|gamètes")
CSP_KW = rx(r"filiation|empreintes génétiques|assistance médicale à la procréation|tiers donneur|don de gamètes"
            r"|données non identifiantes|secret de son identité|accès aux origines")


def sel_csp(a):
    L, n = labels(a), a["num"]
    if re.search(r"Livre [IV]+ : (Mayotte|Iles Wallis|Îles Wallis)", L):
        return False
    if CSP_HEAD.search(L):
        return True
    if re.search(r"Don et utilisation des éléments et produits du corps humain > Titre Ier : Principes généraux", L):
        return True
    if re.search(r"^Deuxième partie[^>]*> Livre Ier[^>]*> Titre VI : Dispositions pénales", L):
        return True
    return bool(CSP_KW.search(a["text"]))


# ---------------------------------------------------------------- Code pénal
CP_HEAD = rx(r"Des atteintes aux mineurs et à la famille|Des atteintes volontaires à l'intégrité|Du viol, de l'inceste"
             r"|Du harcèlement moral|Des atteintes à l'état civil|de la filiation")
CP_KW = rx(r"conjoint|concubin|partenaire lié|autorité parentale|mariage|anti-rapprochement|ordonnance de protection"
           r"|pacte civil de solidarité|non-représentation|abandon de famille")


def sel_cp(a):
    L = labels(a)
    if CP_HEAD.search(L):
        return True
    return bool(CP_KW.search(a["text"]))


# ---------------------------------------------------------------- CPP
CPP_HEAD = rx(r"anti-rapprochement|décisions de protection européenne"
              r"|infractions de nature sexuelle et (de la protection des|aux) mineurs victimes > Chapitre Ier")
CPP_KW = rx(r"anti-rapprochement|conjoint|concubin|pacte civil de solidarité|autorité parentale|violences intrafamiliales"
            r"|grave danger|ordonnance de protection|non-représentation|abandon de famille|227-3|227-5|227-7")


def sel_cpp(a):
    L = labels(a)
    if CPP_HEAD.search(L):
        return True
    return bool(CPP_KW.search(a["text"]))


# ---------------------------------------------------------------- CGI
CGI_KW = rx(r"pensions? alimentaires?|prestation compensatoire|divorc|séparation de corps|pacte civil de solidarité"
            r"|conjoint survivant|entre époux|quotient familial|résidence alternée|donations? entre vifs"
            r"|mutations? à titre gratuit|successions?\b")


def sel_cgi(a):
    n, L = a["num"], labels(a)
    if L.startswith("Livre premier") or L.startswith("Livre I"):
        if R(n, ("6", "6 bis"), ("80 septies", "80 septies"), ("156", "156 bis"), ("193", "199"),
             ("199 octodecies", "199 octodecies"), ("641", "667"), ("746", "750 bis"), ("750 ter", "808")):
            return True
    if R(n, ("1691 bis", "1691 bis")):
        return True
    return bool(CGI_KW.search(a["text"]))


# ---------------------------------------------------------------- CSS
CSS_HEAD = rx(r"recouvrement des (créances|pensions) alimentaires|intermédiation financière|allocation de soutien familial"
              r"|pensions? de réversion|réversion|veuvage|conjoint survivant|Dispositions relatives au recouvrement des")
CSS_KW = rx(r"pensions? alimentaires?|créances? alimentaires?|prestation compensatoire|divorc|séparation de corps"
            r"|intermédiation financière|conjoint survivant|résidence alternée|ex-conjoint|anciens? conjoints?"
            r"|contribution à l'entretien et à l'éducation|allocation de soutien familial|pacte civil de solidarité")


def sel_css(a):
    L = labels(a)
    if CSS_HEAD.search(re.sub(r"Assurance vieillesse\s*-\s*Assurance veuvage", "", L, flags=re.I)):
        return True
    return bool(CSS_KW.search(a["text"]))


# ---------------------------------------------------------------- CESEDA
CES_HEAD = rx(r"MEMBRES DE LEUR FAMILLE|MOTIF FAMILIAL|REGROUPEMENT FAMILIAL|Réunification familiale|Mariage contracté"
              r"|violences (familiales|conjugales)|conjoint de Français|parent d'un Français|Enfant étranger d'un Français")
CES_KW = rx(r"violences conjugales|violences familiales|ordonnance de protection|conjoint de Français|mariage"
            r"|père ou mère d'un enfant français|parent d'un enfant français|regroupement familial"
            r"|réunification familiale|pacte civil de solidarité|kafala|autorité parentale")


def sel_ceseda(a):
    L = labels(a)
    if CES_HEAD.search(L):
        return True
    return bool(CES_KW.search(a["text"]))


# ---------------------------------------------------------------- CPCE
CPCE_HEAD = rx(r"paiement direct des pensions alimentaires")
CPCE_KW = rx(r"pensions? alimentaires?|créances? alimentaires?|aliments|prestation compensatoire"
             r"|contribution à l'entretien|époux|conjoint")


def sel_cpce(a):
    L = labels(a)
    if CPCE_HEAD.search(L):
        return True
    return bool(CPCE_KW.search(a["text"]))


# ---------------------------------------------------------------- Constitution
def sel_const(a):
    return a["num"].upper() in {"PREAMBULE", "1", "34", "53", "53-1", "53-2", "55", "61-1", "62", "66", "88-1"}


CODES = {
    "fr-cc": dict(repo="code_civil", legitext="LEGITEXT000006070721", label="Code civil", select=sel_cc),
    "fr-cpc": dict(repo="code_de_procedure_civile", legitext="LEGITEXT000006070716", label="Code de procédure civile", select=sel_cpc),
    "fr-coj": dict(repo="code_de_l_organisation_judiciaire", legitext="LEGITEXT000006071164", label="Code de l'organisation judiciaire", select=sel_coj),
    "fr-casf": dict(repo="code_de_l_action_sociale_et_des_familles", legitext="LEGITEXT000006074069", label="Code de l'action sociale et des familles", select=sel_casf),
    "fr-csp": dict(repo="code_de_la_sante_publique", legitext="LEGITEXT000006072665", label="Code de la santé publique", select=sel_csp),
    "fr-cp": dict(repo="code_penal", legitext="LEGITEXT000006070719", label="Code pénal", select=sel_cp),
    "fr-cpp": dict(repo="code_de_procedure_penale", legitext="LEGITEXT000006071154", label="Code de procédure pénale", select=sel_cpp),
    "fr-cgi": dict(repo="code_general_des_impots", legitext="LEGITEXT000006069577", label="Code général des impôts", select=sel_cgi),
    "fr-css": dict(repo="code_de_la_securite_sociale", legitext="LEGITEXT000006073189", label="Code de la sécurité sociale", select=sel_css),
    "fr-ceseda": dict(repo="code_de_l_entree_et_du_sejour_des_etrangers_et_du_droit_d_asile", legitext="LEGITEXT000006070158", label="Code de l'entrée et du séjour des étrangers et du droit d'asile", select=sel_ceseda),
    "fr-cpce": dict(repo="code_des_procedures_civiles_d_execution", legitext="LEGITEXT000025024948", label="Code des procédures civiles d'exécution", select=sel_cpce),
    "fr-const": dict(repo="constitution_du_4_octobre_1958", legitext="LEGITEXT000006071194", label="Constitution du 4 octobre 1958", select=sel_const, org="constitution"),
}
