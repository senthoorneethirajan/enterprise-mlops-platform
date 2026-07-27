# Task 1 Evidence — Experiment Tracking & Versioning

Collected 2026-07-27 on the local machine (Python 3.12.13, mlflow 2.22.5, dvc 3.67.1,
scikit-learn 1.9.0 — full pins in `requirements.lock.txt`).

| File | What it shows |
| --- | --- |
| `dvc_repro_run1.log` | Full pipeline run: generate_data -> preprocess -> train -> evaluate, quality gate passed |
| `dvc_repro_run2_forced.log` | Second run with `dvc repro --force` (everything recomputed from scratch) |
| `metrics.json` | Test metrics from the evaluation stage (test ROC-AUC 0.8625, F1 0.7041) |
| `mlflow_state.json` | Export of the MLflow store: experiment `churn-training`, 2 runs with params/metrics/artifacts, registered model `churn-classifier` versions 1 & 2 |
| `dvc.lock` | DVC lockfile pinning data/model hashes for the exact reproduced state |

## Reproducibility proof

Both runs produced **byte-identical** `reports/metrics.json` (verified with `diff`;
exit code 0) and identical metric values in MLflow (`mlflow_state.json` shows the two
runs side by side). Determinism comes from seeded data generation, a seeded
train/test split, and a seeded RandomForest — all seeds live in `params.yaml`, which
is DVC-tracked and attached to every MLflow run as an artifact along with `dvc.lock`.

Each MLflow run therefore records: hyperparameters, train + CV + test metrics, the
serialized model (also registered in the Model Registry), and the exact pipeline
lockfile that produced it — the full audit trail the spec asks for.

To regenerate this evidence:

```bash
make repro-force
.venv/bin/python -m src.common.registry_report > docs/evidence/task-01/mlflow_state.json
```

MLflow UI screenshots (optional extra): run `make mlflow-ui` and capture the
`churn-training` experiment and `churn-classifier` model pages.
