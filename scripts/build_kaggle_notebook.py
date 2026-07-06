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
# The four leaderboard rows the scored rerun fills in (2 models x 2 guardrails).
SUBMISSION_ROWS = ("gpt_oss_public", "gpt_oss_private", "gemma_public", "gemma_private")
# Standard CPU Kaggle image (NOT the BYOD/GPU image). The submission notebook never runs the
# target models — during the scored rerun Kaggle's OWN gateway drives gpt_oss/gemma and overwrites
# submission.csv. So no GPU, no models, no internet needed on our side. Pinned to the image a
# verified working submission used (matches the top-voted starter's env).
DOCKER_IMAGE = ("gcr.io/kaggle-images/python@sha256:"
                "dafd4ce5668bbf1ad422e4c109e0f18c9623c3a7c7f48b0235f13142755c40b9")

MARKDOWN = [
    "# agent-redteam-lab — Kaggle submission\n",
    "\n",
    "Code-competition submission. Three cells: (1) put the competition data on the path,\n",
    "(2) write `attack.py` + siblings to `/kaggle/working/`, (3) write a placeholder\n",
    "`submission.csv` and start the inference server.\n",
    "\n",
    "On a normal Save & Run, `serve()` just starts the server and returns — the placeholder\n",
    "`submission.csv` is the required output file. During Kaggle's scored rerun, `serve()`\n",
    "blocks and Kaggle's gateway connects, loads `attack.py`, drives it against the real\n",
    "`gpt_oss`/`gemma` targets, and **overwrites** `submission.csv` with the real scores.\n",
    "This notebook never runs the target models itself (no GPU / no internet needed).\n",
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
    "# 1) Placeholder submission.csv so the committed version carries the required output file.\n",
    "#    Kaggle's gateway OVERWRITES it with real scores during the scored rerun.\n",
    "from pathlib import Path\n",
    f"_rows = {list(SUBMISSION_ROWS)!r}\n",
    "_csv = 'Id,Score\\n' + ''.join(f'{r},0.0\\n' for r in _rows)\n",
    "Path('/kaggle/working').mkdir(parents=True, exist_ok=True)\n",
    "(Path('/kaggle/working') / 'submission.csv').write_text(_csv)\n",
    "print('wrote placeholder submission.csv')\n",
    "# 2) Start the inference server. On a normal run serve() starts the server and returns;\n",
    "#    during the scored rerun it blocks and Kaggle's gateway drives attack.py against the\n",
    "#    real gpt_oss/gemma targets (no models run here).\n",
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
    """Kaggle `kernels push` spec: CPU only, internet OFF, competition data attached.

    No GPU / no models: the notebook only serves the inference server. The target models
    (gpt_oss/gemma) are run by Kaggle's gateway during the scored rerun, not here. Mirrors
    a verified working submission's metadata (top-voted starter uses the same env).
    """
    return {
        "id": kernel_id,
        "title": kernel_id.split("/")[-1],
        "code_file": NOTEBOOK_FILENAME,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": False,          # models run on Kaggle's side during the rerun, not here
        "enable_tpu": False,
        "machine_shape": "None",      # CPU notebook (T4/P100 not needed and P100 is rejected)
        "docker_image": DOCKER_IMAGE,  # standard CPU image
        "enable_internet": False,     # code-competition requirement
        "competition_sources": [COMPETITION],  # attaches aicomp_sdk + fixtures + evaluator
        "dataset_sources": [],
        "kernel_sources": [],
        "model_sources": [],
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
    print(f"  push-ready folder: {sub}/  (notebook + kernel-metadata.json, CPU / internet off)")
    print("  next (you, needs Kaggle API token):")
    print(f"    kaggle kernels push -p {sub}")
    print(f"    kaggle competitions submit -c {COMPETITION} "
          f"-k {args.kernel_id} -v <VERSION> -m \"...\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
