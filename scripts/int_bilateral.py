"""France-United States bilateral instruments relevant to family law -> raw/int/bilateral.json (consumed by int_treaties.py).
Status source: U.S. Department of State, Treaties in Force 2026 (France section), extract in raw/int/texts/tif2026_france.txt.
Re-run: python3 scripts/int_bilateral.py && python3 scripts/int_treaties.py"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, dump

TIF = "https://www.state.gov/wp-content/uploads/2026/06/Treaties-in-Force-2026.pdf"
TIF_LABEL = "U.S. Department of State, Treaties in Force 2026 (France)"


def st(fr_eif, us_eif, note):
    return {"FR": {"status": "party", "entry_into_force": fr_eif}, "US": {"status": "party", "entry_into_force": us_eif}, "note": note}


INSTR = [
    {"key": "consular-1966", "title": "Consular Convention between the United States of America and France, with protocol and exchange of letters (Paris, 18 July 1966)",
     "eif": "1968-01-07", "cite": "18 UST 2939; TIAS 6389; 700 UNTS 257", "url": "https://treaties.un.org/Pages/showDetails.aspx?objid=08000002801353f1",
     "text": "consular1966", "issues": ["int.bilateral.consular"], "keep": None},
    {"key": "ssa-1987", "title": "Agreement on Social Security between the United States of America and the French Republic (Paris, 2 March 1987)",
     "eif": "1988-07-01", "cite": "TIAS 12106", "url": "https://www.ssa.gov/international/Agreement_Texts/french.html",
     "text": "ssa-fr", "issues": ["int.bilateral.social-security"], "keep": None},
    {"key": "estate-tax-1978", "title": "Convention for the avoidance of double taxation and the prevention of fiscal evasion with respect to taxes on estates, inheritances, and gifts (Washington, 24 November 1978), as amended by the Protocol of 8 December 2004",
     "eif": "1980-10-01", "cite": "32 UST 1935; TIAS 9812; 1234 UNTS 187; Protocol TIAS 06-1221", "url": "https://www.irs.gov/businesses/international-businesses/france-tax-treaty-documents",
     "text": None, "issues": ["int.bilateral.tax", "int.successions"], "keep": None},
    {"key": "income-tax-1994", "title": "Convention for the avoidance of double taxation and the prevention of fiscal evasion with respect to taxes on income and capital (Paris, 31 August 1994), as amended by the Protocols of 8 December 2004 and 13 January 2009",
     "eif": "1995-12-30", "cite": "1963 UNTS 67", "url": "https://www.irs.gov/businesses/international-businesses/france-tax-treaty-documents",
     "text": None, "issues": ["int.bilateral.tax"], "keep": None},
]


def clean_lines(t):
    out = []
    for l in t.split("\n"):
        s = l.strip()
        if not s or re.fullmatch(r"\d{1,4}", s) or re.search(r"United Nations\s*[—-]\s*Treaty Series|Nations Unies\s*[—-]\s*Recueil", s) or re.fullmatch(r"Article \d+(\.\d+)? annotation|Preamble annotation|\*\*", s):
            continue
        out.append(s)
    return out


def french_score(s):
    w = re.findall(r"\b\w+\b", s.lower())
    return sum(1 for x in w if x in ("les", "des", "le", "la", "du", "et", "aux", "est", "sont", "dans", "une")) / max(1, len(w))


def articles(fname):
    p = os.path.join(RAW, "texts", fname + ".txt")
    t = open(p, encoding="utf-8").read()
    t = re.sub(r"\*\*", "", t)
    t = re.sub(r"(?m)^#+\s*", "", t)
    t = "\n".join(clean_lines(t))
    parts = re.split(r"\n(Article \d+)\n", "\n" + t + "\n")
    arts, dropped = {}, []
    for k in range(1, len(parts) - 1, 2):
        num = parts[k].split()[1]
        body = parts[k + 1]
        stop = re.search(r"(IN WITNESS WHEREOF|EN FOI DE QUOI|Done at Paris|Fait à Paris)", body)
        if stop:
            body = body[:stop.start()]
        body = re.sub(r"\n(?:PART|Part|CHAPTER|Chapter|TITLE) [IVX]+\b[^\n]*(\n[A-Z ,]+)?\s*$", "", body.strip())
        if french_score(body) > 0.12:
            dropped.append(num)
            continue
        if num not in arts:
            arts[num] = body.strip()
    return arts, dropped


def main():
    out, gaps = [], []
    for i in INSTR:
        base = {"corpus": "int-bilateral", "side": "int", "lang": "en", "status": "in force",
                "status_detail": st(i["eif"], i["eif"], f"Listed in {TIF_LABEL}: {i['cite']}"),
                "applies_to": ["FR", "US"], "official_url": i["url"],
                "alt_urls": [{"label": TIF_LABEL, "url": TIF}], "xrefs": [], "interps": []}
        rec = dict(base, id=f"int-bilateral-{i['key']}", kind="text", num=i["key"], heading=i["title"],
                   path=[{"label": i["title"], "id": f"int-bilateral-{i['key']}"}], text=f"Treaty record ({i['cite']}).", in_force_since=i["eif"],
                   source_ids={"tif": i["cite"]}, issues=i["issues"] + ["int.status"])
        out.append(rec)
        if not i["text"]:
            gaps.append(f"{i['key']}: article-level text not ingested (tax treaty; status record + link only)")
            continue
        arts, dropped = articles(i["text"])
        if dropped:
            gaps.append(f"{i['key']}: articles {dropped} dropped (bilingual page mixing detected)")
        for num, body in arts.items():
            out.append(dict(base, id=f"int-bilateral-{i['key']}-art-{num}", kind="treaty-article", num=num, heading=f"Article {num}",
                            path=[{"label": i["title"], "id": f"int-bilateral-{i['key']}"}], text=body, in_force_since=i["eif"],
                            source_ids={"tif": i["cite"], "article": num}, issues=i["issues"]))
    # Child-support reciprocity: no invented dates
    out.append({"id": "int-bilateral-child-support-reciprocity", "corpus": "int-bilateral", "side": "int", "lang": "en", "kind": "text",
                "num": "child-support-reciprocity", "heading": "France–United States reciprocity for the enforcement of child support (42 U.S.C. § 659a foreign reciprocating country)",
                "path": [], "text": "Not listed as a treaty in Treaties in Force 2026. Since 1 January 2017 the 2007 Hague Child Support Convention (int-hcch-2007) applies between the United States and the European Union Member States including France; see int-hcch-2007.",
                "in_force_since": None, "status": "superseded-by-multilateral", "status_detail": {"FR": {"status": "see int-hcch-2007"}, "US": {"status": "see int-hcch-2007"}},
                "applies_to": ["FR", "US"], "official_url": TIF, "alt_urls": [], "source_ids": {}, "issues": ["int.maintenance", "int.status"], "xrefs": ["int-hcch-2007"], "interps": []})
    dump(os.path.join(RAW, "bilateral.json"), out)
    dump(os.path.join(RAW, "bilateral_gaps.json"), gaps)
    print(len(out), gaps)


if __name__ == "__main__":
    main()
