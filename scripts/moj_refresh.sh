#!/bin/sh
# Missouri case-law pipeline (mo-sc, mo-app, mo-common). Resumable; safe to re-run daily.
# 1) CAP full-text scan (one-time; skips volumes already in raw/moj/cap_done.txt)
# 2) CourtListener enumeration (resumes from raw/moj/cl/enum_state.json; to pick up NEW opinions delete the state entries
#    or set FILED_AFTER in moj_enum.py to the last run date)
# 3) fetch texts, 4) screen, 5) build JSON + ledgers, 6) verify mo-common quotations
set -e
cd /home/user/workspace/flb
python3 scripts/moj_cap.py
python3 scripts/moj_enum.py
python3 scripts/moj_text.py
python3 scripts/moj_ott.py gap; python3 scripts/moj_screen.py && python3 scripts/moj_funcreview.py && python3 scripts/moj_screen.py
python3 scripts/moj_build.py
python3 scripts/moj_common_check.py | tail -n 1
python3 scripts/moj_ott.py urls && python3 scripts/moj_build.py
python3 scripts/moj_qa.py | tail -n 1
