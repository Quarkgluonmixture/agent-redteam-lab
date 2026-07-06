#!/usr/bin/env python3
"""Feedback loop: fold replay observations into the bank, rank by the risk model,
and report the attempt-vs-confirmed reconciliation + per-strategy hit rates.

Usage:
    python scripts/rank_candidates.py --parsed artifacts/eval_X/parsed_candidates.jsonl \
        [--run artifacts/eval_X/parsed_run.json] [--bank kaggle/candidate_bank.jsonl] \
        [--mode public_lb|private_transfer|research] [--out artifacts/ranked_candidates.jsonl]

Writes the ranked/selected bank to --out (does NOT overwrite the committed bank, which
stays reproducible from gen_candidates.py). Analytics go to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages"))

import risk  # noqa: E402
from portfolio import enrich_from_replay, select  # noqa: E402


def _load_jsonl(path: str) -> list[dict]:
    rows = []
    if path and os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            s = line.strip()
            if s and not s.startswith("#"):
                rows.append(json.loads(s))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bank", default=os.path.join(ROOT, "kaggle", "candidate_bank.jsonl"))
    ap.add_argument("--parsed", required=True, help="parsed_candidates.jsonl from parse_artifacts")
    ap.add_argument("--run", default=None, help="parsed_run.json (for confirmed findings_count)")
    ap.add_argument("--mode", default="public_lb")
    ap.add_argument("--out", default=os.path.join(ROOT, "artifacts", "ranked_candidates.jsonl"))
    args = ap.parse_args(argv)

    bank = _load_jsonl(args.bank)
    records = _load_jsonl(args.parsed)
    if not bank:
        print(f"rank_candidates: empty/missing bank: {args.bank}")
        return 1
    confirmed = None
    if args.run and os.path.exists(args.run):
        confirmed = json.load(open(args.run, encoding="utf-8")).get("findings_count")

    enriched = enrich_from_replay(bank, records)
    selected = select(enriched, mode=args.mode)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in selected:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    rec = risk.reconcile(records, confirmed)
    print(f"rank_candidates: mode={args.mode} bank={len(bank)} selected={len(selected)} -> {args.out}")
    print(f"  reconcile: attempts_local={rec['attempts_local']} confirmed={rec['confirmed_findings']} "
          f"blocked={rec['blocked_or_unscored']} optimism={rec['evaluator_optimism']}")
    if rec["note"]:
        print(f"  ⚠ {rec['note']}")
    print("  attempt rate by strategy:")
    for sid, d in risk.strategy_hit_rates(records).items():
        print(f"    {sid}: {d['attempts']}/{d['n']} ({d['attempt_rate']})")
    print("  attempt rate by predicate:")
    for p, d in risk.predicate_hit_rates(records).items():
        print(f"    {p}: {d['attempts']}/{d['n']} ({d['attempt_rate']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
