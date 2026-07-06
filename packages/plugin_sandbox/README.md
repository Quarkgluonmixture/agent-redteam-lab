# packages/plugin_sandbox

A synthetic, public-safe model of the competition's tool-use attack surface — the
substrate the Phase-5 strategy generators target. It contains **no competition data
and no weaponised prompts**: only our own toy fixtures, a clean-room predicate
evaluator (re-implemented from the public spec), and a scenario catalog.

| File | What |
|---|---|
| `tools.py` | the 10-tool surface + side-effect classes (READ/WRITE/SHARE/EXEC), exfil sink, secret path, entry-point taxonomy |
| `predicates.py` | clean-room evaluator for the 4 predicates over a trace; credits encoded exfil (base64/hex/url/reversal/separator) |
| `scenarios.py` | `Scenario` dataclass + loader + validator |
| `scenarios.json` | 14 scenarios covering all 4 predicates, all 10 tools, entry points E1–E4, encoded exfil, + 2 false-positive controls |
| `fixtures/` | synthetic `file_seed.json` (toy `secret.txt`), `web_corpus.json` (incl. a synthetic poisoned page), `mail_seed.json` (incl. a synthetic poisoned email) |

The validator (`validate_scenario`) checks each scenario's example trace fires
**exactly** its declared predicates via `predicates.evaluate`, keeping the catalog
honest. `tests/test_plugin_sandbox.py` runs this over the whole catalog.

Secrets/hosts/emails are toy and non-operational (`toy-abc123`, `*.invalid`,
`@corp.invalid`). Fixtures model the untrusted-content **environment**; crafting the
attacker's user-message chains is Phase 5.
