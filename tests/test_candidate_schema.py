"""Core candidate-schema validation (packages/core)."""

from __future__ import annotations

from core.candidate import (
    AttackCandidateDraft,
    LOCAL_SDK_MAX_CHARS,
    MAX_CHARS_PER_MESSAGE,
    MAX_USER_MESSAGES_PER_FINDING,
    validate,
)


def _valid_row(**over):
    row = {
        "id": "c1",
        "userMessages": ["hello"],
        "strategyId": "placeholder_noop",
        "intendedPredicate": "UNKNOWN",
    }
    row.update(over)
    return row


def test_valid_row_passes():
    assert validate(_valid_row()) == []


def test_missing_required_fields_fail_closed():
    assert validate({}) != []
    for missing in ("id", "userMessages", "strategyId", "intendedPredicate"):
        row = _valid_row()
        del row[missing]
        assert validate(row) != [], f"missing {missing} should fail"


def test_non_dict_fails():
    assert validate("nope") != []
    assert validate(["a"]) != []


def test_message_count_limit_enforced():
    assert validate(_valid_row(userMessages=["x"] * MAX_USER_MESSAGES_PER_FINDING)) == []
    assert validate(_valid_row(userMessages=["x"] * (MAX_USER_MESSAGES_PER_FINDING + 1))) != []
    assert validate(_valid_row(userMessages=[])) != []


def test_message_length_caveat_2000_vs_10000():
    row_3k = _valid_row(userMessages=["a" * 3000])
    # default competition cap (10,000) allows a 3,000-char message
    assert validate(row_3k) == []
    assert validate(row_3k, max_chars=MAX_CHARS_PER_MESSAGE) == []
    # local wheel cap (2,000) rejects it
    assert validate(row_3k, max_chars=LOCAL_SDK_MAX_CHARS) != []
    # exactly at the competition cap is fine; one over fails
    assert validate(_valid_row(userMessages=["a" * MAX_CHARS_PER_MESSAGE])) == []
    assert validate(_valid_row(userMessages=["a" * (MAX_CHARS_PER_MESSAGE + 1)])) != []


def test_bad_predicate_fails():
    assert validate(_valid_row(intendedPredicate="NOPE")) != []


def test_dataclass_roundtrip_drops_none_optionals():
    d = AttackCandidateDraft(id="c1", userMessages=["hi"], strategyId="s", intendedPredicate="EXFILTRATION")
    row = d.to_row()
    assert "notes" not in row and "templateId" not in row  # None optionals dropped
    assert validate(row) == []
    assert AttackCandidateDraft.from_row(row).id == "c1"
