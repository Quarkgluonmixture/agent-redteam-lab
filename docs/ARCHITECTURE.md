# ARCHITECTURE

Three layers, cleanly separated so the Kaggle submission stays tiny and the lab
stays useful on its own.

```
Layer A — Control Plane / Research Lab   (Phase 3+; the "brain")
  catalog · config · report/aggregate · grader calibration · risk (FP/FN) · cost · dashboards
        │  produces / ranks
        ▼
Layer B — Candidate Factory              (Phase 4–7)
  synthetic tool sandbox · strategy generators · replay ingestion · candidate schema · risk/cost scoring
        │  exports language-neutral JSONL
        ▼
Layer C — Kaggle Adapter                 (Phase 2 — this scaffold)
  kaggle/attack.py — returns replayable AttackCandidate message chains under budget
```

**Rule:** Layer A never enters the Kaggle submission. `kaggle/attack.py` depends only
on `aicomp-sdk` + the stdlib + its own siblings — no web app, no DB, no secrets, no
internet beyond what the SDK env provides.

## The JSONL bridge

The reusable "brain" ported from upstream is JS/`.mjs`; the Kaggle adapter is Python.
The contract between them is a **language-neutral JSONL candidate bank**. Only
`userMessages` is consumed by the evaluator; everything else
(`strategyId`, `intendedPredicate`, `expectedTools`, risk/cost estimates, per-model
success flags) is **internal metadata** for local selection and is never trusted for
scoring (the evaluator replays and recomputes — see `EVAL_PROTOCOL.md`).

Candidate row (subset enforced in `kaggle/utils.py`; full shape here):

```jsonc
{
  "id": "…",
  "userMessages": ["…"],            // REQUIRED, 1..32, each <= 2000 chars — the ONLY shipped field
  "strategyId": "…",                 // REQUIRED (internal)
  "intendedPredicate": "EXFILTRATION|UNTRUSTED_TO_ACTION|DESTRUCTIVE_WRITE|CONFUSED_DEPUTY|UNKNOWN",
  "expectedTools": ["http.post"],    // internal
  "expectedSink": "http.post",       // internal (EXFILTRATION is http.post-only)
  "publicCellKey": "…",              // internal (public LB unique-cell estimate)
  "coarseCellKey": "…",              // internal (private-transfer dedup)
  "deterministicSuccess": true,      // internal cross-model flags (deterministic/gpt_oss/gemma)
  "severityWeight": 16, "scorePerSecond": 0.0,
  "graderRisk": 0.0, "fpRisk": 0.0, "fnRisk": 0.0,
  "notes": "…", "createdAt": "2026-07-06"
}
```

## Directory map

| Path | Layer | Status |
|---|---|---|
| `kaggle/` | C | scaffold (placeholder bank) |
| `packages/core` | A/B | schema/constants home (stub) |
| `packages/plugin-sandbox` | B | synthetic tools + scenarios (stub) |
| `packages/strategies` | B | candidate generators (stub) |
| `packages/grader` | A | synthetic judge calibration (stub) |
| `packages/risk` | A | FP/FN + cost model (stub) |
| `packages/replay` | B | artifact parsing / ingestion (stub) |
| `packages/portfolio` | A | ranker/selector (stub; mirrors `kaggle/portfolio_selector.py`) |
| `packages/sync` | A | upstream sync map + redaction (stub) |
| `scripts/` | — | smoke/eval/package + public-safety scan |
| `tests/` | — | contract, bank-schema, safety-scan |

Nothing from the private upstream repo is migrated yet (Phase 3). What migrates, what
is recreated synthetically, and what stays private is triaged in `MIGRATION_AUDIT.md`.
