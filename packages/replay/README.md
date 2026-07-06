# packages/replay

Parse `aicomp evaluate` artifacts into normalised local JSONL (Phase 6) — the
measurement layer that turns a raw run into "what fired, what the agent did, and why".

| File | What |
|---|---|
| `records.py` | `RunRecord` (run-level) + `PerCandidateRecord` (the Phase-9.3 metric set) |
| `parse.py` | load score/report/framework/agent-debug; attribute tool calls to candidates by user-message preview; reconstruct traces and score them with the Phase-4 evaluator; diagnose failures |

`report.json` is **run-level only** (aggregate score / findings_count / cells). Per-candidate
observation is reconstructed from **`agent-debug.jsonl`**: `request_built` records carry the
user-message preview (→ candidate attribution); `decision_emitted` records carry the agent's
tool call (`{tool_name, arguments}`) → the observed trace. Observed predicates come from the
clean-room `plugin_sandbox.predicates` evaluator, so the loop is consistent with scoring.

Run it with `scripts/parse_artifacts.py <artifacts-dir>`. Success/observed-predicate fields are
filled per agent (`deterministic` / `gpt_oss` / `gemma`); UNTRUSTED_TO_ACTION uses a provenance
heuristic (agent-debug doesn't label it) and is approximate — noted in the code.
