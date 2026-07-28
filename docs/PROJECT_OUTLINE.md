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
- [x] Task 2: GitHub Actions workflow — on push: install, `dvc repro`, evaluation gate,
      upload model + metrics artifacts — COMPLETE 2026-07-27, run 30251369242 green
      (repo: github.com/senthoorneethirajan/enterprise-mlops-platform)
- [x] Task 3: Docker image built + smoke-tested; 3-replica K8s Deployment + Service on
      Colima k3s; `/predict`, `/health`, `/metrics` live — COMPLETE 2026-07-28
- [x] Task 4: canary at ~25% traffic (verified 29:9 over 40 requests); blue/green flip
      + instant rollback both directions; v2 promoted to stable; automated rollback via
      `scripts/canary_guard.sh` — COMPLETE 2026-07-28 (registry alias rollback lands
      with Task 6 promotion tooling)
- Evidence → `docs/evidence/task-02..04/` (CI run logs, endpoint responses, rollback logs)

### Phase 3 — Monitoring & Drift (Tasks 5-6)
- [x] Task 5: Prometheus (+RBAC pod discovery) + Pushgateway + Grafana deployed on k3s;
      provisioned 4-panel dashboard (latency p50/p95, error rate, drift PSI, deployment
      health + canary split); 4 alert rules loaded; verified under live traffic —
      COMPLETE 2026-07-28 (dashboard screenshots for submission: see task-05 README)
- [x] Task 6: PSI drift detector -> Pushgateway -> DataDriftDetected alert; drift-gated
      retraining orchestrator (+ Airflow DAG); gated registry promotion + rollback via
      `production` alias — COMPLETE 2026-07-28
- Evidence → `docs/evidence/task-05..06/` (live-stack proof, baseline no-drift run,
      rollback demo)

### Phase 4 — LLM Integration (Task 7) — COMPLETE 2026-07-28
- [x] RAG pipeline over the platform's own ops docs (`llm/rag/`, local Ollama stack)
- [x] Incident-triage agent with tool-based state gathering (`llm/agents/`) — correct
      decisions on drift-incident vs healthy snapshots
- [x] Prompt management: versioned prompt files, version logged per run
- [x] RAGAS-methodology evaluation with local LLM judge, logged to MLflow
      (faithfulness 0.90 / relevancy 0.90 / correctness 0.88 / context 0.845)
- Evidence → `docs/evidence/task-07/`

### Phase 5 — Failure & Incident Simulation (Tasks 8-9)
- [x] Task 8: bad model deployed to canary (SIMULATE_UNHEALTHY drill) → stuck rollout
      detected → automated rollback in <90s, stable v2 untouched; RCA written including
      a real finding (readiness-based guard masked crash-looping pod during rolling
      update; fixed with rollout gate) — COMPLETE 2026-07-28, `docs/evidence/task-08/`
- [x] Task 9: drift 1.2 injected -> PSI > 0.2 on 3 features -> DataDriftDetected FIRING
      in Prometheus -> automated retraining (gate passed) -> production alias v3 -> v4 —
      COMPLETE 2026-07-28
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

- ~~Docker Desktop~~ — resolved with **Colima** (docker engine + k3s Kubernetes,
  no licensing concerns on a corporate machine): `colima start --cpu 4 --memory 8 --kubernetes`
- ~~GitHub remote repo~~ — live at github.com/senthoorneethirajan/enterprise-mlops-platform
- ~~LLM access~~ — resolved with local **Ollama** (answerer llama3.2:latest, judge
  llama3.1:latest, embeddings nomic-embed-text); no hosted-API credentials needed.
