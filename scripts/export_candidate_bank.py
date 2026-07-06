#!/usr/bin/env python3
"""Merge strategy outputs into a validated, normalised candidate bank (JSONL).

Consumes one or more JSONL inputs (each line an AttackCandidateDraft row — the
format Phase-5 strategy generators will emit) and writes a single normalised bank:
validate → normalise (drop None optionals, known fields only) → dedup by id →
write. Invalid rows are skipped with a report; ``--strict`` fails on any invalid row.

Usage:
    python scripts/export_candidate_bank.py INPUT.jsonl [INPUT2.jsonl ...] \
        -o kaggle/candidate_bank.jsonl [--strict] [--local]

Phase-3 scaffold: the plumbing is complete; real strategy inputs arrive in Phase 5.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages"))

from core.candidate import (  # noqa: E402
    AttackCandidateDraft,
    validate,
    MAX_CHARS_PER_MESSAGE,
    LOCAL_SDK_MAX_CHARS,
)

DEFAULT_OUT = os.path.join(ROOT, "kaggle", "candidate_bank.jsonl")


def _read_rows(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            rows.append(json.loads(s))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="+", help="strategy-output JSONL file(s)")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="fail on any invalid row")
    ap.add_argument("--local", action="store_true", help="use the 2,000-char local cap")
    args = ap.parse_args(argv)

    max_chars = LOCAL_SDK_MAX_CHARS if args.local else MAX_CHARS_PER_MESSAGE
    kept: list[dict] = []
    seen: set[str] = set()
    dropped = 0

    for path in args.inputs:
        if not os.path.exists(path):
            print(f"export_candidate_bank: input not found: {path}")
            return 1
        for row in _read_rows(path):
            errs = validate(row, max_chars=max_chars)
            if errs:
                dropped += 1
                msg = f"  drop {row.get('id')!r}: {errs[0]}"
                if args.strict:
                    print(f"export_candidate_bank: FAIL (strict) — invalid row:\n{msg}")
                    return 1
                print(msg)
                continue
            cid = row["id"]
            if cid in seen:
                dropped += 1
                print(f"  drop {cid!r}: duplicate id")
                continue
            seen.add(cid)
            # Normalise: keep known fields only, drop None optionals.
            kept.append(AttackCandidateDraft.from_row(row).to_row())

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for row in kept:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"export_candidate_bank: wrote {len(kept)} candidate(s) to {args.out} "
          f"({dropped} dropped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
