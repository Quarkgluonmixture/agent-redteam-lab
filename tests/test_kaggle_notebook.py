"""The Kaggle submission notebook is valid and embeds the adapter files verbatim."""

from __future__ import annotations

import base64
import os

import build_kaggle_notebook as bkn


def test_notebook_structure():
    nb = bkn.build_notebook()
    assert nb["nbformat"] == 4
    kinds = [c["cell_type"] for c in nb["cells"]]
    assert kinds == ["markdown", "code"]


def test_code_cell_writes_to_kaggle_working():
    nb = bkn.build_notebook()
    code = "".join(nb["cells"][1]["source"])
    assert "/kaggle/working" in code
    assert "write_bytes" in code


def test_all_adapter_files_embedded_verbatim():
    nb = bkn.build_notebook()
    code = "".join(nb["cells"][1]["source"])
    for name in bkn.FILES:
        raw = open(os.path.join(bkn.KAGGLE, name), "rb").read()
        b64 = base64.b64encode(raw).decode("ascii")
        assert b64 in code, f"{name} not embedded verbatim"


def test_kernel_metadata_is_code_comp_ready():
    md = bkn.kernel_metadata("quarkgluonmixture/agent-redteam-lab-attack")
    assert md["enable_gpu"] is True            # gpt_oss/gemma need the T4
    assert md["enable_internet"] is False      # code-competition requirement
    assert bkn.COMPETITION in md["competition_sources"]
    assert md["code_file"] == bkn.NOTEBOOK_FILENAME
    assert md["id"].startswith("quarkgluonmixture/")


def test_embedded_attack_py_roundtrips():
    """Decoding an embedded payload must reproduce the source file byte-for-byte."""
    nb = bkn.build_notebook()
    code = "".join(nb["cells"][1]["source"])
    src = open(os.path.join(bkn.KAGGLE, "attack.py"), "rb").read()
    assert base64.b64decode(base64.b64encode(src)).decode("utf-8").startswith('"""Kaggle attack')
    assert base64.b64encode(src).decode("ascii") in code
