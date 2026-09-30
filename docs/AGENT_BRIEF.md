# Common brief for every contributing agent

Project root: /home/user/workspace/flb  (raw/ = mirrors & downloads, data/ = output JSON, scripts/ = your scripts, docs/)
READ FIRST: docs/SCOPE.md (perimeter, temporal rule (a)/(b), authorities) and docs/SCHEMA.md (exact JSON shapes, corpus ids).

Rules
1. Binding sources only; interpretations only from the authorities in SCOPE §3; apply the temporal rule SCOPE §2 to
   every norm link and record `basis` (+ `b_method`, `b_justification` for b). Exclude decisions interpreting language
   that has since changed in substance.
2. Hyperlink, don't ingest: store current norm text, citation metadata, official summary (verbatim) and 1–4 short
   verbatim excerpts per decision — never full decision texts. Every record must have a working `official_url`
   to the official/authoritative page (not a search page). Build URLs from identifiers where deterministic
   (e.g. https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI…, /juri/id/JURITEXT…, /cons/id/CONSTEXT…,
   /ceta/id/CETATEXT…, https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:…, https://hudoc.echr.coe.int/eng?i=001-…,
   https://revisor.mo.gov/main/OneSection.aspx?section=452.375, https://www.law.cornell.edu is NOT official → use
   uscode.house.gov / ecfr.gov / supremecourt.gov / courts.mo.gov; CourtListener may be an alt_url and an official_url
   only when no official page exists for that opinion).
3. Never invent citations, dates, numbers or quotes. Every excerpt must be copied verbatim from the fetched source.
   If unverified, don't include it; log it in the coverage ledger `gaps`.
4. Exhaustiveness is the goal (user chose "exhaustive now"). Work systematically (enumerate candidates programmatically,
   screen all, include all qualifying) and write an honest coverage ledger data/coverage/<corpus>.json.
5. Tool notes: the bash tool times out ~30 s per call → run long jobs with `setsid nohup python3 script.py > log 2>&1 < /dev/null & disown`
   and poll; write scripts that checkpoint/resume (JSONL). pplx_sdk content.fetch is BLOCKED for legifrance.gouv.fr,
   courdecassation.fr and courtlistener.com — use the git mirrors / direct HTTP APIs with curl or python urllib instead.
   Reachable: git.tricoteuses.fr (DILA mirrors, Forgejo API /api/v1), courtlistener.com REST API v4 anonymous
   (be polite: ≤1 req/s, back off on 429), revisor.mo.gov (pplx_sdk fetch or curl), huggingface.co.
   Use pplx_sdk search/fetch for other sites (EUR-Lex, HCCH, HUDOC, ecfr, uscode, courts.mo.gov, state.gov).
6. Language: annotations (heading, summary when not official, b_justification, issue labels) in French for fr/eu sides,
   English for us/mo sides; international instruments: English labels, with French titles where France-specific.
7. Only write your own files (the corpora assigned to you + your issue-tree file + your coverage ledgers + scripts/<yourprefix>_*).
   Do not edit other agents' files. Do not push to GitHub. Do not deploy.
8. Finish with a short report: files written, counts (norms, candidates screened, interps included, basis a vs b),
   known gaps, and the exact commands to re-run/refresh your pipeline (these feed the daily update job).
