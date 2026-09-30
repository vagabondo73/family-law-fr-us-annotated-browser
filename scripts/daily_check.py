#!/usr/bin/env python3
"""Daily source check — detects upstream changes; NEVER rewrites legal content.

For every entry of data/sources*.json:
  check = "git-head"  → `git ls-remote <url> HEAD`; if the host is a Forgejo/Gitea instance (git.tricoteuses.fr),
                         the compare API maps changed files to norm ids (article_<num>.md) and new decisions (JURITEXT…).
  check = "http-hash" → GET the page; records ETag / Last-Modified and sha256 of the normalised text
                         (optional "hash_regex" narrows the hashed region; "check_url" overrides the URL).
  check = "api"       → channel "api:legifrance": Légifrance consult/getArticle for every norm with source_ids.legiarti,
                         comparing état + dateDebut with the corpus; channel "api:judilibre": lists published decisions
                         since the last check. Runs only when PISTE_CLIENT_ID / PISTE_CLIENT_SECRET are set.
Baseline = the source's "last_version" (set by the ingestion pipeline when data was built). The previous report is
used to tell *new* changes from ones already reported.

Outputs data/update-report.json (+ a Markdown summary). With --open-issue and GITHUB_TOKEN/GITHUB_REPOSITORY set, opens
(or comments on) a GitHub issue labelled `source-change` listing changed sources and affected norms. No file under
data/norms or data/interps is ever modified.

Usage: python3 scripts/daily_check.py [--data data] [--open-issue] [--summary update-report.md] [--max-api 3000]
"""
import argparse, datetime, glob, hashlib, html, json, os, pathlib, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "flb-daily-check/1.0 (+https://github.com/vagabondo73/family-law-fr-us-annotated-browser)"
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
PISTE_OAUTH = os.environ.get("PISTE_OAUTH_URL", "https://oauth.piste.gouv.fr/api/oauth/token")
LF_API = os.environ.get("LEGIFRANCE_API", "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app")
JL_API = os.environ.get("JUDILIBRE_API", "https://api.piste.gouv.fr/cassation/judilibre/v1.0")


def http(url, data=None, headers=None, method=None, timeout=30):
    h = {"User-Agent": UA, **(headers or {})}
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, dict(r.headers), r.read()


def load_json(p, default=None):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def load_norm_index(data):
    """norm id -> (corpus, num, in_force_since, legiarti)"""
    idx = {}
    for f in glob.glob(str(data / "norms" / "*.json")):
        d = load_json(f, {}) or {}
        for n in d.get("norms", []):
            idx[n["id"]] = {"corpus": n.get("corpus"), "num": n.get("num"), "in_force_since": n.get("in_force_since"),
                            "legiarti": (n.get("source_ids") or {}).get("legiarti"), "status": n.get("status")}
    return idx


# ---------------------------------------------------------------- git
def git_head(url):
    out = subprocess.run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:300] or "git ls-remote failed")
    line = out.stdout.strip().split("\n")[0]
    return line.split()[0] if line else None


def forgejo_compare(url, base, head):
    """Return list of changed file paths using the Forgejo/Gitea compare API, or None if unavailable."""
    m = re.match(r"https?://([^/]+)/([^/]+)/([^/.]+?)(?:\.git)?/?$", url)
    if not m:
        return None
    host, owner, repo = m.groups()
    api = f"https://{host}/api/v1/repos/{owner}/{repo}/compare/{base}...{head}"
    try:
        _, _, body = http(api, timeout=60)
        d = json.loads(body)
        files = set()
        for c in d.get("commits", []) or []:
            for f in c.get("files", []) or []:
                files.add(f.get("filename"))
        for f in d.get("files", []) or []:
            files.add(f.get("filename"))
        return sorted(x for x in files if x)
    except Exception:
        return None


def map_files(files, corpora, nidx):
    by_corpus_num = {(v["corpus"], str(v["num"])): k for k, v in nidx.items()}
    norms, decisions, other, unmapped = [], [], 0, []
    for f in files:
        base = f.rsplit("/", 1)[-1]
        m = re.match(r"article_(.+)\.md$", base)
        if m:
            hit = [by_corpus_num[(c, m.group(1))] for c in corpora if (c, m.group(1)) in by_corpus_num]
            norms += hit
            if not hit:
                unmapped.append(f)  # article outside the current corpus (possibly new or out of scope) — screen it
            continue
        m = re.match(r"((?:JURI|CONS|CETA)TEXT\d+)\.xml$", base)
        if m:
            decisions.append(m.group(1))
            continue
        other += 1
    return sorted(set(norms)), sorted(set(decisions)), other, unmapped


# ---------------------------------------------------------------- http
def page_fingerprint(url, hash_regex=None):
    st, hd, body = http(url, timeout=45)
    text = body.decode("utf-8", "replace")
    if hash_regex:
        m = re.search(hash_regex, text, re.S)
        text = m.group(1) if m and m.groups() else (m.group(0) if m else text)
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", text)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t).strip()
    # strip volatile tokens (dates/times printed on the page, session ids)
    t = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", "", t)
    return {"status": st, "etag": hd.get("ETag"), "last_modified": hd.get("Last-Modified"),
            "hash": "sha256:" + hashlib.sha256(t.encode()).hexdigest(), "length": len(t)}


# ---------------------------------------------------------------- PISTE
_token = None


def piste_token():
    global _token
    if _token:
        return _token
    cid, sec = os.environ.get("PISTE_CLIENT_ID"), os.environ.get("PISTE_CLIENT_SECRET")
    if not (cid and sec):
        return None
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": cid, "client_secret": sec, "scope": "openid"}).encode()
    _, _, b = http(PISTE_OAUTH, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    _token = json.loads(b)["access_token"]
    return _token


def legifrance_articles(src, nidx, max_api):
    tok = piste_token()
    if not tok:
        return {"status": "skipped", "note": "PISTE_CLIENT_ID / PISTE_CLIENT_SECRET not set"}
    corpora = set(src.get("corpora") or [])
    targets = [(k, v) for k, v in nidx.items() if v.get("legiarti") and (not corpora or v["corpus"] in corpora)][:max_api]
    changed, errors = [], []
    for nid, v in targets:
        try:
            _, _, b = http(f"{LF_API}/consult/getArticle", data={"id": v["legiarti"]}, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
            art = (json.loads(b) or {}).get("article") or {}
            etat = art.get("etat")
            deb = art.get("dateDebut")
            if isinstance(deb, (int, float)):
                deb = datetime.datetime.fromtimestamp(deb / 1000, datetime.timezone.utc).date().isoformat()
            reasons = []
            if etat and etat != "VIGUEUR":
                reasons.append(f"état {etat}")
            if deb and v.get("in_force_since") and deb != v["in_force_since"]:
                reasons.append(f"dateDebut {deb} ≠ corpus {v['in_force_since']}")
            if reasons:
                changed.append({"norm": nid, "legiarti": v["legiarti"], "reasons": reasons})
        except Exception as e:
            errors.append(f"{nid}: {e}")
        time.sleep(0.15)
    return {"status": "changed" if changed else "unchanged", "checked_norms": len(targets), "changed_norms": changed,
            "errors": errors[:50], "observed": hashlib.sha256(json.dumps(changed, sort_keys=True).encode()).hexdigest()[:16]}


def judilibre_new(src, since):
    tok = piste_token()
    if not tok:
        return {"status": "skipped", "note": "PISTE_CLIENT_ID / PISTE_CLIENT_SECRET not set"}
    since = (since or (NOW - datetime.timedelta(days=2)).date().isoformat())[:10]
    q = {"date_start": since, "date_end": NOW.date().isoformat(), "batch_size": 100, "batch": 0,
         "type": "arret", "publication": ["b", "r", "l"], **(src.get("api_params") or {})}
    found = []
    for batch in range(0, 20):
        q["batch"] = batch
        url = f"{JL_API}/export?" + urllib.parse.urlencode(q, doseq=True)
        _, _, b = http(url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
        d = json.loads(b)
        for r in d.get("results", []):
            found.append({"id": r.get("id"), "number": r.get("number"), "date": r.get("decision_date"), "chamber": r.get("chamber"),
                          "publication": r.get("publication"), "themes": (r.get("themes") or [])[:3]})
        if not d.get("next_batch"):
            break
    return {"status": "changed" if found else "unchanged", "new_decisions": found, "observed": f"{len(found)} since {since}"}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--open-issue", action="store_true")
    ap.add_argument("--summary", default=None, help="write a Markdown summary here")
    ap.add_argument("--max-api", type=int, default=3000)
    ap.add_argument("--only", default="", help="comma-separated source ids")
    a = ap.parse_args()
    data = pathlib.Path(a.data)
    sources = []
    for f in sorted(glob.glob(str(data / "sources*.json"))):
        d = load_json(f, [])
        sources += (d.get("sources", []) if isinstance(d, dict) else d) or []
    only = {x for x in a.only.split(",") if x}
    if only:
        sources = [s for s in sources if s.get("id") in only]
    prev = {r["id"]: r for r in (load_json(data / "update-report.json", {}) or {}).get("results", [])}
    nidx = load_norm_index(data)
    results = []
    for s in sources:
        r = {"id": s.get("id"), "label": s.get("label"), "check": s.get("check"), "corpora": s.get("corpora", []),
             "checked": NOW.isoformat(), "baseline": s.get("last_version"), "status": "unknown", "changed": False}
        ch = s.get("channel") or ""
        pv = prev.get(s.get("id")) or {}
        # Baselines written by pipelines in another format (e.g. raw-body hashes) are not comparable with ours:
        # fall back to the value observed by the previous run of this script.
        bl = r["baseline"]
        if s.get("check") == "http-hash" and not (isinstance(bl, str) and bl.startswith("sha256:")):
            r["baseline"], r["baseline_from"] = pv.get("observed"), "previous-report"
        elif s.get("check") == "git-head" and not (isinstance(bl, str) and re.fullmatch(r"[0-9a-f]{40}", bl)):
            r["baseline"], r["baseline_from"] = pv.get("observed"), "previous-report"
        try:
            if s.get("check") == "git-head":
                url = ch[4:] if ch.startswith("git:") else ch
                head = git_head(url)
                r["observed"] = head
                if not r["baseline"]:
                    r["status"] = "no-baseline"
                elif head != r["baseline"]:
                    r["status"], r["changed"] = "changed", True
                    files = forgejo_compare(url, r["baseline"], head)
                    if files is not None:
                        norms, decs, other, unm = map_files(files, r["corpora"], nidx)
                        r.update({"files_changed": len(files), "affected_norms": norms, "new_decisions": decs[:200],
                                  "new_decisions_count": len(decs), "other_files": other,
                                  "unmapped_articles": unm[:300], "unmapped_articles_count": len(unm)})
                else:
                    r["status"] = "unchanged"
            elif s.get("check") == "http-hash":
                c2 = ch[5:] if re.match(r"^https?:https?://", ch) else ch  # tolerate "http:https://…" channel prefixes
                url = s.get("check_url") or (c2 if re.match(r"^https?://", c2) else s.get("official"))
                fp = page_fingerprint(url, s.get("hash_regex"))
                r["observed"], r["http"] = fp["hash"], fp
                if not r["baseline"]:
                    r["status"] = "no-baseline"
                elif fp["hash"] != r["baseline"]:
                    r["status"], r["changed"] = "changed", True
                    r["affected_norms"] = s.get("norm_ids", [])
                else:
                    r["status"] = "unchanged"
            elif s.get("check") == "api":
                if ch == "api:legifrance":
                    out = legifrance_articles(s, nidx, a.max_api)
                    r["affected_norms"] = [c["norm"] for c in out.get("changed_norms", [])]
                elif ch == "api:judilibre":
                    out = judilibre_new(s, (prev.get(s.get("id")) or {}).get("checked") or s.get("last_checked"))
                else:
                    out = {"status": "skipped", "note": f"unknown api channel {ch}"}
                r.update(out)
                r["changed"] = out.get("status") == "changed"
            else:
                r["status"] = "skipped"
                r["note"] = f"unknown check type {s.get('check')!r}"
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):  # bot wall / rate limit: not a content change, not a script failure
                r["status"], r["note"] = "blocked", f"HTTP {e.code} for automated client — verify manually or via an API/mirror"
            else:
                r["status"], r["error"] = "error", f"HTTPError {e.code}: {e.reason}"[:400]
        except Exception as e:
            r["status"], r["error"] = "error", f"{type(e).__name__}: {e}"[:400]
        p = prev.get(r["id"]) or {}
        r["new_since_last_check"] = bool(r["changed"] and (not p.get("changed") or r.get("observed") != p.get("observed")))
        results.append(r)
        print(f"[{r['status']:>11}] {r['id']}" + (f" — {r.get('error')}" if r.get("error") else ""))

    rep = {"generated": NOW.isoformat(), "changed_count": sum(r["changed"] for r in results),
           "new_count": sum(r["new_since_last_check"] for r in results),
           "error_count": sum(r["status"] == "error" for r in results),
           "blocked_count": sum(r["status"] == "blocked" for r in results),
           "note": "Detection only — no legal content was modified. Changes must be reviewed and re-ingested via the pipelines (docs/PIPELINES.md).",
           "results": results}
    (data / "update-report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = summary_md(rep)
    if a.summary:
        pathlib.Path(a.summary).write_text(md, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(md)
    if a.open_issue and rep["new_count"]:
        open_issue(rep, md)
    print(f"changed={rep['changed_count']} new={rep['new_count']} errors={rep['error_count']}")


def summary_md(rep):
    L = [f"## Source check — {rep['generated']}", "",
         f"**{rep['changed_count']}** changed source(s) (**{rep['new_count']}** new since the last check), **{rep['error_count']}** error(s), {rep.get('blocked_count', 0)} blocked (HTTP 403/429).",
         "", "_Detection only: no legal content was rewritten. Review, then re-run the relevant pipeline (workflow_dispatch → rebuild)._", "",
         "| Source | Check | Status | Observed | Affected norms |", "|---|---|---|---|---|"]
    for r in rep["results"]:
        aff = r.get("affected_norms") or []
        L.append(f"| {r['label'] or r['id']} (`{r['id']}`) | {r.get('check')} | {r['status']}{' (new)' if r.get('new_since_last_check') else ''} | "
                 f"`{str(r.get('observed') or '')[:16]}` | {', '.join(aff[:15])}{' …+' + str(len(aff) - 15) if len(aff) > 15 else ''} |")
    for r in rep["results"]:
        if r.get("changed"):
            L += ["", f"### {r['label'] or r['id']}"]
            if r.get("affected_norms"):
                L.append("Affected norms: " + ", ".join(f"`{n}`" for n in r["affected_norms"][:200]))
            for c in r.get("changed_norms", [])[:200]:
                L.append(f"- `{c['norm']}` ({c['legiarti']}): {'; '.join(c['reasons'])}")
            if r.get("unmapped_articles"):
                L.append(f"Changed articles not in the corpus (screen for scope): {r['unmapped_articles_count']}")
                L += [f"- `{u}`" for u in r["unmapped_articles"][:50]]
            if r.get("new_decisions_count") or r.get("new_decisions"):
                nd = r.get("new_decisions") or []
                L.append(f"New/changed decisions to screen: {r.get('new_decisions_count', len(nd))}")
                L += [f"- {d if isinstance(d, str) else json.dumps(d, ensure_ascii=False)}" for d in nd[:50]]
            if r.get("error"):
                L.append(f"Error: {r['error']}")
    return "\n".join(L) + "\n"


def open_issue(rep, md):
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not (tok and repo):
        print("open-issue: GITHUB_TOKEN/GITHUB_REPOSITORY not set — skipped")
        return
    api = f"https://api.github.com/repos/{repo}"
    H = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    fp = hashlib.sha256(json.dumps(sorted((r["id"], str(r.get("observed"))) for r in rep["results"] if r["changed"])).encode()).hexdigest()[:12]
    body = md + f"\n<!-- flb-fingerprint:{fp} -->\n"
    try:
        _, _, b = http(f"{api}/issues?state=open&labels=source-change&per_page=50", headers=H)
        for iss in json.loads(b):
            if f"flb-fingerprint:{fp}" in (iss.get("body") or ""):
                print(f"open-issue: already reported in #{iss['number']}")
                return
        n = rep["new_count"]
        title = f"Source changes detected ({n} source{'s' if n > 1 else ''}) — {rep['generated'][:10]}"
        _, _, b = http(f"{api}/issues", data={"title": title, "body": body[:65000], "labels": ["source-change", "needs-review"]}, headers=H, method="POST")
        print("open-issue: created #" + str(json.loads(b)["number"]))
    except urllib.error.HTTPError as e:
        print(f"open-issue failed: {e.code} {e.read()[:300]!r}")


if __name__ == "__main__":
    main()
