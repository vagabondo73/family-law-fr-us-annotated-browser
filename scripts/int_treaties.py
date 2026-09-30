"""Build int-hcch, int-un, int-coe, int-ciec, int-bilateral norm corpora + status table (raw/int/status_table.json).
Inputs (fetch first): raw/int/hcch/st_*.html & ft_{en,fr}_*.html (curl, see int_status_check.py), raw/int/un/*.html,
raw/int/coe/status_browser.json + texts_fetch.json, raw/int/ciec/ciec.json, raw/int/texts/*.txt.
Re-run: python3 scripts/int_treaties.py"""
import os, re, sys, json, html, datetime
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, DATA, dump, load, strip_tags

TODAY = datetime.date.today().isoformat()
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12}
MONTHS = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def hdate(s):
    """HCCH '1-XII-1983' -> ISO"""
    m = re.match(r"(\d{1,2})-([IVX]+)-(\d{4})", s or "")
    return f"{m.group(3)}-{ROMAN[m.group(2)]:02d}-{int(m.group(1)):02d}" if m else None


def udate(s):
    """UN '7 Aug 1990' -> ISO"""
    m = re.match(r"(\d{1,2}) ([A-Z][a-z]{2})[a-z]* (\d{4})", s or "")
    return f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}" if m and m.group(2) in MONTHS else None


def edate(s):
    """dd/mm/yyyy -> ISO"""
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


# ---------------------------------------------------------------- HCCH
HCCH = [  # key, cid, title_fr, issues, full_text, lang, note
    ("1961a", 41, "Convention du 5 octobre 1961 supprimant l'exigence de la légalisation des actes publics étrangers (Apostille)", ["int.procedure.apostille"], True, "en", ""),
    ("1965", 17, "Convention du 15 novembre 1965 relative à la signification et la notification à l'étranger des actes judiciaires et extrajudiciaires", ["int.procedure.service"], True, "en", ""),
    ("1970e", 82, "Convention du 18 mars 1970 sur l'obtention des preuves à l'étranger en matière civile ou commerciale", ["int.procedure.evidence"], True, "en", ""),
    ("1980", 24, "Convention du 25 octobre 1980 sur les aspects civils de l'enlèvement international d'enfants", ["int.abduction.hague-1980"], True, "en", ""),
    ("1993", 69, "Convention du 29 mai 1993 sur la protection des enfants et la coopération en matière d'adoption internationale", ["int.adoption"], True, "en", ""),
    ("1996", 70, "Convention du 19 octobre 1996 concernant la compétence, la loi applicable, la reconnaissance, l'exécution et la coopération en matière de responsabilité parentale et de mesures de protection des enfants", ["int.child-protection"], True, "en", "United States: signed 22 Oct 2010, not ratified."),
    ("2000", 71, "Convention du 13 janvier 2000 sur la protection internationale des adultes", ["int.adults"], True, "fr", "Treaty-level only (adult protection is outside the domestic perimeter)."),
    ("2007", 131, "Convention du 23 novembre 2007 sur le recouvrement international des aliments destinés aux enfants et à d'autres membres de la famille", ["int.maintenance"], True, "en", "France bound through the EU's approval (Ap EU)."),
    ("2007p", 133, "Protocole du 23 novembre 2007 sur la loi applicable aux obligations alimentaires", ["int.maintenance", "eu.maintenance.applicable-law"], True, "fr", "Bound through the EU (applied by the EU since 18 June 2011 under Council Decision 2009/941/EC; entry into force 1 Aug 2013)."),
    ("1973a", 86, "Convention du 2 octobre 1973 sur la loi applicable aux obligations alimentaires", ["int.maintenance"], True, "fr", "Replaced between EU Member States bound by the 2007 Protocol (Protocol art. 18)."),
    ("1973r", 85, "Convention du 2 octobre 1973 concernant la reconnaissance et l'exécution de décisions relatives aux obligations alimentaires", ["int.maintenance"], True, "fr", "Replaced between States bound by the 2007 Convention (art. 48)."),
    ("1958", 38, "Convention du 15 avril 1958 concernant la reconnaissance et l'exécution des décisions en matière d'obligations alimentaires envers les enfants", ["int.maintenance"], True, "fr", ""),
    ("1956", 37, "Convention du 24 octobre 1956 sur la loi applicable aux obligations alimentaires envers les enfants", ["int.maintenance"], True, "fr", ""),
    ("1961m", 39, "Convention du 5 octobre 1961 concernant la compétence des autorités et la loi applicable en matière de protection des mineurs", ["int.child-protection"], True, "fr", "Replaced by the 1996 Convention between States Parties to both (1996 art. 51)."),
    ("1978m", 87, "Convention du 14 mars 1978 sur la loi applicable aux régimes matrimoniaux", ["int.marriage"], True, "fr", "Applies to spouses married before 29 Jan 2019; for later marriages Regulation (EU) 2016/1103 (art. 62 and 69)."),
    ("1961t", 40, "Convention du 5 octobre 1961 sur les conflits de lois en matière de forme des dispositions testamentaires", ["int.successions"], True, "fr", "Preserved by Regulation (EU) 650/2012, art. 75(1)."),
    ("1954", 33, "Convention du 1er mars 1954 relative à la procédure civile", ["int.procedure"], True, "fr", ""),
    ("1980j", 91, "Convention du 25 octobre 1980 tendant à faciliter l'accès international à la justice", ["int.procedure"], True, "fr", ""),
    ("2005", 98, "Convention du 30 juin 2005 sur les accords d'élection de for", ["int.procedure.judgments"], False, "en", "Family matters excluded (art. 2(2)(a)-(d)); status only."),
    ("2019", 137, "Convention du 2 juillet 2019 sur la reconnaissance et l'exécution des jugements étrangers en matière civile ou commerciale", ["int.procedure.judgments"], False, "en", "Family matters excluded (art. 2(1)(a)-(d)); status only."),
    ("1985", 59, "Convention du 1er juillet 1985 relative à la loi applicable au trust et à sa reconnaissance", ["int.successions"], False, "en", "Signed by France and the United States, ratified by neither; status only."),
]
HCCH_EXCLUDED = [(80, "1970 Recognition of Divorces"), (88, "1978 Celebration and Recognition of the Validity of Marriages"), (62, "1989 Succession")]


def hcch_status(cid):
    h = open(os.path.join(RAW, "hcch", f"st_{cid}.html"), encoding="utf-8", errors="replace").read()
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))
    title = re.search(r"(Convention|Protocol) of \d{1,2} \w+ \d{4}[^:]*?(?= Entry into force| Not yet in force)", t)
    eif = re.search(r"Entry into force: (\d{1,2}-[IVX]+-\d{4})", t)
    rows = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if cells and re.match(r"^(France|United States of America|European Union)$", cells[0]):
            k = {"France": "FR", "United States of America": "US", "European Union": "EU"}[cells[0]]
            if k in rows:
                continue
            sig, rat, typ, ef = (cells + [""] * 5)[1:5]
            st = "party" if hdate(ef) and hdate(ef) <= TODAY else ("signed" if sig else "not party")
            if typ.startswith("Ap EU") and "*" in typ:
                st = "party (through the EU)"
            rows[k] = {"status": st, "signature": hdate(sig), "ratification_or_accession": hdate(rat), "type": typ or None,
                       "entry_into_force": hdate(ef), "raw": cells[:8]}
    for k in ("FR", "US", "EU"):
        rows.setdefault(k, {"status": "not party"})
    return (title.group(0) if title else None), (hdate(eif.group(1)) if eif else None), rows


def hcch_articles(cid, lang):
    p = os.path.join(RAW, "hcch", f"ft_{lang}_{cid}.html")
    if not os.path.exists(p):
        return []
    h = open(p, encoding="utf-8", errors="replace").read()
    i = h.find('id="maincontent"')
    h = h[i:]
    j = h.find("<!-- /do conventions.text -->")
    if j < 0:
        j = h.find('class="col-md-3"')
    h = h[:j] if j > 0 else h
    t = strip_tags(h)
    stop = re.search(r"\n(IN WITNESS WHEREOF|EN FOI DE QUOI)", t)
    t = t[:stop.start()] if stop else t
    parts = re.split(r"\n(Article (?:\d+|premier|1er))\s*\n", "\n" + t + "\n")
    arts, chap = [], None
    for k in range(1, len(parts) - 1, 2):
        num = parts[k].split()[1]
        num = {"premier": "1", "1er": "1"}.get(num, num)
        body = parts[k + 1].strip().split("\n")
        nxt = None
        while body and re.match(r"^(CHAPTER|Chapter|chapter|CHAPITRE|Chapitre|chapitre)\b", body[-1]):
            nxt = body.pop()
        arts.append({"num": num, "text": "\n".join(body).strip(), "path": [chap] if chap else []})
        if nxt:
            chap = nxt
    return arts


# ---------------------------------------------------------------- UN
UN = [  # key, mtdsg, chapter, title_en, textfile, articles (None=all), issues, full
    ("crc", "IV-11", 4, "Convention on the Rights of the Child (New York, 20 November 1989)", "crc", None, ["int.human-rights", "int.child-protection"], True),
    ("crc-opac", "IV-11-b", 4, "Optional Protocol to the Convention on the Rights of the Child on the involvement of children in armed conflict (2000)", "crc-opac", None, ["int.human-rights"], True),
    ("crc-opsc", "IV-11-c", 4, "Optional Protocol to the Convention on the Rights of the Child on the sale of children, child prostitution and child pornography (2000)", "crc-opsc", None, ["int.human-rights", "int.adoption"], True),
    ("crc-opic", "IV-11-d", 4, "Optional Protocol to the Convention on the Rights of the Child on a communications procedure (2011)", None, None, ["int.human-rights"], False),
    ("iccpr", "IV-4", 4, "International Covenant on Civil and Political Rights (1966)", "iccpr", ["23", "24"], ["int.human-rights"], True),
    ("icescr", "IV-3", 4, "International Covenant on Economic, Social and Cultural Rights (1966)", "icescr", ["10"], ["int.human-rights"], True),
    ("cedaw", "IV-8", 4, "Convention on the Elimination of All Forms of Discrimination against Women (1979)", "cedaw", ["16"], ["int.human-rights", "int.marriage"], True),
    ("crpd", "IV-15", 4, "Convention on the Rights of Persons with Disabilities (2006)", "crpd", ["23"], ["int.human-rights"], True),
    ("marriage1962", "XVI-3", 16, "Convention on Consent to Marriage, Minimum Age for Marriage and Registration of Marriages (1962)", "marriage1962", None, ["int.marriage"], True),
    ("maint1956", "XX-1", 20, "Convention on the Recovery Abroad of Maintenance (New York, 20 June 1956)", "maint1956", None, ["int.maintenance"], True),
]
UN_EXCLUDED = [("XVI-2", "Convention on the Nationality of Married Women (1957) — neither France nor the United States is a signatory or party")]


def un_status(mt):
    h = open(os.path.join(RAW, "un", mt + ".html"), encoding="utf-8", errors="replace").read()
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))
    eif = re.search(r"Entry into force\s*:\s*(\d{1,2} [A-Z]\w+ \d{4})", t)
    rows = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if len(cells) in (3, 4) and re.match(r"^(France|United States of America|European Union)( \d+)?$", cells[0]) and re.match(r"^(\d{1,2} \w{3} \d{4})?$", cells[1]):
            k = {"France": "FR", "United States of America": "US", "European Union": "EU"}[re.sub(r" \d+$", "", cells[0])]
            if k in rows:
                continue
            rat = cells[2]
            typ = "a" if rat.endswith(" a") else ("c" if rat.endswith(" c") else ("d" if rat.endswith(" d") else "r"))
            rows[k] = {"status": "party" if udate(rat) else ("signed" if udate(cells[1]) else "not party"),
                       "signature": udate(cells[1]), "ratification_or_accession": udate(rat), "type": typ if udate(rat) else None, "raw": cells}
    for k in ("FR", "US", "EU"):
        rows.setdefault(k, {"status": "not party"})
    return (udate(eif.group(1)) if eif else None), rows


def un_articles(fname):
    p = os.path.join(RAW, "texts", fname + ".txt")
    if not os.path.exists(p):
        return []
    t = open(p, encoding="utf-8").read()
    t = re.sub(r"\*\*", "", t)
    t = re.sub(r"(?m)^#+\s*", "", t)
    parts = re.split(r"\n\s*(Article (?:\d+|[IVXL]+))(?:\s*[-–]\s*([^\n]+))?\s*\.?\s*\n", "\n" + t + "\n")
    arts, part = [], None
    for k in range(1, len(parts) - 2, 3):
        num = parts[k].split()[1]
        heading = (parts[k + 1] or "").strip()
        body = parts[k + 2].strip()
        stop = re.search(r"\n(IN WITNESS WHEREOF|In witness whereof|Footnotes|Share this|\[Signatures|CONFERENCE DES NATIONS UNIES|CONVENTION SUR LE RECOUVREMENT)", body)
        if stop:
            body = body[:stop.start()]
        lines = body.split("\n")
        nxt = None
        while lines and re.match(r"^(PART|Part) [IVX]+", lines[-1].strip()):
            nxt = lines.pop().strip()
        if not any(a["num"] == num for a in arts):
            arts.append({"num": num, "heading": heading, "text": "\n".join(l.strip() for l in lines if l.strip() and not re.fullmatch(r"_{3,}|\d{1,3}", l.strip())), "path": [part] if part else []})
        if nxt:
            part = nxt
    return arts


# ---------------------------------------------------------------- CoE
COE = [  # key, ets, title, text url key, articles, issues, full
    ("echr", "005", "Convention for the Protection of Human Rights and Fundamental Freedoms (ETS No. 005), as amended by Protocols Nos. 11, 14 and 15", "https://www.echr.coe.int/documents/d/echr/convention_ENG", ["8", "12", "14"], ["int.echr"], True),
    ("echr-p7", "117", "Protocol No. 7 to the Convention for the Protection of Human Rights and Fundamental Freedoms (ETS No. 117)", "https://www.echr.coe.int/documents/d/echr/Library_Collection_P7postP11_ETS117E_ENG", ["5"], ["int.echr.spousal-equality"], True),
    ("ets105", "105", "European Convention on Recognition and Enforcement of Decisions concerning Custody of Children and on Restoration of Custody of Children (Luxembourg, 20 May 1980) (ETS No. 105)", "https://rm.coe.int/1680078b09", None, ["int.abduction.luxembourg-1980"], True),
    ("ets160", "160", "European Convention on the Exercise of Children's Rights (ETS No. 160)", "https://rm.coe.int/168007cc53", None, ["int.child-protection"], True),
    ("cets210", "210", "Council of Europe Convention on preventing and combating violence against women and domestic violence (Istanbul, CETS No. 210)", "https://rm.coe.int/168008482e", None, ["int.domestic-violence"], True),
    ("echr-p12", "177", "Protocol No. 12 to the Convention (ETS No. 177)", None, None, ["int.echr"], False),
    ("ets058", "058", "European Convention on the Adoption of Children (ETS No. 058)", None, None, ["int.adoption"], False),
    ("cets202", "202", "European Convention on the Adoption of Children (Revised) (CETS No. 202)", None, None, ["int.adoption"], False),
    ("ets085", "085", "European Convention on the Legal Status of Children born out of Wedlock (ETS No. 085)", None, None, ["int.echr.filiation"], False),
    ("ets192", "192", "Convention on Contact concerning Children (ETS No. 192)", None, None, ["int.child-protection"], False),
    ("ets166", "166", "European Convention on Nationality (ETS No. 166)", None, None, ["int.civil-status"], False),
    ("ets043", "043", "Convention on the Reduction of Cases of Multiple Nationality and on Military Obligations in Cases of Multiple Nationality (ETS No. 043)", None, None, ["int.civil-status"], False),  # FR: Chapter I denounced (Treaty Office note)
    ("ets062", "062", "European Convention on Information on Foreign Law (ETS No. 062)", None, None, ["int.procedure"], False),
    ("ets097", "097", "Additional Protocol to the European Convention on Information on Foreign Law (ETS No. 097)", None, None, ["int.procedure"], False),
]
COE_EIF = {"005": "1953-09-03", "117": "1988-11-01", "105": "1983-09-01", "160": "2000-07-01", "210": "2014-08-01"}  # general EIF, from texts/Treaty Office


def coe_status(ets):
    sb = load(os.path.join(RAW, "coe", "status_browser.json"), {})
    rows = {}
    for line in sb.get(ets, {}).get("rows", []):
        c = line.split("\t")
        k = {"France": "FR", "United States of America": "US", "European Union": "EU"}.get(c[0])
        if not k:
            continue
        sig, rat, ef = (c + ["", "", ""])[1:4]
        st = "party" if edate(ef) else ("signed" if edate(sig) else "not party")
        rows[k] = {"status": st, "signature": edate(sig), "ratification_or_accession": edate(rat), "entry_into_force": edate(ef), "raw": c[:4]}
    for k in ("FR", "US", "EU"):
        rows.setdefault(k, {"status": "not party" if ets in sb else "unknown"})
    return rows


def coe_articles(url, keep):
    tf = load(os.path.join(RAW, "coe", "texts_fetch.json"), {})
    t = (tf.get(url) or {}).get("content") or ""
    t = re.sub(r"\*\*", "", t)
    parts = re.split(r"\n\s*(?:#+\s*)?((?i:Article) (?:\d+))(?:\s*[–-]\s*([^\n]+))?\s*\n", "\n" + t + "\n")
    arts = []
    for k in range(1, len(parts) - 2, 3):
        num = parts[k].split()[1]
        heading = (parts[k + 1] or "").strip()
        body = parts[k + 2].strip()
        stop = re.search(r"(In witness whereof|IN WITNESS WHEREOF|\nDone at [A-Z]|En foi de quoi|\nConvention européenne|\nCONVENTION EUROPÉENNE)", body)
        if stop:
            body = body[:stop.start()]
        raw_lines = [l.strip() for l in body.split("\n") if l.strip() and not re.fullmatch(r"_{3,}|(?:C?ETS|STCE|STE) ?(?:No\. ?)?\d+ [–-] .*\d{1,2}\.[IVX]+\.\d{4}", l.strip())]
        lines, expect, pend = [], 1, None
        for l in raw_lines:
            if re.fullmatch(r"\d{1,3}", l):
                if int(l) == expect:
                    pend, expect = l, expect + 1
                continue  # page numbers (not the next paragraph number) are dropped
            if re.fullmatch(r"[a-z]{1,4}", l) and l not in ("and", "or"):
                pend = (pend + " " if pend else "") + l
                continue
            lines.append((pend + " " + l) if pend else l)
            pend = None
        if not heading and lines and len(lines[0]) < 90 and not re.match(r"^\d", lines[0]) and not lines[0].endswith((".", ";", ":")):
            heading = lines.pop(0)
        # trim trailing section/chapter headings
        while lines and re.match(r"^(Section|SECTION|Chapter|CHAPTER|Title|TITLE) [IVX\d]+", lines[-1]):
            lines.pop()
        if keep and num not in keep:
            continue
        if any(a["num"] == num for a in arts):
            continue
        arts.append({"num": num, "heading": heading, "text": "\n".join(lines)})
    return arts


# ---------------------------------------------------------------- build
def norm(corpus, iid, num, heading, text, path, d, status, applies, url, alts, sids, issues, lang, detail, title_fr=None, kind="treaty-article"):
    return {"id": f"{corpus}-{iid}-art-{num}".lower(), "corpus": corpus, "side": "int", "lang": lang, "kind": kind, "num": num,
            "heading": heading or f"Article {num}", "path": path, "text": text, "in_force_since": d, "status": status,
            "status_detail": detail, "applies_to": applies, "official_url": url, "alt_urls": alts, "source_ids": sids,
            "issues": issues, "xrefs": [], "interps": [], **({"title_fr": title_fr} if title_fr else {})}


def status_word(detail):
    s = [v["status"] for v in detail.values()]
    if any(x.startswith("party") for x in s):
        return "in force"
    if any(x == "signed" for x in s):
        return "signed-not-ratified"
    return "not binding"


def applies(detail):
    return [k for k in ("FR", "US", "EU") if detail.get(k, {}).get("status", "").startswith("party")]


def instrument_record(corpus, iid, title, url, d, detail, issues, note, lang, title_fr=None):
    return {"id": f"{corpus}-{iid}", "corpus": corpus, "side": "int", "lang": lang, "kind": "text", "num": iid, "heading": title,
            "path": [{"label": title, "id": f"{corpus}-{iid}"}], "text": note or "", "in_force_since": d,
            "status": status_word(detail), "status_detail": detail, "applies_to": applies(detail), "official_url": url,
            "alt_urls": [], "source_ids": {}, "issues": issues + ["int.status"], "xrefs": [], "interps": [], **({"title_fr": title_fr} if title_fr else {})}


def main():
    out = {c: [] for c in ("int-hcch", "int-un", "int-coe", "int-ciec", "int-bilateral")}
    table, ledger = [], {}
    # HCCH
    for key, cid, tfr, issues, full, lang, note in HCCH:
        title, eif, st = hcch_status(cid)
        url = f"https://www.hcch.net/en/instruments/conventions/status-table/?cid={cid}"
        texturl = f"https://www.hcch.net/{'fr' if lang=='fr' else 'en'}/instruments/conventions/full-text/?cid={cid}"
        rec = instrument_record("int-hcch", key, title or tfr, url, eif, st, issues, note, lang, tfr)
        rec["alt_urls"] = [{"label": "HCCH full text (EN)", "url": f"https://www.hcch.net/en/instruments/conventions/full-text/?cid={cid}"},
                           {"label": "HCCH texte intégral (FR)", "url": f"https://www.hcch.net/fr/instruments/conventions/full-text/?cid={cid}"}]
        out["int-hcch"].append(rec)
        n = 0
        if full and rec["status"] == "in force":
            en = {a["num"]: a for a in hcch_articles(cid, "en")}
            fr = {a["num"]: a for a in hcch_articles(cid, "fr")}
            base = fr if lang == "fr" else en
            other = en if lang == "fr" else fr
            for num, a in base.items():
                r = norm("int-hcch", key, num, None, a["text"], [{"label": (title or tfr), "id": f"int-hcch-{key}"}] + [{"label": p} for p in a["path"]],
                         eif, "in force" if lang == "en" else "en vigueur", applies(st), texturl,
                         [{"label": "Status table (HCCH)", "url": url}], {"hcch_cid": cid, "article": num}, issues, lang, st, tfr)
                if num in other:
                    r["text_" + ("en" if lang == "fr" else "fr")] = other[num]["text"]
                r["status_note"] = "Current text unchanged since conclusion; in_force_since = general entry into force. Party dates: " + \
                    "; ".join(f"{k}: {v.get('status')}{(' since ' + v['entry_into_force']) if v.get('entry_into_force') else ''}" for k, v in st.items())
                out["int-hcch"].append(r)
                n += 1
        table.append({"instrument": title or tfr, "corpus": "int-hcch", "id": f"int-hcch-{key}", "entry_into_force": eif, "FR": st["FR"], "US": st["US"], "EU": st["EU"], "depositary_url": url, "articles": n, "note": note})
    for cid, name in HCCH_EXCLUDED:
        _, eif, st = hcch_status(cid)
        ledger.setdefault("excluded", []).append({"instrument": "HCCH " + name, "reason": "binding on neither FR nor US (no signature/ratification in HCCH status table)", "status": {k: v["status"] for k, v in st.items()}})
    # UN
    for key, mt, ch, title, tf, keep, issues, full in UN:
        eif, st = un_status(mt)
        url = f"https://treaties.un.org/Pages/ViewDetails.aspx?src=TREATY&mtdsg_no={mt}&chapter={ch}&clang=_en"
        rec = instrument_record("int-un", key, title, url, eif, st, issues, "", "en")
        out["int-un"].append(rec)
        n = 0
        if full and rec["status"] == "in force":
            arts = un_articles(tf) if tf else []
            for a in arts:
                if keep and a["num"] not in keep:
                    continue
                r = norm("int-un", key, a["num"], a.get("heading") or None, a["text"], [{"label": title, "id": f"int-un-{key}"}] + [{"label": p} for p in a["path"]],
                         eif, "in force", applies(st), url, [], {"mtdsg_no": mt, "article": a["num"]}, issues, "en", st)
                r["status_note"] = "Text source: OHCHR/UNTC; party dates: " + "; ".join(f"{k}: {v.get('status')}{(' (' + v['ratification_or_accession'] + ')') if v.get('ratification_or_accession') else ''}" for k, v in st.items())
                out["int-un"].append(r)
                n += 1
            if not arts:
                ledger.setdefault("gaps", []).append(f"int-un {key}: article text not retrieved (status record only)")
        table.append({"instrument": title, "corpus": "int-un", "id": f"int-un-{key}", "entry_into_force": eif, "FR": st["FR"], "US": st["US"], "EU": st["EU"], "depositary_url": url, "articles": n})
    # CoE
    for key, ets, title, turl, keep, issues, full in COE:
        st = coe_status(ets)
        url = f"https://www.coe.int/en/web/conventions/full-list?module=signatures-by-treaty&treatynum={ets}"
        s = status_word(st)
        if s == "not binding":
            ledger.setdefault("excluded", []).append({"instrument": title, "reason": "neither signed nor ratified by FR/US/EU (CoE Treaty Office chart)", "status": {k: v["status"] for k, v in st.items()}})
            table.append({"instrument": title, "corpus": "int-coe", "id": None, "FR": st["FR"], "US": st["US"], "EU": st["EU"], "depositary_url": url, "articles": 0, "note": "excluded — binding on neither"})
            continue
        lang = "fr" if not st["US"]["status"].startswith(("party", "signed")) else "en"
        rec = instrument_record("int-coe", key, title, url, COE_EIF.get(ets), st, issues,
                                {"043": "France: Chapter I (reduction of multiple nationality) denounced — only Chapter II (military obligations) remains in force for France (CoE Treaty Office note to the chart of signatures)."}.get(ets, ""), "en")
        out["int-coe"].append(rec)
        n = 0
        if full and s == "in force":
            arts = coe_articles(turl, keep)
            for a in arts:
                r = norm("int-coe", key, a["num"], a["heading"], a["text"], [{"label": title, "id": f"int-coe-{key}"}],
                         COE_EIF.get(ets), "in force", applies(st), url, [{"label": "Text (Council of Europe)", "url": turl}],
                         {"ets": ets, "article": a["num"]}, issues, "en", st)
                if key == "echr":
                    r["status_note"] = "Article wording unchanged since 1953 (Protocol No. 11 of 1998 only added headings). France: in force since 3 May 1974."
                out["int-coe"].append(r)
                n += 1
            if not arts:
                ledger.setdefault("gaps", []).append(f"int-coe {key}: article text not parsed")
        table.append({"instrument": title, "corpus": "int-coe", "id": f"int-coe-{key}", "entry_into_force": COE_EIF.get(ets), "FR": st["FR"], "US": st["US"], "EU": st["EU"], "depositary_url": url, "articles": n})
    # CIEC
    for c in load(os.path.join(RAW, "ciec", "ciec.json"), []):
        fr = c.get("france") or {}
        key = f"ciec{c['num']}" if c.get("num") else "ciec-" + c["slug"][:40]
        st = {"FR": {"status": "party" if edate(fr.get("entry_into_force")) or edate(fr.get("ratification")) else ("signed" if fr.get("signature") else "not party"),
                     "signature": edate(fr.get("signature")), "ratification_or_accession": edate(fr.get("ratification")), "entry_into_force": edate(fr.get("entry_into_force"))},
              "US": {"status": "not party", "note": "the United States is not a CIEC member"}, "EU": {"status": "not party"}}
        if st["FR"]["status"] == "not party":
            ledger.setdefault("excluded", []).append({"instrument": c["title"], "reason": "not signed/ratified by France (CIEC status table)"})
            table.append({"instrument": c["title"], "corpus": "int-ciec", "id": None, "FR": st["FR"], "US": st["US"], "EU": st["EU"], "depositary_url": c["url"], "articles": 0, "note": "excluded — binding on neither"})
            continue
        d = st["FR"]["entry_into_force"]
        rec = instrument_record("int-ciec", key, c["title"], c["url"], d, st, ["int.civil-status"], "", "fr", c["title"])
        rec["status_note"] = "in_force_since = entry into force for France (CIEC table)." + ("" if d else " France's entry-into-force date not shown in the CIEC table.")
        out["int-ciec"].append(rec)
        n = 0
        if st["FR"]["status"] == "party":
            seen = set()
            for a in c["articles"]:
                if a["num"] in seen:  # numbering restarts: explanatory report / annex follows the convention text
                    ledger.setdefault("ciec_truncated", []).append(f"{key}: text cut at repeated article {a['num']} (explanatory report follows)")
                    break
                seen.add(a["num"])
                txt = re.split(r"\n?Seul l'original français fait foi\.|\nRapport Explicatif|\nRAPPORT EXPLICATIF", a["text"])[0].strip()
                r = norm("int-ciec", key, a["num"], None, txt, [{"label": c["title"], "id": f"int-ciec-{key}"}], d, "en vigueur",
                         ["FR"], c["url"], [], {"ciec": c.get("num"), "article": a["num"]}, ["int.civil-status"], "fr", st, c["title"])
                out["int-ciec"].append(r)
                n += 1
        table.append({"instrument": c["title"], "corpus": "int-ciec", "id": f"int-ciec-{key}", "entry_into_force": d, "FR": st["FR"], "US": st["US"], "EU": st["EU"], "depositary_url": c["url"], "articles": n})
    # Bilateral
    bil = load(os.path.join(RAW, "bilateral.json"), [])
    for b in bil:
        out["int-bilateral"].append(b)
        if b["kind"] == "text":
            table.append({"instrument": b["heading"], "corpus": "int-bilateral", "id": b["id"], "entry_into_force": b["in_force_since"], "FR": b["status_detail"]["FR"], "US": b["status_detail"]["US"], "EU": {"status": "n/a"}, "depositary_url": b["official_url"], "articles": sum(1 for x in bil if x["id"].startswith(b["id"] + "-art-"))})
    for c, lst in out.items():
        dump(os.path.join(DATA, "norms", c + ".json"), {"corpus": c, "generated": TODAY, "norms": lst})
        print(c, len(lst), sum(1 for x in lst if x["kind"] != "text"))
    dump(os.path.join(DATA, "status-int.json"), {"generated": TODAY, "note": "FR / US / EU status of every international family-law instrument screened (SCOPE §4.4)", "instruments": table})
    dump(os.path.join(RAW, "treaties_ledger.json"), ledger)


if __name__ == "__main__":
    main()
