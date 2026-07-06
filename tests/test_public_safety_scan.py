"""Tests for the fail-closed public-safety scanner.

Bad strings are BUILT AT RUNTIME via concatenation so this test file itself
contains no literal secret/host/email and therefore passes the repo scan.
"""

from __future__ import annotations

import os
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import public_safety_scan as pss  # noqa: E402


def test_clean_text_passes():
    text = "Just some clean docs. Contact you@example.com for the sample.\nprint('hello')"
    assert pss.scan_text(text) == []


def test_flags_openai_style_key():
    bad = "token = " + "sk-" + "A" * 24
    kinds = {k for _, k, _ in pss.scan_text(bad)}
    assert "openai-style-key" in kinds


def test_flags_managed_cloud_host():
    host = "myres" + "." + "azure" + "." + "com"
    line = "endpoint: https://" + host + "/x"
    kinds = {k for _, k, _ in pss.scan_text(line)}
    assert "managed-cloud-host" in kinds


def test_flags_non_allowlisted_email():
    addr = "alice" + "@" + "acmecorp" + "." + "com"
    kinds = {k for _, k, _ in pss.scan_text(addr)}
    assert "external-email" in kinds


def test_allowlisted_email_is_ignored():
    assert pss.scan_text("ping you@example.com") == []


def test_forbidden_substring_from_private_seed():
    findings = pss.scan_text("we partner with " + "Acme" + "Corp", forbidden_substrings=["acmecorp"])
    kinds = {k for _, k, _ in findings}
    assert "forbidden-substring" in kinds


def test_repo_is_clean():
    """The committed tree (incl. private seed if present) must scan clean."""
    findings = pss.scan_repo()
    assert findings == [], f"public-safety findings in committed tree: {findings}"
