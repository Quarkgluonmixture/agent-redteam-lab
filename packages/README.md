# packages/ — the lab "brain"

Reusable architecture (Layers A/B in `docs/ARCHITECTURE.md`). **Stubs only** in Phase 2;
each subpackage documents its intended responsibility. Code is ported/recreated in
Phase 3+ per `docs/MIGRATION_AUDIT.md` — never blind-copied from upstream, always through
the redaction + public-safety gate.

| Package | Responsibility |
|---|---|
| `core` | shared candidate schema + verified-contract constants **(Phase 3 ✓)** |
| `plugin_sandbox` | synthetic tools + predicate evaluator + scenario catalog over the 10-tool surface **(Phase 4 ✓)** |
| `strategies` | candidate generators (the strategy families in THREAT_MODEL.md) **(Phase 5 ✓)** |
| `grader` | synthetic LLM-rubric calibration (no private examples) |
| `risk` | score+cost model + FP/FN reconciliation **(Phase 7 ✓)** |
| `replay` | parse artifacts → run + per-candidate JSONL (attempt vs confirmed) **(Phase 6 ✓)** |
| `portfolio` | ranker/selector + replay feedback (mirrors `kaggle/portfolio_selector.py`) **(Phase 7 ✓)** |
| `sync` | upstream sync map + redaction transform |
