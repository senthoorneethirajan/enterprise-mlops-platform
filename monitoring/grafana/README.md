# Grafana dashboards

Task 5 deliverable. The dashboard JSON will live here (`churn-serving-dashboard.json`)
with panels required by the spec's observability expectations:

1. Model latency (p50/p95 from `inference_latency_seconds`)
2. Error rate (`inference_requests_total{status=~"5.."}` vs total)
3. Drift indicators (`drift_psi` per feature, from the Task 6 drift detector)
4. Deployment health (`up`, ready replicas, stable vs canary request split by
   `model_version` label)

Screenshots of the live dashboards go to `docs/evidence/task-05/`.
