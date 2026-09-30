# Family Law Annotated Browser (FR ↔ US / Missouri) — Scope Charter

Status: validated with the user on 2026-09-30. This charter binds every contributor (human or agent).

## 1. Purpose
A closed "legal universe" of binding legal norms and binding interpretations governing family law in and between
France and the United States (federal law, and Missouri law where state law governs under U.S. federalism),
including all binding international / EU instruments and procedures. It is an annotated code: each norm opens the
binding interpretations that qualify under the temporal rule below, and an issue tree indexes norms and interpretations.

## 2. Temporal rule for binding interpretations (apply to EVERY interpretation)
Let D(norm) = date on which the current version of the norm has been extant in its current formulation
(FR: LEGI "Date de début" of the current LEGIARTI version; RSMo: current "Effective" date; USC: date of last amendment
of the section/subsection interpreted; treaties/regulations: entry into force of the current consolidated text/article).
An interpretation qualifies if:
- (a) its date >= D(norm); or
- (b) its date < D(norm) BUT the interpreted language is identical in wording and function to the current text.
  Record `basis: "b"` with a written `b_justification` (what text the decision interpreted, why it is identical
  in wording and function). Where an automated text comparison proves identity, `b_method: "text-identical"`;
  where a human/agent judgment of functional identity is made, `b_method: "functional-review"`.
Decisions interpreting language that has since changed in substance are EXCLUDED.

## 3. Authorities whose interpretations are binding (included)
- France: Conseil constitutionnel (DC, QPC); Cour de cassation — decisions PUBLISHED (Bulletin/Rapport/Lettre = DILA
  CASS dataset), avis de la Cour de cassation, Assemblée plénière & chambre mixte; Conseil d'État (published/Lebon
  decisions and avis contentieux). NOT included: Cassation arrêts inédits; cours d'appel; first-instance courts.
- EU / Council of Europe / UN: CJEU (preliminary rulings and judgments interpreting included EU instruments);
  ECtHR (judgments against France, and Grand Chamber leading judgments on included Convention articles).
  UN treaty bodies are not binding courts — excluded (may be linked as non-binding context: no).
- U.S.: U.S. Supreme Court; U.S. Court of Appeals for the Eighth Circuit (federal questions incl. ICARA/Hague);
  Supreme Court of Missouri; PUBLISHED opinions of the Missouri Court of Appeals (all districts).
  NOT included: Rule 84.16(b) summary orders/unpublished memoranda; federal district courts; other states' courts.

## 4. Subject-matter perimeter
Core family law + the peripheral areas selected by the user + contract-law components needed to analyse agreements
concluded within a matrimonial regime or its derivatives (PACS, separation, divorce, post-nuptial/pre-nuptial).
Adult protection (tutelle/curatelle; Mo. ch. 475) is OUT of the domestic perimeter; the Hague 2000 Adults Convention
is IN only at treaty level (international-instrument completeness rule).

### 4.1 France (annotations in French)
- Code civil: Titre préliminaire (art. 1–6-1, esp. 3 conflits de lois); Livre Ier entire (personnes: nationalité
  art. 17–33-2, actes de l'état civil, nom, domicile, absence, mariage, divorce, séparation de corps, filiation,
  AMP (311-19 s.), adoption, obligations alimentaires, autorité parentale, minorité, émancipation, PACS & concubinage
  (515-1 s.)); Livre III: successions (720–892), libéralités (893–1099-1, incl. donations entre époux 1091–1099-1),
  Titre III sources d'obligations/contrats (1100–1231-7 — formation, validité, vices du consentement, interprétation,
  effets, inexécution) and régime général des obligations (1304–1352-9) and preuve (1353–1386-1) as needed for
  marital agreements; Titre V régimes matrimoniaux (1387–1581); indivision (815–815-18; 1873-1 s.); prescription (2219–2254).
- Code de procédure civile: art. 1038–1269 area as applicable to family matters (Livre III Titre Ier personnes,
  Titre II régimes matrimoniaux, Titre III successions/libéralités), plus general provisions governing JAF
  procedure, international service (683 s.) and procédure participative (1542 s.) as used in family matters.
- Code de l'organisation judiciaire: JAF and family-matter jurisdiction (L. 213-3 s., R. 213-…).
- Code de l'action sociale et des familles: adoption, pupilles de l'État, ASE, protection de l'enfance.
- Code de la santé publique: AMP / bioéthique provisions (L. 2141-1 s.), filiation-related.
- Code pénal: non-représentation d'enfant (227-5 s.), abandon de famille (227-3), soustraction de mineur (227-7 s.),
  violences au sein du couple (222-…, circonstances aggravantes), bigamie (433-20), mariage forcé etc.
- Code de procédure pénale: ordonnances/mesures relatives aux violences conjugales (bracelet anti-rapprochement,
  TGD, 138, 41-1 …).
- Code général des impôts: fiscalité des pensions alimentaires / prestation compensatoire (80 septies, 156 II 2°,
  199 octodecies), partage (746–750), donations/successions entre époux/PACS (777 s., 790 s., 796-0 bis).
- Code de la sécurité sociale: pension de réversion, ARIPA / intermédiation financière des pensions alimentaires
  (L. 582-1, L. 523-1…).
- CESEDA: family-based residence (regroupement familial, conjoint de Français, parent d'enfant français).
- Code des procédures civiles d'exécution: recouvrement des pensions alimentaires (paiement direct etc.).
- Non-codified textes: lois, ordonnances, décrets, arrêtés in force relevant to the above (e.g. barème indicatif,
  décrets d'application), and circulaires only if opposable (CRPA L. 312-2, published on circulaires.legifrance.gouv.fr).

### 4.2 United States — federal (annotations in English)
- U.S. Constitution: Art. IV §1 (Full Faith and Credit), Art. VI cl. 2 (Supremacy; treaties), Amend. XIV (Due Process
  incl. family-privacy liberty; Equal Protection), Amend. V; Art. I §8 (spending power — Title IV-D), Art. II §2 (treaties).
- 28 U.S.C. 1738A (PKPA), 1738B (FFCCSOA), 1738C; 1 U.S.C. 7 (Respect for Marriage Act).
- 22 U.S.C. 9001–9011 (ICARA) + 22 CFR Part 94; 42 U.S.C. 14901 et seq. (IAA) + 22 CFR Parts 96–99;
  18 U.S.C. 1204 (IPKCA); 22 U.S.C. 9101 et seq. (Goldman Act); Hague Service/Evidence implementation (FRCP 4(f), 28 U.S.C. 1781–1782).
- 42 U.S.C. 651–669b (Title IV-D) + 45 CFR Parts 301–310 (incl. 303.7 intergovernmental cases, 303.3x).
- Tax: 26 U.S.C. 71 (pre-2019 instruments), 215 (repealed; transition), 1041, 152(e), 24, 2056/2523 (marital deduction;
  non-citizen spouse QDOT 2056A), 6015 (innocent spouse). Pensions: 29 U.S.C. 1056(d)(3) & 26 U.S.C. 414(p) (QDRO);
  10 U.S.C. 1408 (USFSPA); 42 U.S.C. 402(b),(c),(e),(f) & 416 (Social Security spousal/divorced-spouse benefits).
- Bankruptcy: 11 U.S.C. 101(14A), 362(b)(2), 507(a)(1), 523(a)(5),(15).
- Immigration/nationality: 8 U.S.C. 1101(b) (child definitions incl. adoption), 1151(b)(2)(A)(i), 1154, 1186a (conditional
  residence), 1401, 1409, 1431 (Child Citizenship Act), 1433; related 8 CFR provisions (204.2, 204.3, 204.300 s., 216).
- Domestic violence (federal penal): 18 U.S.C. 2261–2262, 2261A, 2265 (full faith and credit to protection orders), 922(g)(8),(9).

### 4.3 Missouri (annotations in English)
- RSMo ch. 451 (marriage, marital agreements context), 452 (dissolution, legal separation, maintenance, property
  division, custody, UCCJEA 452.700–452.930, parenting plans), 453 (adoption), 453A? n/a, 454 (support; UIFSA
  454.1500–454.2197; Family Support Division), 455 (Adult Abuse Act / Child Protection Orders), 210 (paternity
  210.817–210.852; child abuse reporting as relevant), 211 (juvenile — TPR 211.442–211.487),
  193 (vital records as relevant), 474 (probate: surviving-spouse rights, elective share 474.160, homestead,
  474.220 marital agreements waiver), 473/474/475 excluded except as above, 432.010 (statute of frauds),
  516 (limitations) as needed, 565 (domestic assault 565.072–565.076; 565.150–565.156 interference with custody).
- Missouri Constitution: art. I §33 (marriage — note Obergefell supersedes), art. I §2.
- Missouri Supreme Court Rules: Rules 41–101 as applicable to family matters (e.g., 55, 74, 75, 78, 84.16), Rule 88
  (Dissolution/Custody/Support incl. 88.01 Form 14 presumed amount), Civil Procedure Forms No. 14 & directions,
  Rule 128 (Rule 128 / court-appointed), Local rules excluded.
- Judge-made (common-law) Missouri rules stated as summary rules with verbatim case language: validity/enforceability
  of antenuptial & postnuptial agreements; separation-agreement unconscionability review (452.325); contract
  interpretation principles applied to marital agreements; equitable doctrines; transmutation/commingling (source of funds
  rule); recognition of foreign-country divorce/custody judgments (comity); choice of law (Restatement (Second)
  Conflict of Laws §§ 187–188 as adopted).

### 4.4 International & EU instruments — completeness rule
Include EVERY instrument of international family law (incl. procedure) binding on France and/or the United States,
individually or collectively, with a status table showing FR / US / EU status (party, signed only, not party).
Instruments binding on neither are excluded; signed-not-ratified ones are listed with status only.
- HCCH: 1961 Apostille; 1965 Service; 1970 Evidence; 1980 Child Abduction; 1993 Intercountry Adoption;
  1996 Child Protection (FR party; US signed); 2000 Protection of Adults (FR party); 2007 Child Support (FR via EU, US);
  2007 Protocol on Law Applicable to Maintenance (EU); 1973 Maintenance Obligations (applicable law) and 1973
  Recognition & Enforcement of Maintenance Decisions (FR); 1958 Maintenance (children) Recognition (FR); 1956 Law
  applicable to maintenance for children (FR); 1961 Protection of Minors (FR, largely replaced); 1978 Matrimonial
  Property Regimes (FR); 1961 Form of Testamentary Dispositions (FR); 1970 Recognition of Divorces (check status);
  1978 Celebration of Marriages (check status); 2019 Judgments (EU — family excluded, list status only).
- UN: 1956 New York Convention on the Recovery Abroad of Maintenance (FR); 1962 Consent to Marriage (US? FR? check);
  CRC 1989 and OP-SC / OP-AC (FR; US party to the two OPs only); ICCPR arts. 23–24 (both); CEDAW art. 16 (FR).
- Council of Europe: ECHR arts. 8, 12, 14; Protocol 7 art. 5; Protocol 12 (FR not party — check); European
  Convention on Custody 1980 (Luxembourg; FR); European Convention on the Adoption of Children (revised 2008 — FR?);
  European Convention on the Exercise of Children's Rights 1996 (FR); Istanbul Convention 2011 (FR); Convention on
  Contact concerning Children 2003 (check FR).
- CIEC (Commission internationale de l'état civil) conventions ratified by France.
- EU: Reg. 2019/1111 (Brussels II ter); Reg. 4/2009 (maintenance); Reg. 1259/2010 (Rome III); Reg. 2016/1103
  (matrimonial property); Reg. 2016/1104 (registered partnerships); Reg. 650/2012 (successions); Reg. 2016/1191
  (public documents); Reg. 2020/1784 (service) & 2020/1783 (evidence) & 1215/2012 (Brussels I bis, only where family-
  adjacent e.g. marital agreements outside 2016/1103 scope); Charter arts. 7, 9, 24, 33; TFEU art. 81(3); Directive
  2004/38 (family members' free movement) & Directive 2003/86 (family reunification) — family-migration link.
- Bilateral France–United States: Consular Convention (1966); Social Security Totalization Agreement (1987);
  Income Tax Convention (1994, arts. on pensions/alimony, art. 18/…); Estate & Gift Tax Convention (1978 as amended 2004);
  any bilateral arrangement on child support (reciprocity declarations under UIFSA/42 USC 659a — France was a
  "foreign reciprocating country"; superseded by Hague 2007 — record status).

## 5. Sources (hyperlink, do not bulk-ingest full documents)
Norm texts are projected (current text) with a link to the official page. Decisions: citation, official link,
official summary/sommaire where it exists, and verbatim excerpts (key passages); never the full text.
- Official link targets: legifrance.gouv.fr (LEGIARTI / JURITEXT / CONSTEXT / CETATEXT / JORFTEXT), conseil-constitutionnel.fr,
  courdecassation.fr, conseil-etat.fr, eur-lex.europa.eu (CELEX / ECLI), curia.europa.eu, hudoc.echr.coe.int,
  hcch.net, treaties.un.org, coe.int/treaty, uscode.house.gov, govinfo.gov, ecfr.gov, supremecourt.gov,
  ca8.uscourts.gov, revisor.mo.gov, courts.mo.gov, state.gov (treaties in force).
- Ingestion channels (mirrors used only to read data; every record links to the official page): Tricoteuses/DILA git
  mirrors of LEGI, CASS, CONSTIT, JADE (Licence Ouverte/Etalab 2.0); CourtListener API (Free Law Project) for U.S.
  opinions; revisor.mo.gov directly; EUR-Lex; HUDOC; HCCH status tables. When PISTE credentials (Légifrance/Judilibre API)
  are provided they become the primary FR verification channel.

## 6. Languages
French for French and EU-in-France annotations; English for U.S., Missouri and Hague/UN/CoE-in-US annotations.
Source texts always in original language.

## 7. Delivery
PUBLIC GitHub repository vagabondo73/family-law-fr-us-annotated-browser (user decision 2026-09-30); GitHub Pages site
(free plan); GitHub Actions daily source check (hash/version diff) that opens an issue/PR with flagged changes.

## 4.5 Independent axis — Comparative civil procedure (CPC ↔ Missouri) (added 2026-09-30, user decision)
- Purpose: map Missouri civil procedure to the French Code de procédure civile ARTICLE-TO-RULE, on an axis separate
  from the family-law issue tree (norm field `axes`: ["family"], ["procedure"] or both).
- Missouri side (ingested + annotated here, English): Missouri Supreme Court Rules 41–101 (all rules/subdivisions in
  force, same `mo-rules` id namespace: mo-rules-<n>) and RSMo procedural chapters 506, 507, 508, 509, 510, 511, 512,
  513, 514, 515, 516, 517, 525 (same `mo-rsmo` namespace). Binding interpretations (Supreme Court of Missouri +
  published Court of Appeals) under the same temporal rule (a)/(b) → interp files data/interps/mo-sc-proc.json and
  mo-app-proc.json (authority mo-sc / mo-app).
- French side: CROSS-LINKS ONLY to the existing CPC annotated browser
  https://vagabondo73.github.io/cpc-annotated-browser/ (content/article-LEGIARTI….html pages; ~2,300 articles with
  Cassation annotations) and to Légifrance. No CPC case law duplicated here beyond the family-law corpus.
- U.S. federal procedure: cross-links only to the FRCP annotated browser
  https://vagabondo73.github.io/frcp-annotated-browser/ (content/provision-frcp-N.html) where a Missouri rule has an
  FRCP counterpart.
- Mapping file: data/mapping/cpc-mo.json — entries {cpc_article, cpc_legiarti, cpc_url (cpc-annotated-browser),
  legifrance_url, mo_norms:[ids], equivalence: "equivalent"|"partial"|"functional"|"none", note_fr, note_en,
  frcp:[{rule, url}]}; every CPC article of Livre Ier (dispositions communes) and Livre II (dispositions particulières
  à chaque juridiction — tribunal judiciaire incl. JAF procedure) plus Livres III–VI where a Missouri counterpart
  exists; articles with no counterpart recorded as equivalence "none".
- JAF: the family-procedure CPC articles in fr-cpc carry cross-links to their cpc-annotated-browser pages.
