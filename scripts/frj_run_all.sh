#!/bin/bash
# Full FR case-law pipeline (re-runnable; caches LEGI versions in work/frj/legi)
set -e
cd /home/user/workspace/flb/scripts
python3 frj_catalog.py
python3 frj_index_cass.py --full --src=cass
python3 frj_index_cass.py --full --src=jade
python3 frj_index_cass.py --full --src=constit
python3 frj_link.py --phase=1
python3 frj_versions.py
python3 frj_link.py --phase=2
python3 frj_build.py
echo PIPELINE_DONE
