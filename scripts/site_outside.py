"""Search outside the dataset and "Propose for inclusion" links, one function per norm.

These are links only. Nothing is fetched at build time or at run time, and no API or server is involved.
Results found through these links are OUTSIDE the closed universe: they have not been screened against SCOPE.md §2.

Every template below was checked by hand in a real browser on 2026-10-01. Each one opened a result list
filtered by the pre-filled query. Templates that could not be verified are not shipped:
- Légifrance jurisprudence: Cloudflare challenge, and robots.txt disallows automated access;
- law.justia.com and FindLaw caselaw: Cloudflare challenge;
- Google Scholar: bot wall, and the court code could not be confirmed;
- news.mobar.org ?s=: the query is ignored and the newsroom page is shown.
ArianeWeb (Conseil d'État) has no URL query parameter (its hash route is always #/recherche). It is offered as
an entry link, and the user pastes the citation by hand.
"""
import re
from urllib.parse import quote, urlencode

REPO = "vagabondo73/family-law-fr-us-annotated-browser"
VERIFIED = "2026-10-01"

FR_CODE_NAMES = {
    "fr-cc": "code civil", "fr-cpc": "code de procédure civile", "fr-coj": "code de l'organisation judiciaire",
    "fr-casf": "code de l'action sociale et des familles", "fr-csp": "code de la santé publique",
    "fr-cp": "code pénal", "fr-cpp": "code de procédure pénale", "fr-cgi": "code général des impôts",
    "fr-css": "code de la sécurité sociale", "fr-ceseda": "code de l'entrée et du séjour des étrangers et du droit d'asile",
    "fr-cpce": "code des procédures civiles d'exécution",
}


def _q(s):
    return quote(s, safe="")


def courtlistener(q, courts):
    return "https://www.courtlistener.com/?" + urlencode({"q": q, "type": "o", "court": " ".join(courts)}, quote_via=quote)


def justia(q):
    return "https://www.justia.com/search?" + urlencode({"q": q}, quote_via=quote)


def judilibre(q):
    return "https://www.courdecassation.fr/recherche-judilibre?" + urlencode({"search_api_fulltext": q}, quote_via=quote)


def eurlex(q, lang="fr"):
    return "https://eur-lex.europa.eu/search.html?" + urlencode({"scope": "EURLEX", "text": q, "lang": lang, "type": "quick"}, quote_via=quote)


def infocuria(q, lang="FR"):
    return "https://infocuria.curia.europa.eu/tabs/affair?" + urlencode({"lang": lang, "searchTerm": q}, quote_via=quote)


def hudoc(q):
    return "https://hudoc.echr.coe.int/eng#" + quote('{"fulltext":["%s"]}' % q.replace('"', '\\"'), safe='{}[]:,')


def incadat(q):
    return "https://www.incadat.com/en/search?" + urlencode({"search[keyword]": q}, quote_via=quote)


ARIANE = "https://www.conseil-etat.fr/arianeweb/#/recherche"


def _fr_num(num):
    m = re.match(r"^([LRDA])\.?\s*(\d.*)$", str(num or ""))
    return f"{m.group(1)}. {m.group(2)}" if m else str(num or "")


def _instrument(n):
    p = n.get("path") or []
    return (p[0].get("label") if p else "") or ""


def _short(s, k=90):
    s = re.split(r"\s+[—–]\s+|\s+\(", str(s or ""))[0].strip().rstrip(".")
    return s[:k]


def citation(n):
    """Return the query string used to pre-fill the outside searches. It is not an official citation."""
    c, num, kind = n.get("corpus", ""), str(n.get("num") or ""), n.get("kind")
    if kind == "judge-made-rule":
        return _short(n.get("heading"))
    if c in FR_CODE_NAMES:
        return f'"article {_fr_num(num)} du {FR_CODE_NAMES[c]}"'
    if c == "fr-const":
        return f'"article {num} de la Constitution"'
    if c == "fr-textes":
        return f'article {num} {_short(n.get("heading"), 70)}'
    if c == "eu-reg":
        m = re.match(r"eu-reg-(\d{4})-(\d+)", n["id"])
        act = f"{m.group(1)}/{m.group(2)}" if m else _short(_instrument(n), 60)
        return f"{act} article {num}" if n.get("kind") != "text" else act
    if c == "mo-rsmo":
        return f'"{num}"'
    if c == "mo-rules":
        return f'"Rule {num}"'
    if c == "mo-const":
        return f'"Mo. Const. {num}"'
    if c in ("us-usc", "us-cfr", "us-const"):
        return f'"{num}"'
    if c.startswith("int-"):
        inst = _short(_instrument(n) or n.get("heading"), 70)
        return f'{inst} article {num}' if re.match(r"^\d", num) else inst
    return f'"{num}"'


MONTHS_FR = dict(zip("january february march april may june july august september october november december".split(),
                     "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()))


def int_queries(n):
    """(French-court query, U.S.-court query) for a treaty provision: instrument date + article number."""
    num = str(n.get("num") or "")
    art = re.match(r"^\d", num) is not None
    if n["id"].startswith("int-coe-echr"):
        return ((f'"article {num} de la Convention européenne"' if art else '"Convention européenne des droits de l\'homme"'),
                (f'"European Convention on Human Rights" "article {num}"' if art else '"European Convention on Human Rights"'))
    title = _instrument(n) or n.get("heading") or ""
    m = re.search(r"(\d{1,2})(?:er)?\s+([A-Za-zéèûôî]+)\s+(\d{4})", title)
    if m:
        mon = m.group(2).lower()
        fr = f"{m.group(1)} {MONTHS_FR.get(mon, mon)} {m.group(3)}"
        # U.S. opinions rarely cite treaty dates; they use the instrument name ("Hague Convention", "Article 13")
        name = "Hague Convention" if n["id"].startswith("int-hcch") else re.split(r",\s", _short(title, 120))[0]
        return ((f'"{fr}" "article {num}"' if art else f'"{fr}"'), (f'"{name}" "article {num}"' if art else f'"{name}"'))
    words = " ".join(re.sub(r"\([^)]*\)", " ", title).split()[:7])
    q = (f'"{words}" article {num}' if art else f'"{words}"') if words else citation(n)
    return q, q


def _link(engine, label_fr, label_en, url, note_fr="", note_en="", manual=False):
    return {"engine": engine, "label_fr": label_fr, "label_en": label_en, "url": url,
            "note_fr": note_fr, "note_en": note_en, "manual": manual}


def outside_links(n):
    """Return a list of outside-search links for norm n (an empty list if none apply)."""
    c, side, q = n.get("corpus", ""), n.get("side"), citation(n)
    out = []
    if side == "mo":
        out += [
            _link("courtlistener", "CourtListener — Cour suprême et cours d'appel du Missouri", "CourtListener — Missouri Supreme Court & Court of Appeals",
                  courtlistener(q, ["mo", "moctapp"])),
            _link("justia", "Justia (recherche générale)", "Justia (site search)", justia(f"{q} Missouri")),
        ]
    elif side == "us":
        out += [
            _link("courtlistener", "CourtListener — Cour suprême des États-Unis et 8e circuit", "CourtListener — U.S. Supreme Court & Eighth Circuit",
                  courtlistener(q, ["scotus", "ca8"])),
            _link("justia", "Justia (recherche générale)", "Justia (site search)", justia(q)),
        ]
    elif side == "fr":
        out += [
            _link("judilibre", "Judilibre — Cour de cassation et juridictions judiciaires", "Judilibre — Cour de cassation & judicial courts", judilibre(q)),
            _link("arianeweb", "ArianeWeb — Conseil d'État (saisir la citation)", "ArianeWeb — Conseil d'État (enter the citation)", ARIANE,
                  "pas de pré-remplissage possible : copier la citation", "no pre-fill possible: copy the citation", manual=True),
        ]
    elif side == "eu":
        out += [
            _link("infocuria", "InfoCuria — Cour de justice de l'UE", "InfoCuria — Court of Justice of the EU", infocuria(q)),
            _link("eurlex", "EUR-Lex (actes et jurisprudence)", "EUR-Lex (acts and case law)", eurlex(q)),
            _link("judilibre", "Judilibre — application en France", "Judilibre — application in France", judilibre(q)),
        ]
    elif side == "int":
        if c == "int-coe":
            num = str(n.get("num") or "")
            hq = f"Article {num}" if n["id"].startswith("int-coe-echr-art-") else q.replace('"', "")
            out.append(_link("hudoc", "HUDOC — Cour européenne des droits de l'homme", "HUDOC — European Court of Human Rights", hudoc(hq)))
        if c == "int-hcch" and re.match(r"int-hcch-1980(\b|-)", n["id"]):
            num = str(n.get("num") or "")
            out.append(_link("incadat", "INCADAT — HCCH, enlèvement d'enfants 1980", "INCADAT — HCCH, 1980 Child Abduction case law",
                             incadat(f"Article {num}") if re.match(r"^\d", num) else "https://www.incadat.com/en/search"))
        qfr, qen = int_queries(n)
        out += [
            _link("judilibre", "Judilibre — France", "Judilibre — France", judilibre(qfr)),
            _link("courtlistener", "CourtListener — États-Unis (Cour suprême, 8e circuit, Missouri)", "CourtListener — U.S. (Supreme Court, 8th Cir., Missouri)",
                  courtlistener(qen, ["scotus", "ca8", "mo", "moctapp"])),
        ]
    return out


def propose_url(n, base=""):
    """Return a pre-filled GitHub new-issue URL; field ids match .github/ISSUE_TEMPLATE/proposal.yml."""
    num = n.get("num") or n["id"]
    params = {
        "template": "proposal.yml",
        "labels": "proposal,needs-screening",
        "title": f"[Proposal] {n['id']} — ",
        "norm_id": n["id"],
        "norm_page": f"{base}content/{n['id']}.html" if base else f"content/{n['id']}.html",
    }
    return f"https://github.com/{REPO}/issues/new?" + urlencode(params, quote_via=quote)
