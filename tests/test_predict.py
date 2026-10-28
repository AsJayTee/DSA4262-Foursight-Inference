"""Tests of the prediction script, as a reviewer runs it.

    pip install ".[dev]"
    python -m pytest -q
"""

from __future__ import annotations

import gzip
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from m6a import registry
from m6a.data import iter_sites
from m6a.evaluation import validate_submission

SAMPLE = ROOT / "data" / "sample" / "sample.json.gz"


def test_sample_dataset_is_readable():
    sites = list(iter_sites(SAMPLE))
    assert len(sites) == 1000
    assert all(site.reads.shape[1] == 9 for site in sites)


def test_shipped_model_is_registered():
    meta = json.loads((ROOT / "models" / "final" / "meta.json").read_text())
    assert meta["model"] in registry.available("models"), registry.failures("models")


def test_predict_on_sample_gives_a_valid_submission(tmp_path):
    output = tmp_path / "predictions.csv"
    run = subprocess.run(
        [sys.executable, "scripts/predict.py", "--model", "models/final",
         "--input", str(SAMPLE), "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stderr
    assert "1,000 sites scored" in run.stdout
    problems = validate_submission(output, SAMPLE)
    assert problems == [], "\n".join(problems)


def test_validator_catches_a_broken_submission(tmp_path):
    json_path = tmp_path / "tiny.json.gz"
    with gzip.open(json_path, "wt") as out:
        out.write(json.dumps({"ENST00000000001": {"100": {"GGACTTA": [[0.01, 4.0, 110.0] * 3]}}}) + "\n")
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"transcript_id": ["ENST99999999999"], "transcript_position": [1], "score": [1.7]}).to_csv(bad, index=False)
    problems = validate_submission(bad, json_path)
    assert any("outside [0, 1]" in p for p in problems)
    assert any("no prediction" in p for p in problems)


def test_prediction_needs_no_heavy_packages():
    # The script must run with only numpy, pandas and scikit-learn installed.
    probe = (
        "import sys; sys.path.insert(0, 'src');"
        "import m6a.data, m6a.evaluation; from m6a import registry; registry.available('models');"
        "print(','.join(m for m in ('torch', 'tensorflow', 'lightgbm', 'wandb', 'boto3') if m in sys.modules))"
    )
    run = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "", f"pulled in: {run.stdout.strip()}"
