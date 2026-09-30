# Data schema (JSON) — Family Law Annotated Browser

All data lives in `/home/user/workspace/flb/data/`. UTF-8 JSON, pretty-printed (2 spaces). One file per corpus:
`data/norms/<corpus>.json` and `data/interps/<corpus>.json`. The site loads `data/manifest.json` then corpora lazily.
IDs are stable, lowercase, URL-safe: `[a-z0-9._-]`.

## Corpus ids (use exactly these)
FR: `fr-cc` (Code civil), `fr-cpc`, `fr-coj`, `fr-casf`, `fr-csp`, `fr-cp`, `fr-cpp`, `fr-cgi`, `fr-css`, `fr-ceseda`,
`fr-cpce`, `fr-const` (Constitution 1958 / DDHC as relevant), `fr-textes` (non-codified lois/décrets/arrêtés/circulaires).
EU: `eu-reg` (all EU regulations/directives/Charter/TFEU articles). INT: `int-hcch`, `int-un`, `int-coe`, `int-ciec`,
`int-bilateral`. US: `us-const`, `us-usc`, `us-cfr`, `us-common` (federal judge-made rules). MO: `mo-const`, `mo-rsmo`,
`mo-rules` (Supreme Court Rules + Forms), `mo-common` (Missouri judge-made rules).

## Norm record (`data/norms/<corpus>.json` = {"corpus": id, "generated": ISO date, "norms": [ ... ]})
```json
{
  "id": "fr-cc-371-1",                 // corpus + number
  "corpus": "fr-cc",
  "side": "fr" | "eu" | "int" | "us" | "mo",
  "lang": "fr" | "en",                 // annotation language (FR/EU -> fr; US/MO/HCCH-in-US -> en; int -> en unless FR-specific)
  "kind": "article" | "section" | "rule" | "treaty-article" | "judge-made-rule" | "text",
  "num": "371-1",
  "heading": "Autorité parentale — définition",   // short heading (official heading if any)
  "path": [ {"label":"Livre Ier : Des personnes","id":"livre_ier"}, {"label":"Titre IX : De l'autorité parentale"} ],
  "text": "current official text (plain text, paragraphs separated by \n\n)",   // omit for judge-made rules
  "summary_rule": "…",                 // judge-made-rule only: rule statement mostly in verbatim case language, quotes marked with “ ”
  "rule_sources": ["interp-id", ...],  // judge-made-rule only: cases establishing the rule
  "in_force_since": "2024-02-21",      // D(norm) — see SCOPE §2
  "status": "en vigueur" | "in force" | "signed-not-ratified" | ...,
  "applies_to": ["FR","US","EU","MO"], // for treaties: parties among FR/US/EU
  "official_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049164413",
  "alt_urls": [{"label":"Tricoteuses", "url":"…"}],
  "source_ids": {"legiarti":"LEGIARTI000049164413"},   // any upstream identifiers (celex, rsmo, usc, cfr…)
  "issues": ["fr.autorite-parentale.definition"],       // issue-tree node ids (data/issues.json)
  "xrefs": ["fr-cc-373-2"],            // related norms (any corpus)
  "interps": ["cass-juritext000047123456", …]          // ids of qualifying interpretations (filled by merge step)
}
```

## Interpretation record (`data/interps/<corpus>.json` = {"corpus": id, "interps": [ ... ]})
Interp corpora: `fr-cc-decisions` is NOT used; use by authority: `fr-cons` (Conseil constitutionnel), `fr-cass`,
`fr-ce`, `eu-cjeu`, `coe-ecthr`, `us-scotus`, `us-ca8`, `mo-sc`, `mo-app`.
```json
{
  "id": "cass-juritext000047123456",
  "authority": "fr-cass",
  "court": "Cour de cassation, 1re chambre civile",
  "date": "2023-05-17",
  "number": "21-19.766",               // pourvoi / docket / application no.
  "ecli": "ECLI:FR:CCASS:2023:C100321",
  "citation": "Civ. 1re, 17 mai 2023, n° 21-19.766, publié au Bulletin",   // formatted per side conventions
  "publication": "B" | "P" | "R" | "L" | "Lebon" | "published" | "GC" | …,
  "official_url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000047123456",
  "alt_urls": [{"label":"Cour de cassation","url":"…"},{"label":"CourtListener","url":"…"}],
  "summary": "Official sommaire / headnote where it exists (verbatim) — else short neutral summary",
  "summary_is_official": true,
  "excerpts": ["verbatim key passage 1", "…"],       // 1-4 short verbatim passages (chapeau/attendu, holding)
  "titrage": ["DIVORCE, SEPARATION DE CORPS - Prestation compensatoire - …"],   // official classification if any
  "norms": [
    {"norm": "fr-cc-270", "basis": "a" | "b",
     "cited_version": "LEGIARTI000006422…",           // version actually interpreted, if known
     "b_method": "text-identical" | "functional-review",
     "b_justification": "…"}                          // required when basis = b
  ],
  "issues": ["fr.divorce.prestation-compensatoire.fixation"],
  "lang": "fr" | "en"
}
```
An interpretation appears only if ≥1 of its `norms` entries qualifies under SCOPE §2. Non-qualifying links are dropped.

## Issue tree (`data/issues/<side>.json`)
`{"side":"fr","lang":"fr","nodes":[{"id":"fr.divorce","label":"Divorce","children":[{"id":"fr.divorce.consentement-mutuel","label":"…","children":[]}]}]}`
Sides: `fr`, `eu-int`, `us`, `mo`. Node ids are dot-paths. Every norm and interp should map to ≥1 leaf or node.

## Sources registry (`data/sources.json`)
`[{"id":"legi-code-civil","label":"Code civil (LEGI)","official":"https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006070721","channel":"git:https://git.tricoteuses.fr/codes/code_civil.git","check":"git-head"|"http-hash"|"api","corpora":["fr-cc"],"last_checked":"…","last_version":"…"}]`

## Coverage ledger (`data/coverage/<corpus>.json`)
Honest completeness tracking: `{"corpus":…, "norms_expected":N, "norms_done":N, "interps_candidates":N,
"interps_screened":N, "interps_included":N, "method":"…", "gaps":["…"], "updated":"…"}`.
