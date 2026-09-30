# Site agent hand-off — 2026-09-30

Built: static SPA (site/), build (scripts/site_build.py), fixtures (scripts/site_make_fixtures.py), daily check
(scripts/daily_check.py), pipeline runner (scripts/run_pipelines.py + docs/PIPELINES.md), workflows
(.github/workflows/daily-check.yml, pages.yml), QA scripts (qa/screenshots.mjs, qa/axis-check.mjs). Run instructions: docs/SITE.md.

## SCOPE §4.5 support (procedure axis)
- norm `axes`, header axis switcher, axis-filtered source tree and issue pane, `#/axis/<id>`, search facet `a=`.
- all data/interps/*.json merged regardless of file name (duplicates unioned); all data/sources*.json merged.
- data/mapping/*.json → `#/mapping/<id>` view + "Correspondances" panel on Missouri norms (and matching fr-cpc norm) +
  content/mapping-<id>.html.
- fr-cpc → CPC annotated browser cross-links (582/582 matched on the current corpus); FRCP links from mapping rows.
- Fixture mapping site/fixtures/mapping/cpc-mo.json (4 rows, illustrative qualifications flagged FIXTURE).

## Data observations for the other agents (not edited by the site agent)
- data/mapping/cpc-mo.json does not exist yet → procedure axis shows "mapping in preparation".
- Only mo-rules norms carry axes "procedure"; the RSMo procedural chapters (506–517, 525) in mo-rsmo have no `axes` yet.
- data/issues/fr-interps.json (side "fr") holds 767 nodes labelled with raw analysis codes ("01-01-02-01,rj1 actes
  legislatifs et administratifs") — they appear after the fr-norms tree in the French issue pane.
- build-report: 12 basis-a-too-early errors (e.g. mo-app-cl10698445 → mo-rules-78.04, decision 2025-07-15 < D 2026-07-01).
- Missouri sources on courts.mo.gov answer 403 to automated clients → daily check reports them as `blocked`.

## Known limits
- Client-side search index is built on first use (~6 s on 9.4k norms / 13.4k interps); prebuilt sharded index is the next step.
- Large corpus bundles (fr-cc.json ~12.7 MB incl. embedded interps) — consider per-norm interp shards.
- PISTE endpoints implemented but untested without credentials; many official sites refuse framing (link fallback).

## Refinements (second pass, 2026-09-30)
- Issue pane: collapsible side sections; the side of the current norm/decision opens, others collapse, pane scrolls to it.
- Sharding: light corpus index + text chunks + interp chunks; authority chunks; issue-index shards; prebuilt search index
  (848 posting shards, max ~0.9 MB; 23k docs). Largest file in site/data ≈ 1.47 MB. Search ~1 s (was ~6.6 s).
- "Classement CE": issue nodes whose label is a raw analysis code are hidden and exposed as a search facet (ce=1) and on
  the decision card (field `classement_ce`). Current data/issues/fr-interps.json has 0 such nodes (tested with a fixture node).
- Source tree: per-norm badge with the count of qualifying interpretations.
- Root README.md added.
