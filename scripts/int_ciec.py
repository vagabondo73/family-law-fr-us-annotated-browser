"""CIEC conventions: crawl ciec1.org list pages, parse France's status row and the French text (articles).
Output raw/int/ciec/ciec.json. Re-run: python3 scripts/int_ciec.py"""
import os, re, sys, html, json, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, dump, UA

D = os.path.join(RAW, "ciec")
os.makedirs(D, exist_ok=True)


def get(url, dest):
    if not os.path.exists(dest) or os.path.getsize(dest) < 2000:
        subprocess.run(["curl", "-s", "-L", "-m", "60", "-A", UA, "-o", dest, url])
    return open(dest, encoding="utf-8", errors="replace").read()


def text_of(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", h)).replace("\xa0", " ")
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


def main():
    links = []
    for i, u in enumerate(["https://ciec1.org/conventions/", "https://ciec1.org/conventions/page/2/", "https://ciec1.org/conventions/page/3/"]):
        h = get(u, os.path.join(D, f"list{i}.html"))
        for l in re.findall(r"https://ciec1\.org/convention/[^\"'<> ]+/", h):
            if l not in links:
                links.append(l)
    out = []
    for l in links:
        slug = l.rstrip("/").split("/")[-1]
        h = get(l, os.path.join(D, slug + ".html"))
        t = text_of(h)
        m = re.search(r"Convention \(n°\s*(\d+)\)", t) or re.search(r"n(\d+)-", slug)
        num = m.group(1) if m else None
        title = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
        title = text_of(title.group(1)) if title else slug
        # France status row: FRANCE \n sig \n ratif \n eif
        st = re.search(r"\n[+*]?\s*FRANCE\n((?:\d{2}/\d{2}/\d{4}|/)\n(?:\d{2}/\d{2}/\d{4}|/)?\n?(?:\d{2}/\d{2}/\d{4}|/)?)", "\n" + t)
        fr = None
        if st:
            vals = st.group(1).split("\n")
            vals = [v for v in vals if v]
            fr = {"signature": vals[0] if len(vals) > 0 and vals[0] != "/" else None,
                  "ratification": vals[1] if len(vals) > 1 and vals[1] != "/" else None,
                  "entry_into_force": vals[2] if len(vals) > 2 and vals[2] != "/" else None}
        signed_at = re.search(r"(signée|ouverte à la signature|adopté[e]?) à ([^\n]+?) le (\d{1,2}(?:er)? \w+ \d{4})", t)
        eif_gen = re.search(r"Entrée en vigueur\s*:?\s*\n?([^\n]{0,40}\d{4})", t)
        body = t[t.find("Texte de la Convention"):] if "Texte de la Convention" in t else ""
        if not body and "Texte du Protocole" in t:
            body = t[t.find("Texte du Protocole"):]
        stop = re.search(r"\n(EN FOI DE QUOI|Contactez Nous)", body)
        body = body[:stop.start()] if stop else body
        parts = re.split(r"\n(Article (?:1er|premier|\d+))\n", "\n" + body + "\n")
        arts = []
        for i in range(1, len(parts) - 1, 2):
            n = parts[i].replace("Article", "").strip()
            n = {"1er": "1", "premier": "1"}.get(n, n)
            arts.append({"num": n, "text": parts[i + 1].strip()})
        out.append({"url": l, "slug": slug, "num": num, "title": title, "france": fr,
                    "signed": signed_at.group(0) if signed_at else None, "eif_general": eif_gen.group(1) if eif_gen else None,
                    "articles": arts})
        print(num, (fr or {}), len(arts), title[:70], flush=True)
    dump(os.path.join(D, "ciec.json"), out)


if __name__ == "__main__":
    main()
