"""Upstream sync: pull generic modules through redaction + a fail-closed scan."""

from .redact import redact  # noqa: F401
from .upstream_map import MAPPINGS, NEVER_SYNC, SOURCE_REPO_ENV  # noqa: F401
