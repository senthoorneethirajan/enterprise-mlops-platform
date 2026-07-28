# Task 6 Evidence — Drift Detection & Retraining

Collected 2026-07-28.

| File | What it shows |
| --- | --- |
| `baseline_no_drift_run.log` | Fresh live batch (new seed, no shift): max PSI 0.0015 -> "no drift -> retraining skipped (cost awareness)" |
| `registry_rollback_demo.txt` | Registry-based rollback: production alias v4 -> v3 and back, via `src.common.promote` |
| Components | `src/monitoring/drift.py` (PSI detector + Pushgateway export), `src/common/promote.py` (gated promotion / rollback), `scripts/retrain_on_drift.sh` (orchestrator), `airflow/dags/retrain_on_drift_dag.py` (DAG) |
| Executed drift path | see `../task-09/` — the full detect -> alert -> retrain -> promote incident |

## Design

- **Drift monitoring:** PSI per feature (quantile-binned for numerics, frequency-based
  for categoricals) between the DVC-tracked training reference and a live batch.
  Threshold 0.2 (industry convention for "significant shift").
- **Metrics path:** detector pushes `drift_psi{feature=...}` to the Pushgateway;
  Prometheus scrapes it; the `DataDriftDetected` alert and the Grafana drift panel
  consume the same series — one source of truth.
- **Automated retraining:** the orchestrator retrains ONLY on drift (spec's cost
  awareness requirement), reusing the exact same DVC pipeline + evaluation gate as
  CI — no shadow training path.
- **Registry-based promotion:** `promote` refuses models below the evaluation gate,
  then moves the `production` alias; `rollback` restores any earlier version.
  The alias is the serving contract (governance layer).

## Why the DAG isn't executed by a local Airflow

The DAG file mirrors the orchestrator 1:1 (check_drift branch -> retrain -> promote
-> notify). Running an Airflow scheduler locally adds ~700MB of dependencies and a
metadata DB without changing the logic under test, so the orchestration logic is
validated via `scripts/retrain_on_drift.sh` (see task-09 for a real execution) and
the DAG ships ready for the platform's Airflow deployment.
