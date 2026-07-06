#!/usr/bin/env bash
# 60s local smoke evaluation against the deterministic target in the Kaggle-parity env.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
AICOMP="${AICOMP:-aicomp}"
AGENT="${AGENT:-deterministic}"
OUT="${OUT:-artifacts/eval_60s}"
mkdir -p "$OUT"

echo "[eval] aicomp evaluate redteam attack.py --budget-s 60 --agent $AGENT --env gym"
"$AICOMP" evaluate redteam attack.py \
  --budget-s 60 --agent "$AGENT" --env gym \
  --save-transcript --save-framework-events --save-agent-debug \
  --artifacts-dir "$OUT"

echo "[eval] artifacts in $OUT:"
ls -1 "$OUT"
if [ -f "$OUT/score.txt" ]; then echo -n "[eval] attack score: "; cat "$OUT/score.txt"; fi
