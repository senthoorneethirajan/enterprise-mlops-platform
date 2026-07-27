# Project Outline & Execution Plan

Working plan for completing the Enterprise Unified MLOps Capstone. See
`PROJECT_SPEC.md` for the full requirements. Status legend: [ ] todo, [~] in
progress, [x] done.

## The ML problem we operate

**Customer churn prediction** — a binary classifier predicting whether a telecom-style
customer will churn. Chosen because it matches the "enterprise running predictive systems"
narrative, is tabular/CPU-friendly, and keeps the focus on MLOps rather than modeling.

- Data: synthetic, generated deterministically (seeded) by `src/preprocessing/generate_data.py`.
  No external downloads; fully reproducible; drift can be simulated by shifting feature
  distributions (used in Phase 5).
- Model: scikit-learn RandomForestClassifier (packaged with Pickle per spec; ONNX optional).
- Registry name: `churn-classifier` in the MLflow Model Registry (sqlite-backed store).

## Key design decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| Serving | FastAPI custom API (not TF Serving) | Spec's architecture diagram allows "TF Serving / Custom API"; sklearn model doesn't fit TF Serving |
| MLflow backend | `sqlite:///mlflow/mlflow.db`, artifacts in `mlflow/experiments/` | Registry features (versions, aliases, rollback) require a DB-backed store; keeps everything local |
| DVC pipeline file | `dvc/dvc.yaml` with `wdir: ..` per stage | Honors the spec's prescribed layout while keeping paths root-relative; run with `dvc repro dvc/dvc.yaml` |
| CI workflow | Real file in `.github/workflows/ci.yml`, symlinked from `ci-cd/github-actions.yml` | GitHub only reads `.github/workflows/`; symlink satisfies the spec layout without duplication |
| Kubernetes | Manifests written for any cluster; tested with Docker Desktop K8s or kind | Docker is not installed on this machine yet — install Docker Desktop to run Tasks 3-4 locally |
| Canary | Two Deployments (stable + canary) behind one Service selector, weighted by replica count | Simple, dependency-free canary; documented in k8s/ |

## Phase plan & deliverables checklist

### Phase 1 — ML Lifecycle Foundation (Task 1) — COMPLETE 2026-07-27
- [x] Synthetic data generation stage (seeded, params-driven)
- [x] Preprocessing stage (clean, encode, stratified train/test split)
- [x] Training stage: MLflow logs params/metrics/artifacts, registers model version
      (registry `churn-classifier`, versions 1-2)
- [x] Evaluation stage: test metrics + quality gate (fails pipeline below threshold —
      verified: v0 data failed the gate and blocked the pipeline; current model passes
      with test ROC-AUC 0.8625 / F1 0.7041)
- [x] DVC pipeline (`dvc/dvc.yaml` + `dvc.lock`) wiring all stages
- [x] Reproducibility evidence: two `dvc repro` runs → byte-identical metrics
- [x] Bonus: serving API smoke-tested against the trained model (/health, /predict,
      /metrics all working)
- Evidence → `docs/evidence/task-01/` (run logs, metrics, MLflow state export, dvc.lock)

### Phase 2 — CI/CD for ML (Tasks 2-4)
- [ ] Task 2: GitHub Actions workflow — on push: install, `dvc repro`, evaluation gate,
      upload model + metrics artifacts
- [ ] Task 3: `docker/Dockerfile` for FastAPI serving app; `k8s/deployment.yaml`,
      `k8s/service.yaml`; working `/predict` + `/health` endpoints
- [ ] Task 4: `k8s/canary.yaml`; rollback script/job that flips traffic back and rolls the
      registry alias to the previous version
- Evidence → `docs/evidence/task-02..04/` (CI run logs, endpoint responses, rollback logs)

### Phase 3 — Monitoring & Drift (Tasks 5-6)
- [ ] Task 5: `/metrics` endpoint (prometheus_client) with request count, latency histogram,
      error counter; `monitoring/prometheus/prometheus.yml` scrape config +
      `monitoring/prometheus/alerts.yml`; Grafana dashboard JSON (latency, error rate, drift,
      deployment health panels)
- [ ] Task 6: drift detector (PSI/KS on feature distributions) → alert → retraining pipeline
      (Airflow DAG in `airflow/dags/`) → evaluation → registry promotion (alias update)
- Evidence → `docs/evidence/task-05..06/` (dashboard screenshots, alert config, retraining
      logs, registry version history)

### Phase 4 — LLM Integration (Task 7)
- [ ] RAG pipeline over project/ops docs (`llm/rag/`)
- [ ] Agent workflow (`llm/agents/`) — e.g. incident-triage agent that reads metrics/drift
      reports and recommends actions
- [ ] Prompt management (versioned prompt templates)
- [ ] Evaluation with RAGAS/TruLens (`llm/evaluation/`), results logged to MLflow
- Evidence → `docs/evidence/task-07/`

### Phase 5 — Failure & Incident Simulation (Tasks 8-9)
- [ ] Task 8: deploy an intentionally bad model → canary health check fails → automated
      rollback; write RCA in `docs/evidence/task-08/RCA.md`
- [ ] Task 9: simulate data drift (shifted generator params) → drift alert fires → retraining
      triggered → validation report
- Evidence → `docs/evidence/task-08..09/`

## Milestone order

1. Phase 1 end-to-end locally (now)
2. Git repo + CI workflow (needs GitHub remote to demonstrate push triggers)
3. Docker Desktop install → build image → local K8s deploy (Tasks 3-4)
4. Monitoring stack via docker-compose (Prometheus + Grafana) (Task 5)
5. Drift + retraining automation (Task 6)
6. LLM phase (Task 7) — needs an LLM provider/API key decision
7. Incident simulations + RCA docs (Tasks 8-9)

## External dependencies to sort out

- **Docker Desktop** (not installed) — required for Tasks 3-5, 8
- **GitHub remote repo** — required to show push-triggered CI (Task 2)
- **LLM access** (OpenAI/Bedrock/local Ollama) — required for Task 7 (RAGAS also needs an
  LLM as judge)
