"""Strategy interface + shared context for candidate generation.

A Strategy is a PURE candidate producer: given a StrategyContext (the synthetic
scenario catalog + knobs), it yields ``AttackCandidateDraft`` rows. It does not
call the competition SDK or the network; generation is deterministic given
``seed`` so banks are reproducible.

All generated content targets the AUTHORISED offline competition sandbox
semantics only (toy ``secret.txt``, ``*.invalid`` sink) — no real systems.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterable

from core.candidate import (
    AttackCandidateDraft,
    MAX_CHARS_PER_MESSAGE,
    MAX_USER_MESSAGES_PER_FINDING,
    PREDICATE_FAMILIES,
    SEVERITY_WEIGHT,
)


@dataclass
class StrategyContext:
    """Inputs + knobs for generation."""

    scenarios: list = field(default_factory=list)   # list[plugin_sandbox.Scenario]
    n_per_scenario: int = 1                          # wording variants per scenario
    seed: int = 123
    sink_url: str = "https://sink.invalid/collect"
    secret_path: str = "secret.txt"

    def rng(self, salt: int) -> random.Random:
        """Deterministic per-item RNG (no global state, reproducible)."""
        return random.Random(self.seed * 1_000_003 + salt)


class Strategy:
    """Base strategy. Subclasses set ``id`` and implement ``generate``."""

    id: str = "base"
    #: predicates / entry points this strategy is applicable to (None = any)
    predicates: tuple[str, ...] | None = None
    entries: tuple[str, ...] | None = None

    def applicable(self, scenario) -> bool:
        if not scenario.expected_predicates:
            return False  # skip the false-positive control scenarios
        if self.entries is not None and scenario.entry_point not in self.entries:
            return False
        if self.predicates is not None and not (
            set(scenario.expected_predicates) & set(self.predicates)
        ):
            return False
        return True

    def generate(self, ctx: StrategyContext) -> Iterable[AttackCandidateDraft]:
        raise NotImplementedError


def _clip(messages: list[str]) -> list[str]:
    """Enforce the hard limits so every draft is replayable-by-construction."""
    out = [m[:MAX_CHARS_PER_MESSAGE] for m in messages if m]
    return out[:MAX_USER_MESSAGES_PER_FINDING]


def make_draft(
    *,
    strategy_id: str,
    scenario,
    idx: int,
    user_messages: list[str],
    notes: str = "",
) -> AttackCandidateDraft:
    """Build a schema-valid draft, pulling intent/sink from the scenario."""
    predicate = (scenario.expected_predicates or ["UNKNOWN"])[0]
    sev = PREDICATE_FAMILIES.get(predicate, 1)
    return AttackCandidateDraft(
        id=f"{strategy_id}:{scenario.scenario_id}:{idx}",
        userMessages=_clip(user_messages),
        strategyId=strategy_id,
        intendedPredicate=predicate,
        templateId=strategy_id,
        expectedTools=list(scenario.tools_used),
        expectedSink=scenario.target_tool,
        syntheticScenarioId=scenario.scenario_id,
        severityWeight=SEVERITY_WEIGHT.get(sev, 1),
        notes=notes or scenario.title,
    )
