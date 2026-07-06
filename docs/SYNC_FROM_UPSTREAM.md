# SYNC_FROM_UPSTREAM

The public repo is developed independently but can pull **selected, redacted** updates
from the private upstream project. **Never a blind copy.** (Implemented in Phase 9:
`packages/sync/{upstream_map.py,redact.py}` + `scripts/sync_from_upstream.py`; the YAML
below is an illustrative mirror of `upstream_map.MAPPINGS`.)

## Principles

- The upstream repo is only ever a **source**. The sync tool pulls **generic modules**
  through a **redaction transform** and a **fail-closed scanner**, then runs tests.
- What may sync, what must be recreated synthetically, and what stays private is fixed by
  `MIGRATION_AUDIT.md`. In short: sync the results/grading/catalog/db/localgen
  *architecture*; **never** sync the harmful axis, platform adapters, branded taxonomy,
  traces, or internal docs.
- Threat-model note: upstream targets harmful-*content* generation; this lab targets
  agent *tool misuse*. So most "sync" is really **re-implementation of patterns** against
  the 10-tool sandbox, which conveniently keeps the harmful/company material out.

## Pieces (Phase 9 — implemented)

```
packages/sync/upstream-map.yaml     # explicit from→to mappings, include/exclude globs, transform
scripts/sync_from_upstream.py       # --dry-run, file-level diff, redaction, scanner, tests, sync_report.md
scripts/public_safety_scan.py       # ALREADY PRESENT — the fail-closed gate
```

`upstream-map.yaml` sketch:

```yaml
source_repo_env: SOURCE_REPO         # path to the private repo (never hard-coded)
mappings:
  - from: packages/strategies
    to:   packages/strategies
    mode: rsync
    include: ["**/*.ts", "**/*.py", "**/*.mjs"]
    exclude: ["**/*.secret.*", "**/.env*", "**/_private/**",
              "**/<ORG>/**", "**/customers/**", "**/private/**", "**/real_traces/**"]
  - from: packages/risk
    to:   packages/risk
    mode: transform
    transform: redact_private_examples
```

## Sync tool requirements

- `--dry-run` with a file-level diff summary; **never deletes** targets unless
  `--allow-delete` is passed explicitly.
- Runs the redaction transform, then `public_safety_scan.py`, then the test suite.
- **Fails closed** on any company name, credential, private URL, real email, or
  suspicious token; writes `sync_report.md`.
- The literal forbidden list stays in the gitignored private seed (see
  `PUBLIC_SAFE_CHECKLIST.md`); the map/scripts themselves carry no company strings.
