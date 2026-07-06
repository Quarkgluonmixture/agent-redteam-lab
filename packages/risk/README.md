# packages/risk

Score + cost model and FP/FN reconciliation (Phase 7). See `docs/RISK_MODEL.md`.

| File | What |
|---|---|
| `cost.py` | raw/normalized scoring, replay-time cost, `candidate_value` (master-prompt §9.4) |
| `fpfn.py` | local ATTEMPT vs authoritative CONFIRMED reconciliation + per-strategy/predicate hit rates |

Lab-side canonical; `kaggle/utils` + `kaggle/portfolio_selector` keep self-contained mirrors of
the shipping subset. FP/FN here = the gap between our local attempt signal (agent decisions, from
`packages/replay`) and the SDK's `findings_count` (post-guardrail) — the Phase-9 lever.
