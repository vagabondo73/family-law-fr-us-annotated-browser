"""Build data/norms/eu-reg.json from the latest EUR-Lex consolidated versions (Cellar content negotiation, FR).
Re-run: python3 scripts/int_eu_norms.py   (use --refresh to re-download)"""
import re, sys, os, json, datetime
sys.path.insert(0, os.path.dirname(__file__))
from int_common import *
from int_issues import issues_for, write_tree
EIF_OVERRIDE = {'32012R0650': '2012-08-16'}  # Cellar lists a spurious 2012-07-05; art. 84: 20th day after OJ L 201, 27.7.2012

TODAY = datetime.date.today().isoformat()
ACTS = [
    # base celex, short id, title FR, issue ids, articles filter (None = all), note
    ("32019R1111", "2019-1111", "Règlement (UE) 2019/1111 du Conseil du 25 juin 2019 (Bruxelles II ter)", ["eu.matrimonial", "eu.parental-responsibility", "eu.abduction"], None,
     "Applicable depuis le 1er août 2022 (art. 100, 105) ; tous les États membres sauf le Danemark."),
    ("32009R0004", "4-2009", "Règlement (CE) n° 4/2009 du Conseil du 18 décembre 2008 (obligations alimentaires)", ["eu.maintenance"], None,
     "Applicable depuis le 18 juin 2011 ; loi applicable via le Protocole de La Haye de 2007 (art. 15)."),
    ("32010R1259", "1259-2010", "Règlement (UE) n° 1259/2010 du Conseil du 20 décembre 2010 (Rome III — loi applicable au divorce)", ["eu.divorce-law"], None,
     "Coopération renforcée ; applicable depuis le 21 juin 2012 ; la France est participante."),
    ("32016R1103", "2016-1103", "Règlement (UE) 2016/1103 du Conseil du 24 juin 2016 (régimes matrimoniaux)", ["eu.property-regimes"], None,
     "Coopération renforcée ; applicable depuis le 29 janvier 2019 ; la France est participante."),
    ("32016R1104", "2016-1104", "Règlement (UE) 2016/1104 du Conseil du 24 juin 2016 (effets patrimoniaux des partenariats enregistrés)", ["eu.partnerships"], None,
     "Coopération renforcée ; applicable depuis le 29 janvier 2019 ; la France est participante."),
    ("32012R0650", "650-2012", "Règlement (UE) n° 650/2012 du 4 juillet 2012 (successions)", ["eu.successions"], None,
     "Applicable aux successions ouvertes à compter du 17 août 2015 ; tous les États membres sauf DK et IE."),
    ("32016R1191", "2016-1191", "Règlement (UE) 2016/1191 du 6 juillet 2016 (documents publics)", ["eu.public-documents"], None,
     "Applicable depuis le 16 février 2019."),
    ("32020R1784", "2020-1784", "Règlement (UE) 2020/1784 du 25 novembre 2020 (signification et notification — refonte)", ["eu.procedure.service"], None,
     "Applicable depuis le 1er juillet 2022."),
    ("32020R1783", "2020-1783", "Règlement (UE) 2020/1783 du 25 novembre 2020 (obtention des preuves — refonte)", ["eu.procedure.evidence"], None,
     "Applicable depuis le 1er juillet 2022."),
    ("32012R1215", "1215-2012", "Règlement (UE) n° 1215/2012 du 12 décembre 2012 (Bruxelles I bis)", ["eu.procedure.brussels-i-bis"], None,
     "Applicable depuis le 10 janvier 2015 ; inclus pour les accords matrimoniaux hors champ du règlement 2016/1103 (exclusion art. 1er, § 2, a) et f))."),
    ("32004L0038", "2004-38", "Directive 2004/38/CE du 29 avril 2004 (libre circulation des citoyens et des membres de leur famille)", ["eu.family-migration"], None,
     "Délai de transposition : 30 avril 2006."),
    ("32003L0086", "2003-86", "Directive 2003/86/CE du Conseil du 22 septembre 2003 (regroupement familial)", ["eu.family-migration"], None,
     "Délai de transposition : 3 octobre 2005."),
]
CHARTER = ("12016P/TXT", "charte", "Charte des droits fondamentaux de l'Union européenne", ["7", "9", "24", "33"])
TFEU = ("12016E/TXT", "tfue", "Traité sur le fonctionnement de l'Union européenne", ["81"])
ISSUE_BY_CHARTER = {"7": ["eu.fundamental-rights"], "9": ["eu.fundamental-rights"], "24": ["eu.fundamental-rights", "eu.parental-responsibility"], "33": ["eu.fundamental-rights"]}


def latest_consolidated(base):
    num = base[1:]
    rows = sparql(f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?celex WHERE {{ ?w cdm:resource_legal_id_celex ?celex . FILTER(STRSTARTS(STR(?celex),"0{num}-")) }}""")
    cands = sorted(r["celex"] for r in rows if re.match(r"0" + num + r"-\d{8}$", r["celex"]))
    cands = [c for c in cands if c[-8:] <= TODAY.replace("-", "")]
    return cands


def eif(celex, latest=False):
    """Entry-into-force date(s) from Cellar; ignores the 1001-01-01 placeholder. Falls back to publication + 20 days."""
    rows = sparql(f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?d ?t ?p WHERE {{ ?w cdm:resource_legal_id_celex "{celex}"^^<http://www.w3.org/2001/XMLSchema#string> .
OPTIONAL {{?w cdm:resource_legal_date_entry-into-force ?d}} OPTIONAL {{?w cdm:work_date_document ?t}}
OPTIONAL {{?w cdm:official-journal-act_date_publication ?p}} }}""")
    ds = sorted({r["d"] for r in rows if r.get("d") and not r["d"].startswith("1001") and r["d"] <= TODAY})
    if ds:
        return (ds[-1] if latest else ds[0]), (rows[0].get("t") if rows else None)
    pubs = sorted({r["p"] for r in rows if r.get("p")})
    if pubs:
        d = datetime.date.fromisoformat(pubs[0][:10]) + datetime.timedelta(days=20)
        return d.isoformat(), "computed: publication + 20 days"
    return None, None


ART_RE = re.compile(r'<p[^>]*class="(?:title-article-norm|ti-art|oj-ti-art)"[^>]*>(.*?)</p>', re.S)
STI_RE = re.compile(r'^\s*<p[^>]*class="(?:stitle-article-norm|sti-art|oj-sti-art)"[^>]*>(.*?)</p>', re.S)
DIV_RE = re.compile(r'<p[^>]*class="(title-division-1|title-division-2|ti-section-1|ti-section-2|oj-ti-section-1|oj-ti-section-2)"[^>]*>(.*?)</p>', re.S)
ANNEX_RE = re.compile(r'class="(?:separator-annex|title-annex-1|doc-sep|oj-doc-ti)"')


def parse_articles(h):
    # body after first article; stop at first annex separator after last article
    arts = list(ART_RE.finditer(h))
    out = []
    divs = [(m.start(), m.group(1), strip_tags(m.group(2))) for m in DIV_RE.finditer(h)]
    for i, m in enumerate(arts):
        start = m.end()
        end = arts[i + 1].start() if i + 1 < len(arts) else len(h)
        seg = h[start:end]
        am = ANNEX_RE.search(seg)
        if am and i + 1 == len(arts):
            seg = seg[:am.start()]
        # cut trailing division titles belonging to next article
        dm = DIV_RE.search(seg)
        if dm:
            seg = seg[:dm.start()]
        # also cut signature block
        sig = re.search(r'(Fait à [A-ZÉ][a-zé]+, le|Par le Conseil|Par le Parlement européen)', seg)
        if sig and i + 1 == len(arts):
            seg = seg[:sig.start()]
        heading = ""
        sm = STI_RE.match(seg)
        if sm:
            heading = strip_tags(sm.group(1))
            seg = seg[sm.end():]
        markers = sorted(set(re.findall(r"▼(M\d+|A\d+|B|C\d+)", seg)))
        text = strip_tags(seg)
        text = re.sub(r"▼[A-Z]\d*\s*", "", text).strip()
        text = re.sub(r"\n(\(\d+\)|\d+\))\n", r"\n\1 ", text)
        # paragraph joining: "1." on its own line merges with following line
        text = re.sub(r"(?m)^(\d+\.|[a-z]\)|[ivx]+\)|—)\n", r"\1 ", text)
        # path: current chapter/section titles before this article
        path, last = [], {}
        for pos, cls, lab in divs:
            if pos > m.start():
                break
            lvl = 1 if cls.endswith("1") else 2
            last[lvl] = lab
            if lvl == 1:
                last.pop(2, None)
        label = strip_tags(m.group(1))
        num = label.replace("Article", "").strip()
        num = {"premier": "1", "1er": "1"}.get(num, num)
        out.append({"label": label, "num": num, "heading": heading, "text": text, "markers": markers,
                    "path": [last[k] for k in sorted(last)]})
    return out


def parse_articles_plain(h):
    """Fallback for unstructured OJ HTML (older acts): split plain text on 'Article N' lines."""
    t = strip_tags(h)
    t = t[t.find("\nArticle premier") if "\nArticle premier" in t else t.find("\nArticle 1\n"):]
    stop = re.search(r"\nFait à [A-ZÉ][a-zé]+, le", t)
    if stop:
        t = t[:stop.start()]
    parts = re.split(r"\n(Article (?:premier|\d+[a-z]*))\n", "\n" + t.strip() + "\n")
    out, chap = [], None
    for i in range(1, len(parts) - 1, 2):
        label, body = parts[i], parts[i + 1]
        lines = body.strip().split("\n")
        nxt_chap = None
        if lines and re.match(r"^CHAPITRE [IVXL]+", lines[-1]):
            nxt_chap = lines.pop()
        num = label.replace("Article", "").strip()
        num = {"premier": "1"}.get(num, num)
        out.append({"label": label, "num": num, "heading": "", "text": "\n".join(lines).strip(), "markers": [],
                    "path": [chap] if chap else []})
        if nxt_chap:
            chap = nxt_chap
    return out


def modrefs(h):
    """Map M1.. codes to amending CELEX from the consolidated header."""
    m = {}
    for a in re.finditer(r'<a href="http://publications.europa.eu/resource/celex/([^"]+)"[^>]*>▼(M\d+|A\d+)</a>', h):
        m[a.group(2)] = urllib.parse.unquote(a.group(1))
    # header table: rows with ►M1  Règlement ... then link
    for row in re.finditer(r'►(M\d+)(.*?)</tr>', h, re.S):
        c = re.search(r'resource/celex/([0-9A-Z()%]+)', row.group(2))
        if c and row.group(1) not in m:
            m[row.group(1)] = urllib.parse.unquote(c.group(1))
    return m


def main():
    write_tree()
    refresh = "--refresh" in sys.argv
    norms, ledger = [], []
    for base, sid, title, issues, filt, note in ACTS:
        cons = latest_consolidated(base)
        use = cons[-1] if cons else base
        path = cellar_get(use)
        if not path and cons:
            use = base
            path = cellar_get(base)
        if not path:
            ledger.append({"act": base, "error": "download failed"})
            continue
        h = open(path, encoding="utf-8", errors="replace").read()
        arts = parse_articles(h) or parse_articles_plain(h)
        mods = modrefs(h)
        base_eif, base_date = eif(base)
        base_eif = EIF_OVERRIDE.get(base, base_eif)
        applic = eif(base, latest=True)[0]
        mod_eif = {}
        for code, mc in mods.items():
            mc2 = re.sub(r"\(.*$", "", mc)
            mod_eif[code] = eif(mc2, latest=True)[0]
        seen = set()
        for a in arts:
            if a["num"] in seen:
                continue
            seen.add(a["num"])
            ds = [mod_eif.get(c) for c in a["markers"] if c.startswith("M") and mod_eif.get(c)]
            d = max(ds) if ds else base_eif
            amended_by = sorted({mods[c] for c in a["markers"] if c in mods})
            nid = f"eu-reg-{sid}-art-{slug(a['num'])}"
            norms.append({
                "id": nid, "corpus": "eu-reg", "side": "eu", "lang": "fr", "kind": "article",
                "num": a["num"], "heading": a["heading"] or a["label"],
                "path": [{"label": title, "id": f"eu-reg-{sid}"}] + [{"label": p} for p in a["path"]],
                "text": a["text"], "in_force_since": d, "applicable_since": max(applic, d) if applic and d else applic,
                "status": "en vigueur", "status_note": note + (f" Article modifié par {', '.join(amended_by)}." if amended_by else ""),
                "applies_to": ["EU", "FR"],
                "official_url": f"https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:{use}",
                "alt_urls": [{"label": "Cellar (FR)", "url": "http://publications.europa.eu/resource/celex/" + use},
                             {"label": "EUR-Lex acte initial", "url": f"https://eur-lex.europa.eu/eli/{'reg' if base[5]=='R' else 'dir'}/{base[1:5]}/{int(base[6:])}/oj?locale=fr"}],
                "source_ids": {"celex": base, "celex_consolidated": use, "article": a["num"]},
                "issues": issues_for(sid, a["num"], issues), "xrefs": [], "interps": []})
        ledger.append({"act": base, "consolidated_used": use, "versions_found": cons[-3:], "articles": len(seen),
                       "base_entry_into_force": base_eif, "amendments": mods, "amendment_eif": mod_eif})
        print(base, use, len(seen), base_eif, mods, flush=True)
    # Charter & TFEU (article-level)
    for celex, sid, title, keep in (CHARTER, TFEU):
        path = cellar_get(celex)
        h = open(path, encoding="utf-8", errors="replace").read()
        arts = parse_articles(h)
        got = set()
        for a in arts:
            if a["num"] in keep and a["num"] not in got:
                got.add(a["num"])
                art_celex = celex[:6] + a["num"].zfill(3)
                norms.append({
                    "id": f"eu-reg-{sid}-art-{a['num']}", "corpus": "eu-reg", "side": "eu", "lang": "fr",
                    "kind": "treaty-article" if sid == "tfue" else "article", "num": a["num"],
                    "heading": a["heading"] or a["label"],
                    "path": [{"label": title, "id": f"eu-reg-{sid}"}] + [{"label": p} for p in a["path"]],
                    "text": a["text"], "in_force_since": "2009-12-01", "status": "en vigueur",
                    "status_note": "Force juridique contraignante depuis l'entrée en vigueur du traité de Lisbonne (1er décembre 2009) ; version codifiée JO C 202 du 7.6.2016.",
                    "applies_to": ["EU", "FR"],
                    "official_url": f"https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:{celex}",
                    "alt_urls": [{"label": "EUR-Lex (article)", "url": f"https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:{art_celex}"}],
                    "source_ids": {"celex": celex, "celex_article": art_celex},
                    "issues": ISSUE_BY_CHARTER.get(a["num"], ["eu.procedure.judicial-cooperation"]) if sid == "charte" else ["eu.procedure.judicial-cooperation"],
                    "xrefs": [], "interps": []})
        ledger.append({"act": celex, "articles": sorted(got)})
    dump(os.path.join(RAW, "eu_norms_ledger.json"), ledger)
    dump(os.path.join(DATA, "norms", "eu-reg.json"), {"corpus": "eu-reg", "generated": TODAY, "norms": norms})
    print("norms", len(norms))


if __name__ == "__main__":
    main()
