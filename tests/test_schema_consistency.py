"""The Kaggle adapter's self-contained schema mirror must equal packages/core.

The submission ships only kaggle/, so kaggle/utils.py duplicates the shared invariants
instead of importing packages/core. This test fails if the two ever drift.
"""

from __future__ import annotations

import core.candidate as core
import utils


def test_constants_match():
    assert utils.MAX_USER_MESSAGES_PER_FINDING == core.MAX_USER_MESSAGES_PER_FINDING
    assert utils.MAX_CHARS_PER_MESSAGE == core.MAX_CHARS_PER_MESSAGE
    assert utils.LOCAL_SDK_MAX_CHARS == core.LOCAL_SDK_MAX_CHARS
    assert utils.MAX_FINDINGS_PER_RUN == core.MAX_FINDINGS_PER_RUN
    assert utils.SEVERITY_WEIGHT == core.SEVERITY_WEIGHT
    assert utils.PREDICATE_FAMILIES == core.PREDICATE_FAMILIES
    assert tuple(utils.REQUIRED_FIELDS) == tuple(core.REQUIRED_FIELDS)


def test_validate_agrees_on_samples():
    samples = [
        {"id": "a", "userMessages": ["hi"], "strategyId": "s", "intendedPredicate": "UNKNOWN"},
        {},                                                        # missing everything
        {"id": "b", "userMessages": [], "strategyId": "s", "intendedPredicate": "UNKNOWN"},
        {"id": "c", "userMessages": ["x"], "strategyId": "s", "intendedPredicate": "NOPE"},
        {"id": "d", "userMessages": ["x" * 5000], "strategyId": "s", "intendedPredicate": "UNKNOWN"},
    ]
    for row in samples:
        for mc in (core.MAX_CHARS_PER_MESSAGE, core.LOCAL_SDK_MAX_CHARS):
            core_ok = not core.validate(row, max_chars=mc)
            utils_ok = not utils.validate_candidate(row, max_chars=mc)
            assert core_ok == utils_ok, (row, mc)
