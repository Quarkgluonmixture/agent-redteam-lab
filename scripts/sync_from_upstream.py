#!/usr/bin/env python3
"""Pull generic modules from the private upstream repo, redacted + fail-closed.

NEVER a blind copy: each file is redacted, then RE-SCANNED with the public-safety
scanner; anything still tripping the scanner is refused (fail-closed) and never
written. Dry-run by default. See docs/SYNC_FROM_UPSTREAM.md + MIGRATION_AUDIT.md.

Usage:
    SOURCE_REPO=/path/to/private/repo python scripts/sync_from_upstream.py [--apply]
        [--allow-delete] [--report artifacts/sync_report.md]
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import public_safety_scan as pss  # noqa: E402
from sync import MAPPINGS, NEVER_SYNC, SOURCE_REPO_ENV, redact  # noqa: E402


def _match(rel: str, pat: str) -> bool:
    """Glob match that tolerates a leading `**/` for top-level + nested files."""
    tail = pat[3:] if pat.startswith("**/") else pat
    return (fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, tail)
            or fnmatch.fnmatch(os.path.basename(rel), tail))


def _iter_files(base: str, include: list[str], exclude: list[str]):
    for dp, _dns, fns in os.walk(base):
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            if not any(_match(rel, g) for g in include):
                continue
            if any(_match(rel, g) for g in exclude):
                continue
            if any(n in rel for n in NEVER_SYNC):
                continue
            yield full, rel


def run_sync(source_repo: str, target_root: str, forbidden: list[str], *, apply: bool):
    """Return a report dict; writes files only when apply=True AND redaction is clean."""
    results = []
    ok = True
    for m in MAPPINGS:
        src_base = os.path.join(source_repo, m["from"])
        if not os.path.isdir(src_base):
            results.append({"mapping": m["from"], "status": "source-missing"})
            continue
        for full, rel in _iter_files(src_base, m.get("include", ["**/*"]), m.get("exclude", [])):
            try:
                text = open(full, "r", encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            redacted, hits = (redact(text, forbidden) if m.get("transform") == "redact" else (text, []))
            findings = pss.scan_text(redacted, forbidden)
            entry = {"from": rel, "to": os.path.join(m["to"], rel),
                     "redactions": hits, "residual_findings": len(findings)}
            if findings:
                ok = False
                entry["status"] = "REFUSED (residual findings after redaction)"
            elif apply:
                dest = os.path.join(target_root, m["to"], rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(redacted)
                entry["status"] = "written"
            else:
                entry["status"] = "would-sync (dry-run)"
            results.append(entry)
    return {"ok": ok, "apply": apply, "results": results}


def _write_report(report: dict, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines = [f"# sync_report (ok={report['ok']}, apply={report['apply']})", ""]
    for r in report["results"]:
        lines.append(f"- {r.get('status')}: {r.get('from', r.get('mapping'))} "
                     f"→ {r.get('to', '')} redactions={r.get('redactions', [])}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write files (default: dry-run)")
    ap.add_argument("--allow-delete", action="store_true", help="permit deletions (unused; never deletes)")
    ap.add_argument("--report", default=os.path.join(ROOT, "artifacts", "sync_report.md"))
    args = ap.parse_args(argv)

    source = os.environ.get(SOURCE_REPO_ENV)
    if not source or not os.path.isdir(source):
        print(f"sync_from_upstream: set {SOURCE_REPO_ENV} to the private repo path (got {source!r}).")
        return 1

    forbidden = pss.load_forbidden_substrings(os.path.join(ROOT, pss.PRIVATE_SEED))
    report = run_sync(source, ROOT, forbidden, apply=args.apply)
    _write_report(report, args.report)

    n = len(report["results"])
    refused = sum(1 for r in report["results"] if str(r.get("status", "")).startswith("REFUSED"))
    print(f"sync_from_upstream: {n} file(s), refused={refused}, apply={args.apply} → {args.report}")
    if not report["ok"]:
        print("  ⚠ FAIL-CLOSED: redaction left residual findings; fix redact rules before syncing.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
