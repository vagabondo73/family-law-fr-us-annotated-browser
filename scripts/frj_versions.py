# -*- coding: utf-8 -*-
"""Fetch LEGI article version histories from dila/donnees_juridiques (per-article raw JSON, cached).
Input: work/frj/need_versions.txt (one current LEGIARTI id per line). Output cache: work/frj/legi/<LEGIARTI>.json"""
import os, sys, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from frj_common import *

CACHE = f"{WORK}/legi"
os.makedirs(CACHE, exist_ok=True)
BASE = "https://git.tricoteuses.fr/dila/donnees_juridiques/raw/branch/main/LEGI/ARTI"


def url_for(aid):
    d = aid[8:]
    return f"{BASE}/{d[0:2]}/{d[2:4]}/{d[4:6]}/{d[6:8]}/{d[8:10]}/{aid}.json"


def fetch(aid, refresh=False):
    p = f"{CACHE}/{aid}.json"
    if os.path.exists(p) and not refresh:
        return json.load(open(p))
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url_for(aid), timeout=30) as r:
                d = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                rec = {"id": aid, "missing": True}
                json.dump(rec, open(p, "w"))
                return rec
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    else:
        return {"id": aid, "error": True}
    ma = d.get("META", {}).get("META_SPEC", {}).get("META_ARTICLE", {})
    vers = d.get("VERSIONS", {}).get("VERSION", [])
    if isinstance(vers, dict):
        vers = [vers]
    vl = []
    for v in vers:
        la = v.get("LIEN_ART", {})
        vl.append({"id": la.get("@id"), "debut": la.get("@debut"), "fin": la.get("@fin"), "etat": la.get("@etat"), "num": la.get("@num")})
    liens = d.get("LIENS", {}) or {}
    ll = liens.get("LIEN", []) if isinstance(liens, dict) else []
    if isinstance(ll, dict):
        ll = [ll]
    modif = [{"typelien": l.get("@typelien"), "sens": l.get("@sens"), "text": norm_ws(l.get("#text", "")),
              "cidtexte": l.get("@cidtexte"), "numtexte": l.get("@numtexte"), "date": l.get("@datesignatexte")}
             for l in ll if l.get("@typelien") in ("MODIFIE", "CREATION", "ABROGE", "TRANSFERE", "CODIFICATION", "MODIFICATION", "CREE", "TRANSFERT")]
    txt = (d.get("BLOC_TEXTUEL") or {}).get("CONTENU", "") or ""
    if isinstance(txt, dict):
        txt = json.dumps(txt, ensure_ascii=False)
    rec = {"id": aid, "num": ma.get("NUM"), "etat": ma.get("ETAT"), "debut": ma.get("DATE_DEBUT"), "fin": ma.get("DATE_FIN"),
           "versions": vl, "text_html": txt, "modif": modif}
    json.dump(rec, open(p, "w"), ensure_ascii=False)
    return rec


def fetch_all(ids, workers=4):
    out = {}
    with ThreadPoolExecutor(workers) as ex:
        for rec in ex.map(fetch, ids):
            out[rec["id"]] = rec
    return out


def main():
    ids = [l.strip() for l in open(f"{WORK}/need_versions.txt") if l.strip()]
    print("current ids", len(ids), flush=True)
    cur = fetch_all(ids)
    vids = sorted({v["id"] for r in cur.values() for v in r.get("versions", []) if v.get("id")} - set(ids))
    print("version ids", len(vids), flush=True)
    for i in range(0, len(vids), 200):
        fetch_all(vids[i:i + 200])
        print("fetched", i + 200, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
