"""Verify the Kaggle adapter honours the aicomp-sdk contract."""

from __future__ import annotations

import importlib.util
import os

import pytest

aicomp_attacks = pytest.importorskip("aicomp_sdk.attacks")  # skip if SDK not installed
AttackAlgorithmBase = aicomp_attacks.AttackAlgorithmBase
AttackCandidate = aicomp_attacks.AttackCandidate
AttackRunConfig = aicomp_attacks.AttackRunConfig

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MAX_MESSAGES = 32
MAX_CHARS = 10_000   # competition "Max Message Length"
MAX_FINDINGS = 2_000


def _load_root_attack():
    spec = importlib.util.spec_from_file_location(
        "root_attack", os.path.join(REPO_ROOT, "attack.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_root_attack_exposes_algorithm():
    mod = _load_root_attack()
    assert hasattr(mod, "AttackAlgorithm")
    assert issubclass(mod.AttackAlgorithm, AttackAlgorithmBase)


def test_run_returns_replayable_candidates_within_limits():
    mod = _load_root_attack()
    algo = mod.AttackAlgorithm()
    # The scaffold ignores `env`, so a bare object is a sufficient stub.
    candidates = algo.run(object(), AttackRunConfig(time_budget_s=5.0))

    assert isinstance(candidates, list)
    assert len(candidates) <= MAX_FINDINGS
    for c in candidates:
        assert isinstance(c, AttackCandidate)
        msgs = c.user_messages
        assert isinstance(msgs, tuple)
        assert 1 <= len(msgs) <= MAX_MESSAGES
        for m in msgs:
            assert isinstance(m, str)
            assert len(m) <= MAX_CHARS


def test_run_accepts_env_only_call():
    """Competition prose shows run(env); ensure the optional-config override works."""
    mod = _load_root_attack()
    candidates = mod.AttackAlgorithm().run(object())
    assert isinstance(candidates, list)


def test_shipped_candidates_are_sandbox_scoped():
    """Phase-5: real attacks now, but every shipped candidate must stay inside the
    authorised toy sandbox — no HTTP host outside *.invalid may appear."""
    import re

    mod = _load_root_attack()
    candidates = mod.AttackAlgorithm().run(object(), AttackRunConfig(time_budget_s=5.0))
    assert candidates, "expected a non-empty candidate bank"
    for c in candidates:
        for m in c.user_messages:
            for host in re.findall(r"https?://([^/\s]+)", m):
                assert host.endswith(".invalid"), f"non-sandbox host {host!r} in a shipped candidate"
