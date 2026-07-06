"""Synthetic, public-safe tool-use attack sandbox: tool surface, fixtures,
predicate evaluator, and a scenario catalog. Lab-side only (never shipped)."""

from . import guardrail, predicates, tools  # noqa: F401
from .guardrail import blocked_steps, evades, evaluate_trace  # noqa: F401
from .predicates import contains_secret, evaluate, fired_predicates  # noqa: F401
from .scenarios import Scenario, load_scenarios, validate_scenario  # noqa: F401
