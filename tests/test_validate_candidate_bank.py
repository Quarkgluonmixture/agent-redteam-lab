"""scripts/validate_candidate_bank.py: fail-closed on invalid/duplicate JSONL."""

from __future__ import annotations

import json

import validate_candidate_bank as vcb

VALID = {"id": "a", "userMessages": ["hi"], "strategyId": "s", "intendedPredicate": "EXFILTRATION"}
INVALID = {"id": "b", "userMessages": [], "strategyId": "s", "intendedPredicate": "EXFILTRATION"}


def _write(tmp_path, rows):
    p = tmp_path / "bank.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return str(p)


def test_valid_jsonl_passes(tmp_path):
    path = _write(tmp_path, [VALID, {**VALID, "id": "a2"}])
    assert vcb.main([path]) == 0


def test_invalid_jsonl_fails_closed(tmp_path):
    path = _write(tmp_path, [VALID, INVALID])
    assert vcb.main([path]) == 1


def test_duplicate_ids_fail(tmp_path):
    path = _write(tmp_path, [VALID, {**VALID, "userMessages": ["yo"]}])  # same id "a"
    assert vcb.main([path]) == 1


def test_local_cap_flag_enforces_2000(tmp_path):
    big = {**VALID, "id": "big", "userMessages": ["a" * 3000]}
    path = _write(tmp_path, [big])
    assert vcb.main([path]) == 0            # ok under competition 10,000 cap
    assert vcb.main([path, "--local"]) == 1  # fails under local 2,000 cap


def test_missing_bank_fails(tmp_path):
    assert vcb.main([str(tmp_path / "nope.jsonl")]) == 1
