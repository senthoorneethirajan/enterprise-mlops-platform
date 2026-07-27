"""Evaluate the trained model on the held-out test set and enforce the quality gate.

This is the "evaluation validation" step required by Task 2: it exits non-zero when the
model misses the thresholds in params.yaml, which fails the DVC pipeline and therefore
the CI run — bad models never progress towards deployment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import mlflow
import pandas as pd
import yaml
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.common.tracking import setup_mlflow

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_CSV = REPO_ROOT / "data" / "processed" / "test.csv"
MODEL_PATH = REPO_ROOT / "models" / "model.pkl"
RUN_ID_FILE = REPO_ROOT / "models" / "run_id.txt"
REPORT = REPO_ROOT / "reports" / "metrics.json"
EXPERIMENT = "churn-training"


def main() -> None:
    params = yaml.safe_load((REPO_ROOT / "params.yaml").read_text())["evaluate"]
    setup_mlflow(EXPERIMENT)

    df = pd.read_csv(TEST_CSV)
    X, y = df.drop(columns=["churn"]), df["churn"]
    model = joblib.load(MODEL_PATH)

    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)

    metrics = {
        "test_accuracy": float(accuracy_score(y, pred)),
        "test_precision": float(precision_score(y, pred)),
        "test_recall": float(recall_score(y, pred)),
        "test_f1": float(f1_score(y, pred)),
        "test_roc_auc": float(roc_auc_score(y, proba)),
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))

    # Log test metrics onto the training run so each model has one audit trail.
    if RUN_ID_FILE.exists():
        with mlflow.start_run(run_id=RUN_ID_FILE.read_text().strip()):
            mlflow.log_metrics(metrics)

    failures = []
    if metrics["test_roc_auc"] < params["min_roc_auc"]:
        failures.append(f"roc_auc {metrics['test_roc_auc']:.4f} < {params['min_roc_auc']}")
    if metrics["test_f1"] < params["min_f1"]:
        failures.append(f"f1 {metrics['test_f1']:.4f} < {params['min_f1']}")

    if failures:
        print("QUALITY GATE FAILED: " + "; ".join(failures), file=sys.stderr)
        sys.exit(1)
    print("quality gate passed")


if __name__ == "__main__":
    main()
