"""Kaggle attack submission entrypoint (thin adapter).

Verified contract (aicomp-sdk 3.1.2 — see docs/KAGGLE_ADAPTER_SPEC.md):
  * class ``AttackAlgorithm(AttackAlgorithmBase)``
  * ``run(self, env, config: AttackRunConfig) -> list[AttackCandidate]``
  * candidates are built with ``AttackCandidate.from_messages(user_messages)``
  * the evaluator REPLAYS the message chains; attacker metadata is never trusted.

Phase-2 scaffold: this loads harmless placeholder candidates from
``candidate_bank.jsonl`` and returns them through the portfolio selector. It
contains NO real attack logic yet (Phase 5). It imports only the SDK + two
sibling files, so it works both from ``kaggle/`` and when packaged to a
submission root (see scripts/package_kaggle_submission.sh).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Mapping

# Make sibling modules importable whether we run from kaggle/ or a packaged root.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from aicomp_sdk.attacks import AttackAlgorithmBase, AttackCandidate, AttackRunConfig  # noqa: E402,F401

import portfolio_selector  # noqa: E402
import utils  # noqa: E402

_BANK_PATH = os.path.join(_HERE, "candidate_bank.jsonl")


class AttackAlgorithm(AttackAlgorithmBase):
    """Bank-backed attack submission (scaffold)."""

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        # ARL_MODE selects the portfolio mode without editing code (public_lb default).
        self.mode = (self.config.get("mode") or os.environ.get("ARL_MODE") or "public_lb")

    def run(self, env: Any, config: AttackRunConfig | None = None) -> list[AttackCandidate]:
        # `config` is optional: the installed base class declares run(self, env, config),
        # but the competition prose shows run(env). Defaulting to None accepts both shapes.
        # The real per-model attack-generation budget (9000 s) arrives on `config`; the
        # host FAQ names it `budget_s`, the SDK dataclass uses `time_budget_s` — accept both.
        budget = utils.budget_of(config)
        rows = utils.load_candidate_bank(_BANK_PATH)
        # NOTE: cap ships FAR below the 2000 hard limit — replay time (~6x local, and it
        # scales with candidate count) is the real constraint; oversized portfolios time
        # out the replay phase and score nothing. See docs/EVAL_PROTOCOL.md.
        selected = portfolio_selector.select(
            rows,
            mode=self.mode,
            budget_s=budget,
            max_candidates=utils.DEFAULT_MAX_SHIPPED_CANDIDATES,
        )
        return utils.to_attack_candidates(selected)
