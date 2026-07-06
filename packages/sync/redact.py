"""Redaction transform for the upstream sync pipeline.

Replaces literal forbidden substrings (from the gitignored private seed) with
`<REDACTED>` and neutralises managed-cloud host literals + non-allowlisted emails,
so generic modules can be pulled from the private upstream repo without leaking
identifiers. The synced result is then re-scanned (fail-closed) before it is written.
"""

from __future__ import annotations

import re
from typing import Iterable

_CLOUD = r"(?:azure|neon|amazonaws|cognito-idp)"
_HOST_RE = re.compile(r"[a-z0-9][a-z0-9-]*\." + _CLOUD + r"\.[a-z]{2,}", re.I)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

SAFE_EMAIL_DOMAINS = {
    "example.com", "example.org", "example.net", "example.invalid", "corp.invalid",
    "anthropic.com", "users.noreply.github.com", "github.com",
    "openai.com", "google.com", "kaggle.com", "arxiv.org", "pypi.org", "ieee.org",
}


def _redact_emails(text: str) -> tuple[str, int]:
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        domain = m.group(0).rsplit("@", 1)[-1].lower()
        if domain in SAFE_EMAIL_DOMAINS:
            return m.group(0)
        n += 1
        return "<REDACTED_EMAIL>"

    return _EMAIL_RE.sub(sub, text), n


def redact(text: str, forbidden: Iterable[str] = ()) -> tuple[str, list[str]]:
    """Return (redacted_text, list-of-redaction-kinds-applied)."""
    hits: list[str] = []
    for sub in forbidden:
        if sub and sub.lower() in text.lower():
            text = re.sub(re.escape(sub), "<REDACTED>", text, flags=re.I)
            hits.append(f"forbidden:{sub}")
    text, n_host = _HOST_RE.subn("<REDACTED_HOST>", text)
    if n_host:
        hits.append(f"host:{n_host}")
    text, n_mail = _redact_emails(text)
    if n_mail:
        hits.append(f"email:{n_mail}")
    return text, hits
