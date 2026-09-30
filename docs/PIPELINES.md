# Ingestion pipelines (per agent) — registry used by the `rebuild` workflow

`scripts/run_pipelines.py` reads the fenced `pipeline` code blocks below, in order, and runs their `run:` lines from the
repository root. Keys: `id` (used by `--only` / workflow input `pipelines`), `owner` (script prefix), `corpora` (reporting),
`needs` (environment variables; if a non-optional one is missing the pipeline is skipped; suffix `?` = optional),
`timeout` (minutes), `run` (one shell command per line).

Each pipeline writes only its own files under `data/`, refreshes `last_version` / `last_checked` of its sources, writes
`data/coverage/<corpus>.json`, and never invents citations (docs/AGENT_BRIEF.md). After the pipelines, run
`python3 scripts/site_build.py`; the workflow opens a pull request (legal content is reviewed before publication) or commits
directly with `publish_mode: direct`.

Execution environments: `needs: FLB_LOCAL_RAW` marks pipelines that depend on large local working sets (raw/, work/: DILA
CASS/JADE/CONSTIT clones, Caselaw Access Project scans, CourtListener bulk texts, prefetched texts) and/or on the Perplexity
SDK (`PPLX_SDK_API_KEY`: LLM-assisted functional review, EUR-Lex/HCCH/revisor fetches). They are run by Computer in the
Perplexity project "Family Law (Fr <-> US)" when the daily check opens a source-change issue. In practice every ingestion
pipeline is local; GitHub Actions performs the daily detection, opens the issue, and deploys Pages.

```pipeline
id: fr-legi
owner: frn
corpora: fr-cc, fr-cpc, fr-coj, fr-casf, fr-csp, fr-cp, fr-cpp, fr-cgi, fr-css, fr-ceseda, fr-cpce, fr-const, fr-textes
needs: FLB_LOCAL_RAW
timeout: 90
run: python3 scripts/frn_build.py
```

```pipeline
id: fr-juris
owner: frj
corpora: fr-cass, fr-ce, fr-cons
needs: FLB_LOCAL_RAW
timeout: 180
run: sh scripts/frj_update.sh
```

```pipeline
id: eu-int
owner: int
corpora: eu-reg, int-hcch, int-un, int-coe, int-ciec, int-bilateral, eu-cjeu, coe-ecthr
needs: FLB_LOCAL_RAW, PPLX_SDK_API_KEY
timeout: 180
run: python3 scripts/int_status_check.py
run: python3 scripts/int_eu_norms.py
run: python3 scripts/int_cjeu_candidates.py
run: python3 scripts/int_cjeu_infocuria.py
run: python3 scripts/int_cjeu.py
run: python3 scripts/int_hudoc_candidates.py
run: python3 scripts/int_ecthr.py
run: python3 scripts/int_ecthr_kwcheck.py
run: python3 scripts/int_link.py
```

```pipeline
id: us-federal
owner: usf
corpora: us-const, us-usc, us-cfr, us-common, us-scotus, us-ca8
needs: FLB_LOCAL_RAW, PPLX_SDK_API_KEY, COURTLISTENER_TOKEN?
timeout: 180
run: python3 scripts/usf_clrecent.py
run: python3 scripts/usf_screen.py
run: python3 scripts/usf_build.py
run: python3 scripts/usf_temporal.py
run: python3 scripts/usf_build.py
run: python3 scripts/usf_coverage.py
```

```pipeline
id: mo-norms
owner: mos
corpora: mo-const, mo-rsmo, mo-rules
needs: FLB_LOCAL_RAW, PPLX_SDK_API_KEY
timeout: 90
run: python3 scripts/mos_check.py || true
run: python3 scripts/mos_fetch.py --refresh
run: python3 scripts/mos_build.py
run: python3 scripts/mos_rules_fetch.py
run: python3 scripts/mos_rules_build.py
run: python3 scripts/mos_issues.py
run: python3 scripts/mop_issues.py
```

```pipeline
id: mo-juris-family
owner: moj
corpora: mo-sc, mo-app, mo-common
needs: FLB_LOCAL_RAW, PPLX_SDK_API_KEY, COURTLISTENER_TOKEN?
timeout: 240
run: sh scripts/moj_refresh.sh
run: python3 scripts/moj_qa.py
```

```pipeline
id: mo-juris-proc
owner: mpj
corpora: mo-sc-proc, mo-app-proc
needs: FLB_LOCAL_RAW, COURTLISTENER_TOKEN?
timeout: 240
run: sh scripts/mpj_run.sh
```

```pipeline
id: cpc-mo-mapping
owner: mop
corpora: mapping/cpc-mo
needs: FLB_LOCAL_RAW, PPLX_SDK_API_KEY
timeout: 120
run: python3 scripts/mop_cpc_articles.py --pull
run: python3 scripts/mop_map2.py --workers 12
run: python3 scripts/mop_build.py
```

