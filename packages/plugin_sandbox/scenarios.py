"""Synthetic attack-surface scenario catalog + loader/validator.

Each scenario models one tool-use attack surface (public-safe, synthetic): a
benign task, where attacker influence enters, the target tool/sink, the predicate
it should trip, the fixtures it touches, and a public-safe example trace. The
validator checks each example trace fires EXACTLY its declared predicates via the
clean-room evaluator — so the catalog stays honest.

Scenarios carry NO weaponised attack prompts (that is Phase 5); the example trace
is illustrative tool-event analysis over synthetic fixtures.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from . import predicates, tools

_HERE = os.path.dirname(os.path.abspath(__file__))
SCENARIOS_PATH = os.path.join(_HERE, "scenarios.json")


@dataclass
class Scenario:
    scenario_id: str
    title: str
    benign_task: str
    entry_point: str                       # E1..E4 (see tools.ENTRY_POINTS)
    entry_description: str
    target_tool: str
    expected_predicates: list[str]
    tools_used: list[str]
    fixtures: list[str] = field(default_factory=list)
    explicit_send_intent: bool = False
    example_trace: list[dict[str, Any]] = field(default_factory=list)
    mitigation: str = ""
    notes: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Scenario":
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in row.items() if k in known})


def load_scenarios(path: str = SCENARIOS_PATH) -> list[Scenario]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return [Scenario.from_row(r) for r in data]


def validate_scenario(s: Scenario) -> list[str]:
    """Return errors for one scenario (empty == valid)."""
    errors: list[str] = []
    if not s.scenario_id:
        errors.append("missing scenario_id")
    if s.entry_point not in tools.ENTRY_POINTS:
        errors.append(f"entry_point {s.entry_point!r} not in {sorted(tools.ENTRY_POINTS)}")
    if s.target_tool not in tools.TOOLS:
        errors.append(f"target_tool {s.target_tool!r} not a known tool")
    for t in s.tools_used:
        if t not in tools.TOOLS:
            errors.append(f"tools_used has unknown tool {t!r}")
    for p in s.expected_predicates:
        if p not in predicates.PREDICATE_SEVERITY:
            errors.append(f"unknown predicate {p!r}")
    for i, ev in enumerate(s.example_trace):
        if ev.get("tool") not in tools.TOOLS:
            errors.append(f"example_trace[{i}] unknown tool {ev.get('tool')!r}")

    # The example trace must fire EXACTLY the declared predicates.
    fired = predicates.fired_predicates(
        s.example_trace, explicit_send_intent=s.explicit_send_intent
    )
    if fired != set(s.expected_predicates):
        errors.append(
            f"example_trace fires {sorted(fired)} but expected_predicates={sorted(s.expected_predicates)}"
        )
    return errors
