"""Validate the shipped candidate bank against the candidate schema."""

from __future__ import annotations

import os
import sys

KAGGLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kaggle")
sys.path.insert(0, KAGGLE_DIR)

import utils  # noqa: E402

BANK_PATH = os.path.join(KAGGLE_DIR, "candidate_bank.jsonl")


def test_bank_loads():
    rows = utils.load_candidate_bank(BANK_PATH)
    assert isinstance(rows, list)
    assert len(rows) >= 1


def test_every_row_is_valid():
    rows = utils.load_candidate_bank(BANK_PATH)
    for i, row in enumerate(rows):
        errors = utils.validate_candidate(row)
        assert not errors, f"row {i} ({row.get('id')!r}) invalid: {errors}"


def test_ids_are_unique():
    rows = utils.load_candidate_bank(BANK_PATH)
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate candidate ids in bank"


def test_validate_candidate_catches_bad_rows():
    assert utils.validate_candidate({}) != []
    assert utils.validate_candidate(
        {"id": "x", "userMessages": [], "strategyId": "s", "intendedPredicate": "UNKNOWN"}
    ) != []
    too_long = "a" * (utils.MAX_CHARS_PER_MESSAGE + 1)
    assert utils.validate_candidate(
        {"id": "x", "userMessages": [too_long], "strategyId": "s", "intendedPredicate": "UNKNOWN"}
    ) != []
    assert utils.validate_candidate(
        {"id": "x", "userMessages": ["ok"], "strategyId": "s", "intendedPredicate": "NOPE"}
    ) != []
