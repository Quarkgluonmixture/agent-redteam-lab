#!/usr/bin/env python3
"""Fail-closed public-safety scanner for agent-redteam-lab.

Scans the committable tree for material that must never reach the public repo:
generic secrets, managed-cloud host literals, non-allowlisted emails, and any
literal upstream identifier listed in the PRIVATE seed file.

Design (see docs/PUBLIC_SAFE_CHECKLIST.md):
  * The COMMITTED patterns are all GENERIC (no company strings), so this file is
    itself public-safe.
  * The company-specific literals are read at runtime from the gitignored
    ``docs/_private/forbidden-strings.local.txt`` (never committed). If that file
    is absent (fresh clone / CI), the generic patterns still run and a NOTICE is
    printed that the private list was skipped.

Exit code: 0 == clean, 1 == at least one finding (fail closed).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

# --- Generic patterns (public-safe; contain no company identifiers) ---------
# Host detection is assembled from parts so this source file never contains a
# literal "<label>.<cloud>.<tld>" string (which would self-match on scanning).
_CLOUD = r"(?:azure|neon|amazonaws|cognito-idp)"
_HOST_RE = re.compile(r"[a-z0-9][a-z0-9-]*\." + _CLOUD + r"\.[a-z]{2,}", re.I)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

PATTERNS: list[tuple[str, re.Pattern]] = [
    ("openai-style-key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws-access-key-id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")),
    ("managed-cloud-host", _HOST_RE),
    ("external-email", _EMAIL_RE),
]

# Emails at these domains are fine (examples, this project's own accounts, public orgs).
SAFE_EMAIL_DOMAINS = {
    "example.com", "example.org", "example.net", "example.invalid", "corp.invalid",
    "anthropic.com", "users.noreply.github.com", "github.com",
    "openai.com", "google.com", "kaggle.com", "arxiv.org", "pypi.org", "ieee.org",
}

PRIVATE_SEED = os.path.join("docs", "_private", "forbidden-strings.local.txt")

_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build",
              "__pycache__", ".pytest_cache", "artifacts", "tmp"}
_TEXT_EXT = {".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json", ".jsonl",
             ".sh", ".cfg", ".ini", ".env", ".example", ".ts", ".tsx", ".js", ".mjs", ""}


def _redact(s: str) -> str:
    s = s.strip()
    return (s[:3] + "…") if len(s) > 4 else "…"


def _domain_of(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower()


def load_forbidden_substrings(private_path: str = PRIVATE_SEED) -> list[str]:
    """Read literal forbidden substrings from the private seed (empty if absent)."""
    subs: list[str] = []
    if not os.path.exists(private_path):
        return subs
    with open(private_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            subs.append(line)
    return subs


def scan_text(text: str, forbidden_substrings: tuple[str, ...] | list[str] = ()) -> list[tuple[int, str, str]]:
    """Scan text; return findings as (line_no, kind, redacted_match)."""
    findings: list[tuple[int, str, str]] = []
    lowered_subs = [s.lower() for s in forbidden_substrings if s]
    for i, line in enumerate(text.splitlines(), 1):
        for kind, rx in PATTERNS:
            for m in rx.finditer(line):
                hit = m.group(0)
                if kind == "external-email" and _domain_of(hit) in SAFE_EMAIL_DOMAINS:
                    continue
                findings.append((i, kind, _redact(hit)))
        low = line.lower()
        for sub in lowered_subs:
            if sub in low:
                findings.append((i, "forbidden-substring", _redact(sub)))
    return findings


def iter_repo_files(root: str) -> list[str]:
    """Files git would track/keep (excludes gitignored, e.g. docs/_private)."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout
        files = [os.path.join(root, p) for p in out.splitlines() if p]
    except Exception:
        files = []
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in _SKIP_DIRS]
            for f in fns:
                files.append(os.path.join(dp, f))
    self_path = os.path.abspath(__file__)
    keep = []
    for f in files:
        if os.path.abspath(f) == self_path:  # don't scan the scanner (holds the regexes)
            continue
        norm = f.replace(os.sep, "/")
        # Never scan the PRIVATE seed itself (it legitimately holds the forbidden literals).
        if "/_private/" in norm or norm.endswith(".local.txt"):
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext and ext not in _TEXT_EXT:
            continue
        keep.append(f)
    return keep


def scan_repo(root: str | None = None, private_path: str | None = None) -> list[tuple[str, int, str, str]]:
    root = root or _repo_root()
    private_path = private_path or os.path.join(root, PRIVATE_SEED)
    subs = load_forbidden_substrings(private_path)
    results: list[tuple[str, int, str, str]] = []
    for f in iter_repo_files(root):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, kind, red in scan_text(text, subs):
            results.append((os.path.relpath(f, root), line_no, kind, red))
    return results


def _repo_root() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    root = _repo_root()
    private_path = os.path.join(root, PRIVATE_SEED)
    have_private = os.path.exists(private_path)
    if not have_private:
        print(f"NOTICE: private seed {PRIVATE_SEED} not found — "
              "scanning generic patterns only (company-name check skipped).")
    findings = scan_repo(root, private_path)
    if not findings:
        n = "generic + private" if have_private else "generic"
        print(f"public-safety scan: PASS ({n} patterns, no findings).")
        return 0
    print(f"public-safety scan: FAIL — {len(findings)} finding(s):")
    for relpath, line_no, kind, red in findings:
        print(f"  {relpath}:{line_no}: [{kind}] {red}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
