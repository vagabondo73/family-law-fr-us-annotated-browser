#!/bin/bash
# Relink + rebuild without re-indexing (use after norm files change)
set -e
cd /home/user/workspace/flb/scripts
python3 frj_link.py --phase=1
python3 frj_versions.py
python3 frj_link.py --phase=2
python3 frj_build.py
echo RELINK_DONE
