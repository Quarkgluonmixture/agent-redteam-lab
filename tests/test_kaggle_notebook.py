"""The Kaggle submission notebook is valid, code-comp-shaped, and embeds files verbatim."""

from __future__ import annotations

import base64
import os

import build_kaggle_notebook as bkn


def _all_code(nb) -> str:
    return "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")


def test_notebook_structure():
    nb = bkn.build_notebook()
    assert nb["nbformat"] == 4
    kinds = [c["cell_type"] for c in nb["cells"]]
    assert kinds == ["markdown", "code", "code", "code"]  # setup / write / serve


def test_setup_and_serve_cells_present():
    code = _all_code(bkn.build_notebook())
    assert "/kaggle/input/**/kaggle_evaluation" in code     # setup adds competition data
    assert bkn.GATEWAY_MODULE in code
    assert ".serve()" in code                                # serve() handles both normal + rerun
    assert "run_local_gateway" not in code                   # we never run models locally


def test_placeholder_submission_written_before_serve():
    """A submittable version must output submission.csv; the rerun overwrites it."""
    code = _all_code(bkn.build_notebook())
    assert "submission.csv" in code
    assert "Id,Score" in code
    for row in bkn.SUBMISSION_ROWS:                          # the 4 leaderboard rows
        assert row in code


def test_code_cell_writes_to_kaggle_working():
    code = _all_code(bkn.build_notebook())
    assert "/kaggle/working" in code
    assert "write_bytes" in code


def test_all_adapter_files_embedded_verbatim():
    code = _all_code(bkn.build_notebook())
    for name in bkn.FILES:
        raw = open(os.path.join(bkn.KAGGLE, name), "rb").read()
        b64 = base64.b64encode(raw).decode("ascii")
        assert b64 in code, f"{name} not embedded verbatim"


def test_kernel_metadata_is_code_comp_ready():
    md = bkn.kernel_metadata("quarkgluonmixture/agent-redteam-lab-attack")
    assert md["enable_gpu"] is False           # models run on Kaggle's side during the rerun
    assert md["machine_shape"] == "None"       # CPU notebook
    assert md["docker_image"] == bkn.DOCKER_IMAGE  # standard CPU image
    assert md["enable_internet"] is False      # code-competition requirement
    assert bkn.COMPETITION in md["competition_sources"]
    assert md["code_file"] == bkn.NOTEBOOK_FILENAME
    assert md["id"].startswith("quarkgluonmixture/")


def test_embedded_attack_py_roundtrips():
    """Decoding an embedded payload must reproduce the source file byte-for-byte."""
    code = _all_code(bkn.build_notebook())
    src = open(os.path.join(bkn.KAGGLE, "attack.py"), "rb").read()
    assert base64.b64encode(src).decode("ascii") in code
