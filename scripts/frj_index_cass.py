# -*- coding: utf-8 -*-
"""Index every CASS decision (published Cour de cassation decisions, DILA CASS via Tricoteuses mirror).
Output: work/frj/cass_index.jsonl (one line per decision, meta + sommaire + liens + citations). Re-runnable:
only files whose (path, mtime) are not yet indexed are parsed unless --full."""
import os, re, sys, json, glob
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from frj_common import *

KIND = next((a.split("=")[1] for a in sys.argv if a.startswith("--src=")), "cass")
SRC = {"cass": f"{RAW}/cass/global", "jade": f"{RAW}/jade/global/publie", "constit": f"{RAW}/constit/global"}[KIND]
OUT = f"{WORK}/{KIND}_index.jsonl"


def tag(x, name):
    m = re.search(rf"<{name}(?:\s[^>]*)?>(.*?)</{name}>", x, re.S)
    return clean_xml_text(m.group(1)).strip() if m else ""


MOTIF = re.compile(r"^(?:\d+\.\s*|[IVX]+\.\s*|(?:Mais\s+)?(?:Considérant|Attendu)\s+(?:que\s*|qu')(?:,\s*)?|Or,?\s*)?(?:aux termes d[eu']|selon l'|selon les|selon ce|il résulte d[eu']|il résulte des|il se déduit d[eu']|il s'induit d[eu']|il ressort d[eu']|en application d[eu']|en vertu d[eu']|l'article [^,]{1,40} dispose|les dispositions d[eu']|il résulte de la combinaison)", re.I)
DISPO = re.compile(r"^Article (?:1er|premier|\d+)\s*\.?\s*[-–—]", re.I)
OBJET = re.compile(r"relative à la conformité aux droits et libertés que la Constitution garantit", re.I)


CLAUSE_SPLIT = re.compile(r"(?<=[;:])\s+(?=(?:Vu|VU|Attendu|ATTENDU|Mais|MAIS|Considérant|CONSIDERANT|Et attendu|ET ATTENDU|Sur)\b)")


def clauses(p):
    """Split a paragraph into clauses at '; Attendu…', ': Vu…' boundaries (old single-paragraph decisions)."""
    return CLAUSE_SPLIT.split(p)


GRIEF = re.compile(r"^(?:\d+\.\s*)?(?:Les?\s+(?:députés|sénateurs|requérants?|parties?\s+requérantes?|associations?\s+requérantes?|sociétés?\s+requérantes?|parties?\s+intervenantes?)|La\s+(?:partie|société|requérante|association)\s+(?:requérante|intervenante)?|Selon\s+(?:les|le|la)\s+(?:requérants?|députés|sénateurs|parties?)|Le Premier ministre|Il est soutenu|Il est reproché|Les auteurs de la saisine|Les parties intervenantes)", re.I)


def classify(p, i):
    if re.match(r"^(Vu|VU)\b", p):
        return "vu"
    if GRIEF.match(p):
        return "grief"
    if MOTIF.match(p):
        return "motif"
    if DISPO.match(p):
        return "dispositif"
    if OBJET.search(p):
        return "objet"
    return "text"


class _TO(Exception):
    pass


def _alarm(*a):
    raise _TO()


def parse(path):
    import signal
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(20)
    try:
        return _parse(path)
    except _TO:
        return {"path": os.path.relpath(path, RAW), "error": "timeout"}
    finally:
        signal.alarm(0)


def _parse(path):
    try:
        x = open(path, encoding="utf-8").read()
    except Exception as e:
        return {"path": path, "error": str(e)}
    d = {"path": os.path.relpath(path, RAW)}
    for k in ["ID", "TITRE", "DATE_DEC", "NATURE", "FORMATION", "ECLI", "SOLUTION", "NUMERO", "FORM_DEC_ATT", "DATE_DEC_ATT", "JURIDICTION",
              "PUBLI_RECUEIL", "TYPE_REC", "NATURE_QUALIFIEE", "URL_CC", "TITRE_JO", "ANCIEN_ID"]:
        d[k.lower()] = tag(x, k)
    d["numeros"] = [clean_xml_text(n).strip() for n in re.findall(r"<NUMERO_AFFAIRE>(.*?)</NUMERO_AFFAIRE>", x, re.S)]
    m = re.search(r"<PUBLI_BULL([^>]*)/?>(?:(.*?)</PUBLI_BULL>)?", x, re.S)
    d["publi_bull"] = {"publie": (re.search(r'publie="(\w+)"', m.group(1)) or [None, None])[1] if m else None,
                       "text": clean_xml_text(m.group(2) or "").strip() if m else ""}
    d["sct"] = [{"type": t, "text": norm_ws(clean_xml_text(s))} for t, s in re.findall(r'<SCT[^>]*TYPE="(\w+)"[^>]*>(.*?)</SCT>', x, re.S)]
    d["ana"] = [clean_xml_text(a).strip() for a in re.findall(r"<ANA[^>]*>(.*?)</ANA>", x, re.S)]
    liens = []
    for attrs, txt in re.findall(r"<LIEN\s([^>]*?)(?:/>|>(.*?)</LIEN>)", x, re.S):
        a = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
        t = norm_ws(clean_xml_text(txt or ""))
        if t or a.get("id"):
            liens.append({"text": t, "id": a.get("id", ""), "num": a.get("num", ""), "typelien": a.get("typelien", ""), "naturetexte": a.get("naturetexte", "")})
    d["liens"] = liens
    m = re.search(r"<LOI_DEF([^>]*)/?>", x)
    if m:
        d["loi_def"] = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    cm = re.search(r"<CONTENU>(.*?)</CONTENU>", x, re.S)
    body = clean_xml_text(cm.group(1)) if cm else ""
    d["text_len"] = len(body)
    paras = [norm_ws(p) for p in body.split("\n") if norm_ws(p)]
    d["vu"] = [p for p in paras if re.match(r"^(Vu|VU)\b", p)][:12]
    cites = []
    for i, p in enumerate(paras):
        for cl in clauses(p):
            k = classify(cl, i)
            cites += extract_citations(cl, k)
            cites += extract_extra(cl, k)
    for s in d["sct"]:
        cites += extract_citations(s["text"], "titrage") + extract_extra(s["text"], "titrage")
    for a in d["ana"]:
        cites += extract_citations(a, "sommaire") + extract_extra(a, "sommaire")
    for l in liens:
        cites += extract_lien(l["text"]) + extract_extra_lien(l["text"])
    # merge per (corpus,num)
    merged = {}
    for c in cites:
        k = (c["corpus"], c["num"], bool(c.get("ancien")))
        e = merged.setdefault(k, {"corpus": c["corpus"], "num": c["num"], "sources": [], "n": 0})
        e["n"] += 1
        if c["source"] not in e["sources"]:
            e["sources"].append(c["source"])
        for f in ("alineas", "redaction", "range_from", "suivants", "ancien", "devenu", "texte_alt"):
            if f in c and f not in e:
                e[f] = c[f]
    d["cites"] = list(merged.values())
    return d


def main():
    files = sorted(glob.glob(f"{SRC}/**/*.xml", recursive=True))
    print("files", len(files), flush=True)
    done = set()
    if os.path.exists(OUT) and "--full" not in sys.argv:
        for line in open(OUT):
            try:
                done.add(json.loads(line)["path"])
            except Exception:
                pass
    todo = [f for f in files if os.path.relpath(f, RAW) not in done]
    print("todo", len(todo), flush=True)
    mode = "w" if "--full" in sys.argv else "a"
    with open(OUT, mode) as out, Pool(2) as pool:
        for i, d in enumerate(pool.imap_unordered(parse, todo, chunksize=200)):
            out.write(json.dumps(d, ensure_ascii=False) + "\n")
            if i % 10000 == 0:
                print(i, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
