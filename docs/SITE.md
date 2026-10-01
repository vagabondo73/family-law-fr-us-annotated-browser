# Site, build and update tooling

Public URL (planned): https://vagabondo73.github.io/family-law-fr-us-annotated-browser/ — all links in the SPA and in
`site/content/` are relative, so the same bundle works under that sub-path, from any static server, and locally.

## Layout
```
site/
  index.html                 SPA shell (no build step; vanilla ES modules)
  assets/css/app.css         legal-reference theme (Source Serif 4 / Source Sans 3), light + dark, responsive
  assets/js/app.js           bootstrap + hash router
  assets/js/store.js         lazy, fault-tolerant data access (missing file => empty state, never a crash)
  assets/js/panes.js         left source tree (side > corpus > path > norm, lazy) + right issue tree + issue filter
  assets/js/views.js         home, norm, interp, issue, corpus TOC, search, compare, sources, coverage
  assets/js/components.js    legal text rendering (native numbering/indent), badges, interpretation cards
  assets/js/search.js        client-side inverted index, built lazily on first search
  fixtures/                  FIXTURE data set (same layout as data/) — dev only, clearly flagged in the UI
  frame-policy.json          cache of X-Frame-Options/CSP probe results (site_build.py --probe-frames)
  data/        (generated, sharded — no initial fetch above ~1.5 MB)
               manifest.json · corpus/<c>.json (light index: tree, counts `ni`, chunk refs `tc`/`ic`, shared `paths`)
               corpus/<c>/t<k>.json (full norm records ≤ ~600 KB) · corpus/<c>/i<k>.json (interpretations of a group of norms)
               interps/<authority>/<k>.json + interp-index.json (id → [authority, chunk])
               issues.json (trees with precomputed counts) · issue-shards.json + issue-index/<top-node>.json
               search/meta.json · search/p/<2-char prefix>.json (postings) · search/docs/<k>.json (400 docs each)
               mapping/<id>.json · sources.json · coverage.json · build-report.json
  content/     (generated)   <norm-id>.html (full text + all interpretations), corpus-<id>.html, index.html,
                             issues.html, sources.html — static, agent-readable, no JavaScript
  sitemap.xml, robots.txt, .nojekyll (generated)
```

## Axes (SCOPE §4.5)
Norm field `axes` (`["family"]`, `["procedure"]` or both; default `["family"]`). The header switcher (Droit de la famille /
Comparative civil procedure; `#/axis/<id>`) filters the source tree and the issue pane; opening a norm that is not on the current
axis switches automatically. Issue files are assigned to an axis by their `axis` field (or a `-proc` file-name suffix, e.g.
data/issues/mo-proc.json); several files for the same side/axis are merged (norm-based trees first). All data/interps/*.json are
merged regardless of file name (mo-sc.json + mo-sc-proc.json); a decision present in several files keeps one record with unioned
norm links and issues.

Correspondence tables: data/mapping/*.json (e.g. cpc-mo.json — entries {cpc_article, cpc_legiarti, cpc_url, legifrance_url,
mo_norms, equivalence, note_fr, note_en, frcp:[{rule,url}]}) → site/data/mapping/<id>.json, browsable at `#/mapping/<id>`
(`?art=56`, `?q=`, `?eq=partial`) and rendered as a "Correspondances" panel on every Missouri norm listed in `mo_norms` (and on the
fr-cpc norm of the same article number when it exists), plus content/mapping-<id>.html.

Cross-links only (no content copied): every fr-cpc norm links to its page on the CPC annotated browser
(https://vagabondo73.github.io/cpc-annotated-browser/content/article-LEGIARTI….html) — lookup built from that site's
content/index.html (match by LEGIARTI, then by article number, preferring the version in force), cached in
site/xlink-cache/cpc-browser.json (refresh: `site_build.py --refresh-xlinks`); FRCP counterparts from the mapping link to
https://vagabondo73.github.io/frcp-annotated-browser/content/provision-frcp-N.html.

## Routes (permalinks)
`#/` · `#/norm/<id>` (`?hl=term1,term2` highlights, `?i=<interp-id>` opens one interpretation) · `#/interp/<id>` ·
`#/issue/<id>` (also filters the left index) · `#/corpus/<id>` (`?at=<path-id>`) · `#/compare/<norm-id>` ·
`#/search?q=…&t=all|norm|interp&g=all|fr|eu-int|us|mo&a=all|family|procedure` · `#/sources` · `#/coverage` ·
`#/axis/<family|procedure>` · `#/mapping/<id>`.

## Build and run locally
```bash
cd /home/user/workspace/flb
python3 scripts/site_build.py                 # --source auto: data/ if it has norms, else site/fixtures
python3 scripts/site_build.py --source fixtures   # develop against the fixture set
python3 scripts/site_build.py --probe-frames  # also refresh site/frame-policy.json (network)
python3 -m http.server 8765 --directory site  # open http://localhost:8765/
```
`site/data/build-report.json` lists every link dropped by the SCOPE §2 check (basis a with decision < D(norm); basis b without
justification; missing basis), dangling links (norm not yet in the corpus), unknown issue ids, missing official URLs.
`--strict` makes the build fail on errors. The build never writes to `data/`.

Fixtures: `python3 scripts/site_make_fixtures.py` regenerates `site/fixtures/` (French texts and Cour de cassation metadata read
from the local Tricoteuses mirrors; records not verified against an official source carry `fixture_unverified`).

Visual QA: `PW_PATH=~/node_modules/playwright node qa/screenshots.mjs http://localhost:8765/ qa/screens/`
(desktop + mobile, light + dark, 8 routes; console errors are reported).

## Daily check / rebuild / deploy (GitHub Actions)
- `.github/workflows/daily-check.yml`
  - **schedule (05:17 UTC)** or dispatch `task=check`: `scripts/daily_check.py --open-issue` → `data/update-report.json`,
    step summary, artifact; opens (or de-duplicates by fingerprint) an issue labelled `source-change`/`needs-review`.
    Commits only `data/update-report.json`, then triggers `pages.yml` so the Sources page shows the check status.
    Secrets used if present: `PISTE_CLIENT_ID`, `PISTE_CLIENT_SECRET` (Légifrance consult/getArticle per LEGIARTI; Judilibre export).
  - dispatch `task=rebuild`: `scripts/run_pipelines.py --only <ids|all>` (registry: docs/PIPELINES.md) → `site_build.py` →
    `publish_mode=pr` (default) opens a PR for review (Pages deploys on merge) or `direct` commits and deploys to Pages.
- `.github/workflows/pages.yml`: on push to main (data/, site/, build script) or manual → build → deploy `site/` to Pages.
  Repository setting required: Settings → Pages → Source = GitHub Actions.

Check semantics: `git-head` compares `git ls-remote HEAD` with the source's `last_version` (40-hex) and, for Forgejo hosts
(git.tricoteuses.fr), maps changed files to norm ids (`article_<num>.md`) and lists changed articles not in the corpus and new
decision files; `http-hash` compares `sha256:` of the normalised page text (ETag/Last-Modified recorded); HTTP 401/403/429 are
reported as `blocked`, not as changes. Baselines in other formats fall back to the previous report.

## Issue pane
Sections per side are collapsible; opening a norm or a decision opens its side (Missouri, US, EU/INT, France) and collapses the
others. Raw analysis-code nodes (labels such as `01-01-02-01,rj1 …`) are hidden and kept as the "Classement CE" search facet
(`#/search?q=…&ce=1`) and on the decision card. Each norm in the source tree shows its count of qualifying interpretations.

## Notes / limits
- Many official sites refuse framing (Légifrance, HCCH, uscode, revisor, eCFR, GovInfo, HUDOC, CURIA…): the compare view uses the
  frame policy and falls back to a new-tab link; a paste-and-diff panel compares the projected text with the official one word by word.
- Theme follows the OS preference; the toggle is in-memory (no storage APIs).
- Sources: every data/sources*.json file is merged (sources.json, sources-int.json, sources-us.json, sources-mo.json…), both by
  the build and by daily_check.py.
- Search index covers headings, numbers, text, summary rules, citations, numbers/ECLI, titrage, summaries and excerpts (prebuilt at build time; a query
  fetches only the posting shards of its tokens and the doc chunks of the displayed page — about 1 s on the full corpus).


## Search outside the dataset + proposals (2026-10-01)
- `scripts/site_outside.py` gives each norm, at build time, three fields: `outside` (verified deep-link templates), `outside_q` (the pre-filled query) and `propose_url`. They are rendered after the interpretations in the SPA and on the static pages. The block is labelled as outside the closed universe and unscreened. These links are navigation only; no API is called.
- `.github/ISSUE_TEMPLATE/proposal.yml` defines the form fields `norm_id`, `norm_page`, `citation`, `url`, `basis`, `justification`, `excerpt` and `checks`. `propose_url` pre-fills `norm_id`, `norm_page` and the title. The labels `proposal` and `needs-screening` must exist in the repository, or GitHub drops them.
- If one norm's interpretations exceed the chunk budget, they are split across several chunks; `ic` is then a list (for example, mo-rules-84.04 has `ic = [11, 12]`).
- QA: `NORMS='fr-cc-371-1,mo-rsmo-452.375,eu-reg-2019-1111-art-10' PW_PATH=... node qa/outside-check.mjs http://localhost:8765/ qa/screens/ out`
