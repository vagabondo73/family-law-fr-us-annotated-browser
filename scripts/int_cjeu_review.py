"""Manual functional review (criterion b) of predecessor provisions -> current provisions.
Replaces the similarity cut-off as the decisive test (similarity is kept as information only).
Each entry was decided by reading the old provision (consolidated 2201/2003, 1393/2007, 1206/2001, 44/2001),
the new provision (2019/1111, 2020/1784, 2020/1783, 1215/2012), the recast's correlation table and the operative
part of the judgment (raw/int/cjeu/review_texts.txt, review_ops.txt).
Key lookup order: (celex, act, art, para) -> (celex, act, art, None) -> (act, art, para) -> (act, art, None).
Value: {"v": "include"|"exclude", "to": [(new_art, new_para|None), ...], "j": justification (FR)}."""

IIT = "règlement (UE) 2019/1111"
CONT = ("Le considérant 3 du règlement 2019/1111 inscrit la refonte dans la continuité du règlement 2201/2003, "
        "dont il ne modifie que les points identifiés ; la disposition interprétée n'en fait pas partie.")

R = {
    # --- 2201/2003 -> 2019/1111 ---------------------------------------------------------------
    ("32003R2201", "2", "11"): {"v": "include", "to": [("2", None)], "j":
        "Définition du « déplacement ou non-retour illicites » : l'article 2, paragraphe 2, point 11, du " + IIT +
        " reprend mot pour mot les deux conditions de l'ancien article 2, point 11 (violation d'un droit de garde selon le droit de "
        "l'État de résidence habituelle immédiatement avant le déplacement ; exercice effectif de ce droit). Seule la mention "
        "« judiciaire » après « décision » disparaît, sans incidence sur la notion interprétée. " + CONT},
    ("32003R2201", "2", "9"): {"v": "include", "to": [("2", None)], "j":
        "Définition du « droit de garde » : l'article 2, paragraphe 2, point 9, du " + IIT + " est identique à l'ancien article 2, point 9. " + CONT},
    ("32003R2201", "2", "7"): {"v": "include", "to": [("2", None)], "j":
        "Définition de la « responsabilité parentale » : l'article 2, paragraphe 2, point 7, du " + IIT + " conserve les mêmes éléments "
        "(droits et obligations relatifs à la personne ou aux biens de l'enfant, fondés sur une décision, une attribution de plein droit "
        "ou un accord, y compris droit de garde et droit de visite) ; la réorganisation de la phrase n'en change pas la portée. " + CONT},
    ("32003R2201", "2", "10"): {"v": "include", "to": [("2", None)], "j":
        "Définition du « droit de visite » : l'article 2, paragraphe 2, point 10, du " + IIT + " reprend l'ancien article 2, point 10 "
        "(« notamment le droit d'emmener l'enfant pour une période limitée dans un lieu autre que celui de sa résidence habituelle »), "
        "sans restriction quant aux titulaires du droit. " + CONT},
    ("32003R2201", "2", "4"): {"v": "exclude", "j":
        "Notion de « décision » : l'article 2, paragraphe 1, du " + IIT + " conserve la définition générale, mais la refonte crée des "
        "catégories distinctes d'« acte authentique » et d'« accord » (article 2, paragraphe 2, points 2 et 3 ; articles 64 à 68). "
        "La qualification, par l'arrêt, d'un acte d'une autorité non juridictionnelle comme « décision » n'est donc pas transposable "
        "sans examen : changement de fonction de la définition."},
    ("62020CJ0646", "32003R2201", "2", None): {"v": "exclude", "j":
        "Notion de « décision » (ancien article 2, point 4) : la refonte distingue désormais « décision », « acte authentique » et "
        "« accord » (article 2 du " + IIT + " ; articles 64 à 68) ; qualification non transposable sans examen."},
    ("62017CJ0335", "32003R2201", "2", None): {"v": "include", "to": [("2", None)], "j":
        "L'arrêt interprète les notions de « responsabilité parentale » et de « droit de visite » (ancien article 2, points 7 et 10), "
        "reprises à l'article 2, paragraphe 2, points 7 et 10, du " + IIT + " sans restriction quant au cercle des titulaires. " + CONT},
    ("62010CJ0400", "32003R2201", "2", None): {"v": "include", "to": [("2", None)], "j":
        "L'arrêt interprète les notions de « droit de garde » et de « déplacement illicite » (ancien article 2, points 9 et 11), "
        "reprises à l'identique à l'article 2, paragraphe 2, points 9 et 11, du " + IIT + " (le renvoi au droit de l'État de résidence "
        "habituelle pour l'attribution du droit de garde est inchangé). " + CONT},
    ("62014CJ0376", "32003R2201", "2", None): {"v": "include", "to": [("2", None)], "j":
        "L'arrêt interprète la notion de « non-retour illicite » (ancien article 2, point 11), reprise à l'identique à l'article 2, "
        "paragraphe 2, point 11, du " + IIT + ". " + CONT},
    ("62021CJ0262", "32003R2201", "2", None): {"v": "include", "to": [("2", None)], "j":
        "L'arrêt interprète la notion de « déplacement ou non-retour illicites » (ancien article 2, point 11), reprise à l'identique à "
        "l'article 2, paragraphe 2, point 11, du " + IIT + ". " + CONT},
    ("32003R2201", "6", None): {"v": "include", "to": [("6", None)], "j":
        "Caractère exclusif des chefs de compétence des articles 3 à 5 : l'ancien article 6 est repris à l'article 6, paragraphe 2, du " + IIT +
        " (suppression de la seule mention du « domicile » britannique et irlandais, désormais traitée par l'article 2, paragraphe 3). " + CONT},
    ("32003R2201", "7", None): {"v": "include", "to": [("6", None)], "j":
        "Compétences résiduelles : l'ancien article 7, paragraphes 1 et 2, est repris à l'article 6, paragraphes 1 et 3, du " + IIT +
        " ; la nouvelle réserve « sous réserve du paragraphe 2 » codifie l'articulation avec l'ancien article 6 retenue par la Cour. " + CONT},
    ("32003R2201", "11", "1"): {"v": "include", "to": [("22", None)], "j":
        "Champ des règles complétant la convention de La Haye de 1980 : l'article 22 du " + IIT + " reprend le critère de l'ancien "
        "article 11, paragraphe 1 (enfant déplacé ou retenu illicitement dans un État membre autre que celui « dans lequel l'enfant avait "
        "sa résidence habituelle immédiatement avant son déplacement ou son non-retour illicites »). L'ajout de la limite d'âge de 16 ans "
        "est sans incidence sur la notion de résidence habituelle interprétée. " + CONT},
    ("62014CJ0376", "32003R2201", "11", None): {"v": "include", "to": [("22", None)], "j":
        "L'arrêt interprète la condition de résidence habituelle « immédiatement avant » le non-retour (ancien article 11, paragraphe 1), "
        "reprise à l'identique à l'article 22 du " + IIT + ". " + CONT},
    ("62020CJ0501", "32003R2201", "11", None): {"v": "exclude", "j":
        "L'article 11 n'est pas interprété dans le dispositif (localisation Cellar seulement) ; aucun lien retenu."},
    ("32003R2201", "11", "3"): {"v": "include", "to": [("24", None)], "j":
        "Obligation de célérité de la procédure de retour : l'article 24, paragraphe 1, du " + IIT + " reprend mot pour mot le premier alinéa "
        "de l'ancien article 11, paragraphe 3 (« agit rapidement … en utilisant les procédures les plus rapides prévues par le droit national ») ; "
        "le délai de six semaines est seulement ventilé par degré de juridiction (paragraphes 2 et 3). " + CONT},
    ("32003R2201", "11", "6"): {"v": "exclude", "j":
        "Mécanisme dit de « prépondérance » (anciens articles 11, paragraphes 6 à 8, et 42) : refondu à l'article 29 du " + IIT +
        " (champ limité aux refus fondés uniquement sur l'article 13, premier alinéa, point b), ou deuxième alinéa, de la convention de 1980 ; "
        "certificat d'office ; examen approfondi de l'intérêt supérieur de l'enfant ; décision au fond sur le droit de garde, certificat de l'article 47 "
        "et motifs de refus/suspension des articles 50 et 56). Changement de fonction : interprétation non transposée."},
    ("32003R2201", "11", "7"): {"v": "exclude", "j": "Voir ancien article 11, paragraphe 6 : mécanisme refondu à l'article 29 du " + IIT + " ; non transposé."},
    ("32003R2201", "11", "8"): {"v": "exclude", "j": "Voir ancien article 11, paragraphe 6 : mécanisme refondu aux articles 29, 43, 47, 50 et 56 du " + IIT + " ; non transposé."},
    ("32003R2201", "12", "3"): {"v": "exclude", "j":
        "Prorogation de compétence : l'ancien article 12, paragraphe 3, est remplacé par l'article 10 du " + IIT + ", qui modifie les conditions "
        "de l'acceptation (accord libre au plus tard lors de la saisine, ou acceptation expresse en cours d'instance après information du droit de "
        "refuser ; exigence de forme écrite ; fin de la compétence prorogée, paragraphe 4 ; effet exclusif). La notion d'acceptation « de toute autre "
        "manière non équivoque » interprétée par la Cour a disparu : changement de libellé et de fonction."},
    ("32003R2201", "12", None): {"v": "exclude", "j": "Prorogation de compétence : régime remplacé par l'article 10 du " + IIT + " (conditions d'acceptation modifiées) ; non transposé."},
    ("32003R2201", "15", None): {"v": "include", "to": [("12", None)], "j":
        "Transfert de compétence : l'article 12 du " + IIT + " conserve les éléments de l'ancien article 15 interprétés par la Cour — caractère "
        "exceptionnel, juridiction « mieux placée », lien particulier de l'enfant avec l'autre État membre défini par la même liste fermée de "
        "rattachements (article 12, paragraphe 4), et exigence que le transfert serve l'intérêt supérieur de l'enfant — ainsi que les deux voies "
        "(invitation des parties à saisir l'autre juridiction ou demande directe). Les modifications (suppression de l'accord d'une partie, délai de "
        "six semaines, article 13 distinct) ne touchent pas les critères interprétés. " + CONT},
    ("32003R2201", "15", "1"): {"v": "include", "to": [("12", None)], "j":
        "Transfert de compétence (ancien article 15, paragraphe 1) : conditions de la juridiction « mieux placée » et de l'intérêt supérieur de "
        "l'enfant reprises à l'article 12, paragraphe 1, du " + IIT + ". " + CONT},
    ("32003R2201", "19", None): {"v": "include", "to": [("20", None)], "j":
        "Litispendance : l'article 20, paragraphes 1 à 3, du " + IIT + " reprend l'ancien article 19 (sursis d'office de la juridiction saisie "
        "en second lieu, dessaisissement) ; les motifs de non-reconnaissance ne comportent toujours pas la méconnaissance des règles de "
        "litispendance (articles 38 et 39). " + CONT},
    ("32003R2201", "20", None): {"v": "include", "to": [("15", None)], "j":
        "Mesures provisoires et conservatoires : l'article 15 du " + IIT + " conserve les conditions interprétées (urgence ; présence de "
        "l'enfant ou de ses biens dans l'État membre ; mesures prévues par le droit national ; caducité dès que la juridiction compétente au "
        "fond a statué, paragraphe 3). " + CONT},
    ("62009CJ0256", "32003R2201", "20", None): {"v": "exclude", "j":
        "La question de la circulation des mesures fondées sur l'ancien article 20 est désormais réglée expressément par l'article 2, "
        "paragraphe 1, second alinéa, point b), du " + IIT + " : texte nouveau, interprétation non transposée au titre du critère b."},
    ("62010CJ0296", "32003R2201", "20", None): {"v": "exclude", "j":
        "L'articulation litispendance / mesures provisoires est désormais réglée expressément par l'article 20, paragraphe 2, du " + IIT +
        " (« excepté lorsque la compétence … est uniquement fondée sur l'article 15 ») : texte nouveau, non transposé au titre du critère b."},
    ("32003R2201", "23", None): {"v": "include", "to": [("39", None)], "j":
        "Motifs de non-reconnaissance en matière de responsabilité parentale : l'article 39, paragraphe 1, point a), du " + IIT + " reprend "
        "l'ordre public « manifestement contraire … eu égard à l'intérêt supérieur de l'enfant » de l'ancien article 23, point a). " + CONT},
    ("32003R2201", "33", None): {"v": "exclude", "j":
        "Recours contre la déclaration constatant la force exécutoire : l'exequatur est supprimé par le " + IIT + " (articles 34 et 35) ; "
        "aucune disposition correspondante (le tableau de correspondance ne mentionne pas l'ancien article 33, paragraphes 1 et 5)."},
    ("32003R2201", "31", None): {"v": "exclude", "j": "Procédure de déclaration de force exécutoire supprimée par le " + IIT + " ; aucune correspondance."},
    ("32003R2201", "42", None): {"v": "exclude", "j":
        "Certificat de retour de l'ancien article 42 : remplacé par les articles 43, 47 à 49 du " + IIT + " (conditions de délivrance nouvelles, "
        "rectification/annulation dans l'État d'origine, refus et suspension de l'exécution aux articles 50 et 56). Changement de fonction ; non transposé."},
    ("32003R2201", "56", None): {"v": "include", "to": [("82", None)], "j":
        "Placement dans un autre État membre : l'article 82, paragraphe 1, du " + IIT + " maintient l'exigence interprétée par la Cour — "
        "approbation préalable de l'autorité compétente de l'État membre requis avant la décision de placement. Les modifications (transmission "
        "par les autorités centrales, délai de trois mois, exception pour le placement auprès d'un parent) ne touchent pas cette exigence. " + CONT},
    ("32003R2201", "61", None): {"v": "include", "to": [("97", None)], "j":
        "Relations avec la convention de La Haye de 1996 : l'article 97, paragraphe 1, point a), du " + IIT + " reprend le critère de l'ancien "
        "article 61, point a) (application du règlement lorsque l'enfant a sa résidence habituelle sur le territoire d'un État membre). " + CONT},
    ("32003R2201", "64", None): {"v": "exclude", "j":
        "Dispositions transitoires de l'ancien article 64 : propres à l'entrée en application du règlement 2201/2003 ; l'article 100 du " + IIT +
        " fixe un régime transitoire distinct (procédures engagées à compter du 1er août 2022) ; non transposable."},
    ("32003R2201", "47", None): {"v": "exclude", "j":
        "Procédure d'exécution des décisions certifiées (ancien article 47) : remplacée par les articles 51 à 63 du " + IIT + ", qui introduisent "
        "des motifs de suspension et de refus de l'exécution (notamment article 56, paragraphes 4 et 6, en cas de risque grave) absents de l'ancien "
        "régime ; changement de fonction ; non transposé."},
    ("62010CJ0296", "32003R2201", "19", None): {"v": "exclude", "j":
        "Litispendance lorsque la première juridiction n'est saisie qu'au titre de mesures provisoires : point désormais réglé expressément par "
        "l'article 20, paragraphe 2, du " + IIT + " (« excepté lorsque la compétence … est uniquement fondée sur l'article 15 ») ; la solution est "
        "codifiée par un texte nouveau, de sorte que le critère b (libellé identique) n'est pas rempli."},
    ("62019CJ0025", "32007R1393", "152", None): {"v": "exclude", "j":
        "Artefact d'analyse : le règlement 1393/2007 ne comporte pas d'article 152 (renvoi à un autre acte) ; aucun lien."},
    # --- 44/2001 -> 1215/2012 -----------------------------------------------------------------
    ("62014CJ0004", "32001R0044", "1", None): {"v": "include", "to": [("1", None)], "j":
        "Champ d'application (« matière civile et commerciale », exclusion de l'état des personnes) : l'article 1er, paragraphes 1 et 2, "
        "point a), du règlement (UE) n° 1215/2012 reprend ces éléments ; les ajouts (acta jure imperii, régimes patrimoniaux des partenariats, "
        "obligations alimentaires) ne concernent pas l'astreinte accessoire à une décision sur le droit de garde interprétée ici."},
    ("62018CJ0361", "32001R0044", "1", None): {"v": "exclude", "j":
        "L'arrêt porte sur l'exclusion des « régimes matrimoniaux » appliquée à une union de fait ; l'article 1er, paragraphe 2, point a), "
        "du règlement n° 1215/2012 exclut désormais aussi les régimes patrimoniaux des relations ayant des effets comparables au mariage : "
        "changement de libellé sur le point précis interprété ; non transposé."},
    # --- 1393/2007 -> 2020/1784 ---------------------------------------------------------------
    ("32007R1393", "1", "1"): {"v": "exclude", "j":
        "Champ d'application : l'article 1er du règlement (UE) 2020/1784 est réécrit (signification « transfrontière », exclusion expresse des "
        "acta jure imperii, nouveaux paragraphes 2 et 3 relatifs à l'adresse inconnue et au représentant dans l'État du for) ; les questions "
        "tranchées (qualification civile/commerciale ; signification fictive) sont désormais régies par un texte différent ; non transposé."},
    ("32007R1393", "16", None): {"v": "include", "to": [("21", None)], "j":
        "Actes extrajudiciaires : l'article 21 du règlement (UE) 2020/1784 reprend la règle de l'ancien article 16 (les actes extrajudiciaires "
        "peuvent être transmis et signifiés ou notifiés dans un autre État membre conformément au règlement) ; la notion d'« acte extrajudiciaire » "
        "interprétée est inchangée (considérant relatif à la continuité de la refonte)."},
    # --- 1206/2001 -> 2020/1783 ---------------------------------------------------------------
    ("32001R1206", "17", None): {"v": "include", "to": [("19", None)], "j":
        "Exécution directe de l'acte d'instruction par la juridiction requérante : l'article 19 du règlement (UE) 2020/1783 reprend l'ancien "
        "article 17 (demande à l'organisme central, caractère volontaire, absence de mesures coercitives, conditions de refus) ; le caractère "
        "non exclusif des modes d'obtention des preuves prévus par le règlement, interprété par la Cour, est inchangé."},
}

# --- pairs previously kept on similarity >= 0.72: now reviewed individually --------------------------
def _inc(new_art, what, reg=IIT, cont=CONT):
    return {"v": "include", "to": [(new_art, None)], "j": what + " — disposition reprise, pour la règle interprétée, à l'article " + new_art + " du " + reg + " (tableau de correspondance annexé). " + cont}

R.update({
    ("32003R2201", "1", None): _inc("1", "Champ d'application matériel (matière civile ; responsabilité parentale, y compris mesures de protection de droit public telles que le placement ; exclusions) : l'article 1er, paragraphes 1 et 2, du " + IIT + " reprend les mêmes éléments ; la refonte ajoute seulement l'enlèvement international d'enfants (paragraphe 3)"),
    ("32003R2201", "3", None): _inc("3", "Compétence générale en matière de divorce (critères de résidence habituelle et de nationalité, délais de résidence de six et douze mois)"),
    ("32003R2201", "4", None): _inc("4", "Compétence pour la demande reconventionnelle"),
    ("32003R2201", "5", None): _inc("5", "Conversion de la séparation de corps en divorce"),
    ("32003R2201", "8", None): _inc("7", "Compétence générale en matière de responsabilité parentale fondée sur la résidence habituelle de l'enfant au moment de la saisine"),
    ("32003R2201", "9", None): _inc("8", "Maintien de la compétence de l'ancienne résidence habituelle en matière de droit de visite (délai de trois mois ; acceptation du titulaire du droit de visite)"),
    ("32003R2201", "10", None): _inc("9", "Compétence en cas de déplacement ou de non-retour illicites (maintien de la compétence de l'État de résidence habituelle antérieure jusqu'à l'acquisition d'une nouvelle résidence habituelle et à la réunion des conditions d'acquiescement ou de séjour d'un an avec intégration, mêmes hypothèses i) à iv))"),
    ("32003R2201", "13", None): _inc("11", "Compétence fondée sur la présence de l'enfant lorsque sa résidence habituelle ne peut être établie"),
    ("32003R2201", "14", None): _inc("14", "Compétences résiduelles en matière de responsabilité parentale (renvoi à la loi de l'État membre)"),
    ("32003R2201", "16", None): _inc("17", "Moment de la saisine d'une juridiction (dépôt de l'acte introductif ou réception par l'autorité chargée de la notification, sous condition de diligence du demandeur)"),
    ("32003R2201", "17", None): _inc("18", "Vérification d'office de la compétence et déclaration d'incompétence"),
    ("32003R2201", "21", None): _inc("30", "Reconnaissance de plein droit des décisions sans procédure particulière, y compris pour la mise à jour des actes d'état civil"),
    ("62009CJ0256", "32003R2201", "21", None): {"v": "exclude", "j": "La non-application du régime de reconnaissance aux mesures fondées sur l'ancien article 20 est désormais réglée expressément par l'article 2, paragraphe 1, second alinéa, point b), du " + IIT + " ; texte nouveau, non transposé au titre du critère b."},
    ("62020CJ0646", "32003R2201", "21", None): {"v": "exclude", "j": "La reconnaissance d'un divorce constaté par un officier de l'état civil relève désormais, selon le cas, des règles propres aux actes authentiques et accords (articles 64 à 68 du " + IIT + ") ; qualification non transposable sans examen."},
    ("32003R2201", "53", None): _inc("76", "Désignation et rôle des autorités centrales"),
    ("32003R2201", "63", None): _inc("99", "Traités conclus avec le Saint-Siège (concordats) : maintien du régime particulier de reconnaissance des décisions d'annulation"),
    ("32001R1206", "1", None): _inc("1", "Champ d'application (matière civile ou commerciale ; demande par une juridiction d'un État membre d'un acte d'instruction destiné à une procédure judiciaire engagée ou envisagée) ; caractère non exclusif du règlement", "règlement (UE) 2020/1783", "La refonte n'a pas modifié ces éléments (considérants de la refonte relatifs à la continuité)."),
    ("32001R1206", "3", None): _inc("4", "Organisme central (fonctions d'information et de recherche de solutions)", "règlement (UE) 2020/1783", "La refonte n'a pas modifié ces éléments."),
    ("32001R1206", "14", None): _inc("16", "Cas de refus d'exécution des demandes (droit ou interdiction de déposer ; liste limitative des autres motifs)", "règlement (UE) 2020/1783", "La refonte n'a pas modifié ces éléments."),
    ("32001R1206", "18", None): _inc("22", "Frais (gratuité de principe ; remboursement des honoraires d'experts et d'interprètes ; consignation ou avance)", "règlement (UE) 2020/1783", "La refonte n'a pas modifié ces éléments."),
    ("32007R1393", "5", None): _inc("9", "Traduction des actes (information du requérant sur le droit de refus ; frais de traduction à sa charge)", "règlement (UE) 2020/1784", "La refonte n'a pas modifié ces éléments."),
    ("32007R1393", "19", None): _inc("22", "Défendeur non comparant (sursis à statuer tant que la signification/notification en temps utile n'est pas établie ; faculté de statuer et relevé de forclusion)", "règlement (UE) 2020/1784", "La refonte n'a pas modifié ces éléments."),
    ("32007R1393", "8", None): {"v": "exclude", "j": "Refus de réception de l'acte : l'article 12 du règlement (UE) 2020/1784 reformule le droit de refus et limite l'obligation d'information au moyen du formulaire L au cas où l'acte n'est pas rédigé ou traduit dans la langue officielle du lieu de signification (paragraphe 2), alors que la Cour avait déduit de l'ancien article 8 une obligation d'utiliser systématiquement le formulaire type ; changement de libellé et de fonction sur le point interprété ; non transposé."},
})


def review(celex, act, art, para):
    for k in ((celex, act, art, para), (celex, act, art, None), (act, art, para), (act, art, None)):
        if k in R:
            return R[k]
    return None
