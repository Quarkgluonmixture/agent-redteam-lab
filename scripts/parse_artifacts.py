#!/usr/bin/env python3
"""Parse an aicomp artifacts dir into normalised JSONL + print a summary.

Usage:
    python scripts/parse_artifacts.py <artifacts-dir> [--bank kaggle/candidate_bank.jsonl]
        [--agent deterministic|gpt_oss|gemma] [--out <dir>]

Writes <out>/parsed_run.json (RunRecord) and <out>/parsed_candidates.jsonl
(PerCandidateRecord[]); <out> defaults to the artifacts dir.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages"))

from replay import parse_run, summarize  # noqa: E402


def _load_bank(path: str) -> list[dict]:
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s and not s.startswith("#"):
                rows.append(json.loads(s))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("artifacts_dir")
    ap.add_argument("--bank", default=os.path.join(ROOT, "kaggle", "candidate_bank.jsonl"))
    ap.add_argument("--agent", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if not os.path.isdir(args.artifacts_dir):
        print(f"parse_artifacts: not a directory: {args.artifacts_dir}")
        return 1

    bank = _load_bank(args.bank)
    run, per = parse_run(args.artifacts_dir, bank, agent=args.agent)

    out = args.out or args.artifacts_dir
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "parsed_run.json"), "w", encoding="utf-8") as fh:
        json.dump(run.to_dict(), fh, indent=1)
    with open(os.path.join(out, "parsed_candidates.jsonl"), "w", encoding="utf-8") as fh:
        for r in per:
            fh.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

    s = summarize(run, per)
    print(f"parse_artifacts: run {s['run_id']} agent={s['agent']} score={s['score']} "
          f"CONFIRMED findings={s['confirmed_findings']} | local attempts={s['attempted_local']}")
    if s["reconciliation"]:
        print(f"  ⚠ {s['reconciliation']}")
    print(f"  turns={s['total_turns']} tool_calls={s['total_tool_calls']} "
          f"observed_tools={s['observed_tools']}")
    print(f"  candidates={s['candidates']} (attempt-level by strategy):")
    for sid in sorted(s["by_strategy"]):
        d = s["by_strategy"][sid]
        print(f"    {sid}: {d['success']}/{d['n']}")
    print(f"  wrote parsed_run.json + parsed_candidates.jsonl to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
