#!/usr/bin/env python3
"""Run the ingestion pipelines declared in docs/PIPELINES.md (```pipeline blocks).

Usage: python3 scripts/run_pipelines.py [--only id1,id2|all] [--dry-run]
Writes data/pipeline-report.json. Exit code 1 if any executed pipeline failed (skipped/placeholder ≠ failure).
"""
import argparse, datetime, json, os, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent


def parse(md):
    out = []
    for block in re.findall(r"```pipeline\n(.*?)```", md, re.S):
        p = {"run": []}
        for line in block.strip().splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "run":
                p["run"].append(v)
            else:
                p[k] = v
        p["needs"] = [x.strip() for x in p.get("needs", "").split(",") if x.strip()]
        out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default=str(ROOT / "data" / "pipeline-report.json"))
    a = ap.parse_args()
    pipes = parse((ROOT / "docs" / "PIPELINES.md").read_text(encoding="utf-8"))
    want = None if a.only in ("", "all") else {x.strip() for x in a.only.split(",")}
    report, failed = [], False
    for p in pipes:
        if want and p.get("id") not in want:
            continue
        r = {"id": p.get("id"), "owner": p.get("owner"), "corpora": p.get("corpora"), "steps": []}
        missing = [n for n in p["needs"] if not n.endswith("?") and not os.environ.get(n)]
        if missing:
            r["status"] = f"skipped (missing {', '.join(missing)})"
            report.append(r); print(f"[skip] {r['id']}: {r['status']}"); continue
        status = "ok"
        for cmd in p["run"]:
            if cmd.upper().startswith("TODO"):
                r["steps"].append({"cmd": cmd, "status": "placeholder"}); print(f"[todo] {r['id']}: {cmd}")
                status = "placeholder" if status == "ok" else status
                continue
            if a.dry_run:
                r["steps"].append({"cmd": cmd, "status": "dry-run"}); print(f"[dry ] {r['id']}: {cmd}"); continue
            t0 = time.time()
            print(f"[run ] {r['id']}: {cmd}", flush=True)
            try:
                proc = subprocess.run(cmd, shell=True, cwd=ROOT, timeout=int(p.get("timeout", 60)) * 60)
                st = "ok" if proc.returncode == 0 else f"exit {proc.returncode}"
            except subprocess.TimeoutExpired:
                st = "timeout"
            r["steps"].append({"cmd": cmd, "status": st, "seconds": round(time.time() - t0)})
            if st != "ok":
                status, failed = "failed", True
                break
        r["status"] = status
        report.append(r)
    out = {"generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "pipelines": report}
    pathlib.Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.report).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
