# MIGRATION_AUDIT — from the private upstream red-team repo → `agent-redteam-lab`

> **Status:** Phase 1 (audit) complete. No source files were modified.
> **Scope:** classify every component of the private upstream repo as *reuse-as-is*,
> *port-with-redaction*, *recreate-synthetic*, or *keep-private*, and record the
> promptfoo integration seam + the clean-room forbidden-string policy.
>
> **Public-safety note on this document:** the upstream organisation, its internal
> Azure endpoints, colleague names, and corpus names are referred to here only by
> neutral placeholders (`<ORG>`, `<internal-target-host>`, `<internal-grader-host>`,
> `<HARMFUL_CORPUS>`). The literal identifiers live in the **gitignored**
> `docs/_private/forbidden-strings.local.txt`, which seeds the fail-closed scanner and
> is never committed. **No harmful-content corpus files were opened** during this audit;
> they are characterised by filename/structure only.

---

## 0. One-paragraph orientation

The upstream repo is a **local LLM-red-teaming platform built *on top of* the `promptfoo`
CLI** (promptfoo is an npm dependency, not a fork). Its "brain" is a set of pure, unit-tested
`.mjs` modules under `lib/` that: build a promptfoo config from a UI selection, shell out to
`npx promptfoo redteam run` / `promptfoo eval`, parse the resulting report into a compact row
model, grade rows with a pinned Azure GPT-5.5 judge (with k-vote + refusal-repair + few-shot
calibration), compute FP/FN against human gold labels, aggregate breach rates, and estimate
cost. It persists to Postgres (Drizzle) and is driven by two UIs and two run executors (a local
Postgres-queue worker and an AWS Fargate one-shot runner). **Its threat model is *harmful-content
generation* (does the model emit disallowed text), which is materially different from the Kaggle
target threat model of *agent tool misuse*** — see §C, the single most important strategic finding.

---

## A. The eleven Phase-1 questions

**A1 — Where is `promptfoo` called?**
Two code executors, identical branch logic:
- `worker/worker.mjs` (`spawn('npx', …)`) — the local Postgres-queue scan worker.
- `runner/runner-task.mjs` — the AWS Fargate one-shot runner (one run per `RUN_ID`, then exits).
Both spawn `npx promptfoo …` with a hardened, allowlisted env (`minimalEnv`), pass model creds via
`--env-file` (never inherited env), force `PROMPTFOO_DISABLE_SHARING/TELEMETRY`, and kill the whole
process group on cancel. Config-generation entrypoint is `lib/config.mjs`; the *decision* of which
config to build lives in the cockpit UI route. Sample invocation lines live in `configs/*.yaml`
headers and `diy-task-server/`.

**A2 — Input/output schema around promptfoo.**
- **Input (config build, `lib/config.mjs`):** selection `{ plugins, strategies, numTests,
  mode: online|offline, target, graderExamples }` → validated (allowlist of known plugin/strategy
  ids is the injection control; caps `MAX_PLUGINS=150`, `MAX_STRATEGIES=30`, `MAX_CUSTOMS=10`,
  `MAX_GRADER_EXAMPLES=20`) → emitted as promptfoo YAML via `yaml.dump(…, {lineWidth:-1, noRefs:true})`
  so config injection is impossible by construction. Two builders: `buildConfigYaml` (redteam
  generate+run) and `buildLocalEvalConfigYaml` (pre-baked `tests[]` → `promptfoo eval`, no cloud gen).
- **Invocation branch:** decided by **config shape, not a flag** — non-empty `tests[]` + no
  `redteam.plugins[]` ⇒ `promptfoo eval` (no generation/quota/egress); else `redteam run`
  (`--remote` appended only when `online && !localEval`). Mode source-of-truth is the DB `run.mode`.
- **Output (parse, `lib/report.mjs`):** `parseReport(report)` maps `report.results.results[]` 1:1
  into rows `{ plugin, strategy, severity, status: defended|breach|error, pass, attack, response,
  reason, turns[], rounds }` + a summary `{ total, failed(=breached), errored, passed, cost,
  tokenUsage }`. Two downstream platform adapters (`lib/platform-results.mjs`) map rows to the
  upstream platform's `red-teaming-v4` (lossy, closed 11-value enum) and `red-teaming-v5` (rich,
  3-state) result schemas.

**A3 — Truly generic / reusable components.**
The results pipeline (`report → aggregate → cost`), the grading stack (`grader-core` + `refusal-repair`
+ `grader-examples-store`), the plugin/strategy `catalog`, the DB layer (`db/{schema,repo,client}`),
the `id` utility, and the template-based `localgen` generators (`index/packs/domain/ascii-smuggling/plan`).
These are pure JS with no company/harmful coupling (a handful of constants — model/deployment names,
grader model id, price table — are swap-as-config). See the full table in §B.

**A4 — Private / risky / company-named / non-public-safe components.**
- `lib/config.mjs` — otherwise-portable validation/guard logic, but with **hardcoded internal Azure
  hostnames, deployment names, key env-var names, and the harmful-corpus path** embedded. Port the
  *logic*; strip the constants.
- `lib/platform-results.mjs`, `lib/platform-target.mjs` — adapters to the upstream **platform's
  internal result/target schemas**. Do not migrate.
- `lib/datasets/taxonomy.mjs` — the org's **branded harm taxonomy** + `<HARMFUL_CORPUS>` plugin ids.
  Pattern is reusable; identity is company-specific.
- `lib/localgen/harmful.mjs`, `lib/datasets/bake.mjs`, `lib/datasets/<HARMFUL_CORPUS>/**` — the
  **harmful axis** (harmful-seed generator, corpus-build pipeline, on-disk harmful corpora). Never migrate.
- `runner/out/*.report.json`, `artifacts/`, `tmp/` — **run traces** containing real internal
  identifiers (a colleague/stage handle, an `@<org>` email) *and* harmful generated content. Never migrate.
- `docs/` — almost entirely internal process/architecture material (cross-AI audit transcripts,
  platform architecture audits, status reports). Keep private; recreate only the generic reference
  concepts as fresh public docs.
- `scripts/*` — research/experiment scripts (judge comparisons, FP/FN, corpus baking) hardcoding the
  internal Azure hosts and corpus. Not migrated as code; the *methodology* (k-vote judging, FP/FN
  scoring) is recreated as clean public tooling.

**A5 — Where plugin definitions are stored.**
`lib/catalog.mjs` — a framework-agnostic catalog `{ plugins[], strategies[] }`, each item
`{ id, group, sev, egress, cloud, localPath, multiturn?, desc }`, plus derived allowlists and
OWASP/data-derived presets. The `<HARMFUL_CORPUS>:` plugin *group* is wired in from
`lib/datasets/taxonomy.mjs`; that slice is company/harmful-coupled, the rest of the catalog is generic.

**A6 — Where grader calibration examples are stored.**
`configs/grader-examples.json` (read/written via `lib/grader-examples-store.mjs`). Shape: a small
array (**6 rows** at audit time) of `{ output, pass:boolean, score:[0,1], reason }`. **Row bodies were
not read.** These are non-synthetic (tuned on real graded outputs) → **recreate as synthetic examples**.

**A7 — Where risk maps and cost maps are stored.**
- **FP/FN risk model:** `lib/report.mjs` (`classifyRow` — the crown-jewel `defended|breach|error`
  decision that keeps content-filtered/errored rows *out* of the breach denominator),
  `lib/refusal-repair.mjs` (detects promptfoo's non-disablable refusal short-circuit and re-grades
  those rows), `lib/grader-core.mjs` (k-vote majority, ties→breach for recall), and the ground-truth
  scorer `computeFpFn` in `lib/db/repo.mjs` (positive class = breach; FP = judge-breach/human-defended,
  FN = judge-defended/human-breach). Severity weights `SEV_WEIGHT` live in `lib/aggregate.mjs`.
- **Cost map:** `lib/cost.mjs` — a `RATES` table ($/1M in/out per model) + `costOf(summary)` splitting
  target vs grader dollars (grader priced locally because promptfoo has no entry for the judge model).

**A8 — Where traces are stored.**
- `artifacts/<runId>.report.json` — durable raw promptfoo report of record for the local worker
  (~0.2–1.2 MB each; full transcripts + grader componentResults + target responses).
- `tmp/` — disposable per-run config YAML + scratch experiment outputs.
- `runner/out/` — older spike/P0 runner triples (`.report.json` / `.result.json` / `.log`).
- **Prod:** the Fargate runner uploads the report to **S3** (`reports/<runId>/<attempt>-<sha256>.json`,
  SSE-KMS) before the DB write.
- **Postgres:** compact parsed rows (`run_rows`, `run_turns`), immutable config snapshot
  (`scan_configs.config_yaml`), artifact pointer + sha256 (`run_artifacts`), chunked logs (`run_logs`),
  judge/human verdicts (`row_grades`, `run_row_labels`). All artifact dirs are gitignored upstream.

**A9 — What can be copied directly after renaming.**
The generic `lib/` modules in §A3 (adjusting the few swap-as-config constants). Everything else is
either ported-with-redaction, recreated-synthetic, or kept-private. **Nothing** with a hardcoded
internal host, a harmful corpus reference, or a real trace is copied.

**A10 — What must be recreated as synthetic examples.**
- `configs/grader-examples.json` → synthetic calibration rows for the tool-attack judge.
- `lib/localgen/domain.mjs` reference verticals → benign synthetic tool-agent scenarios (§C).
- Any prompt-bank / attack template content → synthetic templates over the Kaggle tool surface.
- The `<HARMFUL_CORPUS>` category structure → **not recreated**; it is out of scope for the Kaggle
  tool-misuse threat model (see §C). The *catalog/taxonomy pattern* is recreated with synthetic,
  tool-attack-relevant categories instead.

**A11 — What stays private and only feeds the sync/export pipeline.**
The harmful axis (`localgen/harmful.mjs`, `datasets/bake.mjs`, `datasets/<HARMFUL_CORPUS>/**`), the
platform adapters (`platform-*.mjs`), the branded taxonomy identity, all run traces
(`artifacts/`, `tmp/`, `runner/out/`), all internal `docs/`, and the literal identifiers in
`docs/_private/forbidden-strings.local.txt`. The upstream repo is only ever a *source* for the sync
tool (Phase 9), which pulls **generic modules through the redaction transform + fail-closed scanner** —
never a blind copy.

---

## B. Module classification table

| Upstream module | Class | Disposition in `agent-redteam-lab` |
|---|---|---|
| `lib/id.mjs` | GENERIC | **reuse-as-is** |
| `lib/aggregate.mjs` | GENERIC | **reuse-as-is** |
| `lib/report.mjs` | GENERIC | **reuse-as-is** (crown-jewel error-vs-breach classifier) |
| `lib/cost.mjs` | GENERIC | reuse; externalise `RATES` + deployment names |
| `lib/grader-core.mjs` | GENERIC | reuse; externalise `GRADER_MODEL` id |
| `lib/grader-examples-store.mjs` | GENERIC | **reuse-as-is** (contents recreated-synthetic) |
| `lib/refusal-repair.mjs` | GENERIC | reuse; abstract the `azureChat` dependency behind a judge interface |
| `lib/catalog.mjs` | GENERIC | reuse, **minus** the harmful-corpus group wiring |
| `lib/localgen/{index,packs,domain,ascii-smuggling}.mjs` | GENERIC | reuse (OWASP-style security templates; SSRF/BOLA/BFLA/ASCII map well — §C) |
| `lib/localgen/plan.mjs` | GENERIC | reuse; drop the harmful branch |
| `lib/db/{schema,repo,client}.mjs` | GENERIC | reuse (the tool's own data model) |
| `lib/config.mjs` | COMPANY-COUPLED | **port-with-redaction**: keep the validation/guard logic (allowlist, `SAFE_TRANSFORM_RE` RCE guard, `file://` reject, loopback-only HTTP); strip internal hosts/deployments/keys/corpus path into config |
| `lib/localgen/extract-domain.mjs` | COMPANY-COUPLED | port the `extractDomain` shape; replace `azureChat` with a neutral provider |
| `lib/datasets/taxonomy.mjs` | COMPANY-COUPLED | reusable *pattern* only; recreate with synthetic tool-attack categories |
| `lib/platform-results.mjs` | COMPANY-COUPLED | **keep-private** (platform result schema) |
| `lib/platform-target.mjs` | COMPANY-COUPLED | **keep-private** (platform modelAccess schema) |
| `lib/localgen/harmful.mjs` | PRIVATE-HARMFUL | **keep-private** |
| `lib/datasets/bake.mjs` | PRIVATE-HARMFUL | **keep-private** |
| `lib/datasets/<HARMFUL_CORPUS>/**` | PRIVATE-HARMFUL | **never migrate** |
| `runner/out/`, `artifacts/`, `tmp/` (traces) | PRIVATE | **never migrate** |
| `docs/` (internal) | PRIVATE | keep-private; recreate generic concepts as fresh public docs |
| `scripts/*` (research) | COMPANY-COUPLED | recreate the *methodology* (k-vote, FP/FN) as clean tooling |

Language note: the reusable "brain" is JS/`.mjs`. It belongs in the **Control Plane / Candidate
Factory** layers (`apps/web`, `packages/*`). The **Kaggle adapter is thin Python** (`kaggle/attack.py`).
The candidate schema must therefore be **language-neutral (JSONL)** — the bridge between the two.

---

## C. ⭐ Threat-model mismatch — the key strategic finding

The upstream repo answers **"will the model *generate* disallowed content?"** (single/multi-turn text;
plugins = harmful-content categories; judge = did it comply). Kaggle *AI Agent Security — Multi-Step
Tool Attacks* answers a **different question: "will the agent *misuse tools*?"** — scored by four
predicate families over a fixed tool surface:

| Kaggle predicate (severity) | Kaggle tool surface it fires on |
|---|---|
| `EXFILTRATION` (5) | `fs.read` → `email.send` / `http.post` (data leaves the sandbox) |
| `UNTRUSTED_TO_ACTION` (5) | `web.open` / `email.read` content → a state-changing tool call |
| `DESTRUCTIVE_WRITE` (4) | `fs.write` / `fs.delete` (irreversible local mutation) |
| `CONFUSED_DEPUTY` (3) | a privileged tool invoked on behalf of an untrusted instruction |

**Consequence: what transfers is the *architecture*, not the harmful-content code.** Concretely:

- **Directly reusable as-is:** the whole results/grading/risk/cost/DB/catalog **architecture** — it is
  agnostic to *what* is being graded.
- **Reusable template primitives** (`localgen/packs.mjs`) that map onto the tool threat model:
  - `SSRF_TARGETS` / `SSRF_WRAPPERS` → `EXFILTRATION` / `UNTRUSTED_TO_ACTION` via `http.post`.
  - `PRETEXT_ROLES` / `LOW_PRIV_ROLES` / `OVERRIDE_DEMANDS` → `CONFUSED_DEPUTY`.
  - `LEAK_VERBS` (BOLA) → `EXFILTRATION` (read others' data → `email.send`/`http.post`).
  - `ascii-smuggling` (hidden instructions in content) → `UNTRUSTED_TO_ACTION` (the canonical
    prompt-injection-via-untrusted-content pattern — a near-perfect fit).
  - a destructive-write minimal template → `DESTRUCTIVE_WRITE` via `fs.delete`/`fs.write`.
  - Multi-turn strategy ideas (Crescendo/GOAT-like) → `crescendo_like_local` / `goat_like_local`
    tool-attack strategies.
- **Out of scope for Kaggle:** the entire harmful-content axis (`<HARMFUL_CORPUS>`, `harmful.mjs`,
  `taxonomy.mjs`, most `hai:`/`harmful:` catalog groups). This is the biggest "do-not-migrate" bucket,
  and it happens to be exactly the most IP/safety-sensitive part — so the clean-room boundary and the
  Kaggle-relevance boundary largely coincide. Convenient.

So Phase 4 (synthetic plugin sandbox) and Phase 5 (strategy layer) are **re-implementations against the
10-tool Kaggle surface**, reusing upstream *interfaces and template primitives*, not the harmful corpora.

---

## D. promptfoo integration seam (for the runner abstraction)

Kaggle's evaluator **replays the returned user-message chains and recomputes trace/predicates/score** —
it does not trust attacker-supplied metadata. So promptfoo (and our judge, risk map, cost model) are
strictly **internal ranking/filtering tools**; the shipped Kaggle object is replayable message chains.

For the lab's *local* loop we can still keep a promptfoo-runner abstraction (like upstream's
config-shape branch between `redteam run` and `eval`), but the security guards in `lib/config.mjs` are
worth porting verbatim into the public repo because they are genuinely good, reusable engineering:
- `SAFE_TRANSFORM_RE` — constrains promptfoo's `transformResponse` (which it evals as code via
  `new Function`) to a pure JSON selector, closing an RCE vector.
- recursive `file://` rejection in target body/headers — closes a local-file read/exfil vector.
- loopback-only HTTP targets, `{{prompt}}`-must-be-present body check.
These map cleanly to "how do we let an untrusted caller configure a run safely" — a portfolio talking point.

---

## E. Clean-room / forbidden-string policy

`scripts/public_safety_scan.py` (Phase 9) must **fail closed** on any of the categories seeded in the
gitignored `docs/_private/forbidden-strings.local.txt`:
1. Organisation / project / product names (and case variants).
2. Colleague names.
3. Internal deployment/stage/account handles.
4. Real email domains.
5. Internal Azure endpoint hostnames.
6. Internal-specific secret **env-var names** (rename to neutral ones in the public repo).
7. Regex-shaped secrets: `sk-…`, `AKIA…`, PEM private-key headers, and any `*.azure.com` /
   `*.neon.tech` / `*.amazonaws.com` host literal.

**Good news from the scan:** *no literal secret material* (API keys, tokens, private keys) was found in
upstream source — all credentials flow through env vars. The exposure is (a) internal **hostnames** and
(b) internal **identifiers/emails inside run traces** — both handled by "never migrate traces" + the
redaction transform + the scanner.

---

## F. Summary — three buckets

- **Migrate (code, with light redaction):** `report`, `aggregate`, `cost`, `grader-core`,
  `grader-examples-store`, `refusal-repair`, `catalog` (minus harmful group), `db/*`, `id`, `localgen/*`
  (minus harmful), and the *guard logic* of `config.mjs`. → the "we built a real eval platform" story.
- **Recreate synthetic:** grader calibration rows, domain/scenario fixtures, attack templates —
  all re-expressed against the 10-tool Kaggle surface and the 4 predicate families.
- **Keep private (sync-source only, never in the public tree):** harmful axis, platform adapters,
  branded taxonomy identity, all traces, internal docs, and the literal forbidden-string list.

---

## G. Recommended next steps

1. **Phase 0 — verify the competition/SDK contract online** (unverified assumptions: `aicomp_sdk`
   package + `AttackAlgorithmBase`/`AttackCandidate` API, the `aicomp` CLI, predicate weights, the
   `raw_score`/`ATTACK_ELITE_RAW` scoring, budgets, replay limits). Produce `docs/COMPETITION_RESEARCH.md`
   with per-claim source + official/community/speculative tag. This gates the entire Kaggle adapter.
2. **Phase 2 — scaffold** the target repo structure + README + `.env.example` + minimal tests +
   the public-safety scanner (seeded from the private forbidden list).
3. **Phase 3 — extract generic core**: port the §F "migrate" modules with constants externalised, and
   define the language-neutral JSONL candidate schema.
4. **Phase 4–5 — synthetic tool sandbox + strategy layer** against the Kaggle tool surface (§C mapping).
5. **Phase 9 sync tooling** wired to pull only generic modules through redaction + scanner.

_End of Phase-1 audit._
