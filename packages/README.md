# packages/ — the lab "brain"

Reusable architecture (Layers A/B in `docs/ARCHITECTURE.md`). **Stubs only** in Phase 2;
each subpackage documents its intended responsibility. Code is ported/recreated in
Phase 3+ per `docs/MIGRATION_AUDIT.md` — never blind-copied from upstream, always through
the redaction + public-safety gate.

| Package | Responsibility |
|---|---|
| `core` | shared candidate schema + verified-contract constants **(Phase 3 ✓)** |
| `plugin_sandbox` | synthetic tools + predicate evaluator + scenario catalog over the 10-tool surface **(Phase 4 ✓)** |
| `strategies` | candidate generators (the strategy families in THREAT_MODEL.md) |
| `grader` | synthetic LLM-rubric calibration (no private examples) |
| `risk` | FP/FN risk map + cost model |
| `replay` | parse `report.json`/transcripts into local JSONL |
| `portfolio` | candidate ranker/selector (mirrors `kaggle/portfolio_selector.py`) |
| `sync` | upstream sync map + redaction transform |
