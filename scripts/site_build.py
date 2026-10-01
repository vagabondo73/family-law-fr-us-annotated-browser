#!/usr/bin/env python3
"""Build the static site data + agent-readable pages for the Family Law Annotated Browser.

Reads   data/norms/*.json, data/interps/*.json, data/issues/*.json, data/sources*.json, data/coverage/*.json
        (or site/fixtures/ with --source fixtures; --source auto uses data/ if it holds any norms, else fixtures)
Writes  site/data/manifest.json            corpora + counts, authorities, sides, frame policy, build info
        site/data/corpus/<corpus>.json     norms (interps back-linked) + the interpretations they cite
        site/data/interps/<authority>.json interpretations (validated links only)
        site/data/interp-index.json        interp id -> authority
        site/data/issues.json              merged issue trees;  site/data/issue-index.json  issue -> norms/interps
        site/data/sources.json             merged registry (+ last update-report status)
        site/data/coverage.json            coverage ledgers
        site/data/mapping/<map>.json       correspondence tables (data/mapping/*.json, e.g. cpc-mo.json)
        site/xlink-cache/*.json            cached number->page lookups of the sibling CPC / FRCP annotated browsers
        site/data/build-report.json        every dropped/flagged link (temporal rule SCOPE §2, schema problems)
        site/content/<norm-id>.html        full projected text + all interpretations (agent-readable, no JS)
        site/content/index.html, corpus-<id>.html, issues.html, sources.html
        site/sitemap.xml, site/robots.txt, site/.nojekyll

The build never edits data/: it only validates and projects. Links failing SCOPE §2 are dropped from the
site and listed in build-report.json so the responsible pipeline can fix them.

Usage: python3 scripts/site_build.py [--source auto|data|fixtures] [--base-url URL] [--probe-frames] [--strict]
"""
import argparse, datetime, glob, html, json, os, pathlib, re, shutil, sys, urllib.parse, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import site_shards  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DEFAULT_BASE = "https://vagabondo73.github.io/family-law-fr-us-annotated-browser/"
CPC_BROWSER = "https://vagabondo73.github.io/cpc-annotated-browser/"
FRCP_BROWSER = "https://vagabondo73.github.io/frcp-annotated-browser/"
AXES = [  # independent navigation axes (SCOPE §4.5); norm field `axes`, default ["family"]
    {"id": "family", "label_fr": "Droit de la famille", "label_en": "Family law"},
    {"id": "procedure", "label_fr": "Procédure civile comparée", "label_en": "Comparative civil procedure"},
]
AXIS_IDS = {a["id"] for a in AXES}
CE_CODE = re.compile(r"^\d{2}(?:-\d{2,3})+\s*[,;]")

SIDES = [  # display order; issue-tree side key; chrome language
    {"id": "fr", "label_fr": "France", "label_en": "France", "lang": "fr", "issue_side": "fr"},
    {"id": "eu-int", "label_fr": "UE & international", "label_en": "EU & International", "lang": "fr", "issue_side": "eu-int"},
    {"id": "us", "label_fr": "États-Unis (fédéral)", "label_en": "United States (federal)", "lang": "en", "issue_side": "us"},
    {"id": "mo", "label_fr": "Missouri", "label_en": "Missouri", "lang": "en", "issue_side": "mo"},
]
NORM_SIDE_TO_GROUP = {"fr": "fr", "eu": "eu-int", "int": "eu-int", "us": "us", "mo": "mo"}

CORPORA = {  # id: (group, lang, French label, English label, order)
    "fr-const": ("fr", "fr", "Constitution de 1958 et bloc de constitutionnalité", "French Constitution", 0),
    "fr-cc": ("fr", "fr", "Code civil", "Civil Code", 1),
    "fr-cpc": ("fr", "fr", "Code de procédure civile", "Code of Civil Procedure", 2),
    "fr-coj": ("fr", "fr", "Code de l'organisation judiciaire", "Code of Judicial Organisation", 3),
    "fr-casf": ("fr", "fr", "Code de l'action sociale et des familles", "Social Action and Families Code", 4),
    "fr-csp": ("fr", "fr", "Code de la santé publique", "Public Health Code", 5),
    "fr-cp": ("fr", "fr", "Code pénal", "Criminal Code", 6),
    "fr-cpp": ("fr", "fr", "Code de procédure pénale", "Code of Criminal Procedure", 7),
    "fr-cgi": ("fr", "fr", "Code général des impôts", "General Tax Code", 8),
    "fr-css": ("fr", "fr", "Code de la sécurité sociale", "Social Security Code", 9),
    "fr-ceseda": ("fr", "fr", "Code de l'entrée et du séjour des étrangers et du droit d'asile", "CESEDA (immigration)", 10),
    "fr-cpce": ("fr", "fr", "Code des procédures civiles d'exécution", "Code of Civil Enforcement Procedures", 11),
    "fr-textes": ("fr", "fr", "Textes non codifiés", "Non-codified texts", 12),
    "eu-reg": ("eu-int", "fr", "Droit de l'Union européenne", "European Union law", 20),
    "int-hcch": ("eu-int", "en", "Conventions de La Haye (HCCH)", "Hague Conventions (HCCH)", 21),
    "int-un": ("eu-int", "en", "Nations unies", "United Nations", 22),
    "int-coe": ("eu-int", "en", "Conseil de l'Europe", "Council of Europe", 23),
    "int-ciec": ("eu-int", "fr", "Conventions CIEC", "CIEC conventions", 24),
    "int-bilateral": ("eu-int", "en", "Accords bilatéraux France–États-Unis", "France–U.S. bilateral agreements", 25),
    "us-const": ("us", "en", "Constitution des États-Unis", "U.S. Constitution", 30),
    "us-usc": ("us", "en", "United States Code", "United States Code", 31),
    "us-cfr": ("us", "en", "Code of Federal Regulations", "Code of Federal Regulations", 32),
    "us-common": ("us", "en", "Règles jurisprudentielles fédérales", "Federal judge-made rules", 33),
    "mo-const": ("mo", "en", "Constitution du Missouri", "Missouri Constitution", 40),
    "mo-rsmo": ("mo", "en", "Revised Statutes of Missouri", "Revised Statutes of Missouri (RSMo)", 41),
    "mo-rules": ("mo", "en", "Règles de la Cour suprême du Missouri", "Missouri Supreme Court Rules & Forms", 42),
    "mo-common": ("mo", "en", "Règles jurisprudentielles du Missouri", "Missouri judge-made rules", 43),
}
AUTHORITIES = {
    "fr-cons": ("fr", "Conseil constitutionnel"), "fr-cass": ("fr", "Cour de cassation"), "fr-ce": ("fr", "Conseil d'État"),
    "eu-cjeu": ("fr", "Cour de justice de l'Union européenne"), "coe-ecthr": ("fr", "Cour européenne des droits de l'homme"),
    "us-scotus": ("en", "Supreme Court of the United States"), "us-ca8": ("en", "U.S. Court of Appeals for the Eighth Circuit"),
    "mo-sc": ("en", "Supreme Court of Missouri"), "mo-app": ("en", "Missouri Court of Appeals"),
}
# Hosts known (or probed) to refuse framing (X-Frame-Options / CSP frame-ancestors). "unknown" -> the SPA tries an iframe.
FRAME_DENY_DEFAULT = ["legifrance.gouv.fr", "www.legifrance.gouv.fr", "eur-lex.europa.eu", "curia.europa.eu",
                      "hudoc.echr.coe.int", "www.courdecassation.fr", "www.conseil-constitutionnel.fr",
                      "www.conseil-etat.fr", "www.supremecourt.gov", "www.govinfo.gov", "www.ecfr.gov", "www.courtlistener.com", "www.hcch.net"]


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, code, msg, **kw):
        self.items.append({"level": level, "code": code, "msg": msg, **kw})


def load_json(p, rep):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception as e:  # tolerate broken files written concurrently by other agents
        rep.add("error", "bad-json", f"{p}: {e}", file=str(p))
        return None


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def dump(p, obj, compact=True):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) if compact else json.dumps(obj, ensure_ascii=False, indent=2)
    p.write_text(txt, encoding="utf-8")


def pick_source(arg):
    data = ROOT / "data"
    fx = SITE / "fixtures"
    if arg == "data":
        return data, False
    if arg == "fixtures":
        return fx, True
    has = any(glob.glob(str(data / "norms" / "*.json")))
    return (data, False) if has else (fx, True)


def iso(d):
    return d if isinstance(d, str) and re.match(r"^\d{4}-\d{2}-\d{2}", d) else None


def issue_ancestors(iid):
    parts = iid.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts) + 1)]


def probe_frames(urls, rep):
    policy = {}
    hosts = {}
    for u in urls:
        h = urllib.parse.urlparse(u).hostname
        if h and h not in hosts:
            hosts[h] = u
    for h, u in sorted(hosts.items()):
        try:
            req = urllib.request.Request(u, method="GET", headers={"User-Agent": "flb-site-build/1.0 (+frame-policy probe)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                xfo = (r.headers.get("X-Frame-Options") or "").lower()
                csp = (r.headers.get("Content-Security-Policy") or "").lower()
            deny = bool(xfo) or ("frame-ancestors" in csp and "*" not in csp.split("frame-ancestors", 1)[1].split(";")[0])
            policy[h] = "deny" if deny else "allow"
        except Exception as e:
            policy[h] = "unknown"
            rep.add("info", "frame-probe-failed", f"{h}: {e}")
    return policy


def load_mappings(src, norms, rep):
    """data/mapping/*.json -> [{id, label_*, axis, entries:[…]}]; entries validated, unknown Missouri ids flagged (kept, unlinked)."""
    out = []
    for f in sorted(glob.glob(str(src / "mapping" / "*.json"))):
        d = load_json(f, rep)
        if d is None:
            continue
        mid = pathlib.Path(f).stem
        entries = d.get("entries", []) if isinstance(d, dict) else d
        meta = d if isinstance(d, dict) else {}
        good = []
        for e in entries or []:
            art = str(e.get("cpc_article") or "").strip()
            if not art:
                rep.add("error", "mapping-no-article", f"{mid}: entry without cpc_article — dropped")
                continue
            if e.get("equivalence") not in ("equivalent", "partial", "functional", "none"):
                rep.add("warn", "mapping-equivalence", f"{mid} art. {art}: equivalence {e.get('equivalence')!r} unknown")
            for m in e.get("mo_norms") or []:
                if m not in norms:
                    rep.add("warn", "mapping-dangling", f"{mid} art. {art} → {m}: Missouri norm not in corpus (shown unlinked)", norm=m)
            e["cpc_article"] = art
            e["fr_norm"] = f"fr-cpc-{art.lower().replace(' ', '-')}" if f"fr-cpc-{art.lower().replace(' ', '-')}" in norms else None
            good.append(e)
        good.sort(key=lambda e: natkey(e["cpc_article"]))
        out.append({"id": mid, "label_fr": meta.get("label_fr", "Correspondances CPC ↔ Missouri"),
                    "label_en": meta.get("label_en", "CPC ↔ Missouri correspondence"), "axis": meta.get("axis", "procedure"),
                    "generated": meta.get("generated"), "fixture": bool(meta.get("fixture")), "entries": good})
    return out


def sibling_index(url, pattern, cache, refresh, rep):
    """Number -> {url, legiarti, abrogated} lookup built from a sibling browser's static index page (cached)."""
    if cache.exists() and not refresh:
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "flb-site-build/1.0 (+cross-links)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            page_html = r.read().decode("utf-8", "replace")
    except Exception as e:
        rep.add("warn", "xlink-index-unavailable", f"{url}: {e} — cross-links omitted")
        return json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    idx = {}
    for attrs, href, legi, num in re.findall(pattern, page_html):
        num = html.unescape(num).strip()
        ab = "abrogated" in attrs
        if num not in idx or (idx[num]["abrogated"] and not ab):  # prefer the version in force
            idx[num] = {"url": href, "legiarti": legi, "abrogated": ab}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"_source": url, "_fetched": datetime.date.today().isoformat(), **idx}, ensure_ascii=False, indent=0), encoding="utf-8")
    return idx


def apply_xlinks(norms, mappings, cpc_pages, rep):
    """Adds n["xlinks"] (sibling CPC / FRCP browser pages) and n["correspondences"] (mapping rows) — links only."""
    by_legi = {v["legiarti"]: v for k, v in cpc_pages.items() if isinstance(v, dict)}
    for nid, n in norms.items():
        if n["corpus"] != "fr-cpc":
            continue
        legi = (n.get("source_ids") or {}).get("legiarti")
        hit = by_legi.get(legi) or cpc_pages.get(str(n.get("num")))
        if isinstance(hit, dict):
            n.setdefault("xlinks", []).append({"kind": "cpc-browser", "url": hit["url"],
                                               "label": "CPC annoté (jurisprudence de la Cour de cassation)"})
        elif cpc_pages:
            rep.add("info", "xlink-cpc-missing", f"{nid}: article {n.get('num')} not found in the CPC annotated browser index", norm=nid)
    for m in mappings:
        for e in m["entries"]:
            row = {"map": m["id"], "cpc_article": e["cpc_article"], "equivalence": e.get("equivalence"),
                   "cpc_url": e.get("cpc_url") or (cpc_pages.get(e["cpc_article"]) or {}).get("url"),
                   "legifrance_url": e.get("legifrance_url"), "note_fr": e.get("note_fr"), "note_en": e.get("note_en"),
                   "mo_norms": e.get("mo_norms") or [], "frcp": e.get("frcp") or [], "fr_norm": e.get("fr_norm")}
            if not e.get("cpc_url") and row["cpc_url"]:
                e["cpc_url"] = row["cpc_url"]
            for mid in row["mo_norms"]:
                if mid in norms:
                    norms[mid].setdefault("correspondences", []).append(row)
            fn = norms.get(e.get("fr_norm") or "")
            if fn:
                fn.setdefault("correspondences", []).append(row)
                for fr in row["frcp"]:
                    if fr.get("url") and not any(x["url"] == fr["url"] for x in fn.get("xlinks", [])):
                        fn.setdefault("xlinks", []).append({"kind": "frcp-browser", "url": fr["url"], "label": f"FRCP {fr.get('rule')} (FRCP annotated browser)"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="auto", choices=["auto", "data", "fixtures"])
    ap.add_argument("--base-url", default=os.environ.get("FLB_BASE_URL", DEFAULT_BASE))
    ap.add_argument("--probe-frames", action="store_true", help="probe official hosts for X-Frame-Options/CSP")
    ap.add_argument("--refresh-xlinks", action="store_true", help="re-fetch the CPC/FRCP browser indexes (network)")
    ap.add_argument("--strict", action="store_true", help="exit 1 if the build report has errors")
    a = ap.parse_args()
    base = a.base_url.rstrip("/") + "/"
    src, is_fixture = pick_source(a.source)
    rep = Report()
    print(f"[site_build] source={src} fixture={is_fixture}")

    # ---------- load norms ----------
    norms, norm_corpus = {}, {}
    corpus_meta_extra = {}
    for f in sorted(glob.glob(str(src / "norms" / "*.json"))):
        d = load_json(f, rep)
        if not d:
            continue
        cid = d.get("corpus") or pathlib.Path(f).stem
        corpus_meta_extra[cid] = {k: d[k] for k in ("label", "label_fr", "label_en", "generated") if k in d}
        for n in d.get("norms", []):
            nid = n.get("id")
            if not nid or not re.match(r"^[a-z0-9._-]+$", nid):
                rep.add("error", "bad-id", f"norm id invalid: {nid!r}", file=f)
                continue
            if nid in norms:
                rep.add("warn", "dup-norm", f"duplicate norm id {nid}", file=f)
            n.setdefault("corpus", cid)
            if not n.get("official_url"):
                rep.add("warn", "no-official-url", f"{nid} has no official_url", norm=nid)
            if n.get("kind") != "judge-made-rule" and not n.get("text"):
                rep.add("warn", "no-text", f"{nid} has no text", norm=nid)
            ax = [x for x in (n.get("axes") or ["family"]) if x in AXIS_IDS]
            if n.get("axes") and len(ax) != len(n["axes"]):
                rep.add("warn", "unknown-axis", f"{nid}: unknown axis in {n['axes']}", norm=nid)
            n["axes"] = ax or ["family"]
            n["_declared_interps"] = list(n.get("interps") or [])
            n["interps"] = []
            norms[nid] = n
            norm_corpus[nid] = n["corpus"]

    # ---------- load interps + temporal validation (SCOPE §2) ----------
    # every data/interps/*.json is merged regardless of file name (mo-sc.json + mo-sc-proc.json …);
    # a decision present in several files keeps one record whose norm links / issues are unioned
    raw = {}
    for f in sorted(glob.glob(str(src / "interps" / "*.json"))):
        d = load_json(f, rep)
        if not d:
            continue
        auth = d.get("authority") or d.get("corpus") or re.sub(r"-(proc|family|fam)$", "", pathlib.Path(f).stem)
        for it in d.get("interps", []):
            iid = it.get("id")
            if not iid:
                rep.add("error", "bad-id", "interp without id", file=f)
                continue
            it.setdefault("authority", auth)
            if iid in raw:
                prev = raw[iid]
                have = {l.get("norm") for l in prev.get("norms", [])}
                prev["norms"] = prev.get("norms", []) + [l for l in it.get("norms", []) if l.get("norm") not in have]
                prev["issues"] = list(dict.fromkeys((prev.get("issues") or []) + (it.get("issues") or [])))
                rep.add("info", "interp-merged", f"{iid} appears in several interp files — links merged", interp=iid, file=f)
            else:
                raw[iid] = it
    interps = {}
    if True:
        for it in raw.values():
            iid = it["id"]
            kept = []
            for link in it.get("norms", []):
                nid = link.get("norm")
                n = norms.get(nid)
                if not n:
                    rep.add("warn", "dangling-link", f"{iid} → {nid}: norm not in corpus (link hidden until the norm exists)", interp=iid, norm=nid)
                    continue
                basis, dd, dn = link.get("basis"), iso(it.get("date")), iso(n.get("in_force_since"))
                if basis not in ("a", "b"):
                    rep.add("error", "no-basis", f"{iid} → {nid}: basis missing/invalid ({basis!r}) — dropped", interp=iid, norm=nid)
                    continue
                if basis == "a" and dd and dn and dd < dn and n.get("kind") == "judge-made-rule" and iid in (n.get("rule_sources") or []):
                    # a case that establishes a judge-made rule necessarily predates the rule's latest formulation
                    rep.add("info", "rule-source-before-D", f"{iid} → {nid}: rule source decided {dd} before D(rule) {dn} — kept as rule source", interp=iid, norm=nid)
                elif basis == "a" and dd and dn and dd < dn:
                    rep.add("error", "basis-a-too-early", f"{iid} → {nid}: basis a but decision {dd} < D(norm) {dn} — dropped (needs basis b + justification or exclusion)", interp=iid, norm=nid)
                    continue
                if basis == "b":
                    if not (link.get("b_justification") or "").strip():
                        rep.add("error", "b-without-justification", f"{iid} → {nid}: basis b without b_justification — dropped", interp=iid, norm=nid)
                        continue
                    if link.get("b_method") not in ("text-identical", "functional-review"):
                        rep.add("warn", "b-method", f"{iid} → {nid}: b_method missing/unknown", interp=iid, norm=nid)
                    if dd and dn and dd >= dn:
                        rep.add("info", "b-could-be-a", f"{iid} → {nid}: basis b although decision date ≥ D(norm)", interp=iid, norm=nid)
                kept.append(link)
            if not kept:
                rep.add("warn", "interp-no-qualifying-link", f"{iid}: no qualifying norm link — excluded from site", interp=iid)
                continue
            if not it.get("official_url"):
                rep.add("warn", "no-official-url", f"{iid} has no official_url", interp=iid)
            it["norms"] = kept
            interps[iid] = it

    # rule_sources of judge-made rules are also back-links
    for nid, n in norms.items():
        for iid in n.get("rule_sources") or []:
            if iid not in interps:
                rep.add("warn", "rule-source-missing", f"{nid}: rule source {iid} not found among qualifying interps", norm=nid, interp=iid)

    for iid, it in interps.items():
        for link in it["norms"]:
            n = norms[link["norm"]]
            if iid not in n["interps"]:
                n["interps"].append(iid)
    for nid, n in norms.items():
        for iid in n.pop("_declared_interps"):
            if iid not in interps:
                rep.add("info", "declared-interp-missing", f"{nid} lists {iid} which is absent or non-qualifying", norm=nid, interp=iid)
        n["interps"].sort(key=lambda i: interps[i].get("date") or "", reverse=True)

    # ---------- issues ----------
    issue_sides, issue_ids, ce_labels = [], {}, {}
    for f in sorted(glob.glob(str(src / "issues" / "*.json")), key=lambda f: ("-interps" in f, f)):  # norm-based trees first
        d = load_json(f, rep)
        if not d:
            continue
        # raw Conseil d'État analysis-code nodes ("01-01-02-01,rj1 …") are hidden from the tree and kept as the
        # searchable "Classement CE" facet until the FR case-law pipeline provides proper labels
        def strip_ce(nodes):
            keep = []
            for nd in nodes:
                if CE_CODE.match(str(nd.get("label") or "")):
                    def grab(x):
                        ce_labels[x["id"]] = x.get("label") or x["id"]
                        for c in x.get("children") or []:
                            grab(c)
                    grab(nd)
                else:
                    nd["children"] = strip_ce(nd.get("children") or [])
                    keep.append(nd)
            return keep
        d["nodes"] = strip_ce(d.get("nodes", []))
        sd = d.get("side") or pathlib.Path(f).stem
        axis = d.get("axis") or ("procedure" if pathlib.Path(f).stem.endswith("-proc") or sd.endswith("-proc") else "family")
        issue_sides.append({"side": sd, "axis": axis, "group": d.get("group") or sd.replace("-proc", "").replace("-norms", ""),
                            "lang": d.get("lang", "en"), "nodes": d.get("nodes", []),
                            "label_fr": d.get("label_fr"), "label_en": d.get("label_en")})

        def walk(nodes, parent=None):
            for nd in nodes:
                issue_ids[nd["id"]] = {"label": nd.get("label"), "parent": parent}
                walk(nd.get("children") or [], nd["id"])
        walk(d.get("nodes", []))
    if ce_labels:
        rep.add("info", "classement-ce-hidden", f"{len(ce_labels)} issue nodes with raw analysis-code labels hidden from the tree (kept as 'Classement CE')")
        for it in interps.values():
            ce = [ce_labels[x] for x in it.get("issues") or [] if x in ce_labels]
            if ce:
                it["classement_ce"] = ce
                it["issues"] = [x for x in it["issues"] if x not in ce_labels]
        for n in norms.values():
            if n.get("issues"):
                n["issues"] = [x for x in n["issues"] if x not in ce_labels]
    order = {s["id"]: i for i, s in enumerate(SIDES)}
    merged = {}
    for sd in issue_sides:  # several files may feed the same side of one axis (fr-norms.json + fr-interps.json)
        k = (sd["side"], sd["axis"])
        if k in merged:
            have = {nd["id"] for nd in merged[k]["nodes"]}
            merged[k]["nodes"] += [nd for nd in sd["nodes"] if nd["id"] not in have]
        else:
            merged[k] = sd
    issue_sides = list(merged.values())
    for sd in issue_sides:
        if sd["axis"] == "procedure" and not (sd.get("label_en") or sd.get("label_fr")):
            g = next((x for x in SIDES if x["id"] == sd["group"]), None)
            if g:
                sd["label_fr"], sd["label_en"] = g["label_fr"] + " — procédure civile", g["label_en"] + " — civil procedure"
    issue_sides.sort(key=lambda s: (s["axis"] != "family", order.get(s["group"], order.get(s["side"], 99))))
    issue_index = {}

    def idx(iid, kind, entry):
        issue_index.setdefault(iid, {"norms": [], "interps": []})[kind].append(entry)
    for nid, n in norms.items():
        for iid in n.get("issues") or []:
            if iid not in issue_ids:
                rep.add("warn", "unknown-issue", f"{nid}: issue {iid} not in any issue tree", norm=nid)
            idx(iid, "norms", [nid, n.get("num"), n.get("heading"), n["corpus"]])
    for iid_, it in interps.items():
        for iid in it.get("issues") or []:
            if iid not in issue_ids:
                rep.add("warn", "unknown-issue", f"{iid_}: issue {iid} not in any issue tree", interp=iid_)
            idx(iid, "interps", [iid_, it.get("citation"), it.get("date"), it.get("authority")])

    # ---------- correspondence tables + cross-links to sibling browsers (links only, no content copied) ----------
    mappings = load_mappings(src, norms, rep)
    cpc_pages = sibling_index(CPC_BROWSER + "content/index.html", r'<li([^>]*)>\s*<a href="([^"]*article-(LEGIARTI\d+)\.html)">Article ([^<]+)</a>',
                              SITE / "xlink-cache" / "cpc-browser.json", a.refresh_xlinks, rep)
    apply_xlinks(norms, mappings, cpc_pages, rep)
    # outside-the-dataset search links + proposal link (site-generated navigation only; legal content untouched)
    from site_outside import outside_links, propose_url, citation as outside_citation, REPO as GH_REPO, VERIFIED as OUTSIDE_VERIFIED
    for n in norms.values():
        n["outside"] = outside_links(n)
        n["outside_q"] = outside_citation(n)
        n["propose_url"] = propose_url(n, base)

    # member counts per issue node (declared descendants + undeclared deeper ids sharing the prefix), precomputed so
    # the client does not scan the whole index for every node of a large tree
    by_prefix = {}
    for k, e in issue_index.items():
        parts = k.split(".")
        mem = {("n", r[0]) for r in e["norms"]} | {("i", r[0]) for r in e["interps"]}
        for j in range(1, len(parts) + 1):
            by_prefix.setdefault(".".join(parts[:j]), set()).update(mem)

    def count_walk(nodes):
        acc = set()
        for nd in nodes:
            m = set(by_prefix.get(nd["id"], ())) | count_walk(nd.get("children") or [])
            nd["count"] = len(m)
            acc |= m
        return acc
    for sd in issue_sides:
        count_walk(sd["nodes"])

    # ---------- write site/data ----------
    out = SITE / "data"
    if out.exists():
        shutil.rmtree(out)
    (out / "corpus").mkdir(parents=True)
    corpora_out = []
    by_corpus = {}
    for nid, n in norms.items():
        by_corpus.setdefault(n["corpus"], []).append(n)
    for cid, lst in by_corpus.items():
        meta = CORPORA.get(cid)
        if not meta:
            g = NORM_SIDE_TO_GROUP.get(lst[0].get("side"), "eu-int")
            meta = (g, lst[0].get("lang", "en"), cid, cid, 99)
            rep.add("warn", "unknown-corpus", f"corpus {cid} not in SCHEMA list")
        extra = corpus_meta_extra.get(cid, {})
        used = sorted({i for n in lst for i in n["interps"]} | {i for n in lst for i in (n.get("rule_sources") or []) if i in interps})
        site_shards.write_corpus(out, cid, lst, interps, dump)
        corpora_out.append({"id": cid, "group": meta[0], "lang": meta[1], "label_fr": extra.get("label_fr", meta[2]),
                            "label_en": extra.get("label_en", meta[3]), "order": meta[4], "norms": len(lst),
                            "interps": len(used), "generated": extra.get("generated"),
                            "axes": {ax: sum(ax in n["axes"] for n in lst) for ax in AXIS_IDS if any(ax in n["axes"] for n in lst)},
                            "fixture": any(n.get("fixture") for n in lst)})
    corpora_out.sort(key=lambda c: (c["order"], c["id"]))
    auth_out = []
    by_auth = {}
    for iid, it in interps.items():
        by_auth.setdefault(it["authority"], []).append(it)
    for aid, lst in sorted(by_auth.items()):
        lst.sort(key=lambda i: i.get("date") or "", reverse=True)
        m = AUTHORITIES.get(aid, ("en", aid))
        auth_out.append({"id": aid, "lang": m[0], "label": m[1], "count": len(lst)})
    site_shards.write_authorities(out, by_auth, dump)
    search_stats = site_shards.build_search(out, norms, interps, {c["id"]: c["order"] for c in corpora_out}, ce_labels, dump)
    rep.add("info", "search-index", f"prebuilt search index: {search_stats}")
    dump(out / "issues.json", {"sides": issue_sides})
    # issue index sharded by top-level node (loaded on demand); counts are precomputed in issues.json
    root_of = {}
    def mark(nodes, root):
        for nd in nodes:
            root_of[nd["id"]] = root or nd["id"]
            mark(nd.get("children") or [], root or nd["id"])
    for sd in issue_sides:
        mark(sd["nodes"], None)
    def shard_of(k):
        parts = k.split(".")
        for j in range(len(parts), 0, -1):
            r = root_of.get(".".join(parts[:j]))
            if r:
                return r
        return "_orphans"
    ishards = {}
    for k, e in issue_index.items():
        ishards.setdefault(shard_of(k), {})[k] = e
    safe = lambda r: re.sub(r"[^a-z0-9._-]", "_", r.lower())
    for r, obj in ishards.items():
        dump(out / "issue-index" / f"{safe(r)}.json", obj)
    dump(out / "issue-shards.json", {r: safe(r) for r in ishards})
    maps_out = []
    for m in mappings:
        dump(out / "mapping" / f"{m['id']}.json", m)
        maps_out.append({k: m.get(k) for k in ("id", "label_fr", "label_en", "axis", "fixture")} | {"count": len(m["entries"])})

    # sources (+ latest update report)
    sources = []
    for f in sorted(glob.glob(str(src / "sources*.json"))):
        d = load_json(f, rep)
        if isinstance(d, dict):
            d = d.get("sources", [])
        for s in d or []:
            s["_file"] = pathlib.Path(f).name
            sources.append(s)
    upd = load_json(src / "update-report.json", Report()) if (src / "update-report.json").exists() else None
    if upd:
        st = {r["id"]: r for r in upd.get("results", [])}
        for s in sources:
            if s.get("id") in st:
                s["check_result"] = {k: st[s["id"]].get(k) for k in ("status", "checked", "observed", "changed", "error", "note", "affected_norms")}
    dump(out / "sources.json", {"sources": sources, "update_report": {k: upd.get(k) for k in ("generated", "changed_count", "new_count", "error_count", "blocked_count")} if upd else None}, compact=False)
    cov = [c for f in sorted(glob.glob(str(src / "coverage" / "*.json"))) if (c := load_json(f, rep))]
    dump(out / "coverage.json", {"coverage": cov}, compact=False)

    # frame policy
    urls = [n.get("official_url") for n in norms.values() if n.get("official_url")] + [i.get("official_url") for i in interps.values() if i.get("official_url")]
    policy = {h: "deny" for h in FRAME_DENY_DEFAULT}
    prev = SITE / "frame-policy.json"  # committed cache of probe results
    if prev.exists():
        policy.update(json.loads(prev.read_text()))
    if a.probe_frames:
        policy.update({h: v for h, v in probe_frames(urls, rep).items() if v != "unknown" or h not in policy})
        prev.write_text(json.dumps(policy, indent=2, sort_keys=True), encoding="utf-8")

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    levels = {}
    for r in rep.items:
        levels[r["level"]] = levels.get(r["level"], 0) + 1
    manifest = {"title": "Family Law Annotated Browser (FR ↔ US / Missouri)", "generated": now, "source": src.name,
                "fixture": is_fixture, "base_url": base, "sides": SIDES, "corpora": corpora_out, "authorities": auth_out,
                "issue_sides": [s["side"] for s in issue_sides], "frame_policy": policy,
                "axes": [ax | {"norms": sum(ax["id"] in n["axes"] for n in norms.values()),
                              "issue_sides": [s["side"] for s in issue_sides if s["axis"] == ax["id"]]} for ax in AXES],
                "search": {k: search_stats[k] for k in ("docs", "shards", "max_shard", "total")}, "classement_ce": len(ce_labels),
                "mappings": maps_out, "sibling_browsers": {"cpc": CPC_BROWSER, "frcp": FRCP_BROWSER},
                "github_repo": GH_REPO, "outside_search_verified": OUTSIDE_VERIFIED,
                "totals": {"norms": len(norms), "interps": len(interps), "issues": len(issue_ids),
                           "sources": len(sources), "coverage": len(cov)},
                "build_report": levels}
    dump(out / "manifest.json", manifest, compact=False)
    dump(out / "build-report.json", {"generated": now, "source": str(src), "counts": levels, "items": rep.items}, compact=False)

    # ---------- static agent-readable pages ----------
    gen_content(norms, interps, corpora_out, issue_sides, issue_index, sources, manifest, base, mappings)
    print(f"[site_build] norms={len(norms)} interps={len(interps)} corpora={len(corpora_out)} issues={len(issue_ids)} report={levels}")
    if a.strict and levels.get("error"):
        sys.exit(1)


# ======================================================================================
PAGE_CSS = """body{font-family:'Source Serif 4',Georgia,serif;max-width:860px;margin:0 auto;padding:24px;line-height:1.65;color:#1d1b16;background:#fbfaf7}
h1{font-size:1.55em;line-height:1.25;margin:.2em 0}h2{font-size:1.15em;margin-top:2em;border-bottom:1px solid #d9d4c7;padding-bottom:4px}
a{color:#7a2e1f}.nav{font:14px/1.4 system-ui,sans-serif;margin-bottom:18px}.nav a{margin-right:14px}
.meta{font:14px/1.5 system-ui,sans-serif;color:#555}.badge{display:inline-block;font:12px system-ui,sans-serif;padding:1px 7px;border:1px solid #bbb;border-radius:3px;margin-right:6px}
.text p{margin:.55em 0}.text{border-left:3px solid #7a2e1f;padding:6px 18px;background:#fff}
.interp{background:#fff;border:1px solid #e3dfd3;padding:12px 16px;margin:12px 0}.interp h3{font-size:1em;margin:0 0 4px}
blockquote{margin:.6em 0;padding-left:12px;border-left:2px solid #c9b88f;font-style:italic}.fixture{background:#fff3cd;border:1px solid #e0c36b;padding:8px 12px;font:14px system-ui,sans-serif}
ul.cols{columns:2;column-gap:32px}ul.cols li{break-inside:avoid;margin-bottom:4px}table{border-collapse:collapse;font:14px system-ui,sans-serif}td,th{border:1px solid #ddd;padding:4px 8px;text-align:left}"""


def page(title, body, base, lang="fr", desc="", canonical=""):
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} — Family Law Annotated Browser</title>
<meta name="description" content="{esc(desc or title)}">
{f'<link rel="canonical" href="{esc(canonical)}">' if canonical else ''}
<style>{PAGE_CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def paras(text):
    return "\n".join(f"<p>{esc(p.strip())}</p>" for p in re.split(r"\n\s*\n", text or "") if p.strip())


def link_list(urls):
    return " · ".join(f'<a href="{esc(u.get("url"))}">{esc(u.get("label") or u.get("url"))}</a>' for u in urls or [] if u.get("url"))


def outside_html(n, fr):
    """Static-page block: searches outside the closed universe (unscreened) + proposal link."""
    links = n.get("outside") or []
    h = ("<h2>Rechercher hors du corpus <span lang='en'>/ Search outside the dataset</span></h2>"
         "<p class='meta'><strong>" + ("Hors de l'univers clos — résultats non filtrés" if fr else "Outside the closed universe — unscreened results")
         + ("</strong> : ces recherches externes ne sont pas soumises à la règle temporelle (SCOPE §2) ; une décision trouvée n'est pas une interprétation retenue."
            if fr else "</strong>: these external searches are not screened under the temporal rule (SCOPE §2); a decision found there is not a qualifying interpretation.")
         + f" {'Requête' if fr else 'Query'} : <code>{esc(n.get('outside_q'))}</code></p>")
    if links:
        h += "<ul>" + "".join(f'<li><a href="{esc(x["url"])}" rel="nofollow noopener">{esc(x["label_fr"] if fr else x["label_en"])}</a>'
                              + (f" — {esc(x['note_fr'] if fr else x['note_en'])}" if (x.get("manual") or x.get("human")) else "") + "</li>" for x in links) + "</ul>"
    if n.get("propose_url"):
        h += (f'<p><a href="{esc(n["propose_url"])}" rel="nofollow noopener">' + ("Proposer une décision pour inclusion (GitHub)" if fr else "Propose a decision for inclusion (GitHub)")
              + "</a> — " + ("à examiner selon les bases (a)/(b)" if fr else "screened under basis (a)/(b)") + "</p>")
    return h


def interp_html(it, nid, base):
    link = next((l for l in it["norms"] if l["norm"] == nid), None)
    fr = it.get("lang") == "fr"
    basis = ""
    if link:
        if link["basis"] == "a":
            basis = '<span class="badge">' + ("Base (a) : décision postérieure à la version en vigueur" if fr else "Basis (a): decided on or after the current version") + "</span>"
        else:
            basis = ('<span class="badge">' + ("Base (b) : texte identique" if fr else "Basis (b): identical text") +
                     f' — {esc(link.get("b_method", ""))}</span><p><strong>{"Justification" if fr else "Justification"} :</strong> {esc(link.get("b_justification"))}</p>')
    ex = "".join(f"<blockquote>{esc(e)}</blockquote>" for e in it.get("excerpts") or [])
    summ = ""
    if it.get("summary"):
        lab = ("Sommaire officiel" if fr else "Official headnote") if it.get("summary_is_official") else ("Résumé (non officiel)" if fr else "Summary (non-official)")
        summ = f"<p><strong>{lab} :</strong> {esc(it['summary'])}</p>"
    tit = "".join(f"<div class='meta'>{esc(t)}</div>" for t in it.get("titrage") or [])
    tit += "".join(f"<div class='meta'>Classement CE : {esc(t)}</div>" for t in it.get("classement_ce") or [])
    return f"""<div class="interp" id="{esc(it['id'])}">
<h3>{esc(it.get('citation'))}</h3>
<div class="meta">{esc(it.get('court'))} · {esc(it.get('date'))} · {esc(it.get('number'))}{' · ' + esc(it['ecli']) if it.get('ecli') else ''} <span class="badge">{esc(it.get('publication'))}</span></div>
{basis}{tit}{summ}{ex}
<p class="meta">{'Source officielle' if fr else 'Official source'} : <a href="{esc(it.get('official_url'))}">{esc(it.get('official_url'))}</a>{' · ' + link_list(it.get('alt_urls')) if it.get('alt_urls') else ''}
 · <a href="../#/interp/{esc(it['id'])}">{'Navigateur interactif' if fr else 'Interactive browser'}</a></p>
</div>"""


def gen_content(norms, interps, corpora, issue_sides, issue_index, sources, manifest, base, mappings=()):
    c = SITE / "content"
    if c.exists():
        shutil.rmtree(c)
    c.mkdir(parents=True)
    fx = '<p class="fixture">FIXTURE DATA — development sample, not the validated corpus. / Données de démonstration.</p>' if manifest["fixture"] else ""
    # relative links so the pages work on GitHub Pages (project sub-path) and locally; canonical/sitemap stay absolute
    nav = ('<div class="nav"><a href="index.html">← Index</a><a href="../">Interactive browser</a>'
           '<a href="issues.html">Issues / Questions</a><a href="sources.html">Sources</a>'
           + ''.join(f'<a href="mapping-{esc(m["id"])}.html">{esc(m["label_en"])}</a>' for m in mappings) + '</div>')
    EQ = {"equivalent": ("équivalent", "equivalent"), "partial": ("partiel", "partial"), "functional": ("fonctionnel", "functional"), "none": ("aucun", "none")}

    def corr_html(rows, fr, self_id=None):
        if not rows:
            return ""
        out = [f"<h2>{'Correspondances' if fr else 'Correspondences'} (CPC ↔ Missouri)</h2><table><tr><th>CPC</th><th>Missouri</th><th>{'Équivalence' if fr else 'Equivalence'}</th><th>FRCP</th><th>Note</th></tr>"]
        for r in rows:
            cpc = f'<a href="{esc(r["cpc_url"])}">art. {esc(r["cpc_article"])}</a>' if r.get("cpc_url") else f"art. {esc(r['cpc_article'])}"
            if r.get("legifrance_url"):
                cpc += f' · <a href="{esc(r["legifrance_url"])}">Légifrance</a>'
            mo = ", ".join((f'<a href="{esc(m)}.html">{esc(norms[m].get("num"))}</a>' if m in norms else esc(m)) for m in r["mo_norms"]) or "—"
            fx_ = ", ".join(f'<a href="{esc(x.get("url"))}">{esc(x.get("rule"))}</a>' for x in r["frcp"]) or "—"
            out.append(f"<tr><td>{cpc}</td><td>{mo}</td><td>{esc(EQ.get(r.get('equivalence'), (r.get('equivalence'),) * 2)[0 if fr else 1])}</td><td>{fx_}</td><td>{esc(r.get('note_fr') if fr else r.get('note_en'))}</td></tr>")
        return "".join(out) + "</table>"

    cmeta = {x["id"]: x for x in corpora}
    urls = [base, base + "content/index.html", base + "content/issues.html", base + "content/sources.html"]
    by_corpus = {}
    for nid, n in norms.items():
        by_corpus.setdefault(n["corpus"], []).append(n)
    for nid, n in norms.items():
        fr = n.get("lang") == "fr"
        cm = cmeta.get(n["corpus"], {})
        path = " › ".join(esc(p.get("label")) for p in n.get("path") or [])
        its = [interps[i] for i in n["interps"] if i in interps]
        if n.get("kind") == "judge-made-rule":
            body_text = (f"<h2>{'Règle' if fr else 'Summary rule'}</h2><div class='text'><p>{esc(n.get('summary_rule'))}</p></div>"
                         + ("<p class='meta'>" + ("Sources de la règle" if fr else "Rule sources") + " : " +
                            ", ".join(f'<a href="#{esc(i)}">{esc(interps[i].get("citation"))}</a>' for i in n.get("rule_sources") or [] if i in interps) + "</p>"))
        else:
            body_text = f"<h2>{'Texte en vigueur' if fr else 'Current text'}</h2><div class='text'>{paras(n.get('text'))}</div>"
        parties = ""
        if n.get("parties"):
            parties = "<h2>Status</h2><table>" + "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in n["parties"].items()) + "</table>"
        xr = ", ".join(f'<a href="{esc(x)}.html">{esc(norms[x].get("num"))} ({esc(norms[x]["corpus"])})</a>' for x in n.get("xrefs") or [] if x in norms)
        body = f"""{nav}{fx}
<div class="meta">{esc(cm.get('label_fr' if fr else 'label_en', n['corpus']))} › {path}</div>
<h1>{esc(('Article ' if fr and n.get('kind') == 'article' else '') + str(n.get('num', '')))} — {esc(n.get('heading'))}</h1>
<div class="meta"><span class="badge">{esc(n.get('status'))}</span>{'En vigueur depuis' if fr else 'In force since'} : {esc(n.get('in_force_since') or '—')}
 · {'Applicable' if not fr else 'Applicable'} : {esc(', '.join(n.get('applies_to') or []))}</div>
<p><strong>{'Source officielle' if fr else 'Official source'} :</strong> <a href="{esc(n.get('official_url'))}">{esc(n.get('official_url'))}</a>{' · ' + link_list(n.get('alt_urls')) if n.get('alt_urls') else ''}
 · <a href="../#/norm/{esc(nid)}">{'Navigateur interactif' if fr else 'Interactive browser'}</a></p>
{body_text}{parties}
{("<h2>" + ("Liens externes (renvois, sans reprise du contenu)" if fr else "External cross-links (links only)") + "</h2><ul>" + "".join(f'<li><a href="{esc(x["url"])}">{esc(x["label"])}</a></li>' for x in n.get("xlinks") or []) + "</ul>") if n.get("xlinks") else ""}
{corr_html(n.get("correspondences"), fr)}
{f"<p class='meta'>{'Voir aussi' if fr else 'See also'} : {xr}</p>" if xr else ''}
<div class="meta">{'Questions' if fr else 'Issues'} : {esc(', '.join(n.get('issues') or []))}</div>
<h2>{'Interprétations obligatoires' if fr else 'Binding interpretations'} ({len(its)})</h2>
{''.join(interp_html(it, nid, base) for it in its) or ('<p>Aucune interprétation retenue.</p>' if fr else '<p>No qualifying interpretation.</p>')}
{outside_html(n, fr)}
"""
        (c / f"{nid}.html").write_text(page(f"{n.get('num')} {n.get('heading') or ''}", body, base, "fr" if fr else "en",
                                            canonical=f"{base}content/{nid}.html"), encoding="utf-8")
        urls.append(f"{base}content/{nid}.html")
    groups = {s["id"]: s for s in manifest["sides"]}
    idx_parts = []
    for g in manifest["sides"]:
        cs = [x for x in corpora if x["group"] == g["id"]]
        if not cs:
            continue
        idx_parts.append(f"<h2>{esc(g['label_fr'])} / {esc(g['label_en'])}</h2><ul>")
        for x in cs:
            idx_parts.append(f'<li><a href="corpus-{esc(x["id"])}.html">{esc(x["label_fr"] if x["lang"] == "fr" else x["label_en"])}</a> — {x["norms"]} norms, {x["interps"]} interpretations</li>')
            lst = sorted(by_corpus[x["id"]], key=lambda n: natkey(n.get("num")))
            fr = x["lang"] == "fr"
            rows = "".join(f'<li><a href="{esc(n["id"])}.html">{esc(n.get("num"))}</a> — {esc(n.get("heading"))} <span class="meta">({len(n["interps"])})</span></li>' for n in lst)
            (c / f"corpus-{x['id']}.html").write_text(page(x["label_fr"] if fr else x["label_en"],
                f"{nav}{fx}<h1>{esc(x['label_fr'] if fr else x['label_en'])}</h1><p class='meta'>{x['norms']} norms · {x['interps']} interpretations · <a href='../#/corpus/{esc(x['id'])}'>Interactive</a></p><ul class='cols'>{rows}</ul>",
                base, "fr" if fr else "en"), encoding="utf-8")
            urls.append(f"{base}content/corpus-{x['id']}.html")
        idx_parts.append("</ul>")
    for m in mappings:
        rows = [dict(e, map=m["id"], frcp=e.get("frcp") or [], mo_norms=e.get("mo_norms") or []) for e in m["entries"]]
        (c / f"mapping-{m['id']}.html").write_text(page(m["label_en"], nav + fx + (f'<p class="fixture">FIXTURE mapping</p>' if m.get("fixture") else "") +
            f"<h1>{esc(m['label_fr'])} / {esc(m['label_en'])}</h1><p class='meta'>{len(rows)} CPC articles · French side: links to the CPC annotated browser and Légifrance only.</p>" +
            corr_html(rows, True), base, "fr", canonical=f"{base}content/mapping-{m['id']}.html"), encoding="utf-8")
        urls.append(f"{base}content/mapping-{m['id']}.html")
    t = manifest["totals"]
    (c / "index.html").write_text(page("Index", f"""{nav.replace('← Index', 'Index')}{fx}
<h1>Family Law Annotated Browser — Droit de la famille annoté (FR ↔ US / Missouri)</h1>
<p>Binding legal norms and binding interpretations of family law in and between France and the United States (federal and Missouri),
with international and EU instruments. Each norm page holds the current official text, a link to the official source and every qualifying
interpretation (SCOPE §2 temporal rule). / Normes et interprétations obligatoires, avec lien vers la source officielle.</p>
<p class="meta">{t['norms']} norms · {t['interps']} interpretations · generated {esc(manifest['generated'])}</p>
{''.join(idx_parts)}""", base, "en", canonical=f"{base}content/index.html"), encoding="utf-8")

    def tree(nodes):
        out = "<ul>"
        for nd in nodes:
            e = issue_index.get(nd["id"], {"norms": [], "interps": []})
            refs = ", ".join(f'<a href="{esc(r[0])}.html">{esc(r[1])}</a>' for r in e["norms"])
            refs2 = ", ".join(f'{esc(r[1])}' for r in e["interps"])
            out += f"<li><strong>{esc(nd['label'])}</strong> <span class='meta'>[{esc(nd['id'])}]</span>{(' — ' + refs) if refs else ''}{('<br><span class=meta>' + refs2 + '</span>') if refs2 else ''}{tree(nd.get('children') or []) if nd.get('children') else ''}</li>"
        return out + "</ul>"
    (c / "issues.html").write_text(page("Issues / Questions", nav + fx + "<h1>Issue tree / Arbre des questions</h1>" +
                                        "".join(f"<h2>{esc(s['side'])}</h2>{tree(s['nodes'])}" for s in issue_sides), base, "en"), encoding="utf-8")
    rows = "".join(f"<tr><td>{esc(s.get('label'))}</td><td><a href='{esc(s.get('official'))}'>{esc(s.get('official'))}</a></td><td>{esc(s.get('check'))}</td><td>{esc(s.get('last_checked'))}</td></tr>" for s in sources)
    (c / "sources.html").write_text(page("Sources", nav + fx + f"<h1>Sources</h1><table><tr><th>Source</th><th>Official</th><th>Check</th><th>Last checked</th></tr>{rows}</table>", base, "en"), encoding="utf-8")
    today = datetime.date.today().isoformat()
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
                                      "".join(f"  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n", encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")


def natkey(s):
    return [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.split(r"(\d+)", str(s or "")) if t]


if __name__ == "__main__":
    main()
