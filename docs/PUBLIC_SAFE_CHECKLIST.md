# PUBLIC_SAFE_CHECKLIST

This repo is public. It must contain **no** company/customer identifiers, secrets, or
non-synthetic material derived from the private upstream project.

## Forbidden (never commit)

- Organisation / project / product / customer / colleague / internal-system names.
- Real emails, credentials, API keys, tokens, cookies, private endpoints, internal URLs,
  production traces, real user data.
- Non-synthetic grader calibration examples, or plugin/scenario definitions derived from
  private/customer workflows.
- Company screenshots or anything targeting real external services.

## Allowed

- Synthetic toy plugins, tasks, traces, and calibration data.
- Public SDK interfaces, public competition data/examples.
- Public-safe attack categories **inside the authorized offline sandbox**.
- The author's own architecture patterns / abstractions / UI designs, after redaction.

## How the guard works

- **Committed scanner** `scripts/public_safety_scan.py` contains only **generic** patterns
  (OpenAI-style `sk-` keys, AWS `AKIA…` ids, PEM private-key blocks, managed-cloud host
  literals, non-allowlisted emails) — so the scanner file is itself public-safe.
- **Company-specific literals** live in the **gitignored**
  `docs/_private/forbidden-strings.local.txt` and are loaded at runtime. This file
  **must never be committed** (`.gitignore` blocks `docs/_private/` and `*.local.txt`).
- If the private seed is absent (fresh clone / CI), generic patterns still run and a
  NOTICE is printed. Exit code 1 on any finding (**fail closed**).
- Test fixtures that need "bad" strings build them at **runtime concatenation** so no
  literal secret/host/email is committed.

## Verified clean (Phase-0 scan of upstream)

No literal secret material was found in the upstream source (all credentials flow through
env vars). The real exposure is (a) internal **host literals** and (b) identifiers/emails
inside **run traces** — handled by "never migrate traces" + the redaction transform +
this scanner. Full triage: `MIGRATION_AUDIT.md`.

## Pre-publish / pre-push checklist

- [ ] `python scripts/public_safety_scan.py` → PASS (with the private seed present).
- [ ] `pytest -q` green (incl. `test_public_safety_scan.py::test_repo_is_clean`).
- [ ] `git status` shows no `.env`, no `docs/_private/**`, no `artifacts/` / `tmp/` / traces.
- [ ] Commit author is the personal identity (no company email in history).
- [ ] The packaged submission (`dist/kaggle_submission/`) contains only `attack.py` +
      `portfolio_selector.py` + `utils.py` + `candidate_bank.jsonl`.
- [ ] Kaggle-shipped `userMessages` carry no internal metadata or identifiers.
