"""Strategy generators: schema-valid, deterministic, covered, sandbox-scoped."""

from __future__ import annotations

import re

from core.candidate import MAX_CHARS_PER_MESSAGE, MAX_USER_MESSAGES_PER_FINDING, validate
from plugin_sandbox.scenarios import load_scenarios
from strategies import StrategyContext, generate_all
from strategies.generators import STRATEGIES

SCENARIOS = load_scenarios()


def _ctx(seed=123, n=1):
    return StrategyContext(scenarios=SCENARIOS, n_per_scenario=n, seed=seed)


def test_generates_candidates():
    assert len(generate_all(_ctx())) > 0


def test_all_drafts_are_schema_valid():
    for d in generate_all(_ctx()):
        assert validate(d.to_row()) == [], f"{d.id}: {validate(d.to_row())}"


def test_every_strategy_produces_output():
    produced = {d.strategyId for d in generate_all(_ctx())}
    assert produced == set(STRATEGIES), f"silent strategies: {set(STRATEGIES) - produced}"


def test_deterministic():
    a = [(d.id, tuple(d.userMessages)) for d in generate_all(_ctx(seed=7))]
    b = [(d.id, tuple(d.userMessages)) for d in generate_all(_ctx(seed=7))]
    assert a == b


def test_limits_respected():
    for d in generate_all(_ctx(n=3)):
        assert 1 <= len(d.userMessages) <= MAX_USER_MESSAGES_PER_FINDING
        assert all(len(m) <= MAX_CHARS_PER_MESSAGE for m in d.userMessages)


def test_intent_and_scenario_linkage():
    by_id = {s.scenario_id: s for s in SCENARIOS}
    for d in generate_all(_ctx()):
        assert d.syntheticScenarioId in by_id
        scenario = by_id[d.syntheticScenarioId]
        assert d.intendedPredicate in scenario.expected_predicates


def test_predicate_coverage():
    covered = {d.intendedPredicate for d in generate_all(_ctx())}
    assert {"EXFILTRATION", "UNTRUSTED_TO_ACTION", "DESTRUCTIVE_WRITE", "CONFUSED_DEPUTY"} <= covered


def test_only_sandbox_hosts():
    for d in generate_all(_ctx()):
        for m in d.userMessages:
            for host in re.findall(r"https?://([^/\s]+)", m):
                assert host.endswith(".invalid"), f"{d.id}: non-sandbox host {host!r}"


def test_controls_are_skipped():
    """False-positive control scenarios (no expected predicate) must not be targeted."""
    controls = {s.scenario_id for s in SCENARIOS if not s.expected_predicates}
    targeted = {d.syntheticScenarioId for d in generate_all(_ctx())}
    assert not (controls & targeted)
