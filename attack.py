"""Root-level Kaggle entrypoint (local convenience).

The canonical adapter lives in ``kaggle/attack.py``. This file defines a literal
``AttackAlgorithm`` with a ``run`` method (so ``aicomp validate redteam attack.py``
and the contract test pass from the repo root) and delegates to that adapter.

For the actual submission, the Kaggle notebook writes ``kaggle/attack.py`` (and its
siblings) to ``/kaggle/working/`` — see ``scripts/package_kaggle_submission.sh`` and
``docs/KAGGLE_ADAPTER_SPEC.md``; this shim is not part of the packaged submission.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

from aicomp_sdk.attacks import AttackAlgorithmBase, AttackCandidate, AttackRunConfig  # noqa: F401

_HERE = os.path.dirname(os.path.abspath(__file__))
_TARGET = os.path.join(_HERE, "kaggle", "attack.py")
_spec = importlib.util.spec_from_file_location("_kaggle_attack_impl", _TARGET)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise ImportError(f"cannot load adapter at {_TARGET}")
_impl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_impl)


class AttackAlgorithm(AttackAlgorithmBase):
    """Thin delegator to ``kaggle/attack.py``'s adapter (keeps a literal class + run)."""

    def __init__(self, config=None) -> None:
        super().__init__(config)
        self._impl = _impl.AttackAlgorithm(config)

    def run(self, env: Any, config: AttackRunConfig | None = None) -> list[AttackCandidate]:
        return self._impl.run(env, config)
