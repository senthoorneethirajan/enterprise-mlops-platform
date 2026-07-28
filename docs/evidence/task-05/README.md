# Task 5 Evidence — Production Monitoring

Collected 2026-07-28 on the Colima k3s cluster.

| Item | Where |
| --- | --- |
| Live-stack proof (Prometheus queries, loaded alerts, Grafana API) | `monitoring_stack_evidence.txt` |
| Alert configuration | `monitoring/prometheus/alerts.yml` (HighErrorRate, HighLatencyP95, ServingDown, DataDriftDetected) |
| Dashboard definition | `monitoring/grafana/churn-serving-dashboard.json` |
| Stack manifests + deploy script | `monitoring/k8s-monitoring.yaml`, `scripts/deploy_monitoring.sh` |
| Dashboard screenshots (spec requirement) | `screenshots/` — see instructions below |

## What runs where

- **Prometheus** (`monitoring` namespace) discovers serving pods via the
  `prometheus.io/*` annotations, evaluates the four alert rules, and scrapes the
  **Pushgateway** (which receives `drift_psi` from the Task 6 drift detector).
- **Grafana** is provisioned with the Prometheus datasource and the
  "Churn Serving — Production Monitoring" dashboard covering all four
  spec-required areas: model latency (p50/p95), error rate, drift indicators
  (PSI per feature with 0.2 threshold line), deployment health (targets up +
  canary traffic split by model_version).

## Verified live (see monitoring_stack_evidence.txt)

- 3/3 serving targets `up`
- p95 latency ~25ms under generated traffic (240 requests)
- Traffic attributed to `model_version="v2"` (the promoted stable)
- 5xx rate 0; all 4 alert rules loaded and in `inactive` (healthy) state

## Taking the required screenshots

```bash
kubectl -n monitoring port-forward svc/grafana 3000:3000
# open http://localhost:3000/d/churn-serving  (anonymous viewer enabled)
```

Capture (1) the full dashboard under traffic, (2) the drift panel during the Task 9
incident (PSI spike above the red 0.2 line). Save into `screenshots/`.
