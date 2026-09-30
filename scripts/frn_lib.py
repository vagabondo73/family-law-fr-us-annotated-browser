"""frn_lib — parsing helpers for Tricoteuses LEGI git mirrors (codes) and dila/textes_juridiques.

Used by scripts/frn_build.py. Pure stdlib.
"""
import html
import json
import os
import re
import subprocess
import time
import urllib.request
import urllib.error

ROOT = "/home/user/workspace/flb"
RAW = os.path.join(ROOT, "raw")
TODAY = time.strftime("%Y-%m-%d")

IN_FORCE_STATES = {"VIGUEUR", "VIGUEUR_DIFF", "ABROGE_DIFF", "MODIFIE", "MODIFIE_DIFF", "VIGUEUR_ETEN", "VIGUEUR_NON_ETEN"}


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def parse_front(md):
    """Return (meta dict, body str)."""
    meta = {}
    body = md
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end > 0:
            for line in md[3:end].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = md[end + 4:]
    return meta, body


TAG_RE = re.compile(r"<[^>]+>")


def clean_text(body):
    """Article body markdown/HTML -> plain text with paragraphs separated by blank lines."""
    # cut the trailing sections
    for marker in ["\n## [Autres formats]", "\n## Références faites", "\n## Articles faisant référence",
                   "\n## Textes faisant référence", "\n<details>"]:
        i = body.find(marker)
        if i >= 0:
            body = body[:i]
    # section/article pages: drop breadcrumb before the page's own "# " heading
    m1 = re.search(r"^# .+$", body, re.M)
    if m1:
        body = body[m1.end():]
    # drop headings (# Article X, ## [text title])
    lines = [l for l in body.splitlines() if not l.startswith("#")]
    body = "\n".join(lines)
    body = re.sub(r"<br\s*[^>]*/?>", "\n\n", body, flags=re.I)
    body = re.sub(r"</p>|</tr>|</li>|</div>|</h\d>", "\n\n", body, flags=re.I)
    body = re.sub(r"</t[dh]>", " | ", body, flags=re.I)
    body = TAG_RE.sub("", body)
    body = html.unescape(body)
    # markdown links [x](y) -> x
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    paras = []
    for block in re.split(r"\n\s*\n", body):
        t = " ".join(x.strip() for x in block.splitlines() if x.strip())
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            paras.append(t)
    return "\n\n".join(paras)


def section_title(readme_path):
    md = read(readme_path)
    meta, body = parse_front(md)
    m = re.search(r"^# (.+)$", body, re.M)
    return (m.group(1).strip() if m else os.path.basename(os.path.dirname(readme_path))), meta.get("Identifiant")


def walk_code(repo_dir):
    """Yield article dicts from a Tricoteuses code repo."""
    title_cache = {}
    for dirpath, dirnames, filenames in os.walk(repo_dir):
        if "/.git" in dirpath or dirpath.endswith(".git"):
            continue
        dirnames.sort()
        for fn in sorted(filenames):
            if not (fn.startswith("article_") and fn.endswith(".md")):
                continue
            p = os.path.join(dirpath, fn)
            meta, body = parse_front(read(p))
            rel = os.path.relpath(dirpath, repo_dir)
            path = []
            if rel != ".":
                parts = rel.split(os.sep)
                for i in range(1, len(parts) + 1):
                    d = os.path.join(repo_dir, *parts[:i])
                    if d not in title_cache:
                        rp = os.path.join(d, "README.md")
                        title_cache[d] = section_title(rp) if os.path.exists(rp) else (parts[i - 1], None)
                    lab, sid = title_cache[d]
                    node = {"label": lab, "id": parts[i - 1]}
                    if sid:
                        node["legiscta"] = sid
                    path.append(node)
            yield {
                "file": os.path.relpath(p, repo_dir),
                "num": meta.get("Numéro") or fn[8:-3],
                "etat": meta.get("État", ""),
                "debut": meta.get("Date de début", ""),
                "fin": meta.get("Date de fin", ""),
                "legiarti": meta.get("Identifiant", ""),
                "path": path,
                "text": clean_text(body),
            }


def in_force(a, today=TODAY):
    if a["etat"] not in IN_FORCE_STATES:
        return False
    if a.get("fin") and a["fin"] <= today:
        return False
    return True


def status_of(a, today=TODAY):
    e = a["etat"]
    if a.get("debut", "") > today or e in ("VIGUEUR_DIFF", "MODIFIE_DIFF"):
        return "en vigueur différée (à compter du %s)" % a.get("debut")
    if e == "ABROGE_DIFF":
        return "en vigueur (abrogation différée au %s)" % a.get("fin")
    if e == "MODIFIE" and a.get("fin", "2999") < "2999":
        return "en vigueur (modification différée au %s)" % a.get("fin")
    return "en vigueur"


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True).stdout.strip()


def http_get(url, tries=4, timeout=60):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "flb-frn/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:  # noqa
            last = e
        time.sleep(2 * (i + 1))
    raise RuntimeError("GET failed %s: %s" % (url, last))


TJ_RAW = "https://git.tricoteuses.fr/dila/textes_juridiques/raw/branch/main"


def tj_path(ident):
    """LEGITEXT000006071192 -> LEGI/TEXT/00/00/06/07/11/LEGITEXT000006071192.md"""
    m = re.match(r"(LEGI|JORF)(TEXT|ARTI|SCTA)(\d{12})$", ident)
    base, kind, d = m.groups()
    return "%s/%s/%s/%s/%s/%s/%s/%s.md" % (base, kind, d[0:2], d[2:4], d[4:6], d[6:8], d[8:10], ident)


NUM_RE = re.compile(r"^([LRDA]\*?\.?\s*)?(\d+)(.*)$", re.I)


def num_key(num):
    """Sort/compare key for article numbers like '311-19', 'L213-3-1', '1099-1', '80 septies'."""
    s = num.strip()
    m = re.match(r"^([A-Za-z]*)\s*\*?\s*(\d+)\s*(.*)$", s)
    if not m:
        return (s, 0, ())
    pre, base, rest = m.groups()
    subs = []
    latin = {"bis": 2, "ter": 3, "quater": 4, "quinquies": 5, "sexies": 6, "septies": 7, "octies": 8,
             "nonies": 9, "decies": 10, "undecies": 11, "duodecies": 12, "terdecies": 13, "quaterdecies": 14,
             "quindecies": 15, "sexdecies": 16, "septdecies": 17, "octodecies": 18, "novodecies": 19,
             "vicies": 20, "A": 0.1, "B": 0.2, "C": 0.3, "D": 0.4, "E": 0.5, "F": 0.6, "G": 0.7}
    for tok in re.split(r"[-\s_]+", rest):
        if not tok:
            continue
        if tok.isdigit():
            subs.append(int(tok))
        elif tok.lower() in latin:
            subs.append(0.5 + latin[tok.lower()] / 100.0)
        elif tok in latin:
            subs.append(latin[tok] / 100.0)
        else:
            subs.append(0.99)
    return (pre.upper(), int(base), tuple(subs))


def in_range(num, lo, hi, prefix=None):
    """Inclusive range on base number + subdivisions. lo/hi like '1100', '1231-7'."""
    k = num_key(num)
    if prefix is not None and k[0] != prefix:
        return False
    lk, hk = num_key(lo), num_key(hi)
    kk = (k[1], k[2])
    lkk = (lk[1], lk[2])
    # hi: include all subdivisions of hi (e.g. hi '892' includes '892-1'? no -> exact; use hi+'-999' to extend)
    hkk = (hk[1], hk[2])
    return lkk <= kk <= hkk or (kk[0] == hkk[0] and hk[2] == () and False)
