"""FP/FN-style analysis of the LOCAL evaluator vs the AUTHORITATIVE SDK result.

We cannot get per-candidate confirmation from one run (report.json is run-level),
so "risk" here is the gap between our local ATTEMPT signal (agent decided the
crossing, from agent-debug) and the SDK's CONFIRMED `findings_count` (post-guardrail).
A large gap = our evaluator is optimistic / the guardrail is blocking — the Phase-7+
lever. Also reports per-strategy attempt rates so ranking can favour what actually
moves the agent.

Inputs are PerCandidateRecord-like objects (or dicts) + the run's findings_count.
"""

from __future__ import annotations

from typing import Any, Iterable


def _get(rec: Any, name: str, default=None):
    return getattr(rec, name, None) if not isinstance(rec, dict) else rec.get(name, default)


def _attempted(rec: Any) -> bool:
    return bool(
        _get(rec, "deterministic_success") or _get(rec, "gpt_oss_success") or _get(rec, "gemma_success")
    )


def reconcile(records: Iterable[Any], confirmed_findings: int | None) -> dict[str, Any]:
    """Attempt-level vs confirmed reconciliation for one run."""
    recs = list(records)
    attempts = sum(1 for r in recs if _attempted(r))
    confirmed = confirmed_findings or 0
    blocked = max(0, attempts - confirmed)
    return {
        "candidates": len(recs),
        "attempts_local": attempts,
        "confirmed_findings": confirmed,
        "blocked_or_unscored": blocked,
        # optimism = fraction of local attempts NOT confirmed by the SDK.
        "evaluator_optimism": round(blocked / attempts, 3) if attempts else 0.0,
        "note": (
            "attempts with 0 confirmed → guardrail/env blocked them (attempt != scored)."
            if attempts and not confirmed else None
        ),
    }


def strategy_hit_rates(records: Iterable[Any]) -> dict[str, dict[str, Any]]:
    """Per-strategy attempt rate (which strategies actually move the agent)."""
    out: dict[str, dict[str, Any]] = {}
    for r in records:
        sid = _get(r, "strategy_id") or "?"
        d = out.setdefault(sid, {"n": 0, "attempts": 0})
        d["n"] += 1
        if _attempted(r):
            d["attempts"] += 1
    for d in out.values():
        d["attempt_rate"] = round(d["attempts"] / d["n"], 3) if d["n"] else 0.0
    return dict(sorted(out.items(), key=lambda kv: (-kv[1]["attempt_rate"], kv[0])))


def predicate_hit_rates(records: Iterable[Any]) -> dict[str, dict[str, Any]]:
    """Per-intended-predicate attempt rate."""
    out: dict[str, dict[str, Any]] = {}
    for r in records:
        p = _get(r, "intended_predicate") or "?"
        d = out.setdefault(p, {"n": 0, "attempts": 0})
        d["n"] += 1
        if _attempted(r):
            d["attempts"] += 1
    for d in out.values():
        d["attempt_rate"] = round(d["attempts"] / d["n"], 3) if d["n"] else 0.0
    return out
