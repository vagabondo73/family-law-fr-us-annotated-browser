#!/usr/bin/env python3
"""frn_build.py — build the French norm corpora (SCOPE §4.1) from Tricoteuses LEGI git mirrors.

Corpora: fr-cc fr-cpc fr-coj fr-casf fr-csp fr-cp fr-cpp fr-cgi fr-css fr-ceseda fr-cpce fr-const fr-textes
Outputs (only this agent's files):
  data/norms/<corpus>.json, data/issues/fr-norms.json, data/coverage/<corpus>.json,
  data/sources.json (merge: only entries with id prefix 'legi-' / 'tj-' written by this script are replaced),
  raw/frn_reports/changes_<date>.json (diff of LEGIARTI / Date de début vs the previous build).

Usage:
  python3 scripts/frn_build.py            # pull mirrors (git fetch --depth 1 + reset), refetch textes, rebuild, report
  python3 scripts/frn_build.py --no-pull  # rebuild from local mirrors / cache only
  python3 scripts/frn_build.py --only fr-cc,fr-cpc
Long runs: setsid nohup python3 scripts/frn_build.py > raw/frn_build.log 2>&1 < /dev/null &
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frn_lib import (ROOT, RAW, TODAY, walk_code, in_force, status_of, parse_front, read, git, clean_text,
                     http_get, TJ_RAW, tj_path, num_key, IN_FORCE_STATES)  # noqa
from frn_select import CODES, labels  # noqa
import frn_issues  # noqa

DATA = os.path.join(ROOT, "data")
TEXTES_CFG = os.path.join(ROOT, "scripts", "frn_textes.json")   # curated list of non-codified texts
TEXTES_CACHE = os.path.join(RAW, "frn_textes")
REPORTS = os.path.join(RAW, "frn_reports")
LF_ART = "https://www.legifrance.gouv.fr/codes/article_lc/%s"
LF_CODE = "https://www.legifrance.gouv.fr/codes/texte_lc/%s"
LF_LODA = "https://www.legifrance.gouv.fr/loda/id/%s"
LF_LODA_ART = "https://www.legifrance.gouv.fr/loda/article_lc/%s"
LF_JORF = "https://www.legifrance.gouv.fr/jorf/id/%s"
TRI_ART = "https://www.tricoteuses.fr/legifrance/articles/%s"


def slug(s):
    s = s.lower().replace("*", "")
    s = re.sub(r"[\s_/]+", "-", s)
    s = re.sub(r"[^a-z0-9.-]", "", s)
    return re.sub(r"-+", "-", s).strip("-")


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ------------------------------------------------------------------ mirrors
def pull(repo_dir, url):
    if not os.path.isdir(repo_dir):
        os.system("git clone -q --depth 1 %s %s" % (url, repo_dir))
        return
    git(repo_dir, "fetch", "-q", "--depth", "1", "origin")
    git(repo_dir, "reset", "-q", "--hard", "FETCH_HEAD")


def repo_url(cfg):
    return "https://git.tricoteuses.fr/%s/%s.git" % (cfg.get("org", "codes"), cfg["repo"])


# ------------------------------------------------------------------ helpers
SEC_PREFIX = re.compile(r"^(Partie|Livre|LIVRE|Titre|TITRE|Sous-titre|Chapitre|Section|Sous-section|Paragraphe|Sous-paragraphe|Annexe)[^:]*:\s*", re.I)


def short_heading(a):
    if not a["path"]:
        return ""
    lab = a["path"][-1]["label"]
    h = SEC_PREFIX.sub("", lab).strip()
    return h[:1].upper() + h[1:] if h else lab


REF_RE = re.compile(r"\barticles?\s+((?:[LRDA]\.?\s?\*?\s?)?\d+(?:-\d+)*(?:\s(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies|[A-Z]{1,2}))?)"
                    r"((?:\s*(?:,|et|à)\s*(?:[LRDA]\.?\s?)?\d+(?:-\d+)*)*)", re.I)


def xrefs_same_code(text, corpus, index):
    out = []
    for m in REF_RE.finditer(text):
        tail = text[m.end(): m.end() + 60]
        if re.match(r"\s*(,\s*)?(du|de la|de l'|des)\s+(code|loi|ordonnance|décret|convention|règlement|traité|arrêté|Constitution)", tail, re.I) \
                and not re.match(r"\s*(,\s*)?du présent code", tail, re.I):
            continue
        nums = [m.group(1)] + re.findall(r"(?:[LRDA]\.?\s?)?\d+(?:-\d+)*", m.group(2) or "")
        for n in nums:
            k = re.sub(r"[\s.]", "", n).upper()
            nid = index.get(k)
            if nid and nid not in out:
                out.append(nid)
    return out[:25]


def hier_node_ids(corpus, a, depth=3):
    ids = []
    base = "fr.code.%s" % corpus.replace("fr-", "")
    cur = base
    for p in a["path"][:depth]:
        cur = cur + "." + slug(p["id"]).replace(".", "-")
        ids.append((cur, p["label"]))
    return base, ids


# ------------------------------------------------------------------ codes
def sort_key(a):
    top = a["path"][0]["label"].lower() if a["path"] else ""
    rank = 0
    if top.startswith("partie"):
        rank = 0 if "législative" in top and "ancienne" not in top else 1 if "ancienne" in top else 2 if "réglementaire" in top else 3
        if "arrêtés" in top or "arretes" in top:
            rank = 4
    elif top.startswith("annexe"):
        rank = 5
    k = num_key(a["num"])
    return (rank, k[0], k[1], tuple(k[2]))


def build_code(cid, cfg, hier):
    repo = os.path.join(RAW, cfg["repo"])
    meta, _ = parse_front(read(os.path.join(repo, "README.md")))
    legitext = meta.get("Identifiant") or cfg["legitext"]
    arts = list(walk_code(repo))
    live = [a for a in arts if in_force(a)]
    sel = [a for a in live if cfg["select"](a)]
    sel.sort(key=sort_key)
    # number index for xrefs (all in-force selected articles of this code)
    ids = {}
    norms = []
    used = set()
    for a in sel:
        nid = "%s-%s" % (cid, slug(a["num"]))
        if nid in used:
            nid = "%s-%s" % (nid, a["legiarti"].lower()[-6:])
        used.add(nid)
        a["_id"] = nid
        ids[re.sub(r"[\s.]", "", a["num"]).upper()] = nid
    base, _ = hier_node_ids(cid, sel[0]) if sel else ("fr.code." + cid[3:], [])
    hroot = hier.setdefault(base, {"id": base, "label": cfg["label"], "children": {}})
    for a in sel:
        L = labels(a)
        rec = {
            "id": a["_id"], "corpus": cid, "side": "fr", "lang": "fr", "kind": "article",
            "num": a["num"], "heading": short_heading(a),
            "path": [dict(label=p["label"], id=p["id"]) for p in a["path"]],
            "text": a["text"], "in_force_since": a["debut"], "status": status_of(a),
            "applies_to": ["FR"],
            "official_url": (LF_LODA_ART if cid == "fr-const" else LF_ART) % a["legiarti"],
            "alt_urls": [{"label": "Tricoteuses", "url": TRI_ART % a["legiarti"]},
                         {"label": "Tricoteuses git", "url": "https://git.tricoteuses.fr/%s/%s/src/branch/main/%s" % (cfg.get("org", "codes"), cfg["repo"], a["file"])}],
            "source_ids": {"legiarti": a["legiarti"], "legitext": legitext},
            "issues": [], "xrefs": [], "interps": [],
        }
        if a["etat"] != "VIGUEUR":
            rec["source_ids"]["legi_etat"] = a["etat"]
        if a.get("fin") and a["fin"] < "2999-01-01":
            rec["in_force_until"] = a["fin"]
        if a["debut"] > TODAY:
            rec["vigueur_diff"] = True
        topical = frn_issues.assign(rec, L)
        _, hids = hier_node_ids(cid, a)
        node = hroot
        for hid, hlab in hids:
            node = node["children"].setdefault(hid, {"id": hid, "label": hlab, "children": {}})
        rec["issues"] = topical + ([hids[-1][0]] if hids else [base])
        rec["xrefs"] = [x for x in xrefs_same_code(a["text"], cid, ids) if x != rec["id"]]
        norms.append(rec)
    if cid == "fr-const":
        norms += const_extras(hroot)
    head = git(repo, "rev-parse", "HEAD")
    stats = {"articles_in_repo": len(arts), "in_force": len(live), "selected": len(sel),
             "states": sorted({a["etat"] for a in sel}), "head": head, "legitext": legitext}
    return norms, stats


# ------------------------------------------------------------------ bloc de constitutionnalité (DDHC, Préambule 1946)
CONST_EXTRAS = [("LEGITEXT000006071192", "ddhc", "Déclaration des droits de l'homme et du citoyen de 1789", "DDHC",
                 {"1", "2", "4", "6", "16", "17"}),
                ("LEGITEXT000006071193", "preambule-1946", "Préambule de la Constitution du 27 octobre 1946", "Préambule 1946", {"PREAMBULE"})]


def const_extras(hroot, refresh=False):
    out = []
    for tid, sl, title, short, wanted in CONST_EXTRAS:
        meta, ttitle, items = parse_text_md(tj_fetch(tid, refresh))
        arts = collect_articles(items, refresh)
        node = hroot["children"].setdefault("fr.code.const." + sl, {"id": "fr.code.const." + sl, "label": title, "children": {}})
        for ar in arts:
            if ar["num"].upper() not in wanted:
                continue
            ameta, abody = parse_front(tj_fetch(ar["id"], refresh))
            a = {"num": ar["num"], "etat": ameta.get("État", ""), "debut": ameta.get("Date de début", ""),
                 "fin": ameta.get("Date de fin", ""), "legiarti": ameta.get("Identifiant", ar["id"])}
            if not in_force(a):
                continue
            rec = {"id": "fr-const-%s-%s" % (sl, slug(ar["num"])), "corpus": "fr-const", "side": "fr", "lang": "fr",
                   "kind": "article", "num": "%s %s" % (short, ar["num"]), "heading": "%s, %s" % (short, "préambule" if ar["num"].upper() == "PREAMBULE" else "art. " + ar["num"]),
                   "path": [{"label": title, "id": sl}], "text": clean_text(abody), "in_force_since": a["debut"],
                   "status": status_of(a), "applies_to": ["FR"], "official_url": LF_LODA_ART % a["legiarti"],
                   "alt_urls": [{"label": "Texte (Légifrance)", "url": LF_LODA % tid}, {"label": "Tricoteuses", "url": TRI_ART % a["legiarti"]}],
                   "source_ids": {"legiarti": a["legiarti"], "legitext": tid},
                   "issues": ["fr.constitution.droits-fondamentaux", node["id"]], "xrefs": [], "interps": []}
            out.append(rec)
    return out


# ------------------------------------------------------------------ textes
EXEC_RE = re.compile(r"^(Le|La) présente? (arrêté|décret|loi|ordonnance|circulaire) sera publiée? au Journal officiel[^\n]*\.?$|(sont|est) chargée?s?,?( chacun| chacune)?( en ce qui (le|la) concerne,?)? de l'exécution|(chargée?|chargés) de l'exécution du présent", re.I)
MODIF_RE = re.compile(r"^(A modifié|A abrogé|A créé|Modifie|Abroge|Crée)\b|^\(?(abrogé|modificateur)"
                      r"|^[^\n]{0,300}\b(est|sont) (ainsi )?(modifiée?s?|remplacée?s?|abrogée?s?|insérée?s?|complétée?s?|ajoutée?s?|rétablie?s?|créée?s?|rédigée?s?)\b"
                      r"|^[^\n]{0,200}\b(est|sont) modifiée?s? conformément", re.I)


def tj_fetch(ident, refresh):
    p = os.path.join(TEXTES_CACHE, "texts" if "TEXT" in ident else "scta" if "SCTA" in ident else "arts", ident + ".md")
    if os.path.exists(p) and not refresh:
        return read(p)
    md = http_get(TJ_RAW + "/" + tj_path(ident))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(md or "")
    time.sleep(0.25)
    return md or ""


def parse_text_md(md):
    """Return (meta, title, items) where items are {'type':'art'|'sec', 'num'/'label', 'id'}."""
    meta, body = parse_front(md)
    titles = re.findall(r"^#{1,2} (.+)$", body, re.M)
    title = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", titles[0]).strip() if titles else ""
    head = re.split(r"\n## (Références faites par|Textes faisant référence|Articles faisant référence|Sections faisant référence)", body)[0]
    m1 = re.search(r"^# .+$", head, re.M)
    if m1:  # section page: skip breadcrumb before its own heading
        head = head[m1.end():]
    items = []
    for line in head.splitlines():
        m = re.match(r"^\s*\* \[article ([^\]]*)\]\([^)]*?((?:LEGI|JORF)ARTI\d+)\.md\)", line)
        if m:
            items.append({"type": "art", "num": m.group(1).strip(), "id": m.group(2)})
            continue
        m = re.match(r"^\s*\* \[(.+)\]\([^)]*?((?:LEGI|JORF)SCTA\d+)\.md\)", line)
        if m:
            lab = m.group(1).strip()
            ended = re.search(r"\(depuis le [0-9-]+ jusqu'au ([0-9-]+)\)$", lab)
            lab2 = re.sub(r"\s*\((depuis|jusqu)[^)]*\)$", "", lab)
            items.append({"type": "sec", "label": lab2, "id": m.group(2), "until": ended.group(1) if ended else None})
    return meta, title, items


def collect_articles(items, refresh, sections=(), depth=0, seen=None):
    seen = set() if seen is None else seen
    out = []
    for it in items:
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        if it["type"] == "art":
            out.append({"num": it["num"], "id": it["id"], "sections": list(sections)})
        elif depth < 8 and not (it.get("until") and it["until"] <= TODAY):
            _, _, sub = parse_text_md(tj_fetch(it["id"], refresh))
            out += collect_articles(sub, refresh, list(sections) + [it["label"]], depth + 1, seen)
    return out


def build_textes(refresh, hier):
    cfg = load(TEXTES_CFG, {"texts": []})
    norms, stats_texts = [], []
    base = "fr.textes"
    hroot = hier.setdefault(base, {"id": base, "label": "Textes non codifiés", "children": {}})
    used = set()
    for t in cfg["texts"]:
        tid = t["id"]
        if t.get("kind") == "circulaire":
            rec = {
                "id": "fr-textes-" + slug(t["slug"]), "corpus": "fr-textes", "side": "fr", "lang": "fr", "kind": "text",
                "num": t.get("number", ""), "heading": t["title"], "path": [{"label": t["title"], "id": slug(t["slug"])}],
                "in_force_since": t.get("date", ""), "status": t.get("status", "en vigueur"), "applies_to": ["FR"],
                "official_url": t["official_url"], "alt_urls": t.get("alt_urls", []),
                "source_ids": {"circulaire": t.get("circ_id", "")}, "issues": t.get("issues", []) + [base + ".circulaires"],
                "xrefs": [], "interps": [], "text_not_ingested": True,
            }
            hroot["children"].setdefault(base + ".circulaires", {"id": base + ".circulaires", "label": "Circulaires publiées (CRPA L. 312-2)", "children": {}})
            norms.append(rec)
            stats_texts.append({"id": tid, "title": t["title"], "articles": 0, "kind": "circulaire"})
            continue
        md = tj_fetch(tid, refresh)
        meta, title, items = parse_text_md(md)
        title = t.get("title") or title
        etat = meta.get("État", "")
        if etat not in IN_FORCE_STATES:
            stats_texts.append({"id": tid, "title": title, "excluded": "état %s" % etat})
            continue
        arts = collect_articles(items, refresh)
        tslug = slug(t["slug"])
        tnode = base + "." + tslug
        hroot["children"].setdefault(tnode, {"id": tnode, "label": title, "children": {}})
        kept = 0
        wanted = set(t.get("articles") or [])
        for ar in arts:
            if wanted and ar["num"] not in wanted:
                continue
            amd = tj_fetch(ar["id"], refresh)
            ameta, abody = parse_front(amd)
            a = {"num": ar["num"], "etat": ameta.get("État", ""), "debut": ameta.get("Date de début", ""),
                 "fin": ameta.get("Date de fin", ""), "legiarti": ameta.get("Identifiant", ar["id"])}
            if not in_force(a):
                continue
            text = clean_text(abody)
            if not text or MODIF_RE.search(text.split("\n\n")[0]):
                continue
            if EXEC_RE.search(text) and len(text) < 1200:  # formule exécutoire / signature
                continue
            if t.get("filter") and not re.search(t["filter"], text, re.I):
                continue
            nid = "fr-textes-%s-art-%s" % (tslug, slug(ar["num"]))
            if nid in used:
                nid += "-" + a["legiarti"][-6:].lower()
            used.add(nid)
            path = [{"label": title, "id": tslug}] + [{"label": s, "id": slug(s)[:40]} for s in ar["sections"]]
            rec = {
                "id": nid, "corpus": "fr-textes", "side": "fr", "lang": "fr", "kind": "article",
                "num": ar["num"], "heading": "%s, art. %s" % (t.get("short", title), ar["num"]),
                "path": path, "text": text, "in_force_since": a["debut"], "status": status_of(a), "applies_to": ["FR"],
                "official_url": (LF_LODA_ART % a["legiarti"]) if a["legiarti"].startswith("LEGIARTI") else (LF_JORF % tid),
                "alt_urls": [{"label": "Texte (Légifrance)", "url": (LF_LODA if tid.startswith("LEGITEXT") else LF_JORF) % tid},
                             {"label": "Tricoteuses git", "url": "https://git.tricoteuses.fr/dila/textes_juridiques/src/branch/main/" + tj_path(a["legiarti"])}],
                "source_ids": {"legiarti": a["legiarti"], "legitext": tid, "nature": meta.get("Nature", ""), "nor": meta.get("NOR", "")},
                "issues": [], "xrefs": [], "interps": [],
            }
            if a["fin"] and a["fin"] < "2999-01-01":
                rec["in_force_until"] = a["fin"]
            topical = frn_issues.assign(rec, title + " > " + " > ".join(ar["sections"]))
            rec["issues"] = sorted(set(topical + t.get("issues", []))) + [tnode]
            norms.append(rec)
            kept += 1
        stats_texts.append({"id": tid, "title": title, "nature": meta.get("Nature"), "etat": etat,
                            "articles_listed": len(arts), "articles": kept})
    return norms, stats_texts


# ------------------------------------------------------------------ issue tree / sources / coverage
def hier_to_list(d):
    out = []
    for k, v in d.items():
        out.append({"id": v["id"], "label": v["label"], "children": hier_to_list(v["children"])})
    return out


def write_sources(entries):
    p = os.path.join(DATA, "sources.json")
    cur = load(p, [])
    if isinstance(cur, dict):
        cur = cur.get("sources", [])
    mine = {e["id"] for e in entries}
    keep = [e for e in cur if e.get("id") not in mine]
    dump(p, keep + entries)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true")
    ap.add_argument("--refresh-textes", action="store_true", help="re-download dila/textes_juridiques files")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = set(x for x in args.only.split(",") if x)
    hier = {}
    sources, report = [], {"date": TODAY, "corpora": {}}
    for cid, cfg in CODES.items():
        if only and cid not in only:
            continue
        repo = os.path.join(RAW, cfg["repo"])
        if not args.no_pull:
            pull(repo, repo_url(cfg))
        norms, st = build_code(cid, cfg, hier)
        outp = os.path.join(DATA, "norms", cid + ".json")
        prev = {n["id"]: n for n in (load(outp, {}) or {}).get("norms", [])}
        dump(outp, {"corpus": cid, "generated": TODAY, "source": {"legitext": st["legitext"], "mirror": repo_url(cfg), "head": st["head"]}, "norms": norms})
        # change report
        cur = {n["id"]: n for n in norms}
        ch = {"added": sorted(set(cur) - set(prev)), "removed": sorted(set(prev) - set(cur)),
              "changed": [{"id": i, "old": prev[i]["source_ids"].get("legiarti"), "new": cur[i]["source_ids"].get("legiarti"),
                           "old_since": prev[i].get("in_force_since"), "new_since": cur[i].get("in_force_since")}
                          for i in sorted(set(cur) & set(prev))
                          if prev[i]["source_ids"].get("legiarti") != cur[i]["source_ids"].get("legiarti")
                          or prev[i].get("in_force_since") != cur[i].get("in_force_since") or prev[i].get("text") != cur[i].get("text")]}
        report["corpora"][cid] = {"count": len(norms), **{k: len(v) for k, v in ch.items()}, "details": ch}
        sources.append({"id": "legi-" + cfg["repo"].replace("_", "-"), "label": "%s (LEGI, miroir Tricoteuses)" % cfg["label"],
                        "official": LF_CODE % st["legitext"] if cid != "fr-const" else LF_LODA % st["legitext"],
                        "channel": "git:" + repo_url(cfg), "check": "git-head", "corpora": [cid],
                        "last_checked": TODAY, "last_version": st["head"]})
        cov = {"corpus": cid, "norms_expected": max(st["selected"], len(norms)), "norms_done": len(norms),
               "interps_candidates": 0, "interps_screened": 0, "interps_included": 0,
               "method": ("Miroir git Tricoteuses %s (HEAD %s), articles LEGI à l'état VIGUEUR/ABROGE_DIFF/MODIFIE (non échus) : %d en vigueur sur %d fichiers ; "
                          "sélection selon SCOPE §4.1 (plages d'articles, intitulés de sections, mots-clés du texte — voir scripts/frn_select.py) : %d retenus. "
                          "Interprétations : hors périmètre de ce pipeline (normes seules).") % (cfg["repo"], st["head"][:12], st["in_force"], st["articles_in_repo"], len(norms)),
               "states_included": st["states"], "gaps": GAPS.get(cid, []), "updated": TODAY}
        dump(os.path.join(DATA, "coverage", cid + ".json"), cov)
        print(cid, len(norms), "added", len(ch["added"]), "removed", len(ch["removed"]), "changed", len(ch["changed"]), flush=True)
    if not only or "fr-textes" in only:
        norms, st = build_textes(args.refresh_textes, hier)
        outp = os.path.join(DATA, "norms", "fr-textes.json")
        prev = {n["id"]: n for n in (load(outp, {}) or {}).get("norms", [])}
        dump(outp, {"corpus": "fr-textes", "generated": TODAY, "texts": st, "norms": norms})
        cur = {n["id"]: n for n in norms}
        ch = {"added": sorted(set(cur) - set(prev)), "removed": sorted(set(prev) - set(cur)),
              "changed": [i for i in sorted(set(cur) & set(prev)) if prev[i].get("source_ids", {}).get("legiarti") != cur[i].get("source_ids", {}).get("legiarti")
                          or prev[i].get("text") != cur[i].get("text")]}
        report["corpora"]["fr-textes"] = {"count": len(norms), **{k: len(v) for k, v in ch.items()}, "details": ch}
        tj_head = ""
        try:
            tj_head = json.loads(http_get("https://git.tricoteuses.fr/api/v1/repos/dila/textes_juridiques/branches/main"))["commit"]["id"]
        except Exception as e:  # noqa
            print("warn: textes_juridiques head", e)
        sources.append({"id": "tj-textes-juridiques", "label": "Textes non codifiés (LEGI/JORF, dila/textes_juridiques, miroir Tricoteuses)",
                        "official": "https://www.legifrance.gouv.fr/liste/loda", "channel": "git:https://git.tricoteuses.fr/dila/textes_juridiques.git",
                        "check": "git-head", "corpora": ["fr-textes"], "last_checked": TODAY, "last_version": tj_head,
                        "texts": [s["id"] for s in st]})
        cfgt = load(TEXTES_CFG, {})
        cov = {"corpus": "fr-textes", "norms_expected": len(norms), "norms_done": len(norms),
               "interps_candidates": 0, "interps_screened": 0, "interps_included": 0,
               "texts_screened": cfgt.get("screened", {}), "texts_included": len([s for s in st if s.get("articles") or s.get("kind") == "circulaire"]),
               "method": cfgt.get("method", ""), "gaps": GAPS.get("fr-textes", []) + cfgt.get("gaps", []), "updated": TODAY}
        dump(os.path.join(DATA, "coverage", "fr-textes.json"), cov)
        print("fr-textes", len(norms), flush=True)
    # issue tree: topical + hierarchy (merge with existing hierarchy nodes when --only)
    ip = os.path.join(DATA, "issues", "fr-norms.json")
    old = load(ip, {}) or {}
    hier_list = hier_to_list(hier)
    if only and old:
        keep = [n for n in old.get("nodes", []) if n["id"].startswith("fr.code.") or n["id"] == "fr.textes"]
        mine = {n["id"] for n in hier_list}
        hier_list = [n for n in keep if n["id"] not in mine and n["id"] != "fr.codes"] + hier_list
        hier_list = [h for h in hier_list if h["id"] != "fr.codes"]
    else:
        hier_list = hier_list
    codes_node = {"id": "fr.codes", "label": "Plan des codes et textes (hiérarchie officielle)", "children":
                  [h for h in hier_list if h["id"] != "fr.codes"]}
    dump(ip, {"side": "fr", "lang": "fr", "generated": TODAY,
              "note": "Arbre des questions (FR) : nœuds thématiques 'fr.<thème>…' et plan des codes 'fr.code.<code>.<livre>.<titre>.<chapitre>' / 'fr.textes.<texte>'.",
              "nodes": frn_issues.export_topics() + [codes_node]})
    write_sources(sources)
    os.makedirs(REPORTS, exist_ok=True)
    dump(os.path.join(REPORTS, "changes_%s.json" % TODAY), report)
    print("report:", {k: {kk: vv for kk, vv in v.items() if kk != "details"} for k, v in report["corpora"].items()})


GAPS = {
    "fr-cc": ["Livre Ier, Titre XI : protection juridique des majeurs (art. 415-495-9, sauf 460-462) exclue — hors périmètre (SCOPE §4).",
              "Livre V (Mayotte) non retenu ; Livre II (biens) hors plages SCOPE sauf renvois.",
              "Articles VIGUEUR_DIFF (versions futures) : le miroir ne publie que la version courante ; les versions différées ne sont pas projetées."],
    "fr-cpc": ["Livre III Titre Ier : sous-sections propres aux majeurs protégés, mandat de protection future et mesure d'accompagnement judiciaire exclues (hors périmètre).",
               "Dispositions générales (Livre Ier, Livre II) non retenues sauf audition de l'enfant, reconnaissance transfrontalière, notifications et commissions rogatoires internationales."],
    "fr-coj": ["Sélection par intitulés (JAF, juridictions des mineurs, pôles VIF) et mots-clés : des articles généraux de compétence du tribunal judiciaire non libellés « famille » peuvent manquer."],
    "fr-casf": ["Livre V (outre-mer) exclu ; Livre IV (assistants familiaux) non retenu."],
    "fr-csp": ["Sélection AMP/gamètes/bioéthique-filiation ; les dispositions sur le consentement aux soins des mineurs (autorité parentale) ne sont pas systématiquement retenues."],
    "fr-cp": ["Sélection par intitulés (atteintes aux mineurs et à la famille, violences, viol/inceste, harcèlement, état civil) et mots-clés (conjoint, concubin, mariage, autorité parentale…)."],
    "fr-cpp": ["Sélection par mots-clés (conjoint, concubin, PACS, autorité parentale, anti-rapprochement, grave danger…) et intitulés ; revue manuelle non exhaustive."],
    "fr-cgi": ["Annexes du CGI (II, III, IV) non intégrées ; IFI et plus-values entre époux non retenus sauf mots-clés."],
    "fr-css": ["Sélection par intitulés (réversion, veuvage, recouvrement des créances alimentaires, ASF) et mots-clés ; régimes spéciaux hors CSS non couverts."],
    "fr-ceseda": ["Sélection par intitulés (membres de famille UE, motif familial, regroupement/réunification familiale, fraude) et mots-clés."],
    "fr-cpce": ["Sélection : paiement direct des pensions alimentaires et articles mentionnant les créances alimentaires/époux."],
    "fr-const": ["Sélection limitée aux articles pertinents : Constitution 1958 (Préambule, 1, 34, 53-55, 61-1, 62, 66, 88-1), DDHC (1, 2, 4, 6, 16, 17 — lus depuis dila/textes_juridiques LEGITEXT000006071192) et Préambule 1946 (LEGITEXT000006071193)."],
    "fr-textes": ["Index table_des_matieres_textes_juridiques (Tricoteuses) figé au 2025-02-08 : les textes publiés après cette date ne sont repérés que par recherche ciblée.",
                  "Circulaires : le fonds CIRCULAIRES (circulaires.legifrance.gouv.fr) n'est pas miroité ; seules des circulaires identifiées par recherche sont listées, sans texte intégral (text_not_ingested). Non vérifiées/non listées : circulaire du 21 septembre 2021 (AMP, JUSC2127286C), du 3 juin 2022 (nom, JUSC2215808C), du 22 septembre 2023 (adoption, JUSC2320454C), publiées au BO Justice.",
                  "Sélection des textes par mots-clés de titre puis exclusion manuelle (scripts/frn_textes_config.py) : des textes familiaux au titre atypique peuvent manquer ; les lois omnibus (J21, LPJ 2019, égalité réelle, simplification) sont filtrées par mots-clés au niveau de l'article.",
                  "Articles modificatifs (« est ainsi modifié », « A modifié… ») exclus par règle textuelle : leur contenu figure dans les codes consolidés ; quelques articles autonomes rédigés sous forme modificative peuvent avoir été écartés.",
                  "Textes postérieurs à février 2025 : essentiellement codifiés (repris via les miroirs de codes) ; aucune recherche exhaustive des textes non codifiés 2025-2026."],
}

if __name__ == "__main__":
    main()
