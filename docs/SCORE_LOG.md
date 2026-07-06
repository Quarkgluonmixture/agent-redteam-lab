# SCORE_LOG — Kaggle submissions & score-response iteration

Running log of every Kaggle submission for `ai-agent-security-multi-step-tool-attacks`
(kernel `quarkgluonmixture/agent-redteam-lab-attack`) and the Phase-9.1 analysis it triggered.
Newest first. Scores are `normalized 0–1000` per the SDK scorer.

## Scoreboard

| Sub ref | Kernel v | Date (UTC) | gpt_oss_public | gpt_oss_private | gemma_public | gemma_private | Status | Bank N |
|---|---|---|---|---|---|---|---|---|
| 54399424 | v6 | 2026-07-06 | ⏳ | ⏳ | ⏳ | ⏳ | PENDING | 73 |

---

## Sub 54399424 — v6 (first accepted submission)

- **What shipped:** CPU serve-only notebook (placeholder `submission.csv` + `serve()`); online-probing
  `attack.py`; committed candidate bank (73 candidates). Verified submission pattern (see
  `KAGGLE_ADAPTER_SPEC` "Real submission").
- **Purpose:** prove the submission pipeline end-to-end and read the *actual* failure mode before any
  strategy change. Expectation: likely near-0 (OptimalGuardrail blocks the keyword/taint paths; see
  `THREAT_MODEL`), but the score pattern tells us which patch is smallest.

### Result  _(fill when the rerun completes)_

- confirmed findings: _TBD_
- public/private scores: _TBD_
- gpt_oss vs gemma: _TBD_

### Analysis  _(Phase 9.1 — parse → rank → attribute)_

_TBD — run `scripts/parse_artifacts.py` (if artifacts) then `scripts/rank_candidates.py`; record
per-strategy / per-predicate / per-tool attempt-vs-confirmed here._

### Decision — smallest next patch

_TBD, gated on the score pattern:_
- all scores 0 → add **E1-direct** guardrail-evasion candidates (keyword-free target, no taint, encoded payload).
- public > 0, private = 0 → add **private_transfer** variants.
- timeout / "Submission Format Error" → fix notebook/adapter (shrink N) first, no strategy change.
