"""Portfolio selector: caps (count + replay-time), modes, ranking."""

from __future__ import annotations

import portfolio_selector as ps
import utils


def _row(i, pred="EXFILTRATION", sink="http.post", tools=("http.post",), msgs=None, **over):
    r = {
        "id": f"c{i}",
        "userMessages": msgs if msgs is not None else [f"msg {i}"],
        "strategyId": "s",
        "intendedPredicate": pred,
        "expectedSink": sink,
        "expectedTools": list(tools),
    }
    r.update(over)
    return r


def test_drops_invalid_rows():
    rows = [_row(1), {"id": "bad", "userMessages": []}]  # 2nd is invalid
    out = ps.select(rows)
    assert [r["id"] for r in out] == ["c1"]


def test_respects_max_candidates():
    rows = [_row(i) for i in range(50)]
    out = ps.select(rows, max_candidates=5, replay_budget_ms=10**12)
    assert len(out) == 5


def test_respects_replay_time_budget():
    # 10 distinct candidates, 1000 ms each; budget 3500 ms -> at most 3 fit.
    rows = [_row(i, estimatedReplayMs=1000) for i in range(10)]
    out = ps.select(rows, max_candidates=1000, replay_budget_ms=3500)
    assert len(out) == 3


def test_never_exceeds_hard_cap():
    rows = [_row(i, estimatedReplayMs=1) for i in range(utils.MAX_FINDINGS_PER_RUN + 500)]
    out = ps.select(rows, max_candidates=10**9, replay_budget_ms=10**18)
    assert len(out) <= utils.MAX_FINDINGS_PER_RUN


def test_mode_dedup_public_vs_private():
    # Same coarse key (predicate/sink/tools), different wording.
    a = _row(1, msgs=["do X please"])
    b = _row(2, msgs=["kindly do X"])
    assert len(ps.select([a, b], mode="public_lb", replay_budget_ms=10**12)) == 2   # exact dedup keeps both
    assert len(ps.select([a, b], mode="private_transfer", replay_budget_ms=10**12)) == 1  # coarse collapses


def test_unknown_mode_raises():
    try:
        ps.select([_row(1)], mode="bogus")
    except ValueError:
        return
    raise AssertionError("unknown mode should raise ValueError")


def test_ranking_prefers_higher_severity():
    low = _row(1, pred="CONFUSED_DEPUTY", sink=None, tools=("email.send",))   # sev 3
    high = _row(2, pred="EXFILTRATION")                                        # sev 5
    out = ps.select([low, high], max_candidates=1, replay_budget_ms=10**12)
    assert out[0]["id"] == "c2"
