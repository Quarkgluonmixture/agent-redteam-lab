"""pytest bootstrap: make the lab's package dirs importable without installation."""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
for _p in ("packages", "kaggle", "scripts"):
    _full = os.path.join(_ROOT, _p)
    if _full not in sys.path:
        sys.path.insert(0, _full)
