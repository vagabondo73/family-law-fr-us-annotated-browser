"""Screen HUDOC candidates and build data/interps/coe-ecthr.json.
Input: raw/int/hudoc/candidates_{fra,gc,hague}.json (int_hudoc_candidates.py). Texts cached in raw/int/hudoc/txt/.
Re-run: python3 scripts/int_hudoc_candidates.py && python3 scripts/int_ecthr.py"""
import json, os, re, sys, time, html, urllib.request, collections
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, DATA, dump, load

HD = os.path.join(RAW, "hudoc")
TXT = os.path.join(HD, "txt")
os.makedirs(TXT, exist_ok=True)
FAM_ARTS = {"8", "8-1", "8-2", "12", "14", "P7-5"}
FAMILY_KW = 425  # HUDOC thesaurus: "Respect for family life"
FAM_TERMS = re.compile(r"(filiation|adoption|adopt|paternit|maternit|accouchement sous X|anonymous birth|gestation pour autrui|surroga|"
                       r"divorce|garde|custody|autorité parentale|parental authority|droit de visite|access rights|contact rights|"
                       r"placement|mariage|marriage|époux|spouse|succession|inheritance|héritier|enfant naturel|adultérin|"
                       r"procréation|insémination|insemination|gamètes|donneur|donor|état civil|civil status|nom de famille|surname|"
                       r"enlèvement|abduction|pension alimentaire|maintenance|regroupement familial|family reunification)", re.I)
# Manual screening decisions for candidates not tagged "family life" (documented in coverage ledger)
MANUAL_EXCLUDE = set()


def get_text(itemid):
    p = os.path.join(TXT, itemid + ".txt")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read()
    url = "https://hudoc.echr.coe.int/app/conversion/docx/html/body?library=ECHR&id=" + itemid
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=90) as r:
                h = r.read().decode("utf-8", "replace")
            break
        except Exception as e:
            print("retry", itemid, e, flush=True)
            time.sleep(4 * (i + 1))
    else:
        return ""
    h = re.sub(r"(?is)<style.*?</style>", " ", h)
    h = re.sub(r"(?i)</p>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    t = "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n") if l.strip())
    open(p, "w", encoding="utf-8").write(t)
    time.sleep(0.7)
    return t


def arts_of(r):
    return set((r.get("article") or "").split(";"))


def is_fam_tag(r):
    a = arts_of(r)
    k = set((r.get("kpthesaurus") or "").split(";"))
    c = (r.get("conclusion") or "").lower()
    return (str(FAMILY_KW) in k) or bool(a & {"12", "P7-5"}) or any(x.startswith(("12+", "P7-5")) for x in a) \
        or "family life" in c or "vie familiale)" in c or "respect de la vie familiale" in c


def touches(r):
    a = arts_of(r)
    return bool(a & FAM_ARTS) or any(re.match(r"^(14\+8|8\+14|14\+12|12\+14|P7-5)", x) for x in a)


def operative(t, lang):
    key = "PAR CES MOTIFS" if lang == "fr" else "FOR THESE REASONS"
    i = t.rfind(key) if t.count(key) == 1 else t.find(key)
    if i < 0:
        return None, []
    end_key = "Fait en" if lang == "fr" else "Done in"
    j = t.find(end_key, i)
    op = t[i:j if j > 0 else i + 4000].strip()
    items = re.split(r"\n(?=\d+\.\s)", op)
    return op, items


def classify(t, rows_art):
    tl = t.lower()
    iss = []
    def has(*w):
        return sum(len(re.findall(x, tl)) for x in w)
    if has(r"hague convention", r"convention de la haye") >= 3 and has(r"abduction", r"enlèvement", r"return of the child", r"retour de l.enfant") >= 3:
        iss.append("int.abduction.hague-1980")
    if has(r"\badopt(ive|ed child|er|ion order|ing parent)", r"\badopt(é|ée|ant|ante|ants|ive|if)s?\b", r"adoption plénière", r"adoption simple", r"full adoption", r"intercountry adoption", r"agrément en vue d.adoption", r"approval for adoption") >= 3:
        iss.append("int.echr.adoption")
    if has(r"gestation pour autrui", r"surroga", r"mère porteuse", r"mères porteuses") >= 3:
        iss.append("int.echr.filiation.surrogacy")
    if has(r"filiation", r"paternit", r"maternit", r"accouchement sous x", r"anonymous birth", r"biological father", r"père biologique", r"origines personnelles", r"personal origins") >= 5:
        iss.append("int.echr.filiation")
    if has(r"expulsion", r"éloignement", r"deportation", r"interdiction (définitive )?du territoire", r"exclusion order", r"reconduite à la frontière", r"regroupement familial", r"family reunification") >= 4:
        iss.append("int.echr.migration")
    if has(r"placement", r"aide sociale à l.enfance", r"public care", r"taken into care", r"care order", r"foster") >= 5:
        iss.append("int.echr.child-protection")
    if has(r"custody", r"droit de garde", r"droit de visite", r"access rights", r"contact rights", r"right of contact", r"résidence (habituelle )?de l.enfant", r"autorité parentale", r"parental authority", r"parental responsibility") >= 5:
        iss.append("int.echr.parental-responsibility")
    if has(r"\bdivorc", r"séparation de corps", r"judicial separation") >= 4:
        iss.append("int.echr.divorce")
    if any(x.startswith("12") for x in rows_art) or has(r"droit de se marier", r"right to marry") >= 2:
        iss.append("int.echr.marriage")
    if has(r"inheritance", r"héritier", r"\bheirs?\b", r"successora?u?x?", r"droits successoraux", r"adultérin", r"born out of wedlock", r"hors mariage", r"reserved portion", r"réserve héréditaire") >= 5:
        iss.append("int.echr.succession")
    if has(r"nom de famille", r"surname", r"patronyme", r"état civil", r"civil status", r"prénom", r"forename", r"birth certificate", r"acte de naissance", r"changement de sexe", r"gender reassignment") >= 4:
        iss.append("int.echr.civil-status")
    if has(r"procréation médicalement assistée", r"insémination", r"insemination", r"gamètes", r"\bembryo", r"\bembryon", r"donneur de gamètes", r"sperm donor", r"in vitro") >= 4:
        iss.append("int.echr.assisted-reproduction")
    if has(r"domestic violence", r"violences conjugales", r"violence domestique", r"violences domestiques", r"intimate partner") >= 3:
        iss.append("int.echr.domestic-violence")
    if "P7-5" in rows_art:
        iss.append("int.echr.spousal-equality")
    return sorted(set(iss)) or ["int.echr.family-life"]


def norm_links(r, t):
    a = arts_of(r)
    out = []
    def add(n):
        if n not in [x["norm"] for x in out]:
            out.append({"norm": n, "basis": "a"})
    if any(x.startswith("8") or "+8" in x for x in a):
        add("int-coe-echr-art-8")
    if any(x.startswith("12") or "+12" in x for x in a):
        add("int-coe-echr-art-12")
    if any(x.startswith("14") for x in a):
        add("int-coe-echr-art-14")
    if any(x.startswith("P7-5") for x in a):
        add("int-coe-echr-p7-art-5")
    # Hague 1980 articles expressly applied
    for m in re.finditer(r"[Aa]rticles? (\d{1,2})(?: ?\(?([a-b])\)?)?(?: [a-z ]{0,6})? of the (?:1980 )?Hague Convention|[Aa]rticles? (\d{1,2})(?: ?\(?([a-b])\)?)? de la Convention de La Haye", t):
        n = m.group(1) or m.group(3)
        if n and 1 <= int(n) <= 45:
            add(f"int-hcch-1980-art-{int(n)}")
    if not out and len(re.findall(r"Hague Convention|Convention de La Haye", t)) >= 3:
        add("int-hcch-1980")  # Hague-related case without an identifiable article: link to the instrument record
    return out


def main():
    fra = load(os.path.join(HD, "candidates_fra.json"), [])
    gc = load(os.path.join(HD, "candidates_gc.json"), [])
    hague = load(os.path.join(HD, "candidates_hague.json"), [])
    groups = collections.OrderedDict()
    for setname, rows in (("fra", fra), ("gc", gc), ("hague", hague)):
        for r in rows:
            key = r.get("ecli") or (r.get("appno"), r.get("kpdate"))
            g = groups.setdefault(key, {"rows": [], "sets": set()})
            g["rows"].append(r)
            g["sets"].add(setname)
    ledger = {"screened": 0, "included": 0, "excluded": [], "by_set": collections.Counter()}
    interps = []
    for key, g in groups.items():
        rows = g["rows"]
        r0 = rows[0]
        is_fra = "FRA" in (r0.get("respondent") or "")
        in_scope_set = False
        if is_fra and touches(r0):
            in_scope_set = True
        if "gc" in g["sets"] and touches(r0):
            in_scope_set = True
        if "hague" in g["sets"]:
            in_scope_set = True
        if not in_scope_set:
            continue
        ledger["screened"] += 1
        # prefer French text for France cases, English otherwise
        pref = "FRE" if is_fra else "ENG"
        rows.sort(key=lambda r: (r.get("languageisocode") != pref))
        r = rows[0]
        lang = "fr" if r.get("languageisocode") == "FRE" else "en"
        t = get_text(r["itemid"])
        fam = is_fam_tag(r)
        score = len(FAM_TERMS.findall(t))
        hague_hits = t.count("Hague Convention") + t.count("Convention de La Haye")
        reason = None
        if "hague" in g["sets"] and not (is_fra and touches(r)) and not ("gc" in g["sets"] and fam):
            if hague_hits < 3:
                reason = f"Hague mention incidental ({hague_hits})"
        elif not fam:
            if score < 25:
                reason = f"not family-life tagged; family-term score {score} < 25"
        if r["itemid"] in MANUAL_EXCLUDE:
            reason = "manual exclusion"
        if reason:
            ledger["excluded"].append({"itemid": r["itemid"], "docname": r["docname"], "reason": reason})
            continue
        op, items = operative(t, lang)
        excerpts = []
        for it in items[1:]:
            if re.search(r"(article|Article)s? (8|12|14)\b|Protocole n° 7|Protocol No\. 7", it):
                excerpts.append(it.strip()[:1200])
        if not excerpts and op:
            excerpts = [op[:1200]]
        coll = r.get("documentcollectionid2") or ""
        chamber = "Grande Chambre" if "GRANDCHAMBER" in coll else ("Comité" if "COMMITTEE" in coll else "Chambre")
        if lang == "en":
            chamber = {"Grande Chambre": "Grand Chamber", "Comité": "Committee", "Chambre": "Chamber"}[chamber]
        date = r["kpdate"][:10]
        name = re.sub(r"^(CASE OF|AFFAIRE)\s+", "", r["docname"]).strip()
        name = re.sub(r"\s*-\s*\[.*$", "", name).title().replace(" V. ", " v. ").replace(" C. ", " c. ")
        appno = (r.get("appno") or "").replace(";", ", ")
        if lang == "fr":
            cit = f"CEDH, {'GC, ' if chamber=='Grande Chambre' else ''}{date}, {name}, n° {appno}"
            court = "Cour européenne des droits de l'homme, " + chamber
        else:
            cit = f"{name}, no. {appno}, ECtHR ({'GC' if chamber=='Grand Chamber' else chamber}) {date}"
            court = "European Court of Human Rights, " + chamber
        norms = norm_links(r, t)
        interps.append({
            "id": "ecthr-" + r["itemid"],
            "authority": "coe-ecthr", "court": court, "date": date, "number": appno,
            "ecli": r.get("ecli"), "citation": cit,
            "publication": "GC" if "GRANDCHAMBER" in coll else ("key-case" if r.get("importance") == "1" else f"importance-{r.get('importance')}"),
            "official_url": "https://hudoc.echr.coe.int/eng?i=" + r["itemid"],
            "alt_urls": [{"label": f"HUDOC ({x.get('languageisocode')})", "url": "https://hudoc.echr.coe.int/eng?i=" + x["itemid"]} for x in rows[1:] if x.get("languageisocode") in ("ENG", "FRE")],
            "summary": "; ".join([c for c in (r.get("conclusion") or "").split(";") if c][:6]),
            "summary_is_official": True,
            "summary_note": "HUDOC official 'Conclusion(s)' metadata (verbatim)",
            "excerpts": excerpts[:4],
            "titrage": [c for c in (r.get("conclusion") or "").split(";") if c],
            "norms": norms,
            "issues": classify(t, arts_of(r)),
            "lang": lang,
            "respondent": r.get("respondent"),
            "hudoc_sets": sorted(g["sets"]),
        })
        ledger["included"] += 1
        for s in g["sets"]:
            ledger["by_set"][s] += 1
        if ledger["screened"] % 25 == 0:
            print("screened", ledger["screened"], "included", ledger["included"], flush=True)
    interps.sort(key=lambda x: x["date"])
    dump(os.path.join(DATA, "interps", "coe-ecthr.json"), {"corpus": "coe-ecthr", "interps": interps})
    ledger["by_set"] = dict(ledger["by_set"])
    dump(os.path.join(HD, "screen_ledger.json"), ledger)
    print("done", ledger["screened"], ledger["included"])


if __name__ == "__main__":
    main()
