#!/bin/sh
# Full refresh chain for the Missouri procedural case-law pipeline (resumable steps).
# Usage: sh scripts/mpj_run.sh [SINCE]   (SINCE = API tail start date, default 2025-05-01)
cd /home/user/workspace/flb
SINCE=${1:-2025-05-01}
python3 scripts/mpj_enum.py --since $SINCE && \
python3 scripts/mpj_text.py && \
python3 scripts/mpj_scan.py && \
python3 scripts/moo_mpj_feed.py   # gap-fill feed + mpj screen + build (moo_mpj_feed wraps mpj_build.meta_cl)
