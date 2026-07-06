#!/usr/bin/env bash
# Build a minimal Kaggle upload folder: attack.py at the root + its siblings.
# Excludes docs, tests, web app, db config, private material, caches, .env, venv.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DIST="${DIST:-dist/kaggle_submission}"

rm -rf "$DIST"
mkdir -p "$DIST"

# The adapter resolves siblings relative to its own dir, so it runs unchanged
# with attack.py at the submission root.
cp kaggle/attack.py             "$DIST/attack.py"
cp kaggle/portfolio_selector.py "$DIST/portfolio_selector.py"
cp kaggle/utils.py              "$DIST/utils.py"
cp kaggle/candidate_bank.jsonl  "$DIST/candidate_bank.jsonl"

echo "[package] contents of $DIST:"
ls -1 "$DIST"

if command -v zip >/dev/null 2>&1; then
  ( cd "$(dirname "$DIST")" && zip -qr "$(basename "$DIST").zip" "$(basename "$DIST")" )
  echo "[package] zip -> $DIST.zip"
fi
echo "[package] done. Upload $DIST/ (or the .zip) to Kaggle."
