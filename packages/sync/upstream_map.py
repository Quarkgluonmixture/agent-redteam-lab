"""Declarative upstream→public sync map (authoritative; the YAML in
docs/SYNC_FROM_UPSTREAM.md is an illustrative mirror).

The private upstream repo is only ever a SOURCE: generic modules are pulled through
the redaction transform + the fail-closed scanner, never blind-copied. What may sync
vs recreate-synthetic vs keep-private is fixed by docs/MIGRATION_AUDIT.md.
"""

from __future__ import annotations

SOURCE_REPO_ENV = "SOURCE_REPO"  # path to the private repo (never hard-coded)

# Each mapping: pull `from` (relative to $SOURCE_REPO) → `to` (relative to this repo),
# keeping include globs, dropping exclude globs, applying `transform`.
MAPPINGS: list[dict] = [
    {
        "from": "lib",
        "to": "packages/_from_upstream/lib",
        "include": ["**/*.mjs", "**/*.ts", "**/*.py"],
        "exclude": [
            "**/*.secret.*", "**/.env*", "**/_private/**",
            "**/datasets/**",          # harmful corpora — never sync
            "**/platform-*.mjs",       # company platform adapters
            "**/localgen/harmful.*",   # harmful-seed generator
            "**/*.test.*",
        ],
        "transform": "redact",
    },
]

# Categories the sync must NEVER pull (belt-and-suspenders over the excludes above).
# Generic path fragments only — no upstream identifiers (this file is committed/public).
NEVER_SYNC = (
    "datasets/", "corpus", "platform-", "localgen/harmful",
    "artifacts/", "tmp/", "runner/out/", "_private/",
)
