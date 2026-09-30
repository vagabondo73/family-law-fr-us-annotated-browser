#!/usr/bin/env python3
"""Parse the Tricoteuses LEGI mirror of the Code de procédure civile (raw/code_de_procedure_civile, git clone --depth 1
https://git.tricoteuses.fr/codes/code_de_procedure_civile.git) into raw/mop/cpc_articles.json: one record per article
number in force today (num, LEGIARTI, dates, état, livre, path of section headings, text).
Also builds the number -> page lookup of the CPC annotated browser (content/index.html) and the list of FRCP pages.
Usage: python3 scripts/mop_cpc_articles.py [--pull]
"""
import os, re, sys, json, glob, datetime, subprocess, urllib.request
ROOT = "/home/user/workspace/flb"
REPO = os.path.join(ROOT, "raw", "code_de_procedure_civile")
OUT = os.path.join(ROOT, "raw", "mop")
os.makedirs(OUT, exist_ok=True)
TODAY = datetime.date.today().isoformat()
CPCB = "https://vagabondo73.github.io/cpc-annotated-browser/content/"
FRCPB = "https://vagabondo73.github.io/frcp-annotated-browser/content/"


def ensure_repo():
    if not os.path.isdir(REPO):
        subprocess.run(["git", "clone", "--depth", "1", "https://git.tricoteuses.fr/codes/code_de_procedure_civile.git", REPO], check=True)
    elif "--pull" in sys.argv:
        subprocess.run(["git", "-C", REPO, "pull", "--depth", "1"], check=False)
    return subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%H %cI"], capture_output=True, text=True).stdout.strip()


def front(t):
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    meta = {}
    if m:
        for l in m.group(1).splitlines():
            if ":" in l:
                k, v = l.split(":", 1); meta[k.strip()] = v.strip()
    return meta, t[m.end():] if m else t


def readme_title(d):
    p = os.path.join(d, "README.md")
    if not os.path.exists(p):
        return None
    meta, body = front(open(p, encoding="utf-8").read())
    m = re.search(r"^# (.+)$", body, re.M)
    return (m.group(1).strip() if m else None), meta.get("Identifiant")


def body_text(b):
    b = re.sub(r"^# Article .*$", "", b, count=1, flags=re.M)
    b = b.split("\n## [Autres formats]")[0]
    nota = None
    if "\n### Nota" in b:
        b, nota = b.split("\n### Nota", 1)
    clean = lambda s: re.sub(r"\n{3,}", "\n\n", re.sub(r"<[^>]+>", "", s)).strip()
    return clean(b), (clean(nota) if nota else None)


def numkey(n):
    parts = re.findall(r"\d+|[A-Za-z]+", n)
    return [int(p) if p.isdigit() else 0 for p in parts] + [0] * (6 - len(parts))


FUT = os.path.join(ROOT, "raw", "code_de_procedure_civile_futur")


AFTER = None


def next_tree():
    """Tricoteuses publishes future consolidated states on branch 'futur' (commit date = entry-into-force date).
    Return (date, path) of the first future state after today, checked out as a worktree raw/cpc_at_<date>."""
    if not os.path.isdir(FUT):
        subprocess.run(["git", "clone", "-q", "--depth", "40", "--branch", "futur", "https://git.tricoteuses.fr/codes/code_de_procedure_civile.git", FUT], check=False)
    else:
        subprocess.run(["git", "-C", FUT, "fetch", "-q", "--depth", "40", "origin", "futur"], check=False)
        subprocess.run(["git", "-C", FUT, "reset", "-q", "--hard", "origin/futur"], check=False)
    log = subprocess.run(["git", "-C", FUT, "log", "--format=%H %cI %s"], capture_output=True, text=True).stdout.splitlines()
    fut = sorted([(l.split()[1][:10], l.split()[0], l.split(" ", 2)[2]) for l in log if l.split()[1][:10] > (AFTER or TODAY)])
    out = []
    for d, h, subj in fut:
        wt = os.path.join(ROOT, "raw", f"cpc_at_{d}")
        if not os.path.isdir(wt):
            subprocess.run(["git", "-C", FUT, "worktree", "add", "-f", wt, h], capture_output=True)
        out.append({"date": d, "commit": h, "subject": subj, "path": wt})
    return out


def parse_tree(repo):
    recs = {}
    for f in glob.glob(os.path.join(repo, "livre_*", "**", "article_*.md"), recursive=True):
        meta, body = front(open(f, encoding="utf-8").read())
        num = meta.get("Numéro")
        if not num:
            continue
        text, nota = body_text(body)
        recs[num] = {"legiarti": meta.get("Identifiant"), "debut": meta.get("Date de début", ""), "fin": meta.get("Date de fin", ""), "text": text}
    return recs


def main():
    global AFTER
    head = ensure_repo()
    base = REPO
    # If main lags behind (a future state's entry-into-force date has arrived), use the latest arrived state of branch futur.
    main_date = head.split()[1][:10] if len(head.split()) > 1 else ""
    AFTER = main_date
    arrived = [f for f in next_tree() if f["date"] <= TODAY]
    AFTER = None
    if arrived:
        base = arrived[-1]["path"]
        head = f"{arrived[-1]['commit']} {arrived[-1]['date']} (branch futur; main HEAD {head.split()[0]} not yet advanced)"
    recs = {}
    for f in glob.glob(os.path.join(base, "livre_*", "**", "article_*.md"), recursive=True):
        meta, body = front(open(f, encoding="utf-8").read())
        num = meta.get("Numéro")
        if not num:
            continue
        deb, fin, etat = meta.get("Date de début", ""), meta.get("Date de fin", "2999-01-01"), meta.get("État", "")
        in_force = deb <= TODAY < fin and etat in ("VIGUEUR", "ABROGE_DIFF", "MODIFIE_MORT_NE", "VIGUEUR_DIFF", "MODIFIE") or (etat == "VIGUEUR" and deb <= TODAY)
        rel = os.path.relpath(f, base)
        dirs = rel.split(os.sep)[:-1]
        path = []
        for k in range(1, len(dirs) + 1):
            t = readme_title(os.path.join(base, *dirs[:k]))
            if t and t[0]:
                path.append({"label": t[0], "id": t[1]})
        text, nota = body_text(body)
        r = {"num": num, "legiarti": meta.get("Identifiant"), "etat": etat, "debut": deb, "fin": fin, "in_force": bool(in_force),
             "livre": dirs[0], "path": path, "text": text, "nota": nota, "file": rel}
        prev = recs.get(num)
        # keep the version in force today; otherwise the latest
        if prev is None or (r["in_force"] and not prev["in_force"]) or (r["in_force"] == prev["in_force"] and r["debut"] > prev["debut"]):
            recs[num] = r
    arts = sorted(recs.values(), key=lambda r: numkey(r["num"]))
    # CPC annotated browser lookup (by article number)
    idx = urllib.request.urlopen(CPCB + "index.html", timeout=60).read().decode("utf-8")
    open(os.path.join(OUT, "cpc_index.html"), "w").write(idx)
    look = {}
    for href, lab in re.findall(r'href="([^"]*article-LEGIARTI\d+\.html)"[^>]*>\s*Article\s+([^<]+?)\s*</a>', idx):
        look.setdefault(lab.strip(), href if href.startswith("http") else CPCB + href)
    fr = urllib.request.urlopen(FRCPB + "index.html", timeout=60).read().decode("utf-8")
    open(os.path.join(OUT, "frcp_index.html"), "w").write(fr)
    frcp = sorted(set(re.findall(r"provision-frcp-([0-9.]+)\.html", fr)), key=lambda x: [int(p) for p in x.split(".")])
    for a in arts:
        a["cpc_url"] = look.get(a["num"])
    # future states (successor versions) — e.g. décret n° 2026-683 entering into force 2026-10-01
    futs = next_tree() if "--no-futur" not in sys.argv else []
    fut_meta = []
    byn = {a["num"]: a for a in arts}
    for ft in futs:
        tr = parse_tree(ft["path"])
        ch = {"date": ft["date"], "commit": ft["commit"], "subject": ft["subject"], "modified": [], "added": [], "removed": []}
        for num, r in tr.items():
            a = byn.get(num)
            if a is None:
                ch["added"].append(num)
            elif re.sub(r"\s+", " ", r["text"]) != re.sub(r"\s+", " ", a["text"]) or r["legiarti"] != a["legiarti"]:
                ch["modified"].append(num)
                a.setdefault("successors", []).append({"date": ft["date"], "legiarti": r["legiarti"], "debut": r["debut"], "text": r["text"]})
        for num in byn:
            if num not in tr:
                ch["removed"].append(num)
                byn[num].setdefault("successors", []).append({"date": ft["date"], "removed": True})
        fut_meta.append(ch)
    ending = [a["num"] for a in arts if a["fin"] < "2999-01-01"]
    json.dump({"generated": TODAY, "mirror_head": head, "future_states": fut_meta, "versions_ending_before_2999": ending, "articles": arts}, open(os.path.join(OUT, "cpc_articles.json"), "w"), ensure_ascii=False, indent=1)
    json.dump({"generated": TODAY, "lookup": look}, open(os.path.join(OUT, "cpc_browser_lookup.json"), "w"), ensure_ascii=False, indent=1)
    json.dump({"generated": TODAY, "rules": frcp, "base": FRCPB}, open(os.path.join(OUT, "frcp_rules.json"), "w"), indent=1)
    from collections import Counter
    print("articles", len(arts), "in force", sum(a["in_force"] for a in arts), Counter((a["livre"], a["in_force"]) for a in arts),
          "browser pages", len(look), "in-force w/o browser page", sum(1 for a in arts if a["in_force"] and not a["cpc_url"]), "frcp", len(frcp))


if __name__ == "__main__":
    main()
