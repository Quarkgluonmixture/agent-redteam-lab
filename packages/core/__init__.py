"""agent-redteam-lab core: the language-neutral candidate schema (lab side)."""

from .candidate import (  # noqa: F401
    MAX_CHARS_PER_MESSAGE,
    LOCAL_SDK_MAX_CHARS,
    MAX_FINDINGS_PER_RUN,
    MAX_USER_MESSAGES_PER_FINDING,
    PREDICATE_FAMILIES,
    REQUIRED_FIELDS,
    SEVERITY_WEIGHT,
    AttackCandidateDraft,
    severity_weight_of,
    validate,
)
