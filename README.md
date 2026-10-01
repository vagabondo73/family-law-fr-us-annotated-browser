# Family Law Annotated Browser — Droit de la famille annoté (FR ↔ US / Missouri)

A closed legal universe of **binding family-law norms** and their **binding interpretations** in and between France and the
United States (federal and Missouri), with the EU and international instruments binding France and/or the United States.
There is also an independent **comparative civil-procedure axis** that maps the French Code de procédure civile to Missouri
civil procedure. Each provision shows its current official text, a prominent link to the official source, and every
qualifying decision under the temporal rule. An issue tree indexes both norms and decisions.

- Public site (planned): https://vagabondo73.github.io/family-law-fr-us-annotated-browser/ (repository
  `vagabondo73/family-law-fr-us-annotated-browser`, GitHub Pages; all links are relative)
- Model: https://vagabondo73.github.io/frcp-annotated-browser/ · sibling browsers (cross-links only):
  https://vagabondo73.github.io/cpc-annotated-browser/ and the FRCP browser above

## Scope and rules
[docs/SCOPE.md](docs/SCOPE.md) is authoritative. It covers the perimeter per side (§4.1–4.4, including contract-law provisions for
marital agreements and every international family-law instrument binding FR and/or US). It also defines the comparative-procedure
axis (§4.5) and the **temporal rule (§2)**. A decision qualifies for a norm when it has:
- **basis (a)**: a decision date on or after D(norm), the date the current wording took effect; or
- **basis (b)**: an earlier date, together with a written justification that the interpreted text is identical in wording and function.

The site build enforces §2: failing links are dropped and listed in `site/data/build-report.json`. It never invents or edits
legal content.

## Repository layout
```
docs/      SCOPE.md (perimeter, temporal rule) · SCHEMA.md (JSON records) · PIPELINES.md (ingestion registry)
           SITE.md (site, build, weekly check — details) · AGENT_BRIEF.md (rules for contributing agents)
data/      norms/<corpus>.json · interps/*.json (all merged, any file name) · issues/*.json · mapping/*.json
           sources*.json (all merged) · coverage/*.json · update-report.json (weekly check output)
scripts/   site_build.py + site_shards.py (static site build) · site_make_fixtures.py · daily_check.py (run weekly) · run_pipelines.py · site_outside.py
           + the ingestion scripts of each pipeline (see docs/PIPELINES.md)
site/      the static SPA (index.html, assets/), fixtures/ (clearly marked development sample), generated data/ and content/
.github/workflows/   weekly-check.yml (weekly source check + manual rebuild) · pages.yml (deploy site/ to Pages)
qa/        Playwright visual QA scripts and screenshots
raw/       local mirrors of the source repositories (not published)
```

## Data schema (summary — full definition in docs/SCHEMA.md)
- **Norm** (`data/norms/<corpus>.json` → `{corpus, generated, norms:[…]}`), with these fields:
  - identity and place: `id` (corpus + number, `[a-z0-9._-]`), `corpus`, `side` (fr|eu|int|us|mo), `lang`, `kind`, `num`,
    `heading`, `path` (hierarchy);
  - content: `text` (current official text), or `summary_rule` + `rule_sources` for judge-made rules;
  - dates and status: `in_force_since` (= D), `status`, `applies_to`;
  - links and indexing: `official_url`, `alt_urls`, `source_ids`, `issues`, `xrefs`, `interps`, `axes` (["family"] default,
    ["procedure"], or both).
- **Interpretation** (`data/interps/*.json` → `{corpus, interps:[…]}`), with these fields:
  - `id`, `authority`, `court`, `date`, `number`, `ecli`, `citation`, `publication`;
  - `official_url`, `alt_urls`, `summary` + `summary_is_official`, `excerpts` (verbatim), `titrage`;
  - `norms:[{norm, basis:"a"|"b", b_method, b_justification}]`, `issues`, `lang`.
- **Issue tree** (`data/issues/*.json` → `{side, axis?, lang, nodes:[{id, label, children}]}`): nodes whose label is a raw
  analysis code (e.g. `01-01-02-01,rj1 …`) are hidden from the tree. They are kept as the searchable "Classement CE" facet.
- **Mapping** (`data/mapping/cpc-mo.json`): each entry has `cpc_article`, `cpc_legiarti`, `cpc_url`, `legifrance_url`,
  `mo_norms[]`, `equivalence` (equivalent|partial|functional|none), `note_fr`, `note_en` and `frcp:[{rule,url}]`.
- **Sources** (`data/sources*.json`): each entry has `id`, `label`, `official`, `channel`, `check`
  (git-head|http-hash|api), `corpora`, `last_checked` and `last_version`. The **coverage ledgers** are in `data/coverage/<corpus>.json`.

## Pipelines
[docs/PIPELINES.md](docs/PIPELINES.md) is the registry of ingestion pipelines:
- the pipelines are fr-legi, fr-cass, fr-cons-ce, eu-int, us-federal, missouri, mo-proc, cpc-mo-mapping and issues;
- each pipeline is a fenced block giving its owner, corpora, needed secrets, timeout and `run:` lines.

`python3 scripts/run_pipelines.py [--only id,id] [--dry-run]` runs them and writes `data/pipeline-report.json`. `TODO` lines
are placeholders that are reported and not executed.

## Build and run
```bash
python3 scripts/site_build.py                 # --source auto: data/ if it holds norms, else site/fixtures
python3 -m http.server 8765 --directory site  # http://localhost:8765/
```
Options: `--source data|fixtures`, `--base-url`, `--probe-frames` (refresh the iframe policy cache), `--refresh-xlinks`
(re-read the CPC browser index), `--strict` (fail on build errors).

The build shards its output, so no initial fetch is larger than about 1.5 MB:
- a light corpus index plus text chunks and interpretation chunks, loaded on demand;
- authority chunks;
- the issue index, split by top-level node;
- a **prebuilt search index** (`site/data/search/`: posting shards keyed by token prefix, plus doc chunks).

## Weekly check
`.github/workflows/weekly-check.yml` runs every Monday at 05:17 UTC (bi-weekly alternative: cron "17 5 1,15 * *"). It calls `scripts/daily_check.py --open-issue`, which:
- runs `git ls-remote` on the git mirrors (with Forgejo compare, it maps changed files to norm ids);
- checks HTTP hash, ETag and Last-Modified on official pages (HTTP 401/403/429 are reported as `blocked`);
- queries the PISTE Légifrance and Judilibre APIs when the secrets `PISTE_CLIENT_ID` and `PISTE_CLIENT_SECRET` exist.

It writes `data/update-report.json` and opens or updates a GitHub issue (`source-change`, `needs-review`) when a source changed.
**It never rewrites legal content.** A human, or the responsible pipeline via workflow_dispatch `task=rebuild`, re-ingests.
That rebuild opens a PR by default, or deploys directly with `publish_mode=direct`. `pages.yml` deploys `site/` on every push to main.

## Search outside the dataset, and proposals
Each norm page has a block headed "Rechercher hors du corpus / Search outside the dataset", in both the SPA and the static `content/` pages. It holds deep links pre-filled with the norm's citation, and it is labelled as **outside the closed universe and unscreened**. The templates are in `scripts/site_outside.py`, and each one was checked in a browser on 2026-10-01:

| Side | Searches |
|---|---|
| Missouri | CourtListener (`court=mo moctapp`) and Justia site search |
| U.S. federal | CourtListener (`scotus ca8`) and Justia |
| France | Judilibre, and ArianeWeb (entry link only: ArianeWeb has no query parameter) |
| EU | InfoCuria, EUR-Lex and Judilibre |
| International | HUDOC (Council of Europe instruments), INCADAT (HCCH 1980), Judilibre and CourtListener |

Some engines were left out because their links could not be verified:
- Légifrance: bot wall, and robots.txt disallows automated access;
- law.justia.com and FindLaw: bot wall;
- Google Scholar: bot wall;
- news.mobar.org: its `?s=` parameter is ignored.

The "Proposer pour inclusion / Propose for inclusion" button opens a pre-filled GitHub issue that uses `.github/ISSUE_TEMPLATE/proposal.yml` (labels `proposal` and `needs-screening`). Nothing proposed this way enters the data until it has been screened under SCOPE §2.

## How an agent should consult the site
Prefer the **static, JavaScript-free pages** and the **JSON data**. Do not rely on the SPA's rendering:

| Need | Where |
|---|---|
| Everything, as a hierarchical list | `content/index.html` → `content/corpus-<corpus>.html` |
| One provision + all qualifying interpretations (full text, basis a/b, justification, excerpts, official links, cross-links, correspondences) | `content/<norm-id>.html` (e.g. `content/fr-cc-371-1.html`, `content/mo-rsmo-452.375.html`) |
| Issue tree with the norms and decisions under each node | `content/issues.html` |
| Official sources + check status | `content/sources.html` · `data/sources.json` |
| CPC ↔ Missouri correspondence | `content/mapping-cpc-mo.html` · `data/mapping/cpc-mo.json` |
| Machine-readable catalogue | `data/manifest.json` (corpora, axes, counts, frame policy, build info) |
| Norms of a corpus | `data/corpus/<corpus>.json` (light index; field `tc`/`ic` → `data/corpus/<corpus>/t<k>.json` text, `i<k>.json` interpretations) |
| One interpretation | `data/interp-index.json` (`id → [authority, chunk]`) → `data/interps/<authority>/<chunk>.json` |
| Norms/decisions tagged with an issue | `data/issue-shards.json` → `data/issue-index/<top-node>.json` |
| Full-text lookup | `data/search/meta.json` + `data/search/p/<first-2-chars>.json` (postings `[doc, weight, …]`) + `data/search/docs/<k>.json` |
| What was dropped and why (temporal rule, dangling links) | `data/build-report.json` |
| Every page URL | `sitemap.xml` |

Interactive permalinks are `#/norm/<id>`, `#/interp/<id>`, `#/issue/<id>`, `#/corpus/<id>`, `#/mapping/<id>`,
`#/axis/<family|procedure>`, `#/search?q=…` and `#/compare/<norm-id>`.

Projected texts carry no official authority. Always cite the official source linked on each record.

## Contributing agents
See `docs/AGENT_BRIEF.md`. Write only your own files, follow docs/SCHEMA.md, never invent citations, and do not push or deploy.
