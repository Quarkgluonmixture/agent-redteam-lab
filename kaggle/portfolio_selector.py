"""Portfolio selection: turn a candidate bank into the set of findings to ship.

Phase-2 scaffold: a minimal, correct-by-construction selector (dedup + limits +
mode hooks). Real scoring-aware ranking arrives with the risk model in Phase 7;
the heuristic weights below are stubs, documented for continuity.

Modes (see docs/EVAL_PROTOCOL.md):
  * ``public_lb``        — optimise replayable score/sec + public unique-cell diversity.
  * ``private_transfer`` — optimise COARSE cell diversity + cross-model robustness;
                           must NOT overfit to the last-3-message-hash cell quirk.
  * ``research``         — interpretability / coverage; keep everything valid.
"""

from __future__ import annotations

from typing import Iterable

try:  # allow both `import utils` (sibling) and `from kaggle import utils`
    import utils  # type: ignore
except ImportError:  # pragma: no cover
    from . import utils  # type: ignore

MODES = ("public_lb", "private_transfer", "research")


def _coarse_key(row: dict) -> tuple:
    """Coarse cell identity for private-transfer dedup: predicate x sink x tools.

    Deliberately IGNORES message wording, so trivially-reworded variants collapse
    to one entry (the opposite of the public unique-cell farming vector).
    """
    return (
        row.get("intendedPredicate", "UNKNOWN"),
        row.get("expectedSink"),
        tuple(sorted(row.get("expectedTools", []) or [])),
    )


def _exact_key(row: dict) -> tuple:
    """Exact identity: coarse key + the message chain (distinct wording kept)."""
    return _coarse_key(row) + (tuple(row.get("userMessages", [])),)


def select(
    rows: Iterable[dict],
    *,
    mode: str = "public_lb",
    budget_s: float = utils.DEFAULT_ATTACK_BUDGET_S,
    max_findings: int = utils.DEFAULT_MAX_SHIPPED_CANDIDATES,
) -> list[dict]:
    """Return a validated, de-duplicated, capped list of candidate rows.

    Invalid rows are dropped (this scaffold never returns malformed candidates).
    ``budget_s`` is accepted for API stability; the scaffold does no timed search.
    ``max_findings`` defaults to a conservative replay-time-safe cap, NOT the 2000 hard
    limit — see the note in utils.py.
    """
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")

    # Drop malformed candidates up front — the shipped object must be replayable.
    valid = [r for r in rows if not utils.validate_candidate(r)]

    # Dedup: private_transfer collapses reworded variants; others keep exact chains.
    key = _coarse_key if mode == "private_transfer" else _exact_key
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for r in valid:
        k = key(r)
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)

    # Cap at the replay limit (excess would be silently dropped by the evaluator).
    return deduped[: min(max_findings, utils.MAX_FINDINGS_PER_RUN)]


# --- Ranking heuristic (stub, wired in Phase 7 once the risk model exists) ---

def candidate_value(row: dict) -> float:
    """Placeholder score/candidate. Real weights come from local eval artifacts."""
    sev = utils.PREDICATE_FAMILIES.get(row.get("intendedPredicate", "UNKNOWN"), 1)
    weight = utils.SEVERITY_WEIGHT.get(sev, 1)
    chars = sum(len(m) for m in row.get("userMessages", []))
    return float(weight) - 0.002 * chars
