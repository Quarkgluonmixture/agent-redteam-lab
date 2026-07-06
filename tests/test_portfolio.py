"""Lab-side portfolio: enrich from replay, rank, dedup/caps by mode."""

from __future__ import annotations

import portfolio


def _row(i, pred="EXFILTRATION", sink="http.post", tools=("http.post",), msgs=None):
    return {
        "id": f"c{i}",
        "userMessages": msgs if msgs is not None else [f"msg {i}"],
        "strategyId": "s",
        "intendedPredicate": pred,
        "expectedSink": sink,
        "expectedTools": list(tools),
    }


def test_enrich_from_replay_folds_observations():
    bank = [_row(1), _row(2)]
    records = [
        {"candidate_id": "c1", "deterministic_success": True, "replay_ms": 50, "failure_reason": None},
        {"candidate_id": "c2", "deterministic_success": False, "replay_ms": 0,
         "failure_reason": "target tool never invoked"},
    ]
    out = {r["id"]: r for r in portfolio.enrich_from_replay(bank, records)}
    assert out["c1"]["deterministicSuccess"] is True
    assert out["c1"]["estimatedReplayMs"] == 50
    assert out["c2"]["deterministicSuccess"] is False
    assert out["c2"]["notes"] == "target tool never invoked"
    # original bank untouched (copy semantics)
    assert "deterministicSuccess" not in bank[0]


def test_rank_orders_by_value():
    lo = _row(1, pred="CONFUSED_DEPUTY", sink="email.send", tools=("email.send",))
    hi = _row(2, pred="EXFILTRATION")
    ranked = portfolio.rank([lo, hi])
    assert ranked[0]["id"] == "c2"


def test_rank_drops_invalid():
    ranked = portfolio.rank([_row(1), {"id": "bad", "userMessages": []}])
    assert [r["id"] for r in ranked] == ["c1"]


def test_select_caps_and_dedup_modes():
    rows = [_row(i) for i in range(20)]
    assert len(portfolio.select(rows, max_candidates=5, replay_budget_ms=10**15)) == 5

    a = _row(1, msgs=["do X"])
    b = _row(2, msgs=["kindly do X"])   # same coarse key, different wording
    assert len(portfolio.select([a, b], mode="public_lb", replay_budget_ms=10**15)) == 2
    assert len(portfolio.select([a, b], mode="private_transfer", replay_budget_ms=10**15)) == 1


def test_select_replay_budget_binds():
    rows = [_row(i) for i in range(10)]  # 72_000 ms default each
    out = portfolio.select(rows, max_candidates=1000, replay_budget_ms=200_000)
    assert len(out) == 2  # 2*72_000=144_000 fits; a 3rd (216_000) would exceed 200_000


def test_unknown_mode_raises():
    try:
        portfolio.select([_row(1)], mode="bogus")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
