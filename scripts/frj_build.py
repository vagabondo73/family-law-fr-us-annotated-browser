# -*- coding: utf-8 -*-
"""Build data/interps/fr-cass.json, fr-ce.json, fr-cons.json, data/issues/fr-interps.json and coverage ledgers
from work/frj/links_*.jsonl + indexes + raw decision XML (for verbatim excerpts)."""
import os, re, sys, json, collections, datetime, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from frj_common import *
from frj_link import fr_date, load_perimeter
from frj_index_cass import MOTIF, clauses

TODAY = datetime.date.today().isoformat()
FORM = {
    "CHAMBRE_CIVILE_1": ("Cour de cassation, 1re chambre civile", "Civ. 1re"),
    "CHAMBRE_CIVILE_2": ("Cour de cassation, 2e chambre civile", "Civ. 2e"),
    "CHAMBRE_CIVILE_3": ("Cour de cassation, 3e chambre civile", "Civ. 3e"),
    "CHAMBRE_COMMERCIALE": ("Cour de cassation, chambre commerciale, financière et économique", "Com."),
    "CHAMBRE_SOCIALE": ("Cour de cassation, chambre sociale", "Soc."),
    "CHAMBRE_CRIMINELLE": ("Cour de cassation, chambre criminelle", "Crim."),
    "ASSEMBLEE_PLENIERE": ("Cour de cassation, Assemblée plénière", "Ass. plén."),
    "CHAMBRE_MIXTE": ("Cour de cassation, chambre mixte", "Ch. mixte"),
    "AVIS": ("Cour de cassation, avis", "Cass., avis"),
    "CHAMBRE_CIVILE": ("Cour de cassation, chambre civile", "Civ."),
    "CHAMBRES_REUNIES": ("Cour de cassation, chambres réunies", "Ch. réun."),
}
ACC = {"separation": "séparation", "regimes": "régimes", "regime": "régime", "autorite": "autorité", "etat": "état", "procedure": "procédure",
       "communaute": "communauté", "nationalite": "nationalité", "securite": "sécurité", "penal": "pénal", "penale": "pénale",
       "execution": "exécution", "interet": "intérêt", "liberalites": "libéralités", "liberalite": "libéralité", "legitime": "légitime",
       "etranger": "étranger", "etrangers": "étrangers", "entree": "entrée", "sejour": "séjour", "egalite": "égalité",
       "representation": "représentation", "legale": "légale", "legal": "légal", "responsabilite": "responsabilité",
       "delictuelle": "délictuelle", "sante": "santé", "donation": "donation", "succession": "succession", "prefix": "préfix",
       "reserve": "réserve", "reservataire": "réservataire", "heritier": "héritier", "heritiers": "héritiers", "legs": "legs",
       "benefice": "bénéfice", "creance": "créance", "creancier": "créancier", "debiteur": "débiteur", "debiteurs": "débiteurs",
       "mineur": "mineur", "majeur": "majeur", "proteges": "protégés", "protege": "protégé", "prestation": "prestation",
       "general": "général", "generale": "générale", "generales": "générales", "civile": "civile", "prescription": "prescription",
       "preuve": "preuve", "testamentaire": "testamentaire", "reduction": "réduction", "recel": "recel", "desaveu": "désaveu",
       "paternite": "paternité", "maternite": "maternité", "legitimation": "légitimation", "adoptee": "adoptée", "adopte": "adopté",
       "pleniere": "plénière", "equite": "équité", "reconnaissance": "reconnaissance", "etablissement": "établissement",
       "procreation": "procréation", "medicalement": "médicalement", "assistee": "assistée", "prive": "privé", "privee": "privée",
       "juridiction": "juridiction", "competence": "compétence", "etrangere": "étrangère", "etrangeres": "étrangères",
       "decision": "décision", "decisions": "décisions", "execute": "exécuté", "caractere": "caractère", "consequences": "conséquences",
       "prejudice": "préjudice", "degradation": "dégradation", "delit": "délit", "delits": "délits", "elements": "éléments",
       "element": "élément", "materiel": "matériel", "intentionnel": "intentionnel", "violences": "violences", "ascendant": "ascendant",
       "enfant": "enfant", "a": "à", "mere": "mère", "pere": "père", "epoux": "époux", "epouse": "épouse", "celibataire": "célibataire",
       "societe": "société", "societes": "sociétés", "contrats": "contrats", "obligations": "obligations", "securite sociale": "sécurité sociale",
       "presomption": "présomption", "revocation": "révocation", "revision": "révision", "interets": "intérêts", "deces": "décès",
       "departement": "département", "mariage": "mariage", "nullite": "nullité", "validite": "validité", "capacite": "capacité",
       "qualite": "qualité", "propriete": "propriété", "immobiliere": "immobilière", "mobiliere": "mobilière", "fiscalite": "fiscalité",
       "impot": "impôt", "impots": "impôts", "enregistrement": "enregistrement", "retraite": "retraite", "prestations": "prestations",
       "familiales": "familiales", "aide": "aide", "sociale": "sociale", "tutelle": "tutelle", "curatelle": "curatelle",
       "emancipation": "émancipation", "residence": "résidence", "communaute legale": "communauté légale", "reprise": "reprise",
       "recompense": "récompense", "recompenses": "récompenses", "gerance": "gérance", "privilege": "privilège", "hypotheque": "hypothèque",
       "cassation": "cassation", "moyen": "moyen", "appel": "appel", "refere": "référé", "refere-provision": "référé-provision",
       "separes": "séparés", "separee": "séparée", "indivisaire": "indivisaire", "indivisaires": "indivisaires", "denonciation": "dénonciation",
       "theatre": "théâtre", "detention": "détention", "privation": "privation", "liberte": "liberté", "libertes": "libertés",
       "controle": "contrôle", "constitutionnalite": "constitutionnalité", "prioritaire": "prioritaire", "delegation": "délégation",
       "retrait": "retrait", "etat civil": "état civil", "francaise": "française", "francais": "français", "reintegration": "réintégration",
       "declaration": "déclaration", "perte": "perte", "decheance": "déchéance", "etude": "étude", "legataire": "légataire",
       "universel": "universel", "execution forcee": "exécution forcée", "saisie": "saisie", "remuneration": "rémunération"}


CE_CODE = re.compile(r"^\s*\d{2,3}(?:-\d{2,3})*(?:\s*\(\d+\))?(?:\s*,\s*(?:rj\d+|\d{2,3}(?:-\d{2,3})*(?:\s*\(\d+\))?))*\s+", re.I)


def accent(label):
    words = re.split(r"(\W+)", label.lower())
    out = "".join(ACC.get(w, w) for w in words)
    return out[:1].upper() + out[1:]


def slug(s):
    s = strip_accents(s.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60].strip("-") or "divers"


def fmt_pourvoi(n):
    m = re.match(r"^(\d{2})-?(\d{2})(\d{3})$", n.replace(".", ""))
    return f"{m.group(1)}-{m.group(2)}.{m.group(3)}" if m else n


def sentences_cut(p, maxlen=900):
    if len(p) <= maxlen:
        return p
    parts = re.split(r"(?<=[.;])\s+", p)
    out = ""
    for s in parts:
        if len(out) + len(s) + 1 > maxlen:
            break
        out = (out + " " + s).strip()
    return out or p[:maxlen].rsplit(" ", 1)[0]


def dec_paras(path):
    try:
        x = open(f"{RAW}/{path}", encoding="utf-8").read()
    except Exception:
        return []
    m = re.search(r"<CONTENU>(.*?)</CONTENU>", x, re.S)
    body = clean_xml_text(m.group(1)) if m else ""
    return [norm_ws(p) for p in body.split("\n") if norm_ws(p)]


def mentions(p, corpus, nums):
    cs = extract_citations(p, "x")
    return any(c["corpus"] == corpus and c["num"] in nums for c in cs)


def excerpts_for(src, d, links):
    raw_paras = dec_paras(d["path"])
    if not raw_paras:
        return []
    paras = [cl for p in raw_paras for cl in clauses(p)]
    bycorp = collections.defaultdict(set)
    for L in links:
        bycorp[L["corpus"]].add(L["num"])
    def ment(p):
        return any(mentions(p, c, n) for c, n in bycorp.items())
    ex = []
    if src == "cass":
        vi = next((i for i, p in enumerate(paras) if re.match(r"^Vu\b", p, re.I) and ment(p)), None)
        if vi is None:
            vi = next((i for i, p in enumerate(paras) if re.match(r"^Vu\b", p, re.I) and len(p) < 400), None)
        if vi is not None:
            ex.append(sentences_cut(paras[vi], 600))
            j = next((k for k in range(vi + 1, min(vi + 8, len(paras))) if re.match(r"^(\d+\.\s*)?(Selon|Aux termes|Il résulte|Il se déduit|Il s'en déduit|Attendu qu|Il en résulte|En application|Il ressort|Si |Ayant|Pour |Vu\b)", paras[k], re.I) and not re.match(r"^Vu\b", paras[k], re.I)), None)
            if j is not None:
                ex.append(sentences_cut(paras[j]))
        else:
            ri = next((i for i, p in enumerate(paras) if re.match(r"^Réponse de la Cour", p)), None)
            rng = range(ri + 1, len(paras)) if ri is not None else range(len(paras))
            j = next((k for k in rng if MOTIF.match(paras[k]) and ment(paras[k])), None)
            if j is None and ri is not None:
                j = next((k for k in rng if len(paras[k]) > 80), None)
            if j is not None:
                ex.append(sentences_cut(paras[j]))
                if j + 1 < len(paras) and re.match(r"^(\d+\.\s*)?(Il en résulte|Il s'en déduit|Dès lors|Ayant|C'est|En l'état|Il résulte)", paras[j + 1]):
                    ex.append(sentences_cut(paras[j + 1]))
        if not ex:
            j = next((k for k, p in enumerate(paras) if re.match(r"^Mais attendu", p, re.I) and ment(p)), None)
            if j is None:
                j = next((k for k, p in enumerate(paras) if re.match(r"^Mais attendu", p, re.I) and len(p) > 80), None)
            if j is None:
                j = next((k for k, p in enumerate(paras) if ment(p) and not re.search(r"selon le moyen|fait grief|reproche", p, re.I)), None)
            if j is not None:
                ex.append(sentences_cut(paras[j]))
    elif src == "jade":
        j = next((k for k, p in enumerate(paras) if MOTIF.match(p) and ment(p)), None)
        if j is None:
            j = next((k for k, p in enumerate(paras) if ment(p) and not re.match(r"^Vu\b", p, re.I)), None)
        if j is not None:
            ex.append(sentences_cut(paras[j]))
            k = next((k for k in range(j + 1, min(j + 4, len(paras))) if re.match(r"^(\d+\.\s*)?(Il résulte|Il ressort|Il se déduit|Il en résulte|Il s'ensuit|Considérant qu'il résulte)", paras[k])
                      and (ment(paras[k]) or re.search(r"(ces|de ces|des) dispositions|ce texte|ces textes|cet article", paras[k]))), None)
            if k is not None:
                ex.append(sentences_cut(paras[k]))
    else:
        for p in paras:
            if re.search(r"Elle est relative à la conformité", p):
                m = re.search(r"Elle est relative à la conformité[^.]*\.", p)
                ex.append(m.group(0) if m else sentences_cut(p, 600))
                break
        j = next((k for k, p in enumerate(paras) if MOTIF.match(p) and ment(p)), None)
        if j is not None and len(ex) < 2:
            ex.append(sentences_cut(paras[j]))
        for p in paras:
            if re.match(r"^Article (1er|premier)\s*\.?\s*[-–—]", p):
                ex.append(sentences_cut(p, 700))
                break
    # verbatim check
    body = "\n".join(raw_paras)
    return [e for e in ex[:3] if e and e in body]


def main():
    cat = load_catalog()
    idx = {}
    for src in ("cass", "jade", "constit"):
        for line in open(f"{WORK}/{src}_index.jsonl"):
            d = json.loads(line)
            if "id" in d:
                idx[d["id"]] = d
    per, nf = load_perimeter(cat, mode="canonical")
    canon = {cat[c][n]["id"] for c, v in per.items() for n in v}
    stats = json.load(open(f"{WORK}/link_stats.json"))
    corp_of = {"cass": "fr-cass", "jade": "fr-ce", "constit": "fr-cons"}
    norm_issues = {}
    for c in list(CODES) + EXTRA_CORPORA:
        pth = f"{ROOT}/data/norms/{c}.json"
        if os.path.exists(pth):
            for n in json.load(open(pth))["norms"]:
                norm_issues[n["id"]] = n.get("issues", [])
    out = {"fr-cass": [], "fr-ce": [], "fr-cons": []}
    issue_nodes = {}
    norm_issue_votes = collections.defaultdict(collections.Counter)
    pending_cc = []
    seen_ids = set()
    per_norm = collections.Counter()
    gaps_ex = collections.Counter()
    for src in ("cass", "jade", "constit"):
        for line in open(f"{WORK}/links_{src}.jsonl"):
            r = json.loads(line)
            inc = [L for L in r["links"] if L["status"] == "included" and L["norm"] in canon]
            if not inc:
                continue
            d = idx[r["id"]]
            rid = {"cass": "cass-", "jade": "ce-", "constit": "cons-"}[src] + d["id"].lower()
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            date = d["date_dec"]
            norms = []
            for L in inc:
                e = {"norm": L["norm"], "basis": L["basis"]}
                if L.get("cited_version"):
                    e["cited_version"] = L["cited_version"]
                if L["basis"] == "b":
                    e["b_method"] = L["b_method"]
                    e["b_justification"] = L["b_justification"]
                elif L.get("note"):
                    e["note"] = L["note"]
                if L.get("alineas"):
                    e["alineas"] = L["alineas"]
                norms.append(e)
                per_norm[L["norm"]] += 1
            sct = [s["text"] for s in d.get("sct", [])]
            if src == "jade":
                sct = [CE_CODE.sub("", s) for s in sct]
            ana = [a.strip() for a in d.get("ana", []) if a.strip()]
            if src == "jade":
                ana = [CE_CODE.sub("", a).replace(",,,", "\n").strip() for a in ana]
            ex = excerpts_for(src, d, inc)
            rec = {"id": rid, "authority": corp_of[src], "lang": "fr", "date": date}
            if src == "cass":
                f = d.get("formation", "")
                court, abbr = FORM.get(f, ("Cour de cassation", "Cass."))
                nums = [fmt_pourvoi(n) for n in d.get("numeros", [])]
                rec.update(court=court, number=", ".join(nums), ecli=d.get("ecli", ""),
                           citation=f"{abbr}, {fr_date(date)}, n° {', '.join(nums)}, publié au Bulletin" if nums else f"{abbr}, {fr_date(date)}, publié au Bulletin",
                           publication="B", official_url=f"https://www.legifrance.gouv.fr/juri/id/{d['id']}", alt_urls=[],
                           solution=d.get("solution", ""), bulletin=d.get("publi_bull", {}).get("text", ""))
                if f == "AVIS":
                    rec["kind"] = "avis"
            elif src == "jade":
                pub = d.get("publi_recueil")
                form = d.get("formation", "")
                avis = bool(re.search(r"avis", d.get("type_rec", "") + " " + d.get("titre", ""), re.I))
                rec.update(court=f"Conseil d'État{', ' + form if form else ''}", number=d.get("numero", ""), ecli=d.get("ecli", ""),
                           citation=f"CE, {form + ', ' if form else ''}{fr_date(date)}, n° {d.get('numero', '')}, " + ("publié au recueil Lebon" if pub == "A" else "mentionné aux tables du recueil Lebon"),
                           publication="Lebon" if pub == "A" else "Tables", official_url=f"https://www.legifrance.gouv.fr/ceta/id/{d['id']}", alt_urls=[])
                if avis:
                    rec["kind"] = "avis"
            else:
                num, nat = d.get("numero", ""), d.get("nature", "")
                ucc = d.get("url_cc", "").replace("http://", "https://")
                rec.update(court="Conseil constitutionnel", number=f"{num} {nat}", ecli=d.get("ecli", ""),
                           citation=f"Cons. const., déc. n° {num} {nat} du {fr_date(date)}", publication=d.get("titre_jo", "") or "JORF",
                           official_url=f"https://www.legifrance.gouv.fr/cons/id/{d['id']}",
                           alt_urls=[{"label": "Conseil constitutionnel", "url": ucc}] if ucc else [], title=d.get("titre", ""))
            if ana:
                rec["summary"] = "\n".join(ana)
                rec["summary_is_official"] = True
            else:
                if src == "constit":
                    disp = next((e for e in ex if e.startswith("Article")), "")
                    rec["summary"] = (f"{d.get('titre', '')}. " + (f"Dispositif : {disp}" if disp else "")).strip()
                else:
                    rec["summary"] = ex[-1] if ex else (sct[0] if sct else "")
                rec["summary_is_official"] = False
                rec["summary_note"] = "Pas de sommaire officiel dans la base DILA ; titre et/ou passage verbatim de la décision."
            rec["excerpts"] = ex
            if not ex:
                gaps_ex[src] += 1
            rec["titrage"] = sct
            rec["norms"] = norms
            # issues from titrage (principal entries)
            iss = []
            for s in (d.get("sct") or []):
                if s["type"] != "PRINCIPAL" and iss:
                    continue
                t = s["text"]
                if src == "jade":
                    t = CE_CODE.sub("", t)
                t = re.sub(r"^(?:\d+\s*°\s*|\d+\s*\)\s*|\d+\s+|\*\s*)", "", t)
                pat = r"\.\s+-?\s*|\s+-\s*|\s*-\s+" if src == "jade" else r"\s+-\s*|\s*-\s+"
                segs = [x.strip(" -.") for x in re.split(pat, t) if x.strip(" -.")]
                if not segs or (len(segs) == 1 and len(segs[0]) > 60):
                    continue
                l1 = segs[0]
                n1 = f"fr.jur.{slug(l1)}"
                issue_nodes.setdefault(n1, {"label": accent(l1), "children": {}})
                nid = n1
                if len(segs) > 1:
                    l2 = segs[1]
                    n2 = f"{n1}.{slug(l2)}"
                    issue_nodes[n1]["children"].setdefault(n2, accent(l2) if l2.isupper() else l2[:1].upper() + l2[1:])
                    nid = n2
                if nid not in iss:
                    iss.append(nid)
            niss = []
            for e in norms:
                for i in norm_issues.get(e["norm"], []):
                    if i not in niss and not i.startswith("fr.code."):
                        niss.append(i)
            # unified French tree: interps take the topical fr.* nodes (data/issues/fr-norms.json) of their linked norms,
            # ranked by how many linked norms carry them; titrage stays as a record field only
            votes = collections.Counter()
            for e in norms:
                for i in norm_issues.get(e["norm"], []):
                    if not i.startswith("fr.code."):
                        votes[i] += 1
            ranked = sorted(votes, key=lambda i: (-votes[i], -i.count("."), i))
            rec["issues"] = ranked[:6]
            for e in norms:
                for i in iss:
                    norm_issue_votes[e["norm"]][i] += 1
            if not rec["issues"]:
                pending_cc.append(rec)
            out[corp_of[src]].append(rec)
    # interps without titrage (mostly Conseil constitutionnel): inherit the most frequent issue of their norms
    for rec in pending_cc:
        votes = collections.Counter()
        for e in rec["norms"]:
            votes.update(norm_issue_votes.get(e["norm"], {}))
        if votes:
            rec["issues"] = [votes.most_common(1)[0][0]]
            rec["issues_inferred"] = True
        else:
            n1 = "fr.jur.controle-de-constitutionnalite" if rec["authority"] == "fr-cons" else "fr.jur.divers"
            issue_nodes.setdefault(n1, {"label": "Contrôle de constitutionnalité" if rec["authority"] == "fr-cons" else "Divers", "children": {}})
            rec["issues"] = [n1]
    os.makedirs(f"{ROOT}/data/interps", exist_ok=True)
    for corpus, recs in out.items():
        recs.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
        json.dump({"corpus": corpus, "generated": TODAY, "interps": recs}, open(f"{ROOT}/data/interps/{corpus}.json", "w"), ensure_ascii=False, indent=2)
        print(corpus, len(recs))
    valid = set()
    def _walk(ns):
        for n in ns:
            valid.add(n["id"]); _walk(n.get("children", []))
    fp = f"{ROOT}/data/issues/fr-norms.json"
    if os.path.exists(fp):
        _walk(json.load(open(fp))["nodes"])
    residual = {}
    for recs in out.values():
        for r in recs:
            r.pop("issues_inferred", None)
            r["issues"] = [i for i in r["issues"] if not valid or i in valid]
            if not r["issues"]:
                nid = "fr.jurisprudence-hors-classement"
                residual[nid] = "Jurisprudence non classée (normes liées sans nœud thématique)"
                r["issues"] = [nid]
    json.dump({"side": "fr", "lang": "fr", "generated": TODAY,
               "note": ("Arbre unifié : les interprétations (fr-cass, fr-ce, fr-cons) sont rattachées aux nœuds thématiques fr.* de "
                        "data/issues/fr-norms.json portés par les normes qu'elles interprètent. Ce fichier ne contient que les nœuds "
                        "résiduels éventuels ; le titrage officiel (SCT) reste disponible dans le champ titrage de chaque décision."),
               "nodes": [{"id": k, "label": v, "children": []} for k, v in sorted(residual.items())]},
              open(f"{ROOT}/data/issues/fr-interps.json", "w"), ensure_ascii=False, indent=2)
    # norm -> interps map for the merge step
    n2i = collections.defaultdict(list)
    for corpus, recs in out.items():
        for r in recs:
            for e in r["norms"]:
                n2i[e["norm"]].append(r["id"])
    json.dump(n2i, open(f"{WORK}/norm_to_interps.json", "w"), ensure_ascii=False, indent=1)
    # coverage ledgers
    heads = {}
    for s in ("cass", "jade", "constit"):
        try:
            heads[s] = subprocess.check_output(["git", "-C", f"{RAW}/{s}", "log", "-1", "--format=%H %cI"], text=True).strip()
        except Exception:
            heads[s] = ""
    per_total = sum(len(v) for v in per.values())
    for src, corpus in corp_of.items():
        st = stats["stats"].get(src, {})
        recs = out[corpus]
        a = sum(1 for r in recs for e in r["norms"] if e["basis"] == "a")
        b = sum(1 for r in recs for e in r["norms"] if e["basis"] == "b")
        bt = sum(1 for r in recs for e in r["norms"] if e.get("b_method") == "text-identical")
        bf = sum(1 for r in recs for e in r["norms"] if e.get("b_method") == "functional-review")
        normset = {e["norm"] for r in recs for e in r["norms"]}
        excl = {k[5:]: v for k, v in st.items() if k.startswith("excl_")}
        led = {"corpus": corpus, "updated": TODAY,
               "source": {"cass": "Tricoteuses/DILA CASS (arrêts publiés de la Cour de cassation) https://git.tricoteuses.fr/dila/cass",
                          "jade": "Tricoteuses/DILA JADE, sous-ensemble global/publie https://git.tricoteuses.fr/dila/jade",
                          "constit": "Tricoteuses/DILA CONSTIT https://git.tricoteuses.fr/dila/constit"}[src],
               "source_head": heads.get(src, ""),
               "norms_expected": per_total, "norms_with_interps": len(normset),
               "perimeter_source": ("data/norms (fichiers de l'agent normes) pour " + ", ".join(nf)) if nf else "définition propre frj_common.in_perimeter (fichiers data/norms absents au moment du calcul)",
               "interps_candidates": st.get("candidates", 0), "interps_screened": st.get("screened", 0),
               "interps_linked": st.get("linked", 0), "interps_included": len(recs),
               "links": {"included": st.get("link_included", 0), "excluded": st.get("link_excluded", 0), "basis_a": a, "basis_b": b,
                         "b_text_identical": bt, "b_functional_review": bf, "exclusion_reasons": excl},
               "screened_breakdown": {k[9:]: v for k, v in st.items() if k.startswith("screened_")},
               "decisions_out_of_screen": st.get("hors_champ", 0),
               "excerpts_missing": gaps_ex.get(src, 0),
               "method": {
                   "cass": "Toutes les décisions CASS (publiées) indexées ; filtrage : 1re et 2e ch. civ., Ass. plén., ch. mixte, avis, anciennes ch. civ./ch. réunies (tout le périmètre) ; ch. criminelle (fr-cp, fr-cpp seulement) ; 3e civ., com., soc. (seulement droit de la famille « cœur » : C. civ. Livre Ier, 720-1099-1, 1387-1581, 1873, CPC Livre III titres I-III, autres codes). Liens : LIENS DILA, « Vu », sommaire (ANA), titrage (SCT), motifs de principe (« Selon l'article… », « Il résulte de… »). Mentions isolées dans le reste du texte (moyens) écartées (« mention-faible »). Règle temporelle SCOPE §2 : a si date ≥ date de début de la version actuelle ; sinon version en vigueur à la date (ou rédaction expressément visée) comparée au texte actuel (LEGI via dila/donnees_juridiques) ; identique → b text-identical ; sinon alinéa visé ou repris textuellement inchangé → b functional-review ; sinon exclusion.",
                   "jade": "Conseil d'État uniquement (JURIDICTION = Conseil d'État), décisions publiées au Lebon (A) ou mentionnées aux tables (B), dont avis contentieux ; mêmes règles de liaison (LIENS, sommaire, titrage, motifs « Aux termes de l'article… ») et règle temporelle.",
                   "constit": ("Toutes les décisions DC et QPC (2 027) criblées ; liaison par toute mention d'un article du périmètre dans les paragraphes du Conseil "
                               "(objet de la QPC, motifs, dispositif), à l'exclusion des griefs des requérants/saisissants et des mentions procédurales (« dans les conditions prévues à l'article 61-1 »). "
                               "Normes constitutionnelles (fr-const : DDHC 1, 2, 4, 6, 16, 17 ; Préambule 1946 ; Constitution art. 1, 34, 53, 55, 61-1, 62, 66, 88-1) liées seulement "
                               "si la décision porte aussi sur une norme familiale du périmètre ou si son objet (titre) relève du droit de la famille. "
                               "DC : la version interprétée est celle issue de la loi déférée (première version entrée en vigueur dans les 400 jours suivant la décision). "
                               "Règle temporelle identique (souvent rédaction expressément visée pour les QPC).")}[src],
               "gaps": []}
        if src == "cass":
            n_avis = sum(1 for x in idx.values() if x.get("formation") == "AVIS" and x["id"].startswith("JURITEXT"))
            led["avis_note"] = (f"Les avis de la Cour de cassation figurent dans CASS (FORMATION = AVIS : {n_avis} avis) ; ils sont tous criblés "
                                "(kind = avis). Les avis rendus par la chambre criminelle apparaissent sous FORMATION = CHAMBRE_CRIMINELLE (SOLUTION « Avis sur saisine »).")
            led["gaps"] += ["Liens LEGIARTI absents des LIENS CASS (0 décision) : liaison exclusivement par analyse textuelle des citations.",
                            "alt_url courdecassation.fr non dérivable de l'identifiant JURITEXT (identifiant Judilibre requis) : non renseigné.",
                            "Arrêts inédits exclus par construction (SCOPE §3) ; Lettre/Rapport non distingués (publication = B).",
                            "Citations sans le mot « article » (ex. « et 1075-1 du code de procédure civile ») non détectées.",
                            "Anciennes numérotations (« ancien article », « devenu ») : seules les correspondances à texte identique sont retenues.",
                            "fr-textes : liaison par « article N de la loi/du décret/de l'ordonnance/de l'arrêté n° … du … » et LIENS DILA (« Loi 85-1372 1985-12-23 art. 55 ») ; aucun identifiant LEGIARTI/JORFTEXT n'est présent dans les LIENS CASS/JADE, la résolution se fait par nature + numéro (ou date) + article ; textes cités sans numéro d'article non liés."]
        if src == "jade":
            led["gaps"] += ["Seul le sous-ensemble « publie » de JADE est utilisé ; décisions CE inédites exclues par construction.",
                            "Le visa CE (« Vu le code civil ») ne désigne pas d'article : liaison par LIENS, sommaire, titrage et motifs."]
        if src == "constit":
            led["gaps"] += ["Pas de sommaire officiel (tables analytiques) dans CONSTIT : résumé = titre officiel + dispositif verbatim (summary_is_official false).",
                            "Décisions DC : liaison aux articles codifiés approximative (lois déférées) ; seuil de 3 mentions.",
                            "Filtre thématique des normes fr-const par mots-clés du titre : quelques décisions périphériques peuvent subsister (bruit résiduel) ; exclusions comptées sous « hors-perimetre-matiere ».",
                            "Articles abrogés ou codes anciens (ex. code de la nationalité, art. 222-31-1 C. pén. abrogé) : non liables à une norme actuelle."]
        json.dump(led, open(f"{ROOT}/data/coverage/{corpus}.json", "w"), ensure_ascii=False, indent=2)
    json.dump(dict(per_norm.most_common()), open(f"{WORK}/per_norm_counts.json", "w"), indent=1)


if __name__ == "__main__":
    main()
