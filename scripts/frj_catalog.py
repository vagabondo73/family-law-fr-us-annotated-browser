# -*- coding: utf-8 -*-
"""Build the catalog of current articles for the 11 French codes from the Tricoteuses code mirrors.
Output: work/frj/articles.json = {corpus: {num: {...}}}"""
import os, re, sys, json, glob, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from frj_common import *


def main():
    cat = {}
    heads = {}
    for corpus, (d, legitext) in CODES.items():
        base = f"{RAW}/{d}"
        if not os.path.isdir(base):
            print("MISSING", d)
            continue
        try:
            heads[corpus] = subprocess.check_output(["git", "-C", base, "log", "-1", "--format=%H %cI"], text=True).strip()
        except Exception:
            heads[corpus] = ""
        arts = {}
        for f in glob.glob(f"{base}/**/article_*.md", recursive=True):
            x = open(f, encoding="utf-8").read()
            m = FM_RE.match(x)
            if not m:
                continue
            fm = dict(re.findall(r"^([^:\n]+):\s*(.*)$", m.group(1), re.M))
            body = m.group(2)
            body = re.sub(r"^# .*\n", "", body.strip() + "\n", count=1)
            body = re.split(r"\n## \[Autres formats\]", body)[0]
            num = fm.get("Numéro", "").strip()
            if not num:
                continue
            rel = os.path.relpath(f, base)
            rec = {"num": num, "legiarti": fm.get("Identifiant", ""), "debut": fm.get("Date de début", ""),
                   "fin": fm.get("Date de fin", ""), "etat": fm.get("État", ""), "path": rel,
                   "text": clean_xml_text(body).strip()}
            rec["id"] = norm_id(corpus, num)
            rec["perimeter"] = in_perimeter(corpus, num, rel)
            if num in arts and arts[num]["etat"] == "VIGUEUR" and rec["etat"] != "VIGUEUR":
                continue
            arts[num] = rec
        cat[corpus] = arts
        print(corpus, len(arts), sum(1 for a in arts.values() if a["perimeter"]), flush=True)
    for corpus, arts in extra_catalog().items():
        cat[corpus] = arts
        print(corpus, len(arts), flush=True)
    json.dump(cat, open(f"{WORK}/articles.json", "w"), ensure_ascii=False)
    json.dump(heads, open(f"{WORK}/code_heads.json", "w"), indent=1)


if __name__ == "__main__":
    main()
