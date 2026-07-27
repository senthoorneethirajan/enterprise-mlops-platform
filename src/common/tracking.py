"""Shared MLflow configuration for all pipeline stages.

The tracking store is a project-local sqlite database (mlflow/mlflow.db) because the
MLflow Model Registry — needed for versioning, promotion, and rollback (Tasks 1, 6, 8) —
requires a database-backed store. Artifacts land in mlflow/experiments/ per the spec's
repository layout.
"""
from __future__ import annotations

import os
from pathlib import Path

import mlflow

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACKING_URI = f"sqlite:///{REPO_ROOT / 'mlflow' / 'mlflow.db'}"
ARTIFACT_ROOT = REPO_ROOT / "mlflow" / "experiments"
REGISTERED_MODEL_NAME = "churn-classifier"


def setup_mlflow(experiment_name: str) -> str:
    """Point MLflow at the local store and make sure the experiment exists."""
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)
    (REPO_ROOT / "mlflow").mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(tracking_uri)

    client = mlflow.MlflowClient()
    if client.get_experiment_by_name(experiment_name) is None:
        artifact_location = (ARTIFACT_ROOT / experiment_name).as_uri()
        client.create_experiment(experiment_name, artifact_location=artifact_location)
    mlflow.set_experiment(experiment_name)
    return tracking_uri
