# kaggle/ — the thin Kaggle adapter

Self-contained submission layer. Depends only on `aicomp-sdk` + the stdlib + its
own siblings, so it works both here and when copied to a submission root.

| File | Role |
|---|---|
| `attack.py` | `AttackAlgorithm(AttackAlgorithmBase).run(env, config) -> list[AttackCandidate]` — loads the bank, selects, returns replayable chains |
| `portfolio_selector.py` | dedup + limits + mode selection (`public_lb` / `private_transfer` / `research`) |
| `utils.py` | verified contract constants (single source of truth) + candidate schema + `to_attack_candidates` |
| `candidate_bank.jsonl` | replayable candidates (Phase-2: harmless placeholders) |

Do **not** put lab internals (grader, risk maps, private plugins, company
identifiers) in this directory — it ships to a public leaderboard. Only
`userMessages` is consumed by the evaluator; everything else is internal metadata.

Package for upload with `scripts/package_kaggle_submission.sh` (writes
`dist/kaggle_submission/` with `attack.py` at its root).
