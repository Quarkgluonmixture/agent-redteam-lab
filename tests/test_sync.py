"""Upstream sync: redaction + fail-closed re-scan (synthetic source, no real repo)."""

from __future__ import annotations

import os

import sync_from_upstream as sfu
from sync.redact import redact

# Built at runtime so this test file stays public-safety-scanner-clean.
HOST = "api." + "azure" + ".com"
EVIL = "a@evil" + "corp.com"


def test_redact_removes_forbidden_and_hosts_and_emails():
    text = f"org ACMECORP host {HOST} mail {EVIL} ok you@example.com"
    out, hits = redact(text, ["acmecorp"])
    assert "ACMECORP" not in out and "<REDACTED>" in out
    assert HOST not in out
    assert "corp.com" not in out.split("mail")[-1].split(" ok")[0]  # evil email domain gone
    assert "you@example.com" in out          # safe domain kept
    assert any(h.startswith("forbidden:") for h in hits)


def _make_source(tmp_path, name, content):
    d = tmp_path / "src" / "lib"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(content, encoding="utf-8")
    return str(tmp_path / "src")


def test_dry_run_would_sync_after_redaction(tmp_path):
    src = _make_source(tmp_path, "foo.mjs", f"// from ACMECORP at {HOST}\nexport const x = 1;\n")
    rep = sfu.run_sync(src, str(tmp_path / "dst"), ["acmecorp"], apply=False)
    assert rep["ok"] is True
    entry = next(r for r in rep["results"] if r.get("from") == "foo.mjs")
    assert entry["status"].startswith("would-sync")
    assert not (tmp_path / "dst").exists()   # dry-run writes nothing


def test_apply_writes_redacted_file(tmp_path):
    src = _make_source(tmp_path, "foo.mjs", "// ACMECORP\nexport const x = 1;\n")
    rep = sfu.run_sync(src, str(tmp_path / "dst"), ["acmecorp"], apply=True)
    assert rep["ok"] is True
    dest = tmp_path / "dst" / "packages" / "_from_upstream" / "lib" / "foo.mjs"
    assert dest.exists()
    assert "ACMECORP" not in dest.read_text() and "<REDACTED>" in dest.read_text()


def test_fail_closed_on_residual_secret(tmp_path):
    # A secret the redactor doesn't neutralise (an sk- key) must be REFUSED, not written.
    key = "sk-" + "A" * 22
    src = _make_source(tmp_path, "bar.mjs", f"const k = '{key}';\n")
    rep = sfu.run_sync(src, str(tmp_path / "dst"), [], apply=True)
    assert rep["ok"] is False
    entry = next(r for r in rep["results"] if r.get("from") == "bar.mjs")
    assert entry["status"].startswith("REFUSED")
    assert not (tmp_path / "dst").exists()   # nothing written on refusal


def test_never_sync_paths_excluded(tmp_path):
    # a datasets/ file must be skipped even if it matches include globs
    d = tmp_path / "src" / "lib" / "datasets"
    d.mkdir(parents=True)
    (d / "corpus.py").write_text("x = 1\n", encoding="utf-8")
    rep = sfu.run_sync(str(tmp_path / "src"), str(tmp_path / "dst"), [], apply=False)
    assert not any("datasets" in r.get("from", "") for r in rep["results"])
