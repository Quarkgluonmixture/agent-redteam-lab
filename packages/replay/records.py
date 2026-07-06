"""Normalised records produced by parsing aicomp evaluation artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class RunRecord:
    """Run-level result (from report.json + score.txt)."""

    run_id: Optional[str] = None
    track: Optional[str] = None
    agent_selection: Optional[str] = None
    env_selection: Optional[str] = None
    env_visibility: Optional[str] = None
    guardrail_id: Optional[str] = None
    guardrail_version: Optional[str] = None
    budget_s: Optional[float] = None
    scoring_mode: Optional[str] = None
    score: Optional[float] = None
    score_raw: Optional[float] = None
    findings_count: Optional[int] = None
    unique_cells: Optional[int] = None
    unique_canonical_cells: Optional[int] = None
    total_turns: int = 0
    total_tool_calls: int = 0
    observed_tool_histogram: dict[str, int] = field(default_factory=dict)
    framework_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PerCandidateRecord:
    """Per-candidate replay observation (the Phase-9.3 metric set we can compute).

    ⚠️ ``*_success`` is **ATTEMPT-LEVEL**: the intended predicate appeared in the agent's
    *decided* tool calls (from `agent-debug.jsonl`). agent-debug records decisions, not
    execution outcomes, so the guardrail/env may still block the call. The AUTHORITATIVE,
    guardrail-confirmed result is the run's ``findings_count`` (RunRecord) — reconcile the
    two (a local attempt with zero confirmed findings means the guardrail blocked it).
    Names mirror the master prompt; gpt_oss/gemma variants are filled per agent.
    """

    candidate_id: str
    strategy_id: Optional[str] = None
    intended_predicate: Optional[str] = None
    severity_weight: Optional[int] = None
    user_message_count: int = 0
    total_chars: int = 0
    expected_tools: list[str] = field(default_factory=list)
    observed_tools: list[str] = field(default_factory=list)
    observed_predicates: list[str] = field(default_factory=list)
    egress_count: int = 0
    replay_turns: int = 0
    replay_ms: float = 0.0
    deterministic_success: Optional[bool] = None
    gpt_oss_success: Optional[bool] = None
    gemma_success: Optional[bool] = None
    failure_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
