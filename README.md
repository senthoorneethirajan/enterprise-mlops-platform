# Enterprise Unified MLOps Platform

Capstone implementation for the Skillfyme "MLOps with Agentic AI Masters Program" —
an end-to-end MLOps platform operating a customer-churn prediction service with
experiment tracking, reproducible pipelines, CI/CD, Kubernetes serving, monitoring,
drift-driven retraining, and an LLM integration layer.

- Full requirements: [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md)
- Execution plan & status: [`docs/PROJECT_OUTLINE.md`](docs/PROJECT_OUTLINE.md)
- Submission evidence: [`docs/evidence/`](docs/evidence/)

## Quickstart

```bash
make install          # create .venv and install pinned dependencies
source .venv/bin/activate
make repro            # run the DVC pipeline: generate -> preprocess -> train -> evaluate
make mlflow-ui        # browse experiments at http://127.0.0.1:5001
make serve            # inference API at http://127.0.0.1:8000/docs
```

## The ML system

Binary churn classifier (RandomForest) over a deterministic synthetic telecom dataset —
generated in-repo so every stage is reproducible offline and drift can be simulated on
demand (`python -m src.preprocessing.generate_data --drift 1.5`).

Pipeline (DVC, defined in [`dvc/dvc.yaml`](dvc/dvc.yaml)):

```
generate_data -> preprocess -> train -> evaluate
                              (MLflow)   (quality gate)
```

- **Tracking/Registry:** MLflow on sqlite (`mlflow/mlflow.db`), artifacts under
  `mlflow/experiments/`, model registered as `churn-classifier`.
- **Quality gate:** `evaluate` fails the pipeline (and CI) if test ROC-AUC or F1 drop
  below the thresholds in `params.yaml`.
- **Packaging:** pickle (`models/model.pkl`) consumed by the FastAPI serving container.

## Repository layout

Follows the structure prescribed by the spec (docs/PROJECT_SPEC.md section 4):
`data/` and `models/` are DVC-managed, `src/` holds pipeline + serving code, `dvc/`,
`mlflow/`, `airflow/`, `kubeflow/`, `docker/`, `k8s/`, `monitoring/`, `ci-cd/`, `llm/`
map one-to-one to the platform components.

## Phase status

| Phase | Task | Status |
| --- | --- | --- |
| 1 ML Lifecycle Foundation | 1 Experiment tracking & versioning | Done (evidence in docs/evidence/task-01) |
| 2 CI/CD for ML | 2 CI pipeline / 3 Packaging & deploy / 4 Safe deployment | Scaffolded |
| 3 Monitoring & Drift | 5 Monitoring / 6 Drift & retraining | Scaffolded |
| 4 LLM Integration | 7 LLM pipeline | Planned |
| 5 Failure & Incident Simulation | 8 Deployment failure / 9 Drift incident | Planned |
