# -*- coding: utf-8 -*-
"""Post-build fixes for data/interps/fr-cass.json, fr-ce.json, fr-cons.json (added 2026-10-12, run after frj_build.py):
1. Conseil constitutionnel: merge decisions published twice by DILA under two CONSTEXT ids (same number and date) into the
   original (lowest) id.
2. Conseil d'État: DILA ships some ECLIs as « ECLI:FR:XX:… »; derive the formation code (CECHR / CESSR) and keep the source
   value in ecli_source.
3. Decisions without excerpts: add verbatim passages from the DILA XML (visa / principle sentences for Cassation, paragraphs
   citing the linked article, Conseil constitutionnel operative part) — never paraphrased."""
import os, re, json, html, glob, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frj_common import ROOT, RAW

DATA = f"{ROOT}/data/interps"


def tp(i):
    d = re.search(r"\d{12}", i).group(0)
    return "/".join([d[0:2], d[2:4], d[4:6], d[6:8], d[8:10]])


def local_xml(c, iid):
    I = iid.split("-", 1)[1].upper()
    pats = {"fr-cons": [f"{RAW}/constit/global/CONS/TEXT/{tp(I)}/{I}.xml"],
            "fr-ce": [f"{RAW}/jade/global/publie/CETA/TEXT/{tp(I)}/{I}.xml"],
            "fr-cass": [f"{RAW}/cass/global/{s}/JURI/TEXT/{tp(I)}/{I}.xml" for s in ("civile", "criminelle", "commerciale", "sociale")]
                       + [f"{RAW}/cass/global/JURI/TEXT/{tp(I)}/{I}.xml"]}[c]
    for p in pats:
        if os.path.exists(p):
            return open(p, encoding="utf-8").read()
    return None


def body(x):
    m = re.search(r"<CONTENU>(.*?)</CONTENU>", x, re.S)
    t = m.group(1) if m else ""
    t = re.sub(r"<br\s*/?>", "\n", t); t = re.sub(r"</p>", "\n", t); t = re.sub(r"<[^>]+>", "", t); t = html.unescape(t)
    return [re.sub(r"[ \t\u00a0]+", " ", l).strip() for l in t.split("\n") if l.strip()]


BAD=re.compile(r"^(Vu la requête|Vu le mémoire|Vu les autres pièces|Par mémoire|Vu le code|Vu la note|Après avoir entendu|Le Conseil constitutionnel a été saisi|LE CONSEIL)",re.I)
def pick(c,lines,norms):
    nums=[n.split('-',2)[2] for n in norms if n.count('-')>=2]
    pat=[re.compile(r'\b'+re.escape(x).replace('\\-','[-‑]')+r'\b',re.I) for x in nums]
    out=[]
    if c=='fr-cass':
        for l in lines:
            if (re.match(r'^(Vu|VU) (l|L)',l) and not BAD.match(l)) or re.match(r"^\d+\. (Selon|Il résulte|Aux termes)",l):
                out.append(l[:600])
            if len(out)>=3: break
    if not out:
        for l in lines:
            if not BAD.match(l) and any(p.search(l) for p in pat) and len(l)>80: out.append(l[:600])
            if len(out)>=2: break
    if c=='fr-cons':
        for i,l in enumerate(lines):
            if re.match(r"^Article (1er|premier)\b",l):
                art=l if len(l)>25 else (l+' '+lines[i+1] if i+1<len(lines) else l)
                out.append(art[:600]); break
    return out[:4]


def main():
    log = {"dedup": [], "ecli": [], "excerpts": 0}
    p = f"{DATA}/fr-cons.json"; d = json.load(open(p))
    by = {}
    for i in d["interps"]:
        by.setdefault((i.get("number"), i.get("date")), []).append(i)
    drop = set()
    for v in by.values():
        if len(v) < 2:
            continue
        v.sort(key=lambda i: i["id"]); keep = v[0]
        for o in v[1:]:
            have = {z["norm"] for z in keep["norms"]}
            keep["norms"] += [z for z in o["norms"] if z["norm"] not in have]
            keep["issues"] = sorted(set(keep.get("issues", [])) | set(o.get("issues", [])))
            keep.setdefault("alt_urls", []).append({"label": "Légifrance (republication DILA, même décision)", "url": o["official_url"]})
            drop.add(o["id"]); log["dedup"].append([keep["id"], o["id"]])
    d["interps"] = [i for i in d["interps"] if i["id"] not in drop]
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
    p = f"{DATA}/fr-ce.json"; d = json.load(open(p))
    for i in d["interps"]:
        e = i.get("ecli") or ""
        if e.startswith("ECLI:FR:XX:"):
            code = "CECHR" if "chambres réunies" in i.get("court", "") else "CESSR" if "SSR" in i.get("court", "") else None
            if code:
                i["ecli_source"] = e; i["ecli"] = e.replace("ECLI:FR:XX:", f"ECLI:FR:{code}:")
                i["ecli_note"] = "ECLI corrigé (code de formation dérivé du champ « formation ») ; valeur DILA d'origine dans ecli_source"
                log["ecli"].append(i["id"])
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
    for c in ("fr-cass", "fr-ce", "fr-cons"):
        p = f"{DATA}/{c}.json"; d = json.load(open(p))
        for it in d["interps"]:
            if it.get("excerpts"):
                continue
            x = local_xml(c, it["id"])
            ex = pick(c, body(x), [z["norm"] for z in it["norms"]]) if x else []
            if ex:
                it["excerpts"] = ex
                it["excerpts_note"] = "Extraits verbatim ajoutés depuis le XML DILA par frj_postfix.py"
                log["excerpts"] += 1
        json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
    # coverage ledgers: counts after merge + basis (c) method note
    note = ("Base (c) (décision de l'utilisateur, 12 octobre 2026) : les décisions interprétant une version antérieure (texte modifié depuis, alinéa modifié, "
            "rédaction antérieure expressément visée, ancienne numérotation) sont conservées comme interprétations historiques ; la version interprétée est "
            "consignée (cited_version, cited_version_period, version_status, version_note). La version en vigueur reste le droit applicable.")
    old_gap = "Anciennes numérotations (« ancien article », « devenu ») : seules les correspondances à texte identique sont retenues."
    new_gap = ("Anciennes numérotations (« ancien article ») : le lien est rattaché à l'article actuel portant le même numéro, signalé en base (c) "
               "« ancienne-numerotation » — l'objet de l'article actuel peut différer ; table de concordance vers l'article successeur non encore établie.")
    for c in ("fr-cass", "fr-ce", "fr-cons"):
        lp = f"{ROOT}/data/coverage/{c}.json"
        if not os.path.exists(lp):
            continue
        L = json.load(open(lp))
        L["interps_included"] = len(json.load(open(f"{DATA}/{c}.json"))["interps"])
        L["gaps"] = [new_gap if g == old_gap else g for g in L.get("gaps", [])]
        if isinstance(L.get("method"), str) and note not in L["method"]:
            L["method"] += " " + note
        json.dump(L, open(lp, "w"), ensure_ascii=False, indent=2)
    print("postfix", {k: (len(v) if isinstance(v, list) else v) for k, v in log.items()})


if __name__ == "__main__":
    main()
