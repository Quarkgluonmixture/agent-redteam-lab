"""Strategy generators: pure, deterministic producers of AttackCandidateDraft rows."""

from .base import Strategy, StrategyContext, make_draft  # noqa: F401
from .generators import STRATEGIES, generate_all  # noqa: F401
