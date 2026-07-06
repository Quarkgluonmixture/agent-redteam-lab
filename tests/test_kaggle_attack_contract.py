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


def test_bank_is_harmless_placeholder_only():
    """Phase-2 guard: shipped candidates must not attempt real boundary crossings."""
    mod = _load_root_attack()
    candidates = mod.AttackAlgorithm().run(object(), AttackRunConfig(time_budget_s=5.0))
    joined = " ".join(m.lower() for c in candidates for m in c.user_messages)
    for banned in ("secret.txt", "http.post", "fs.delete", "exfiltrat"):
        assert banned not in joined, f"placeholder bank unexpectedly contains {banned!r}"
