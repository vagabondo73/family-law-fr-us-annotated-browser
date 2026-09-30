#!/bin/bash
# Daily incremental refresh of the FR case-law corpora (fr-cass, fr-ce, fr-cons).
# 1) pull the DILA mirrors (shallow), 2) index only new decision files, 3) relink + temporal rule, 4) rebuild outputs.
# Run long: setsid nohup ./frj_update.sh > ../work/frj/update.log 2>&1 < /dev/null & disown
cd /home/user/workspace/flb/raw
for r in cass constit jade code_civil code_de_procedure_civile code_de_l_organisation_judiciaire code_de_l_action_sociale_et_des_familles \
         code_de_la_sante_publique code_penal code_de_procedure_penale code_general_des_impots code_de_la_securite_sociale \
         code_de_l_entree_et_du_sejour_des_etrangers_et_du_droit_d_asile code_des_procedures_civiles_d_execution; do
  [ -d "$r/.git" ] && git -C "$r" pull -q --depth 1 --rebase=false 2>&1 | tail -1 && echo "pulled $r"
done
cd /home/user/workspace/flb/scripts
set -e
python3 frj_catalog.py
python3 frj_index_cass.py --src=cass      # incremental: only files not yet indexed
python3 frj_index_cass.py --src=jade
python3 frj_index_cass.py --src=constit
python3 frj_link.py --phase=1
python3 frj_versions.py                   # cached; fetches only new LEGIARTI ids / versions
python3 frj_link.py --phase=2
python3 frj_build.py
echo UPDATE_DONE
