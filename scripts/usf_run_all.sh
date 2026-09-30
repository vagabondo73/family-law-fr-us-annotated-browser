#!/bin/bash
# U.S. federal pipeline (SCOPE §4.2) — full refresh. Long steps: run with
#   setsid nohup bash scripts/usf_run_all.sh > raw/us/run_all.log 2>&1 < /dev/null & disown
set -e
cd /home/user/workspace/flb
python3 scripts/usf_issues.py                 # data/issues/us.json
python3 scripts/usf_const.py                  # data/norms/us-const.json
python3 scripts/usf_usc.py ${REFRESH:+--refresh}   # data/norms/us-usc.json (uscode.house.gov)
python3 scripts/usf_cfr.py ${REFRESH:+--refresh}   # data/norms/us-cfr.json (eCFR API)
python3 scripts/usf_capscan.py us f3d f2d     # CAP bulk regex enumeration -> raw/us/cap_hits (checkpointed; static data)
python3 scripts/usf_seed.py                   # leading SCOTUS cases -> cap_hits / cl_hits
python3 scripts/usf_bound.py --vols 573-585   # SCOTUS bound volumes (official) -> raw/us/cl_hits/scotus-*.json
python3 scripts/usf_slip.py --terms 18-25     # SCOTUS OT2018+ from official supremecourt.gov opinion lists (current term always re-listed)
python3 scripts/usf_bulk.py --since 2019-01-01 && python3 scripts/usf_bulk.py --since 2019-01-01 --step clusters_full && python3 scripts/usf_bulk.py --since 2019-01-01 --step citations
                                              # CourtListener quarterly bulk (no quota; set --date to the newest snapshot)
python3 scripts/usf_ca8bulk.py                # CA8 published >= 2019 -> official ecf.ca8 PDF -> raw/us/cl_hits/cl-*.json
# (optional, API-quota-limited) python3 scripts/usf_clrecent.py
python3 scripts/usf_screen.py                 # LLM screening of new candidates -> raw/us/screen.jsonl (incremental)
python3 scripts/usf_build.py                  # interps + us-common + back-links; writes raw/us/temporal_pending.json
python3 scripts/usf_temporal.py               # basis-b functional review of pending links -> raw/us/temporal.jsonl
python3 scripts/usf_build.py                  # rebuild with temporal verdicts
python3 scripts/usf_coverage.py               # data/sources-us.json + data/coverage/us-*.json
# Daily update job: usf_usc.py --refresh, usf_cfr.py --refresh, usf_slip.py --terms 25-25 (current term),
#   usf_bulk.py (when a new quarterly snapshot exists; --date) + usf_ca8bulk.py, usf_screen.py, usf_build.py, usf_temporal.py, usf_build.py, usf_coverage.py
# and diff data/norms/us-*.json source_ids.text_sha1 / in_force_since to flag amended norms (then re-run temporal review).
