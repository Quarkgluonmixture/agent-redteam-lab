# packages/portfolio

Lab-side candidate ranker/selector (Phase 7) — the richer, research-facing sibling of the
self-contained shipping `kaggle/portfolio_selector`. See `docs/RISK_MODEL.md`.

| Function (`select.py`) | What |
|---|---|
| `enrich_from_replay(bank, records)` | fold `packages/replay` per-candidate observations into the bank (success flags, replay ms, failure notes) |
| `rank(bank)` | validate + sort by `risk.candidate_value` |
| `select(bank, mode, max_candidates, replay_budget_ms)` | rank → dedup (coarse for `private_transfer`, exact else) → cap by count + replay-time |

Composes `packages/risk` for scoring/value. Modes: `public_lb` / `private_transfer` / `research`.
Used by `scripts/rank_candidates.py` (the feedback loop).
