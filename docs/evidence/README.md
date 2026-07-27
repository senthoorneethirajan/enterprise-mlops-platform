# Evidence Locker

Every task in the spec requires submitted evidence ("Expected Outcome"). Collect it here,
one folder per task, so the final submission is a matter of zipping this directory.

| Folder    | Task                              | Required evidence                                        |
| --------- | --------------------------------- | -------------------------------------------------------- |
| `task-01/` | Experiment Tracking & Versioning | MLflow experiment logs/screenshots, DVC pipeline files, proof of reproducible training (two identical runs) |
| `task-02/` | CI Pipeline for ML Training      | CI pipeline YAML, successful training logs from CI        |
| `task-03/` | Model Packaging & Deployment     | Dockerfile, deployment manifests, successful inference endpoint (request/response capture) |
| `task-04/` | Safe Deployment Strategy         | Canary configuration, rollback validation logs            |
| `task-05/` | Production Monitoring            | Grafana dashboard screenshots, alert configuration        |
| `task-06/` | Drift Detection & Retraining     | Drift alerts, retraining logs, registry version update    |
| `task-07/` | LLM Pipeline                     | LLM pipeline code refs, evaluation metrics, logged experiments |
| `task-08/` | Deployment Failure Simulation    | Failure logs, RCA documentation                           |
| `task-09/` | Drift Incident Simulation        | Drift report, retraining validation                       |

Tip: prefer plain-text logs and JSON exports over screenshots where possible — they diff and
review better — but the spec explicitly asks for dashboard screenshots in Task 5.
