#!/usr/bin/env python3
"""Build the Kaggle submission NOTEBOOK from the kaggle/ adapter files.

This is a Code Competition: the submission is a notebook that writes `attack.py`
(and its siblings) to `/kaggle/working/`; the hosted evaluator then loads and runs it.
We embed the four kaggle/ files (base64, so any quoting is safe) into a single write
cell — the notebook is fully reproducible from the source files (single source of truth).

Usage:
    python scripts/build_kaggle_notebook.py [--out dist/agent_redteam_submission.ipynb]
"""

from __future__ import annotations

import argparse
import base64
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAGGLE = os.path.join(ROOT, "kaggle")
FILES = ("attack.py", "portfolio_selector.py", "utils.py", "candidate_bank.jsonl")
DEFAULT_OUT = os.path.join(ROOT, "dist", "agent_redteam_submission.ipynb")

COMPETITION = "ai-agent-security-multi-step-tool-attacks"
DEFAULT_KERNEL_ID = "quarkgluonmixture/agent-redteam-lab-attack"
NOTEBOOK_FILENAME = "agent_redteam_submission.ipynb"
# Competition-specific evaluation gateway (from the official getting-started notebook).
GATEWAY_MODULE = "kaggle_evaluation.jed_attack_134815.jed_attack_inference_server"

MARKDOWN = [
    "# agent-redteam-lab — Kaggle submission\n",
    "\n",
    "Code-competition submission. Three cells: (1) put the competition data on the path,\n",
    "(2) write `attack.py` + siblings to `/kaggle/working/`, (3) serve the evaluation\n",
    "gateway. Real scoring happens during Kaggle's competition rerun.\n",
    "Regenerate with `scripts/build_kaggle_notebook.py` — do not hand-edit.\n",
]

SETUP_CELL = [
    "import sys, glob\n",
    "from pathlib import Path\n",
    "sys.argv = [sys.argv[0]]  # avoid argparse conflicts in notebooks\n",
    "# competition data holds kaggle_evaluation/ + aicomp_sdk/ at its root\n",
    "for _c in glob.glob('/kaggle/input/**/kaggle_evaluation', recursive=True):\n",
    "    _root = str(Path(_c).parent)\n",
    "    if _root not in sys.path:\n",
    "        sys.path.insert(0, _root)\n",
    "    print('Dataset root:', _root)\n",
    "    break\n",
    "print('Setup complete')\n",
]

SERVE_CELL = [
    "# Starts the evaluation gateway; the scorer connects and drives AttackAlgorithm.run().\n",
    f"import {GATEWAY_MODULE} as _srv\n",
    "_srv.JEDAttackInferenceServer().serve()\n",
]


def _write_cell() -> list[str]:
    payload = {name: base64.b64encode(
        open(os.path.join(KAGGLE, name), "rb").read()).decode("ascii") for name in FILES}
    # emit deterministic, human-diffable source lines
    lines = [
        "import base64, pathlib\n",
        "\n",
        "FILES = {\n",
    ]
    for name in FILES:
        lines.append(f"    {name!r}: {payload[name]!r},\n")
    lines += [
        "}\n",
        "out = pathlib.Path('/kaggle/working')\n",
        "out.mkdir(parents=True, exist_ok=True)\n",
        "for _name, _b64 in FILES.items():\n",
        "    (out / _name).write_bytes(base64.b64decode(_b64))\n",
        "    print('wrote', out / _name)\n",
    ]
    return lines


def _code(source: list[str]) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": source}


def build_notebook() -> dict:
    return {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": MARKDOWN},
            _code(SETUP_CELL),
            _code(_write_cell()),
            _code(SERVE_CELL),
        ],
        "metadata": {
            "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def kernel_metadata(kernel_id: str) -> dict:
    """Kaggle `kernels push` spec: GPU on, internet OFF, competition data attached."""
    return {
        "id": kernel_id,
        "title": kernel_id.split("/")[-1],
        "code_file": NOTEBOOK_FILENAME,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,          # gpt_oss/gemma need the T4
        "enable_internet": False,    # code-competition requirement
        "competition_sources": [COMPETITION],  # attaches aicomp_sdk + fixtures + evaluator
        "dataset_sources": [],
        "kernel_sources": [],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--kernel-id", default=DEFAULT_KERNEL_ID)
    args = ap.parse_args(argv)

    for name in FILES:
        if not os.path.exists(os.path.join(KAGGLE, name)):
            print(f"build_kaggle_notebook: missing kaggle/{name}")
            return 1

    nb = build_notebook()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(nb, fh, indent=1)

    # push-ready folder for `kaggle kernels push -p dist/submission`
    sub = os.path.join(os.path.dirname(os.path.abspath(args.out)), "submission")
    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(sub, NOTEBOOK_FILENAME), "w", encoding="utf-8") as fh:
        json.dump(nb, fh, indent=1)
    with open(os.path.join(sub, "kernel-metadata.json"), "w", encoding="utf-8") as fh:
        json.dump(kernel_metadata(args.kernel_id), fh, indent=1)

    print(f"build_kaggle_notebook: wrote {args.out}")
    print(f"  push-ready folder: {sub}/  (notebook + kernel-metadata.json, GPU on / internet off)")
    print("  next (you, needs Kaggle API token):")
    print(f"    kaggle kernels push -p {sub}")
    print(f"    kaggle competitions submit -c {COMPETITION} "
          f"-k {args.kernel_id} -v <VERSION> -m \"...\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
