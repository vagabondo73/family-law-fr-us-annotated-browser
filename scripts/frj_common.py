# -*- coding: utf-8 -*-
"""Shared helpers for the FR case-law pipeline (frj_*): code catalog, citation parser, perimeter."""
import os, re, json, html, unicodedata

ROOT = "/home/user/workspace/flb"
RAW = f"{ROOT}/raw"
WORK = f"{ROOT}/work/frj"
os.makedirs(WORK, exist_ok=True)

# corpus id -> (mirror dir, LEGITEXT)
CODES = {
    "fr-cc": ("code_civil", "LEGITEXT000006070721"),
    "fr-cpc": ("code_de_procedure_civile", "LEGITEXT000006070716"),
    "fr-coj": ("code_de_l_organisation_judiciaire", "LEGITEXT000006071164"),
    "fr-casf": ("code_de_l_action_sociale_et_des_familles", "LEGITEXT000006074069"),
    "fr-csp": ("code_de_la_sante_publique", "LEGITEXT000006072665"),
    "fr-cp": ("code_penal", "LEGITEXT000006070719"),
    "fr-cpp": ("code_de_procedure_penale", "LEGITEXT000006071154"),
    "fr-cgi": ("code_general_des_impots", "LEGITEXT000006069577"),
    "fr-css": ("code_de_la_securite_sociale", "LEGITEXT000006073189"),
    "fr-ceseda": ("code_de_l_entree_et_du_sejour_des_etrangers_et_du_droit_d_asile", "LEGITEXT000006070158"),
    "fr-cpce": ("code_des_procedures_civiles_d_execution", "LEGITEXT000025024948"),
}

# code-name recognition (normalized, lowercase, no accents) -> corpus id or 'other:<name>' / 'old:<name>'
CODE_NAMES = [
    ("nouveau code de procedure civile", "fr-cpc"),
    ("code de procedure civile", "fr-cpc"),
    ("code civil", "fr-cc"),
    ("code de l'organisation judiciaire", "fr-coj"),
    ("code de l'action sociale et des familles", "fr-casf"),
    ("code de la sante publique", "fr-csp"),
    ("nouveau code penal", "fr-cp"),
    ("code penal", "fr-cp"),
    ("code de procedure penale", "fr-cpp"),
    ("code general des impots", "fr-cgi"),
    ("code de la securite sociale", "fr-css"),
    ("code de l'entree et du sejour des etrangers et du droit d'asile", "fr-ceseda"),
    ("code des procedures civiles d'execution", "fr-cpce"),
]
# old codes whose numbering differs -> never linked to current code
OLD_CODE_HINTS = ["code de la famille et de l'aide sociale", "ancien code", "code d'instruction criminelle"]


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


def canon_code(name):
    n = strip_accents(name.lower()).replace("\u2019", "'")
    n = re.sub(r"\s+", " ", n).strip()
    for h in OLD_CODE_HINTS:
        if n.startswith(h):
            return "old"
    for k, v in CODE_NAMES:
        if n.startswith(k):
            return v
    return "other"


SUFFIX = r"(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|novies|decies|undecies|duodecies|terdecies|quaterdecies|quindecies|sexdecies|septdecies|octodecies|novodecies|vicies)"


def norm_num(prefix, num, suffix=None):
    """Return mirror-style number: 'L213-3', '371-1', '80 septies'."""
    p = (prefix or "").upper().replace(".", "").replace(" ", "")
    n = num.replace(" ", "")
    s = f" {suffix.lower()}" if suffix else ""
    return f"{p}{n}{s}"


def norm_id(corpus, num):
    s = strip_accents(num.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return f"{corpus}-{s}"


def clean_xml_text(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("\u00a0", " ")
    return s


def normalize_for_compare(t):
    t = clean_xml_text(t or "")
    t = strip_accents(t.lower()).replace("\u2019", "'").replace("’", "'")
    t = re.sub(r"[«»\"“”]", "", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*([,;:.])\s*", r"\1 ", t)
    return t.strip()


# ---------------- citation parser ----------------
ORD = {"premier": 1, "1er": 1, "deuxieme": 2, "second": 2, "seconde": 2, "troisieme": 3, "quatrieme": 4, "cinquieme": 5,
       "sixieme": 6, "septieme": 7, "huitieme": 8, "neuvieme": 9, "dixieme": 10, "onzieme": 11, "douzieme": 12,
       "dernier": -1, "avant-dernier": -2}

NUMTOK = re.compile(r"(?<![\w.])(?:(L\.?\s?O\.?|L\.?|R\.?|D\.?|A\.?)\s*)?(\d+(?:\s?-\s?\d+)*)(?:\s?(?:er|°))?(?:\s+(" + SUFFIX + r"))?\b(?![\w-]*\s*°)", re.I)

# article-list segment: allowed vocabulary between 'article(s)' and 'du code …'
SEG_WORD = r"(?>\b[LRDAO](?:\.|\b)|\b\d++(?:\s?-\s?\d++)*+(?:er)?\b|\b" + SUFFIX + r"\b|\bet\b|\bà\b|\ba\b|\bou\b|\bsuivants?\b|\bs\.|\balin[ée]as?\b|\bal\.|\bpremier\b|\bdeuxi[èe]me\b|\btroisi[èe]me\b|\bquatri[èe]me\b|\bcinqui[èe]me\b|\bsixi[èe]me\b|\bsepti[èe]me\b|\bhuiti[èe]me\b|\bdernier\b|\bsecond\b|\banciens?\b|\bnouveaux?\b|\bdevenus?\b|\b[IVX]{1,4}\b|§|paragraphes?\b|[,\-°])"
SEG_RE = re.compile(r"\b(anciens?\s+)?articles?\s+((?:" + SEG_WORD + r"\s*+){1,60}?)\s*,?\s*(?:du|de\s+ce|dudit|du\s+m[êe]me|au|de\s+l'ancien)\s+(code\b[^,;:.()\n\[\]]{0,90})", re.I)
# DILA LIENS format: "Code civil 301 AL. 1", "Code de procédure civile 58-1"
LIEN_RE = re.compile(r"^\s*((?:Nouveau\s+)?Code[^0-9]{3,90}?)\s+((?:[LRDAO]\.?\s?)?\d[\w\-\s.,]*)", re.I)
ALIN_RE = re.compile(r"(?:alin[ée]as?|al\.)\s*((?:\d+(?:er)?|premier|deuxi[èe]me|dernier)(?:\s*(?:,|et|à)\s*(?:\d+(?:er)?|premier|deuxi[èe]me|dernier))*)", re.I)
PRE_ALIN_RE = re.compile(r"\b(premier|deuxi[èe]me|troisi[èe]me|quatri[èe]me|cinqui[èe]me|sixi[èe]me|septi[èe]me|huiti[èe]me|dernier|avant-dernier|second)\s+alin[ée]a\s+(?:de\s+l'|des\s+)$", re.I)
REDAC_RE = re.compile(r"^\s*,?\s*(?:pris\s+)?(?:dans|en)\s+sa\s+r[ée]daction\s+(ant[ée]rieure|issue|r[ée]sultant|applicable|en\s+vigueur)[^.;:]{0,160}", re.I)
DATE_FR = re.compile(r"(\d{1,2}|1er)\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+(\d{4})", re.I)
MONTHS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "septembre": 9,
          "octobre": 10, "novembre": 11, "decembre": 12}


def parse_fr_date(s):
    m = DATE_FR.search(s)
    if not m:
        return None
    d = 1 if m.group(1).lower() == "1er" else int(m.group(1))
    mo = MONTHS[strip_accents(m.group(2).lower())]
    return f"{int(m.group(3)):04d}-{mo:02d}-{d:02d}"


def _alineas(txt):
    out = []
    for m in ALIN_RE.finditer(txt):
        for tok in re.split(r"\s*(?:,|et)\s*", m.group(1)):
            tok = strip_accents(tok.lower()).strip()
            if tok.endswith("er"):
                tok = tok[:-2]
            if tok.isdigit():
                out.append(int(tok))
            elif tok in ORD:
                out.append(ORD[tok])
    return out


def parse_numbers(seg):
    """Parse an article-list segment into [(num, flags)], flags: range_to, alineas, devenu, ancien, suivants."""
    s = seg
    # remove alinéa groups (keep them for info)
    al = _alineas(s)
    s2 = ALIN_RE.sub(" ", s)
    s2 = re.sub(r"\b(?:paragraphes?|§)\s*[IVX\d]+", " ", s2, flags=re.I)
    s2 = re.sub(r"\b[IVX]+\b(?!\.)", " ", s2)
    s2 = re.sub(r"\d+\s*°", " ", s2)
    items = []
    last_end = 0
    toks = list(NUMTOK.finditer(s2))
    for i, m in enumerate(toks):
        between = s2[last_end:m.start()]
        last_end = m.end()
        num = norm_num(m.group(1), re.sub(r"\s*-\s*", "-", m.group(2)), m.group(3))
        flags = {}
        if re.search(r"\bà\b|\ba\b", between) and items:
            flags["range_from"] = items[-1][0]
        if re.search(r"devenus?", between, re.I):
            flags["devenu"] = True
        items.append((num, flags))
    suivants = bool(re.search(r"suivants|\bs\.", s2, re.I))
    return items, al, suivants


def extract_citations(text, source):
    """Find article citations in running text. Returns list of dicts."""
    out = []
    if not text:
        return out
    t = text.replace("\u2019", "'").replace("’", "'").replace("\u00a0", " ")
    last_code = None
    pos = 0
    while True:
        m = SEG_RE.search(t, pos)
        if not m:
            break
        ancien = bool(m.group(1))
        seg = m.group(2)
        codename = m.group(3)
        # trim code name to its real extent so the next citation is not swallowed
        cut = re.search(r"\s(?:et|ou|dans|en|pris|tel|telle|ainsi|qui|que|a|ont|l'|le|la|les|des|aux?|sur|selon|issu|issue|modifi\w*)\b|\s(?:l'|d')", codename[5:])
        cn = strip_accents(codename.lower())
        known = [k for k, _ in CODE_NAMES if cn.startswith(k)]
        if known:
            cend = m.start(3) + max(len(k) for k in known)
        elif cut:
            cend = m.start(3) + 5 + cut.start()
        else:
            cend = m.end()
        codename = t[m.start(3):cend]
        pos = cend
        before = t[max(0, m.start() - 12):m.start()]
        if re.search(r"ancien\s*$", before, re.I):
            ancien = True
        c = canon_code(codename)
        if re.match(r"code\s*$", codename.strip(), re.I) or re.search(r"(m[êe]me|dudit|ce)\s*$", t[m.start(3) - 8:m.start(3)], re.I):
            c = last_code or "other"
        if c not in ("other", "old"):
            last_code = c
        else:
            last_code = c
            continue
        items, al, suiv = parse_numbers(seg)
        pre = PRE_ALIN_RE.search(t[max(0, m.start() - 40):m.start()] + "")
        if pre:
            al = al + [ORD.get(strip_accents(pre.group(1).lower()), 0)]
        after = t[cend:cend + 220]
        red = REDAC_RE.match(after)
        redac = None
        if red:
            redac = {"kind": strip_accents(red.group(1).lower()).split()[0], "text": norm_ws(red.group(0).lstrip(" ,")),
                     "date": parse_fr_date(red.group(0))}
        anc_local = ancien or bool(re.search(r"\bancien", seg, re.I))
        for idx, (num, fl) in enumerate(items):
            d = {"corpus": c, "num": num, "source": source}
            if al and len(items) == 1:
                d["alineas"] = al
            elif al:
                d["alineas_group"] = al
            if fl.get("range_from"):
                d["range_from"] = fl["range_from"]
            if suiv and idx == len(items) - 1:
                d["suivants"] = True
            # 'article 1134, devenu 1103, du code civil': the first is old numbering, the devenu one is current
            if any(f.get("devenu") for _, f in items):
                if fl.get("devenu"):
                    d["devenu"] = True
                else:
                    d["ancien"] = True
            elif anc_local:
                d["ancien"] = True
            if redac:
                d["redaction"] = redac
            out.append(d)
    return out


def extract_lien(text):
    """DILA LIENS text formats: 'Code civil 301 AL. 1' or modern 'articles 908 et 909 du code de procédure civile'."""
    out = []
    if not text:
        return out
    if re.search(r"\barticles?\b", text, re.I):
        return extract_citations(text, "liens")
    m = LIEN_RE.match(text)
    if m:
        c = canon_code(m.group(1))
        if c in ("other", "old"):
            return out
        rest = m.group(2)
        al = [int(x) for x in re.findall(r"AL\.?\s*(\d+)", rest, re.I)]
        rest = re.sub(r"AL\.?\s*\d+.*$", "", rest, flags=re.I)
        items, _, _ = parse_numbers(rest)
        for num, fl in items[:1]:
            d = {"corpus": c, "num": num, "source": "liens"}
            if al:
                d["alineas"] = al
            out.append(d)
    return out


# ---------------- code catalog ----------------
FM_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


def load_catalog():
    p = f"{WORK}/articles.json"
    if os.path.exists(p):
        return json.load(open(p))
    return None


def num_key(num):
    """Sort key for article numbers within a code (e.g. 'L213-3-1', '80 septies')."""
    m = re.match(r"([A-Z]*)(\d+)((?:-\d+)*)\s*(\w+)?", num)
    if not m:
        return ("~", [999999], num)
    parts = [int(m.group(2))] + [int(x) for x in m.group(3).split("-") if x]
    return (m.group(1), parts, m.group(4) or "")


# ---------------- perimeter (SCOPE §4.1) ----------------
def _base(num):
    m = re.match(r"([A-Z]*)(\d+)", num)
    return (m.group(1), int(m.group(2))) if m else ("", -1)


def _in(num, prefix, lo, hi):
    p, b = _base(num)
    return p == prefix and lo <= b <= hi


def _starts(num, *prefixes):
    return any(num == x or num.startswith(x + "-") for x in prefixes)


def in_perimeter(corpus, num, path=""):
    """Own perimeter fallback; the canonical perimeter is data/norms/<corpus>.json when present."""
    if corpus == "fr-cc":
        return (_in(num, "", 1, 6) or path.startswith("titre_preliminaire") or path.startswith("livre_ier")
                or _in(num, "", 720, 892) or _in(num, "", 893, 1099) or _in(num, "", 1100, 1231)
                or _in(num, "", 1304, 1352) or _in(num, "", 1353, 1386) or _in(num, "", 1387, 1581)
                or _in(num, "", 1873, 1873) or _in(num, "", 2219, 2254))
    if corpus == "fr-cpc":
        return (path.startswith("livre_iii/titre_ier") or path.startswith("livre_iii/titre_ii/") or path.startswith("livre_iii/titre_iii")
                or _in(num, "", 683, 688) or _in(num, "", 1542, 1568) or _in(num, "", 1038, 1269))
    if corpus == "fr-coj":
        return _starts(num, "L213-3", "L213-3-1", "L213-4", "L213-4-1", "L213-4-2", "L213-4-3", "L213-4-4", "L213-4-5",
                       "L213-4-6", "L213-4-7", "L213-4-8") or num.startswith("R213-") or num.startswith("L312-6-1")
    if corpus == "fr-casf":
        return (_in(num, "L", 221, 228) or _in(num, "R", 221, 228) or _in(num, "L", 111, 112) or _in(num, "D", 221, 228)
                or _in(num, "L", 147, 148) or _in(num, "R", 147, 148) or _in(num, "L", 225, 225))
    if corpus == "fr-csp":
        return _in(num, "L", 2141, 2143) or _in(num, "R", 2141, 2143) or _in(num, "L", 1244, 1244) or num.startswith("L1211-") or num.startswith("L1131-")
    if corpus == "fr-cp":
        return (num.startswith("227-") or num == "227" or _starts(num, "433-20", "433-21", "433-21-1", "222-14-3", "222-14-4", "222-14-5",
                "222-33-2-1", "222-13", "222-12", "222-11", "222-8", "222-10", "222-24", "222-28", "222-22", "222-23", "221-4",
                "132-80", "221-5-5", "222-48-2", "222-48-3", "222-31-2", "225-4-1", "222-33-2-2", "226-4-1"))
    if corpus == "fr-cpp":
        return _starts(num, "41-1", "41-3-1", "138", "138-3", "142-12-1", "132-80", "10-2", "706-50", "706-51-1", "706-52",
                       "706-53", "706-53-1", "706-53-2", "706-53-3", "706-53-4", "706-53-5", "515-11") or num.startswith("41-1-")
    if corpus == "fr-cgi":
        return _starts(num, "80 septies", "156", "199 octodecies", "746", "747", "748", "749", "750", "777", "779", "790",
                       "790 A", "790 B", "790 E", "790 F", "790 G", "796-0 bis", "796-0 ter", "757", "757 B", "784", "196", "6", "194", "195")
    if corpus == "fr-css":
        return _in(num, "L", 582, 582) or _in(num, "R", 582, 582) or _in(num, "L", 523, 523) or _starts(num, "L353-1", "L353-3", "L353-6", "R353-1", "L342-1", "L161-14", "L161-15")
    if corpus == "fr-ceseda":
        return _in(num, "L", 423, 423) or _in(num, "L", 434, 434) or _in(num, "R", 434, 434) or _in(num, "L", 424, 424) or _starts(num, "L611-3", "L631-2", "L631-3", "L252-2")
    if corpus == "fr-cpce":
        return _in(num, "L", 213, 213) or _in(num, "R", 213, 213)
    return False


def perimeter_from_norm_files():
    """If the norm agent has produced data/norms/fr-*.json, return {corpus: set(ids)}."""
    out = {}
    for corpus in list(CODES) + ["fr-const", "fr-textes"]:
        p = f"{ROOT}/data/norms/{corpus}.json"
        if os.path.exists(p):
            try:
                out[corpus] = {n["id"] for n in json.load(open(p))["norms"]}
            except Exception:
                pass
    return out


# ---------------- constitutional norms & non-codified texts ----------------
EXTRA_CORPORA = ["fr-const", "fr-textes"]
_LIST = r"((?:" + SEG_WORD + r"\s*+){1,40}?)"
DDHC_RE = re.compile(r"\barticles?\s+" + _LIST + r"\s*,?\s*de\s+la\s+(?:m[êe]me\s+)?D[ée]claration(?:\s+des\s+droits\s+de\s+l'homme\s+et\s+du\s+citoyen)?(?:\s+du\s+26\s+ao[ûu]t)?(?:\s+de)?\s+1789", re.I)
DDHC_SAME_RE = re.compile(r"\barticles?\s+" + _LIST + r"\s*,?\s*de\s+(?:la\s+m[êe]me\s+D[ée]claration|cette\s+D[ée]claration)", re.I)
CONST_RE = re.compile(r"\barticles?\s+" + _LIST + r"\s*,?\s*de\s+la\s+Constitution\b(?!\s+du\s+27\s+octobre)(?!\s+de\s+1946)", re.I)
PREAMB46_RE = re.compile(r"(?:((?:premier|deuxi[èe]me|troisi[èe]me|quatri[èe]me|cinqui[èe]me|sixi[èe]me|septi[èe]me|huiti[èe]me|neuvi[èe]me|dixi[èe]me|onzi[èe]me|douzi[èe]me|treizi[èe]me|quatorzi[èe]me|\s|et|,)+)\s*alin[ée]as?\s+du\s+)?Pr[ée]ambule\s+de\s+(?:la\s+Constitution\s+du\s+27\s+octobre\s+)?1946", re.I)
ORD2 = dict(ORD, dixieme=10, onzieme=11, douzieme=12, treizieme=13, quatorzieme=14, neuvieme=9)
TEXTE_RE = re.compile(r"\barticles?\s+" + _LIST + r"\s*,?\s*(?:de\s+la|du|de\s+l')\s*(loi|d[ée]cret|ordonnance|arr[êe]t[ée])(?:\s+organique)?\s*(?:n[°o]\s*([\d]+[\-–][\d]+(?:[\-–]\d+)?))?\s*du\s+((?:\d{1,2}|1er)\s+\w+\s+\d{4})", re.I)
TEXTE_LIEN_RE = re.compile(r"^\s*(Loi|D[ée]cret|Ordonnance|Arr[êe]t[ée])\s+(?:(\d+[\-–]\d+)\s+)?(\d{4}-\d{2}-\d{2})\s+(?:ART\.?|art\.?)\s*([\w\-]+)", re.I)


def _nature(s):
    s = strip_accents(s.lower())
    return {"loi": "loi", "decret": "decret", "ordonnance": "ordonnance", "arrete": "arrete"}.get(s, s)


def texte_key(nature, numero, date_iso, art):
    art = strip_accents(str(art).lower()).replace("er", "") if str(art).lower() in ("1er",) else strip_accents(str(art).lower())
    return f"{nature}|{numero or date_iso}|{art}"


def extract_extra(text, source):
    out = []
    if not text:
        return out
    t = text.replace("\u2019", "'").replace("\u00a0", " ")
    for rx in (DDHC_RE, DDHC_SAME_RE):
        for m in rx.finditer(t):
            items, al, _ = parse_numbers(m.group(1))
            for num, fl in items:
                out.append({"corpus": "fr-const", "num": f"ddhc-{num}", "source": source})
    for m in CONST_RE.finditer(t):
        if re.search(r"(conditions\s+prévues\s+(?:à|au|par)|prévues?\s+(?:à|par)|en\s+application\s+de|sur\s+le\s+fondement\s+de|conformément\s+à|saisi[e]?\s+(?:en\s+application|sur\s+le\s+fondement)\s+de)\s*(?:l'|le\s+|du\s+|des\s+)?(?:(?:premier|deuxième|second|troisième|dernier)\s+alinéa\s+de\s+l')?$", t[max(0, m.start() - 70):m.start()], re.I):
            continue
        items, al, _ = parse_numbers(m.group(1))
        for num, fl in items:
            d = {"corpus": "fr-const", "num": num, "source": source}
            if al and len(items) == 1:
                d["alineas"] = al
            out.append(d)
    for m in PREAMB46_RE.finditer(t):
        d = {"corpus": "fr-const", "num": "preambule-1946-preambule", "source": source}
        if m.group(1):
            als = [ORD2.get(strip_accents(w.lower())) for w in re.findall(r"\w+", m.group(1))]
            als = [a for a in als if a]
            if als:
                d["alineas"] = als
        out.append(d)
    for m in TEXTE_RE.finditer(t):
        nat = _nature(m.group(2))
        numero = (m.group(3) or "").replace("–", "-")
        date = parse_fr_date(m.group(4))
        items, al, _ = parse_numbers(m.group(1))
        for num, fl in items:
            out.append({"corpus": "fr-textes", "num": texte_key(nat, numero, date, num), "source": source,
                        "texte_alt": texte_key(nat, "", date, num)})
    return out


def extract_extra_lien(text):
    m = TEXTE_LIEN_RE.match(text or "")
    if not m:
        return extract_extra(text, "liens") if re.search(r"article", text or "", re.I) else []
    nat = _nature(m.group(1))
    numero = (m.group(2) or "").replace("–", "-")
    art = m.group(4)
    return [{"corpus": "fr-textes", "num": texte_key(nat, numero, m.group(3), art), "source": "liens",
             "texte_alt": texte_key(nat, "", m.group(3), art)}]


HEAD_RE = re.compile(r"^(Loi|LOI|D[ée]cret|Ordonnance|Arr[êe]t[ée])\s*(?:organique\s*)?(?:n[°o]\s*([\d]+-[\d]+(?:-\d+)?))?\s*du\s+((?:\d{1,2}|1er)\s+\w+\s+\d{4})", re.I)


def extra_catalog():
    """Catalog entries for fr-const and fr-textes built from the norm agent's files."""
    cat = {}
    for corpus in EXTRA_CORPORA:
        p = f"{ROOT}/data/norms/{corpus}.json"
        if not os.path.exists(p):
            continue
        arts = {}
        for n in json.load(open(p))["norms"]:
            sid = n.get("source_ids", {})
            rec = {"num": n["num"], "legiarti": sid.get("legiarti", ""), "debut": n.get("in_force_since", ""), "fin": "2999-01-01",
                   "etat": "VIGUEUR", "path": "", "text": n.get("text", ""), "id": n["id"], "perimeter": True}
            if corpus == "fr-const":
                key = n["id"][len("fr-const-"):]
            else:
                m = HEAD_RE.match(n.get("heading", ""))
                if not m or not rec["legiarti"]:
                    continue
                key = texte_key(_nature(m.group(1)), m.group(2) or "", parse_fr_date(m.group(3)), n["num"])
                arts.setdefault(texte_key(_nature(m.group(1)), "", parse_fr_date(m.group(3)), n["num"]), rec)
            arts[key] = rec
        cat[corpus] = arts
    return cat
