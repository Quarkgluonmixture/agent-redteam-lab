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

The schema is defined once, three ways (Phase 3): **`packages/core/candidate.py`**
(`AttackCandidateDraft` dataclass + `validate(row, max_chars=…)`), `packages/core/schema.json`
(JSON Schema — the language-neutral artifact), and `packages/core/candidate.ts` (TS types for a
future TS workspace). Because the Kaggle submission ships only the four `kaggle/` files, `kaggle/utils.py`
keeps a **self-contained mirror** of the invariants, pinned equal to core by
`tests/test_schema_consistency.py`. Tooling: `scripts/validate_candidate_bank.py` (fail-closed) and
`scripts/export_candidate_bank.py` (merge strategy outputs → validated bank).

Candidate row (validated by `packages/core.validate` / mirrored `kaggle/utils.validate_candidate`):

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
| `packages/core` | A/B | **candidate schema (Phase 3): `candidate.py` + `schema.json` + `candidate.ts`** |
| `packages/plugin_sandbox` | B | **synthetic tools + predicate evaluator + 14-scenario catalog (Phase 4)** |
| `packages/strategies` | B | **10 candidate generators + `scripts/gen_candidates.py` (Phase 5)** |
| `packages/grader` | A | synthetic judge calibration (stub) |
| `packages/risk` | A | **score+cost model + FP/FN reconciliation (Phase 7)** |
| `packages/replay` | B | **artifact parser → run + per-candidate JSONL + `scripts/parse_artifacts.py` (Phase 6)** |
| `packages/portfolio` | A | **ranker/selector + replay feedback + `scripts/rank_candidates.py` (Phase 7)** |
| `packages/sync` | A | upstream sync map + redaction (stub) |
| `scripts/` | — | smoke/eval/package + public-safety scan |
| `tests/` | — | contract, bank-schema, safety-scan |

Nothing from the private upstream repo is migrated yet (Phase 3). What migrates, what
is recreated synthetically, and what stays private is triaged in `MIGRATION_AUDIT.md`.
