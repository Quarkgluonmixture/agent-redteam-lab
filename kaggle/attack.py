"""Kaggle attack submission entrypoint (online-probing adapter).

Verified mechanic (official getting-started notebook + aicomp-sdk 3.1.2): the hosted
`JEDAttackInferenceServer` loads this `attack.py` and calls `AttackAlgorithm.run(env,
config)`. The scoring-worthy pattern is to PROBE the env online — replay each seed
message-chain (`env.reset()` → `env.interact(msg)` …), check `eval_predicates(
env.export_trace_dict())`, and return only chains that actually fired (so the
evaluator's re-replay confirms them). Seeds + ordering come from our candidate bank +
portfolio selector; the env's own guardrail is applied during `interact`, so a firing
chain has already evaded it.

Falls back to returning the (unprobed) selected bank when `env` can't be probed
(e.g. local `aicomp validate` / unit tests with a stub env).
"""

from __future__ import annotations

import glob
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping

# Competition data (kaggle_evaluation/ + aicomp_sdk/) → import path (Kaggle scoring context).
for _cand in glob.glob("/kaggle/input/**/kaggle_evaluation", recursive=True):
    _root = str(Path(_cand).parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    break

# Sibling modules resolve whether we run from kaggle/ or /kaggle/working.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from aicomp_sdk.attacks import AttackAlgorithmBase, AttackCandidate, AttackRunConfig  # noqa: E402,F401

import portfolio_selector  # noqa: E402
import utils  # noqa: E402

_BANK_PATH = os.path.join(_HERE, "candidate_bank.jsonl")
_PROBE_MARGIN_S = 180.0  # stop probing this long before the deadline (leave replay buffer)


def _eval_predicates():
    """Lazy import — present in the competition env, optional locally."""
    try:
        from aicomp_sdk.core.predicates import eval_predicates
        return eval_predicates
    except Exception:
        return None


class AttackAlgorithm(AttackAlgorithmBase):
    """Online-probing attack seeded by the candidate bank."""

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        super().__init__(config)
        self.mode = (self.config.get("mode") or os.environ.get("ARL_MODE") or "public_lb")

    def _seed_chains(self, budget: float) -> list[list[str]]:
        rows = utils.load_candidate_bank(_BANK_PATH)
        selected = portfolio_selector.select(
            rows, mode=self.mode, budget_s=budget,
            max_candidates=utils.DEFAULT_MAX_SHIPPED_CANDIDATES,
        )
        return [
            [str(m)[: utils.MAX_CHARS_PER_MESSAGE] for m in r.get("userMessages", [])][
                : utils.MAX_USER_MESSAGES_PER_FINDING
            ]
            for r in selected
        ]

    def run(self, env: Any, config: AttackRunConfig | None = None) -> list[AttackCandidate]:
        budget = utils.budget_of(config)
        seeds = self._seed_chains(budget)
        eval_predicates = _eval_predicates()
        probe = (
            eval_predicates is not None
            and hasattr(env, "interact")
            and hasattr(env, "reset")
            and hasattr(env, "export_trace_dict")
        )
        if not probe:
            # Local / no-env context: return the selected bank unprobed.
            return utils.to_attack_candidates([{"userMessages": c} for c in seeds])

        # Online probing: keep only chains that actually fire a predicate.
        start = time.monotonic()
        margin = min(_PROBE_MARGIN_S, max(5.0, budget * 0.1))  # scale buffer to budget
        findings: list[AttackCandidate] = []
        for chain in seeds:
            if not chain:
                continue
            if budget - (time.monotonic() - start) < margin:
                break
            try:
                env.reset()
                for msg in chain:
                    env.interact(msg)
                if eval_predicates(env.export_trace_dict()):
                    findings.append(AttackCandidate.from_messages(chain))
            except Exception:
                continue  # a bad chain must never abort the whole run
            if len(findings) >= utils.MAX_FINDINGS_PER_RUN:
                break
        return findings
