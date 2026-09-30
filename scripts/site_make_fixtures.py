#!/usr/bin/env python3
"""Generate the DEVELOPMENT FIXTURE set in site/fixtures/ (same layout as data/).

FIXTURE DATA — for UI development only. Never publish as the corpus.
French norm texts and Cour de cassation metadata/excerpts are read verbatim from the local
Tricoteuses/DILA mirrors (raw/code_civil, raw/cass) when available. Records whose wording could not be
verified from a local mirror carry "fixture_unverified": true and are labelled as such in the UI.
Run:  python3 scripts/site_make_fixtures.py
"""
import json, re, os, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "site" / "fixtures"
TODAY = datetime.date.today().isoformat()
NOTE = "FIXTURE — development data for the site only; not part of the validated corpus."


def md_article(num):
    hits = list((RAW / "code_civil").rglob(f"article_{num}.md"))
    if not hits:
        return None
    p = hits[0]
    s = p.read_text(encoding="utf-8")
    meta = dict(re.findall(r"^([^:\n]+): (.*)$", s.split("---")[1], re.M))
    body = s.split("\n# Article", 1)[1].split("\n", 1)[1].split("## [Autres formats]")[0]
    body = body.replace("<br />", "").strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    # hierarchy path from README headings
    path = []
    d = p.parent
    while d != RAW / "code_civil":
        rd = d / "README.md"
        if rd.exists():
            m = re.search(r"^# (.+)$", rd.read_text(encoding="utf-8"), re.M)
            idm = re.search(r"^Identifiant: (\S+)", rd.read_text(encoding="utf-8"), re.M)
            path.insert(0, {"label": m.group(1).strip(), "id": d.name, **({"legisecta": idm.group(1)} if idm else {})})
        d = d.parent
    return meta, body, path


def cass(juritext):
    hits = list((RAW / "cass").rglob(f"{juritext}.xml"))
    if not hits:
        return None
    s = hits[0].read_text(encoding="utf-8")
    g = lambda t: (re.search(rf"<{t}>(.*?)</{t}>", s, re.S) or [None, None])[1]
    contenu = re.sub(r"<br\s*/?>", "\n", g("CONTENU") or "")
    return {"titre": g("TITRE"), "date": g("DATE_DEC"), "ecli": g("ECLI"), "num": g("NUMERO_AFFAIRE"),
            "ana": [a.strip() for a in re.findall(r"<ANA ID=\"\d+\">(.*?)</ANA>", s, re.S)],
            "sct": [re.sub(r"\s+", " ", a).strip() for a in re.findall(r"<SCT ID=\"\d+\" TYPE=\"PRINCIPAL\">(.*?)</SCT>", s, re.S)],
            "contenu": contenu}


def sentence_with(text, needle, maxlen=600):
    for para in re.split(r"\n+", text):
        if needle in para:
            para = para.strip()
            i = para.find(needle)
            # clip at ';' boundaries around the needle
            start = para.rfind(";", 0, i) + 1
            m = re.search(r"\.\s+(?=[A-ZÉÈ][a-zéè])", para[i:])
            ends = [e for e in (para.find(";", i), (i + m.start()) if m else -1) if e != -1]
            end = min(ends) if ends else len(para)
            return para[start:end].strip()[:maxlen]
    return None


def legi_norm(num, heading, issues, xrefs=()):
    r = md_article(num)
    if not r:
        return None
    meta, body, path = r
    return {"id": f"fr-cc-{num}", "corpus": "fr-cc", "side": "fr", "lang": "fr", "kind": "article", "num": num,
            "heading": heading, "path": path, "text": body, "in_force_since": meta.get("Date de début"),
            "status": "en vigueur" if meta.get("État") == "VIGUEUR" else meta.get("État", "").lower(),
            "applies_to": ["FR"],
            "official_url": f"https://www.legifrance.gouv.fr/codes/article_lc/{meta['Identifiant']}",
            "alt_urls": [{"label": "Tricoteuses", "url": f"https://www.tricoteuses.fr/legifrance/articles/{meta['Identifiant']}"}],
            "source_ids": {"legiarti": meta["Identifiant"]}, "issues": list(issues), "xrefs": list(xrefs),
            "interps": [], "fixture": True}


def w(rel, obj):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    fr = [n for n in [
        legi_norm("3", "Application de la loi française — lois de police, immeubles, statut personnel", ["fr.conflits.statut-personnel"]),
        legi_norm("270", "Prestation compensatoire — principe", ["fr.divorce.prestation-compensatoire"], ["fr-cc-371-1"]),
        legi_norm("371-1", "Autorité parentale — définition et finalité", ["fr.autorite-parentale.definition"], ["fr-cc-373-2-12"]),
        legi_norm("373-2-12", "Enquête sociale ordonnée par le juge aux affaires familiales", ["fr.autorite-parentale.jaf.enquete-sociale"], ["fr-cc-371-1"]),
    ] if n]
    w("norms/fr-cc.json", {"corpus": "fr-cc", "generated": TODAY, "fixture": True, "_note": NOTE, "norms": fr})

    interps_fr = []
    c = cass("JURITEXT000036214212")
    if c:
        interps_fr.append({
            "id": "cass-juritext000036214212", "authority": "fr-cass", "court": "Cour de cassation, 1re chambre civile",
            "date": c["date"], "number": "16-25.256", "ecli": c["ecli"],
            "citation": "Civ. 1re, 13 déc. 2017, n° 16-25.256, publié au Bulletin", "publication": "B",
            "official_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000036214212",
            "alt_urls": [{"label": "Judilibre (Cour de cassation)", "url": "https://www.courdecassation.fr/decision/" }],
            "summary": c["ana"][0] if c["ana"] else "", "summary_is_official": True,
            "excerpts": [e for e in [sentence_with(c["contenu"], "373-2-12")] if e],
            "titrage": c["sct"][:1],
            "norms": [{"norm": "fr-cc-373-2-12", "basis": "a", "cited_version": "LEGIARTI000006426769"}],
            "issues": ["fr.autorite-parentale.jaf.enquete-sociale"], "lang": "fr", "fixture": True})
        interps_fr[-1]["alt_urls"] = []  # no deterministic Judilibre URL from the mirror
    c = cass("JURITEXT000045823025")
    if c:
        interps_fr.append({
            "id": "cass-juritext000045823025", "authority": "fr-cass", "court": "Cour de cassation, 1re chambre civile (avis)",
            "date": c["date"], "number": "22-70.003", "ecli": c["ecli"],
            "citation": "Cass., avis, 18 mai 2022, n° 22-70.003, publié au Bulletin", "publication": "B",
            "official_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000045823025", "alt_urls": [],
            "summary": "Avis relatif à l'admission en soins psychiatriques d'un mineur à l'initiative des titulaires de l'exercice de l'autorité parentale. (Résumé non officiel — FIXTURE.)",
            "summary_is_official": False,
            "excerpts": [e for e in [sentence_with(c["contenu"], "371-1")] if e],
            "titrage": [],
            "norms": [{"norm": "fr-cc-371-1", "basis": "b", "b_method": "functional-review",
                       "b_justification": "L'avis (18 mai 2022) interprète la version antérieure à la loi n° 2024-120 du 19 février 2024 ; il porte sur la mission de protéger l'enfant « dans sa santé » (al. 2), formulation inchangée — la réforme de 2024 n'a ajouté que « sa vie privée ». Identité de lettre et de fonction du passage interprété. (FIXTURE — justification de démonstration.)"}],
            "issues": ["fr.autorite-parentale.definition", "fr.jur.fixture-code"], "lang": "fr", "fixture": True})
    w("interps/fr-cass.json", {"corpus": "fr-cass", "generated": TODAY, "fixture": True, "_note": NOTE, "interps": interps_fr})

    # --- EU (text reproduced for fixture; verify against EUR-Lex) ---
    w("norms/eu-reg.json", {"corpus": "eu-reg", "generated": TODAY, "fixture": True, "_note": NOTE, "norms": [{
        "id": "eu-reg-2019-1111-7", "corpus": "eu-reg", "side": "eu", "lang": "fr", "kind": "article", "num": "7",
        "heading": "Règlement (UE) 2019/1111 (Bruxelles II ter) — art. 7 : Compétence générale en matière de responsabilité parentale",
        "path": [{"label": "Règlement (UE) 2019/1111 du Conseil du 25 juin 2019", "id": "2019-1111"},
                 {"label": "Chapitre II : Compétence"}, {"label": "Section 2 : Responsabilité parentale"}],
        "text": "1. Les juridictions d'un État membre sont compétentes en matière de responsabilité parentale à l'égard d'un enfant qui réside habituellement dans cet État membre au moment où la juridiction est saisie.\n\n2. Le paragraphe 1 est soumis aux articles 8 à 10.",
        "in_force_since": "2022-08-01", "status": "en vigueur", "applies_to": ["EU", "FR"],
        "official_url": "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32019R1111",
        "alt_urls": [{"label": "EUR-Lex (EN)", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R1111"}],
        "source_ids": {"celex": "32019R1111"}, "issues": ["eu-int.competence.responsabilite-parentale"],
        "xrefs": ["int-hcch-1980-3"], "interps": [], "fixture": True, "fixture_unverified": True}]})

    # --- HCCH 1980 ---
    w("norms/int-hcch.json", {"corpus": "int-hcch", "generated": TODAY, "fixture": True, "_note": NOTE, "norms": [{
        "id": "int-hcch-1980-3", "corpus": "int-hcch", "side": "int", "lang": "en", "kind": "treaty-article", "num": "3",
        "heading": "Hague Convention of 25 October 1980 on the Civil Aspects of International Child Abduction — Art. 3 (wrongful removal or retention)",
        "path": [{"label": "HCCH 1980 Child Abduction Convention", "id": "hcch-1980"}, {"label": "Chapter I – Scope of the Convention"}],
        "text": "The removal or the retention of a child is to be considered wrongful where –\n\na) it is in breach of rights of custody attributed to a person, an institution or any other body, either jointly or alone, under the law of the State in which the child was habitually resident immediately before the removal or retention; and\n\nb) at the time of removal or retention those rights were actually exercised, either jointly or alone, or would have been so exercised but for the removal or retention.\n\nThe rights of custody mentioned in sub-paragraph a) above, may arise in particular by operation of law or by reason of a judicial or administrative decision, or by reason of an agreement having legal effect under the law of that State.",
        "in_force_since": "1983-12-01", "status": "in force", "applies_to": ["FR", "US"],
        "parties": {"FR": "party — in force 1983-12-01", "US": "party — in force 1988-07-01", "EU": "not a party (EU Member States are parties)"},
        "official_url": "https://www.hcch.net/en/instruments/conventions/full-text/?cid=24",
        "alt_urls": [{"label": "HCCH status table", "url": "https://www.hcch.net/en/instruments/conventions/status-table/?cid=24"},
                     {"label": "Texte français (HCCH)", "url": "https://www.hcch.net/fr/instruments/conventions/full-text/?cid=24"}],
        "source_ids": {"hcch_cid": "24"}, "issues": ["eu-int.enlevement.deplacement-illicite", "us.hague.wrongful-removal"],
        "xrefs": ["eu-reg-2019-1111-7"], "interps": [], "fixture": True, "fixture_unverified": True}]})

    # --- US ---
    w("norms/us-usc.json", {"corpus": "us-usc", "generated": TODAY, "fixture": True, "_note": NOTE, "norms": [{
        "id": "us-usc-1-7", "corpus": "us-usc", "side": "us", "lang": "en", "kind": "section", "num": "1 U.S.C. § 7",
        "heading": "Marriage",
        "path": [{"label": "Title 1 — General Provisions", "id": "t1"}, {"label": "Chapter 1 — Rules of Construction"}],
        "text": "(a) For the purposes of any Federal law, rule, or regulation in which marital status is a factor, an individual shall be considered married if that individual's marriage is between 2 individuals and is valid in the State where the marriage was entered into or, in the case of a marriage entered into outside any State, if the marriage is between 2 individuals and is valid in the place where entered into and the marriage could have been entered into in a State.\n\n(b) In this section, the term \"State\" means a State, the District of Columbia, the Commonwealth of Puerto Rico, or any other territory or possession of the United States.\n\n(c) For purposes of subsection (a), in determining whether a marriage is valid in a State or the place where entered into, if outside of any State, only the law of the jurisdiction applicable at the time the marriage was entered into may be considered.",
        "in_force_since": "2022-12-13", "status": "in force", "applies_to": ["US"],
        "official_url": "https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title1-section7&num=0&edition=prelim",
        "alt_urls": [{"label": "GovInfo (Pub. L. 117-228)", "url": "https://www.govinfo.gov/app/details/PLAW-117publ228"}],
        "source_ids": {"usc": "1 USC 7"}, "issues": ["us.marriage.recognition"], "xrefs": [], "interps": [],
        "fixture": True, "fixture_unverified": True}]})
    w("interps/us-scotus.json", {"corpus": "us-scotus", "generated": TODAY, "fixture": True, "_note": NOTE, "interps": [{
        "id": "us-scotus-monasky-v-taglieri-2020", "authority": "us-scotus", "court": "Supreme Court of the United States",
        "date": "2020-02-25", "number": "No. 18-935", "citation": "Monasky v. Taglieri, 589 U.S. 68 (2020)", "publication": "published",
        "official_url": "https://www.supremecourt.gov/opinions/19pdf/18-935_e1pf.pdf",
        "alt_urls": [{"label": "CourtListener", "url": "https://www.courtlistener.com/?q=%22Monasky+v.+Taglieri%22"}],
        "summary": "A child's habitual residence under Article 3 of the Hague Convention depends on the totality of the circumstances; an actual agreement between the parents is not required. (Non-official summary — FIXTURE.)",
        "summary_is_official": False,
        "excerpts": ["We hold that a child's habitual residence depends on the totality of the circumstances specific to the case."],
        "norms": [{"norm": "int-hcch-1980-3", "basis": "a"}], "issues": ["us.hague.habitual-residence"], "lang": "en",
        "fixture": True, "fixture_unverified": True}]})

    # --- Missouri ---
    s452 = ("1.  As used in this chapter, unless the context clearly indicates otherwise:\n\n(1)  \"Custody\" means joint legal custody, sole legal custody, joint physical custody or sole physical custody or any combination thereof;\n\n"
            "(2)  \"Joint legal custody\" means that the parents share the decision-making rights, responsibilities, and authority relating to the health, education and welfare of the child, and, unless allocated, apportioned, or decreed, the parents shall confer with one another in the exercise of decision-making rights, responsibilities, and authority;\n\n"
            "(3)  \"Joint physical custody\" means an order awarding each of the parents significant, but not necessarily equal, periods of time during which a child resides with or is under the care and supervision of each of the parents.  Joint physical custody shall be shared by the parents in such a way as to assure the child of frequent, continuing and meaningful contact with both parents;\n\n"
            "(4)  \"Third-party custody\" means a third party designated as a legal and physical custodian pursuant to subdivision (5) of subsection 5 of this section.\n\n"
            "2.  The court shall determine custody in accordance with the best interests of the child.  There shall be a rebuttable presumption that an award of equal or approximately equal parenting time to each parent is in the best interests of the child.  Such presumption is rebuttable only by a preponderance of the evidence in accordance with all relevant factors, including, but not limited to, the factors contained in subdivisions (1) to (8) of this subsection. […]\n\n[FIXTURE: text truncated after subsection 2 — the full section is in the corpus build.]")
    w("norms/mo-rsmo.json", {"corpus": "mo-rsmo", "generated": TODAY, "fixture": True, "_note": NOTE, "norms": [{
        "id": "mo-rsmo-452.375", "corpus": "mo-rsmo", "side": "mo", "lang": "en", "kind": "section", "num": "452.375",
        "heading": "Custody — definitions — factors determining custody — prohibited, when — public policy of state — custody options — findings required, when — parent plan required — access to records — joint custody not to preclude child support — support, how determined — domestic violence or abuse, specific findings.",
        "path": [{"label": "Title XXX — Domestic Relations", "id": "t30"}, {"label": "Chapter 452 — Dissolution of Marriage, Divorce, Alimony and Separate Maintenance", "id": "ch452"}],
        "text": s452, "in_force_since": "2024-08-28", "status": "in force", "applies_to": ["MO"],
        "official_url": "https://revisor.mo.gov/main/OneSection.aspx?section=452.375",
        "alt_urls": [], "source_ids": {"rsmo": "452.375"}, "issues": ["mo.custody.best-interests"], "xrefs": [], "interps": [],
        "fixture": True}]})
    w("norms/mo-common.json", {"corpus": "mo-common", "generated": TODAY, "fixture": True, "_note": NOTE, "norms": [{
        "id": "mo-common-antenuptial-validity", "corpus": "mo-common", "side": "mo", "lang": "en", "kind": "judge-made-rule",
        "num": "MO-JMR-1", "heading": "Validity and enforceability of antenuptial agreements",
        "path": [{"label": "Marital agreements", "id": "marital-agreements"}],
        "summary_rule": "Missouri courts enforce an antenuptial agreement when it was entered into “freely, fairly, knowingly, understandingly and in good faith and with full disclosure”, and when it is not unconscionable. [FIXTURE — quotation not yet verified against the opinion.]",
        "rule_sources": ["mo-app-fixture-antenuptial"], "in_force_since": None, "status": "in force", "applies_to": ["MO"],
        "official_url": "https://www.courts.mo.gov/page.jsp?id=12086", "alt_urls": [], "source_ids": {},
        "issues": ["mo.marital-agreements.antenuptial"], "xrefs": ["mo-rsmo-452.375"], "interps": [],
        "fixture": True, "fixture_unverified": True}]})
    w("interps/mo-app.json", {"corpus": "mo-app", "generated": TODAY, "fixture": True, "_note": NOTE, "interps": [{
        "id": "mo-app-fixture-antenuptial", "authority": "mo-app", "court": "Missouri Court of Appeals",
        "date": "1979-01-01", "number": "FIXTURE", "citation": "FIXTURE — placeholder Missouri Court of Appeals opinion (antenuptial agreements)",
        "publication": "published", "official_url": "https://www.courts.mo.gov/page.jsp?id=12086", "alt_urls": [],
        "summary": "Placeholder record used to render the judge-made-rule view. Replace with the verified leading case.",
        "summary_is_official": False, "excerpts": [],
        "norms": [{"norm": "mo-common-antenuptial-validity", "basis": "a"}], "issues": ["mo.marital-agreements.antenuptial"],
        "lang": "en", "fixture": True, "fixture_unverified": True}]})

    # --- Procedure axis (SCOPE §4.5): copies of a few real records from data/ (if present) + a FIXTURE mapping ---
    def pick(corpus, ids, axes):
        f = ROOT / "data" / "norms" / f"{corpus}.json"
        if not f.exists():
            return []
        have = {n["id"]: n for n in json.loads(f.read_text(encoding="utf-8")).get("norms", [])}
        out = []
        for i in ids:
            if i in have:
                n = dict(have[i]); n.update({"axes": axes[i], "fixture": True, "interps": []})
                out.append(n)
        return out
    ax = {"fr-cpc-1107": ["family", "procedure"], "mo-rules-55.05": ["procedure"], "mo-rules-74.16": ["family", "procedure"],
          "mo-rsmo-452.310": ["family", "procedure"]}
    fr_cpc = pick("fr-cpc", ["fr-cpc-1107"], ax)
    mo_rules = pick("mo-rules", ["mo-rules-55.05", "mo-rules-74.16"], ax)
    for n in mo_rules:
        n["issues"] = list(n.get("issues") or []) + ["mo-proc." + ("pleadings" if n["num"].startswith("55") else "judgments.fees")]
    mo_extra = pick("mo-rsmo", ["mo-rsmo-452.310"], ax)
    for n in mo_extra:
        n["issues"] = ["mo-proc.family.petition"]
    if fr_cpc:
        w("norms/fr-cpc.json", {"corpus": "fr-cpc", "generated": TODAY, "fixture": True, "_note": NOTE, "norms": fr_cpc})
    if mo_rules:
        w("norms/mo-rules.json", {"corpus": "mo-rules", "generated": TODAY, "fixture": True, "_note": NOTE, "norms": mo_rules})
    if mo_extra:
        d = json.loads((OUT / "norms" / "mo-rsmo.json").read_text(encoding="utf-8"))
        d["norms"] += mo_extra
        w("norms/mo-rsmo.json", d)
    CPCB = "https://vagabondo73.github.io/cpc-annotated-browser/content/"
    FRCPB = "https://vagabondo73.github.io/frcp-annotated-browser/content/"
    w("mapping/cpc-mo.json", {"fixture": True, "_note": NOTE + " Equivalence qualifications are illustrative, not reviewed.",
                              "label_fr": "Correspondances CPC ↔ Missouri (FIXTURE)", "label_en": "CPC ↔ Missouri correspondence (FIXTURE)",
                              "axis": "procedure", "generated": TODAY, "entries": [
        {"cpc_article": "56", "cpc_legiarti": "LEGIARTI000006410156", "cpc_url": CPCB + "article-LEGIARTI000006410156.html",
         "legifrance_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006410156",
         "mo_norms": ["mo-rules-55.05"], "equivalence": "partial",
         "note_fr": "FIXTURE — contenu de l'acte introductif (assignation) / contenu de la petition.",
         "note_en": "FIXTURE — contents of the originating process (assignation) vs. contents of the petition.",
         "frcp": [{"rule": "8", "url": FRCPB + "provision-frcp-8.html"}]},
        {"cpc_article": "700", "cpc_legiarti": "LEGIARTI000006411119", "cpc_url": CPCB + "article-LEGIARTI000006411119.html",
         "legifrance_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006411119",
         "mo_norms": ["mo-rules-74.16"], "equivalence": "functional",
         "note_fr": "FIXTURE — frais non compris dans les dépens / attorney fees (règle américaine : chaque partie supporte ses honoraires sauf texte).",
         "note_en": "FIXTURE — non-taxable costs vs. attorney fees (American rule: each party bears its own fees absent statute or contract).",
         "frcp": [{"rule": "54", "url": FRCPB + "provision-frcp-54.html"}]},
        {"cpc_article": "1107", "cpc_legiarti": None, "cpc_url": None,
         "legifrance_url": fr_cpc[0]["official_url"] if fr_cpc else None,
         "mo_norms": ["mo-rsmo-452.310"], "equivalence": "partial",
         "note_fr": "FIXTURE — acte introductif de l'instance en divorce / petition for dissolution.",
         "note_en": "FIXTURE — originating act of divorce proceedings vs. petition for dissolution of marriage.", "frcp": []},
        {"cpc_article": "1", "cpc_legiarti": "LEGIARTI000006410094", "cpc_url": CPCB + "article-LEGIARTI000006410094.html",
         "legifrance_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006410094",
         "mo_norms": [], "equivalence": "none", "note_fr": "FIXTURE — exemple d'article sans correspondant enregistré.",
         "note_en": "FIXTURE — example of an article with no recorded counterpart.", "frcp": []}]})

    # --- Issue trees ---
    def node(i, l, ch=()):
        return {"id": i, "label": l, "children": list(ch)}
    w("issues/fr.json", {"side": "fr", "lang": "fr", "fixture": True, "nodes": [
        node("fr.conflits", "Conflits de lois", [node("fr.conflits.statut-personnel", "Statut personnel")]),
        node("fr.divorce", "Divorce", [node("fr.divorce.prestation-compensatoire", "Prestation compensatoire")]),
        node("fr.autorite-parentale", "Autorité parentale", [
            node("fr.autorite-parentale.definition", "Définition et finalité"),
            node("fr.autorite-parentale.jaf", "Intervention du JAF", [node("fr.autorite-parentale.jaf.enquete-sociale", "Enquête sociale")])])]})
    w("issues/eu-int.json", {"side": "eu-int", "lang": "fr", "fixture": True, "nodes": [
        node("eu-int.competence", "Compétence internationale", [node("eu-int.competence.responsabilite-parentale", "Responsabilité parentale")]),
        node("eu-int.enlevement", "Enlèvement international d'enfants", [node("eu-int.enlevement.deplacement-illicite", "Déplacement ou non-retour illicite")])]})
    w("issues/us.json", {"side": "us", "lang": "en", "fixture": True, "nodes": [
        node("us.marriage", "Marriage", [node("us.marriage.recognition", "Recognition of marriages")]),
        node("us.hague", "Hague Abduction Convention / ICARA", [node("us.hague.wrongful-removal", "Wrongful removal or retention"),
                                                                node("us.hague.habitual-residence", "Habitual residence")])]})
    w("issues/mo.json", {"side": "mo", "lang": "en", "fixture": True, "nodes": [
        node("mo.custody", "Child custody", [node("mo.custody.best-interests", "Best interests of the child")]),
        node("mo.marital-agreements", "Marital agreements", [node("mo.marital-agreements.antenuptial", "Antenuptial agreements")])]})

    w("issues/mo-proc.json", {"side": "mo-proc", "axis": "procedure", "group": "mo", "lang": "en", "fixture": True,
                              "label_fr": "Missouri — procédure civile", "label_en": "Missouri — civil procedure", "nodes": [
        node("mo-proc.pleadings", "Pleadings and motions (Rule 55)"),
        node("mo-proc.judgments", "Judgments (Rule 74)", [node("mo-proc.judgments.fees", "Attorney fees")]),
        node("mo-proc.family", "Family-court procedure", [node("mo-proc.family.petition", "Petition for dissolution")])]})

    w("issues/fr-interps.json", {"side": "fr", "lang": "fr", "fixture": True,
                                 "_note": "FIXTURE — raw analysis-code node (hidden from the tree, kept as 'Classement CE')", "nodes": [
        node("fr.jur.fixture-code", "00-00-00,rj0 FIXTURE — code d'analyse brut (masqué)")]})

    # --- Sources & coverage ---
    w("sources.json", [
        {"id": "legi-code-civil", "label": "Code civil (LEGI)", "official": "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070721",
         "channel": "git:https://git.tricoteuses.fr/codes/code_civil.git", "check": "git-head", "corpora": ["fr-cc"],
         "last_checked": TODAY, "last_version": None, "fixture": True},
        {"id": "dila-cass", "label": "Cour de cassation (DILA CASS)", "official": "https://www.legifrance.gouv.fr/search/juri",
         "channel": "git:https://git.tricoteuses.fr/dila/cass.git", "check": "git-head", "corpora": ["fr-cass"],
         "last_checked": TODAY, "last_version": None, "fixture": True},
        {"id": "revisor-452-375", "label": "RSMo 452.375 (Revisor of Missouri)", "official": "https://revisor.mo.gov/main/OneSection.aspx?section=452.375",
         "channel": "https://revisor.mo.gov/main/OneSection.aspx?section=452.375", "check": "http-hash", "corpora": ["mo-rsmo"],
         "norm_ids": ["mo-rsmo-452.375"], "last_checked": TODAY, "last_version": None, "fixture": True},
        {"id": "hcch-1980-status", "label": "HCCH 1980 status table", "official": "https://www.hcch.net/en/instruments/conventions/status-table/?cid=24",
         "channel": "https://www.hcch.net/en/instruments/conventions/status-table/?cid=24", "check": "http-hash", "corpora": ["int-hcch"],
         "norm_ids": ["int-hcch-1980-3"], "last_checked": TODAY, "last_version": None, "fixture": True},
        {"id": "legifrance-api", "label": "Légifrance API (PISTE) — article versions", "official": "https://www.legifrance.gouv.fr",
         "channel": "api:legifrance", "check": "api", "corpora": ["fr-cc"], "last_checked": None, "last_version": None, "fixture": True},
    ])
    for cid, ne, nd, ic, isc, ii in [("fr-cc", 4, 4, 2, 2, 2), ("int-hcch", 1, 1, 1, 1, 1), ("mo-rsmo", 1, 1, 0, 0, 0)]:
        w(f"coverage/{cid}.json", {"corpus": cid, "norms_expected": ne, "norms_done": nd, "interps_candidates": ic,
                                   "interps_screened": isc, "interps_included": ii, "method": "FIXTURE — hand-picked sample",
                                   "gaps": ["Fixture set: not exhaustive by design."], "updated": TODAY, "fixture": True})
    (OUT / "README.md").write_text("# FIXTURE DATA\n\n" + NOTE + "\n\nRegenerate with `python3 scripts/site_make_fixtures.py`. "
                                   "Build the site against it with `python3 scripts/site_build.py --source fixtures`.\n"
                                   "Records flagged `fixture_unverified` contain wording not checked against an official source.\n", encoding="utf-8")
    print("fixtures written to", OUT, "| fr norms:", len(fr), "| fr interps:", len(interps_fr))


if __name__ == "__main__":
    main()
