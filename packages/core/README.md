# packages/core

The language-neutral **candidate schema** — the single source of truth for the lab side
(strategies, export, validation, ranking).

| File | What |
|---|---|
| `candidate.py` | `AttackCandidateDraft` dataclass + `validate(row, max_chars=…)` + verified constants |
| `schema.json` | JSON Schema (draft 2020-12) for the JSONL row — the language-neutral artifact |
| `candidate.ts` | TypeScript `type` defs mirroring the above (no TS build yet — for a future TS workspace) |

Only `userMessages` is shipped to the evaluator; every other field is internal metadata.

The Kaggle adapter (`kaggle/utils.py`) keeps a **self-contained mirror** of these invariants
because the submission ships only the four `kaggle/` files and cannot import this package at
run time. `tests/test_schema_consistency.py` pins the two equal.
