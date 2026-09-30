"""Re-check the int/eu sources: HCCH status tables, UNTC status pages, CIEC pages (curl), EUR-Lex/Cellar
latest consolidated versions (SPARQL). Compares with data/sources-int.json and raw/int/eu_norms_ledger.json and
writes raw/int/status_check_report.json. CoE charts need a browser (coe.int blocks scripted clients): the report
lists them as 'manual'.
Run in background (≈2-4 min):  setsid nohup python3 scripts/int_status_check.py > raw/int/status_check.log 2>&1 < /dev/null &
Then, if changes are reported: python3 scripts/int_eu_norms.py; python3 scripts/int_treaties.py; python3 scripts/int_link.py"""
import os, sys, json, hashlib, subprocess, datetime, re, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from int_common import RAW, DATA, load, dump, sparql

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch(url):
    fd, p = tempfile.mkstemp()
    os.close(fd)
    subprocess.run(["curl", "-s", "-L", "-m", "60", "-A", UA, "-o", p, url])
    b = open(p, "rb").read()
    os.unlink(p)
    return b


def rows_digest(b, names=("France", "United States of America", "European Union", "FRANCE")):
    """Hash only the FR/US/EU rows so that page-layout noise does not trigger changes."""
    t = b.decode("utf-8", "replace")
    rows = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r)).strip() for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)]
    keep = [r for r in rows if r.startswith(names) or r.lstrip("+* ").startswith(names)]
    if not keep:  # CIEC pages: plain-text status blocks
        txt = re.sub(r"<[^>]+>", "\n", t)
        m = re.search(r"\n[+*]?\s*FRANCE\s*\n(?:\s*\n)*([0-9/\s\n]{0,80})", txt)
        keep = [m.group(0)] if m else []
    return hashlib.sha256("\n".join(keep).encode()).hexdigest()[:16], keep


def main():
    rep = {"run": datetime.datetime.utcnow().isoformat() + "Z", "changed": [], "unchanged": 0, "manual": [], "errors": []}
    srcs = {s["id"]: s for s in load(os.path.join(DATA, "sources-int.json"), [])}
    base = load(os.path.join(RAW, "status_rows_baseline.json"), {})
    new_base = {}
    for sid, s in srcs.items():
        if s["id"].startswith(("hcch-status-", "untc-")) or s["id"] == "ciec":
            urls = [s["official"]]
            if sid == "ciec":
                urls = [c["url"] for c in load(os.path.join(RAW, "ciec", "ciec.json"), [])]
            for u in urls:
                try:
                    d, keep = rows_digest(fetch(u))
                except Exception as e:
                    rep["errors"].append({"url": u, "error": str(e)})
                    continue
                new_base[u] = {"digest": d, "rows": keep}
                if u in base and base[u]["digest"] != d:
                    rep["changed"].append({"source": sid, "url": u, "before": base[u]["rows"], "after": keep})
                else:
                    rep["unchanged"] += 1
        elif sid in ("coe-treaty-office", "ssa-france"):
            rep["manual"].append({"source": sid, "url": s["official"], "how": "browser_exec (cloud) — see int_coe_status note in coverage/int-coe.json"})
    # Cellar consolidated versions
    for a in load(os.path.join(RAW, "eu_norms_ledger.json"), []):
        act = a["act"]
        if not re.match(r"3\d{4}[RL]\d{4}", act):
            continue
        q = """PREFIX cdm:<http://publications.europa.eu/ontology/cdm#>
SELECT ?c WHERE { ?w cdm:resource_legal_id_celex ?c . FILTER(STRSTARTS(STR(?c), "0%s")) }""" % act[1:]
        try:
            vers = sorted(x["c"] for x in sparql(q))
        except Exception as e:
            rep["errors"].append({"act": act, "error": str(e)})
            continue
        today = datetime.date.today().strftime("%Y%m%d")
        valid = [v for v in vers if re.search(r"-(\d{8})$", v) and v[-8:] <= today]
        latest = valid[-1] if valid else None
        if latest and latest != a.get("consolidated_used"):
            rep["changed"].append({"source": f"eurlex-{act}", "before": a.get("consolidated_used"), "after": latest})
        else:
            rep["unchanged"] += 1
    if not base:
        rep["note"] = "first run: baseline of FR/US/EU status rows written (raw/int/status_rows_baseline.json)"
    dump(os.path.join(RAW, "status_rows_baseline.json"), new_base if new_base else base)
    dump(os.path.join(RAW, "status_check_report.json"), rep)
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in rep.items()}))


if __name__ == "__main__":
    main()
