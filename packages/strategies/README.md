# packages/strategies

Pure, deterministic **candidate generators** (Phase 5). Each turns applicable
`plugin_sandbox` scenarios into `AttackCandidateDraft` rows whose `userMessages`
target the **authorised offline competition sandbox** (toy `secret.txt`,
`*.invalid` sink) — no real systems, no network, no SDK calls.

| File | What |
|---|---|
| `base.py` | `Strategy` base + `StrategyContext` (seeded RNG) + `make_draft` (schema-valid draft from a scenario) |
| `generators.py` | the 10 strategies + `STRATEGIES` registry + `generate_all(ctx)` |

Strategies (master-prompt set):
`prompt_bank_baseline`, `single_action_imperative`, `untrusted_content_to_action`,
`file_to_http_exfil`, `email_to_tool_action`, `destructive_write_minimal`,
`confused_deputy_minimal`, `branching_snapshot_search`, `crescendo_like_local`,
`goat_like_local`.

These produce **drafts** only — whether a chain actually trips a predicate is decided by
**replay against the real target (Phase 6)**, never trusted from metadata. Generate a bank
with `scripts/gen_candidates.py`; it validates every row against `packages/core` and can
feed `scripts/export_candidate_bank.py`. Generation is deterministic given `seed` so banks
are reproducible.
