"""Export the MLflow tracking + registry state as JSON (evidence/audit utility).

Used to capture governance evidence for Tasks 1, 6, and 8:
    python -m src.common.registry_report > docs/evidence/task-XX/mlflow_state.json
"""
from __future__ import annotations

import json

from mlflow import MlflowClient

from src.common.tracking import DEFAULT_TRACKING_URI

import mlflow


def collect_state() -> dict:
    mlflow.set_tracking_uri(DEFAULT_TRACKING_URI)
    client = MlflowClient()

    state: dict = {"experiments": [], "registered_models": []}
    for exp in client.search_experiments():
        runs = client.search_runs([exp.experiment_id], order_by=["start_time ASC"])
        state["experiments"].append(
            {
                "name": exp.name,
                "artifact_location": exp.artifact_location,
                "runs": [
                    {
                        "run_id": r.info.run_id,
                        "status": r.info.status,
                        "params": r.data.params,
                        "metrics": {k: round(v, 6) for k, v in r.data.metrics.items()},
                        "artifacts": [a.path for a in client.list_artifacts(r.info.run_id)],
                    }
                    for r in runs
                ],
            }
        )

    for rm in client.search_registered_models():
        versions = client.search_model_versions(f"name='{rm.name}'")
        state["registered_models"].append(
            {
                "name": rm.name,
                "aliases": dict(rm.aliases) if rm.aliases else {},
                "versions": [
                    {"version": v.version, "run_id": v.run_id, "status": v.status}
                    for v in sorted(versions, key=lambda v: int(v.version))
                ],
            }
        )
    return state


if __name__ == "__main__":
    print(json.dumps(collect_state(), indent=2))
