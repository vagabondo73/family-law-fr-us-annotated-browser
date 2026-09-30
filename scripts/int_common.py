"""Shared helpers for the int_* / eu_* pipeline (International & EU instruments, SCOPE §4.4)."""
import json, os, re, subprocess, time, html, urllib.parse, urllib.request

ROOT = "/home/user/workspace/flb"
RAW = os.path.join(ROOT, "raw", "int")
DATA = os.path.join(ROOT, "data")
SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"
UA = "Mozilla/5.0 (FLB family-law research; contact via repo)"


def sparql(q, retries=3):
    data = urllib.parse.urlencode({"query": q}).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(SPARQL, data=data, headers={
                "Accept": "application/sparql-results+json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            return [{k: v["value"] for k, v in b.items()} for b in d["results"]["bindings"]]
        except Exception as e:
            print("sparql retry", i, e)
            time.sleep(3 * (i + 1))
    raise RuntimeError("sparql failed")


def cellar_get(celex, lang="fra", accept="application/xhtml+xml, text/html", dest=None):
    """Download a document from Cellar by CELEX through content negotiation. Returns path or None."""
    url = "http://publications.europa.eu/resource/celex/" + urllib.parse.quote(celex, safe="")
    dest = dest or os.path.join(RAW, "eu", celex.replace("/", "_") + "." + lang + ".html")
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(["curl", "-s", "-L", "-m", "180", "-A", UA, "-H", "Accept: " + accept,
                        "-H", "Accept-Language: " + lang, "-o", dest, "-w", "%{http_code}", url],
                       capture_output=True, text=True)
    if r.stdout.strip() != "200" or os.path.getsize(dest) < 1000:
        try:
            os.remove(dest)
        except OSError:
            pass
        return None
    return dest


def strip_tags(s):
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|tr|li|h\d|table)>", "\n", s)
    s = re.sub(r"(?i)</td>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in s.split("\n")]
    out, blank = [], False
    for l in lines:
        if not l:
            continue
        out.append(l)
    return "\n".join(out)


def slug(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)
