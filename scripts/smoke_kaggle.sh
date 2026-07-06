#!/usr/bin/env bash
# Validate the Kaggle adapter contract (fast, no eval).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
AICOMP="${AICOMP:-aicomp}"

echo "[smoke] aicomp validate redteam attack.py"
"$AICOMP" validate redteam attack.py
echo "[smoke] OK"
