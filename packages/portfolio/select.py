"""Lab-side portfolio selection: enrich candidates from replay, rank by the risk
model, dedup, and cap by count + replay-time.

This is the richer, research-facing sibling of the self-contained shipping selector
`kaggle/portfolio_selector` (which mirrors the ranking subset). It composes
`packages/risk` for scoring/value and consumes `packages/replay` per-candidate
records to close the feedback loop.
"""

from __future__ import annotations

from typing import Any, Iterable

import risk  # packages/risk
from core.candidate import MAX_FINDINGS_PER_RUN, validate

MODES = ("public_lb", "private_transfer", "research")
DEFAULT_MAX_CANDIDATES = 200
DEFAULT_REPLAY_BUDGET_MS = 9_000_000.0  # one 9000 s replay phase

_SUCCESS_MAP = {
    "deterministic_success": "deterministicSuccess",
    "gpt_oss_success": "gptOssSuccess",
    "gemma_success": "gemmaSuccess",
}


def _get(rec: Any, name: str):
    return rec.get(name) if isinstance(rec, dict) else getattr(rec, name, None)


def _coarse_str(row: dict) -> str:
    return "{}|{}|{}".format(
        row.get("intendedPredicate", "UNKNOWN"),
        row.get("expectedSink"),
        ",".join(sorted(row.get("expectedTools", []) or [])),
    )


def _public_str(row: dict) -> str:
    return _coarse_str(row) + "|" + "¶".join(row.get("userMessages", []))


def enrich_from_replay(bank: list[dict], records: Iterable[Any]) -> list[dict]:
    """Return a copy of the bank with per-candidate replay observations folded in."""
    by_id = {_get(r, "candidate_id"): r for r in records}
    out = []
    for row in bank:
        r2 = dict(row)
        rec = by_id.get(row.get("id"))
        if rec is not None:
            for field, key in _SUCCESS_MAP.items():
                v = _get(rec, field)
                if v is not None:
                    r2[key] = bool(v)
            ms = _get(rec, "replay_ms")
            if ms:
                r2["estimatedReplayMs"] = ms
            fr = _get(rec, "failure_reason")
            if fr:
                r2["notes"] = fr
        out.append(r2)
    return out


def rank(bank: Iterable[dict]) -> list[dict]:
    """Validated candidates sorted by risk.candidate_value (highest first, stable)."""
    valid = [r for r in bank if not validate(r)]
    return sorted(valid, key=risk.candidate_value, reverse=True)


def select(
    bank: Iterable[dict],
    *,
    mode: str = "public_lb",
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    replay_budget_ms: float = DEFAULT_REPLAY_BUDGET_MS,
) -> list[dict]:
    """Validate → rank → dedup (coarse for private_transfer, exact else) → cap by
    both count and replay-time budget."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")

    ranked = rank(bank)
    for r in ranked:
        r.setdefault("coarseCellKey", _coarse_str(r))
        r.setdefault("publicCellKey", _public_str(r))

    hard_cap = min(max_candidates, MAX_FINDINGS_PER_RUN)
    seen: set[str] = set()
    out: list[dict] = []
    spent = 0.0
    for r in ranked:
        key = r["coarseCellKey"] if mode == "private_transfer" else r["publicCellKey"]
        if key in seen:
            continue
        cost = risk.replay_cost_ms(r)
        if out and spent + cost > replay_budget_ms:
            break
        seen.add(key)
        out.append(r)
        spent += cost
        if len(out) >= hard_cap:
            break
    return out
