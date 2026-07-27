"""Train the churn classifier with full MLflow tracking + registry integration (Task 1).

Logs parameters, metrics, and artifacts to the project-local MLflow store, registers the
model as a new version of `churn-classifier`, and packages the model with pickle
(spec: Packaging = Pickle / ONNX) for the Docker/K8s serving path.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import mlflow
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import cross_val_score

from src.common.tracking import REGISTERED_MODEL_NAME, setup_mlflow

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAIN_CSV = REPO_ROOT / "data" / "processed" / "train.csv"
MODEL_DIR = REPO_ROOT / "models"
EXPERIMENT = "churn-training"


def main() -> None:
    params = yaml.safe_load((REPO_ROOT / "params.yaml").read_text())["train"]
    setup_mlflow(EXPERIMENT)

    df = pd.read_csv(TRAIN_CSV)
    X, y = df.drop(columns=["churn"]), df["churn"]

    model = RandomForestClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        min_samples_leaf=params["min_samples_leaf"],
        random_state=params["seed"],
        n_jobs=-1,
    )

    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_param("n_train_rows", len(df))

        cv_auc = cross_val_score(model, X, y, cv=3, scoring="roc_auc")
        model.fit(X, y)
        train_pred = model.predict(X)
        train_proba = model.predict_proba(X)[:, 1]

        metrics = {
            "cv_roc_auc_mean": float(cv_auc.mean()),
            "cv_roc_auc_std": float(cv_auc.std()),
            "train_accuracy": float(accuracy_score(y, train_pred)),
            "train_f1": float(f1_score(y, train_pred)),
            "train_roc_auc": float(roc_auc_score(y, train_proba)),
        }
        mlflow.log_metrics(metrics)

        # Pickle packaging for the serving container + a machine-readable schema.
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_DIR / "model.pkl")
        (MODEL_DIR / "feature_names.json").write_text(json.dumps(list(X.columns)))
        (MODEL_DIR / "run_id.txt").write_text(run.info.run_id)

        # Log to MLflow + register a new model version (governance/audit trail).
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=REGISTERED_MODEL_NAME,
            input_example=X.head(2),
        )

        # Auditability: attach the exact params and DVC lockfile that produced this run.
        mlflow.log_artifact(str(REPO_ROOT / "params.yaml"))
        lockfile = REPO_ROOT / "dvc" / "dvc.lock"
        if lockfile.exists():
            mlflow.log_artifact(str(lockfile))

        print(f"run_id={run.info.run_id}")
        print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
