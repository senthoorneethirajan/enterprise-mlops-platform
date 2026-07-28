# Task 9 Evidence — Drift Incident Simulation

Collected 2026-07-28. Full closed loop: simulated drift -> detection -> alert ->
automated retraining -> gate -> registry promotion.

| File | What it shows |
| --- | --- |
| `drift_report.json` | Detector output: PSI per feature — num_support_tickets 0.624, monthly_charges 0.587, payment_delay_days 0.354 (all > 0.2); drift_detected=true |
| `prometheus_drift_alert.txt` | `drift_psi` series live in Prometheus and `DataDriftDetected` alert in **firing** state |
| `incident_run.log` | Orchestrator run: detection -> pipeline repointed at new data world -> `dvc repro` retrain -> quality gate passed -> promotion |
| `registry_before.json` / `registry_after.json` | `production` alias moved v3 -> v4 (new version registered from the retraining run) |

## Incident narrative

1. **Drift injected:** live batch generated with drift level 1.2 (new seed 778) —
   pricier plans, more support tickets, longer payment delays. Base churn rate moved
   0.362 -> 0.561.
2. **Detection:** PSI exceeded 0.2 on three features; detector exited 2 and pushed
   `drift_psi` to the Pushgateway.
3. **Alert:** Prometheus `DataDriftDetected` went active -> firing (captured).
4. **Automated retraining:** orchestrator repointed the pipeline at the new data
   world and ran the standard DVC pipeline — same code path as CI, including the
   evaluation gate (new model: test ROC-AUC 0.8586, F1 0.8055 — gate passed).
5. **Validation + promotion:** `promote` re-verified the gate and moved the
   `production` alias v3 -> v4. Registry state before/after captured.

The retrained model's F1 (0.806) is notably higher than v3's (0.702) on the drifted
world — expected, since the drifted world has a higher churn base rate.
