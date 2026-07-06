#!/usr/bin/env python3
"""Validate a JSONL candidate bank against the core schema. Fail-closed.

Usage:
    python scripts/validate_candidate_bank.py [BANK.jsonl] [--local] [--quiet]

Default bank: kaggle/candidate_bank.jsonl. ``--local`` validates against the
stricter local-wheel message-length cap (2,000) instead of the competition cap
(10,000). Exit 0 = all valid & unique ids; exit 1 = any invalid row or duplicate id.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages"))

from core.candidate import validate, MAX_CHARS_PER_MESSAGE, LOCAL_SDK_MAX_CHARS  # noqa: E402

DEFAULT_BANK = os.path.join(ROOT, "kaggle", "candidate_bank.jsonl")


def load_jsonl(path: str) -> list[tuple[int, dict]]:
    """Return (line_no, row) for each non-blank, non-comment JSONL line."""
    out: list[tuple[int, dict]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            out.append((i, json.loads(s)))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bank", nargs="?", default=DEFAULT_BANK)
    ap.add_argument("--local", action="store_true",
                    help="validate against the 2,000-char local wheel cap")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    max_chars = LOCAL_SDK_MAX_CHARS if args.local else MAX_CHARS_PER_MESSAGE
    if not os.path.exists(args.bank):
        print(f"validate_candidate_bank: FAIL — bank not found: {args.bank}")
        return 1

    rows = load_jsonl(args.bank)
    problems: list[str] = []
    seen_ids: dict[str, int] = {}
    for line_no, row in rows:
        for err in validate(row, max_chars=max_chars):
            problems.append(f"  {args.bank}:{line_no}: {err}")
        cid = row.get("id")
        if isinstance(cid, str):
            if cid in seen_ids:
                problems.append(f"  {args.bank}:{line_no}: duplicate id {cid!r} (also line {seen_ids[cid]})")
            else:
                seen_ids[cid] = line_no

    if problems:
        print(f"validate_candidate_bank: FAIL — {len(problems)} problem(s):")
        print("\n".join(problems))
        return 1
    if not args.quiet:
        cap = "local 2,000" if args.local else "competition 10,000"
        print(f"validate_candidate_bank: PASS — {len(rows)} candidate(s), unique ids, {cap} char cap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
