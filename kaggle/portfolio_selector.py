"""Portfolio selection: turn a candidate bank into the set of findings to ship.

Pipeline: validate → rank (by schema fields) → dedup → cap by BOTH candidate count
AND replay-time budget. Real risk-model weights arrive in Phase 7; the heuristic
here reads the schema fields (severityWeight/intendedPredicate, cross-model flags,
estimatedReplayMs, chars) rather than ad-hoc dict access.

Modes (see docs/EVAL_PROTOCOL.md):
  * ``public_lb``        — replayable score/sec + public unique-cell diversity (exact dedup).
  * ``private_transfer`` — COARSE cell diversity + cross-model robustness (coarse dedup);
                           must NOT overfit to the last-3-message-hash cell quirk.
  * ``research``         — interpretability / coverage; keep everything valid (exact dedup).
"""

from __future__ import annotations

from typing import Iterable

try:  # allow both `import utils` (sibling) and `from kaggle import utils`
    import utils  # type: ignore
except ImportError:  # pragma: no cover
    from . import utils  # type: ignore

MODES = ("public_lb", "private_transfer", "research")


def _severity_weight(row: dict) -> int:
    """Weight from explicit severityWeight, else derived from the predicate."""
    sw = row.get("severityWeight")
    if isinstance(sw, int) and sw in utils.SEVERITY_WEIGHT.values():
        return sw
    sev = utils.PREDICATE_FAMILIES.get(row.get("intendedPredicate", "UNKNOWN"), 1)
    return utils.SEVERITY_WEIGHT.get(sev, 1)


def _replay_ms(row: dict) -> float:
    v = row.get("estimatedReplayMs")
    return float(v) if isinstance(v, (int, float)) and v > 0 else utils.DEFAULT_REPLAY_MS_PER_CANDIDATE


def _total_chars(row: dict) -> int:
    return sum(len(m) for m in row.get("userMessages", []) if isinstance(m, str))


def candidate_value(row: dict) -> float:
    """Ranking score for one candidate (higher = ship sooner). Reads schema fields.

    Heuristic (tuned empirically in Phase 7): severity weight, a cross-model-transfer
    bonus (matters most for the held-out private LB), minus penalties for replay cost
    and message length. ``scorePerSecond``/``expectedScore`` override when present.
    """
    if isinstance(row.get("scorePerSecond"), (int, float)):
        return float(row["scorePerSecond"]) * 1000.0  # explicit measurement wins
    weight = _severity_weight(row)
    cross_model = sum(
        1 for k in ("deterministicSuccess", "gptOssSuccess", "gemmaSuccess") if row.get(k)
    )
    # A locally-verified evasion (intended trace evades the public guardrail AND fires a
    # predicate) is a stronger signal than any unverified seed → probe/ship it first.
    verified = 100.0 if row.get("verifiedEvasion") else 0.0
    return (
        verified
        + float(weight)
        + 2.0 * cross_model
        - 0.001 * _replay_ms(row) / 1000.0
        - 0.002 * _total_chars(row)
    )


def _coarse_key(row: dict) -> tuple:
    """Coarse cell identity for private-transfer dedup: predicate x sink x tools.

    Deliberately IGNORES message wording, so trivially-reworded variants collapse to
    one entry (the opposite of the public unique-cell farming vector).
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
    max_candidates: int = utils.DEFAULT_MAX_SHIPPED_CANDIDATES,
    replay_budget_ms: float = utils.DEFAULT_REPLAY_BUDGET_MS,
) -> list[dict]:
    """Return a validated, ranked, de-duplicated, twice-capped list of candidate rows.

    Caps are BOTH ``max_candidates`` (never above the 2000 hard limit) AND
    ``replay_budget_ms`` — the portfolio stops growing once its cumulative estimated
    replay time would exceed the phase budget, because replay time (not the count cap)
    is what times out submissions. ``budget_s`` is accepted for API stability; the
    scaffold does no timed exploration.
    """
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")

    # 1. Drop malformed candidates — the shipped object must be replayable.
    valid = [r for r in rows if not utils.validate_candidate(r)]

    # 2. Rank (stable): highest value first.
    ranked = sorted(valid, key=candidate_value, reverse=True)

    # 3. Dedup: private_transfer collapses reworded variants; others keep exact chains.
    key = _coarse_key if mode == "private_transfer" else _exact_key
    hard_cap = min(max_candidates, utils.MAX_FINDINGS_PER_RUN)
    seen: set[tuple] = set()
    out: list[dict] = []
    spent_ms = 0.0
    # 4. Greedy fill under both caps.
    for r in ranked:
        k = key(r)
        if k in seen:
            continue
        cost = _replay_ms(r)
        if out and spent_ms + cost > replay_budget_ms:
            break  # replay-time budget reached (ranked, so we keep the best that fit)
        seen.add(k)
        out.append(r)
        spent_ms += cost
        if len(out) >= hard_cap:
            break
    return out
