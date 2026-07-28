#!/usr/bin/env bash
# Deploy/refresh the Task 5 monitoring stack (Prometheus + Pushgateway + Grafana).
# Idempotent: configs are re-created from the files in monitoring/ on every run.
set -euo pipefail
cd "$(dirname "$0")/.."

kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

kubectl -n monitoring create configmap prometheus-config \
  --from-file=prometheus.yml=monitoring/prometheus/prometheus-k8s.yml \
  --from-file=alerts.yml=monitoring/prometheus/alerts.yml \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n monitoring create configmap grafana-datasources \
  --from-file=monitoring/grafana/datasource.yml \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n monitoring create configmap grafana-dashboard-provider \
  --from-file=monitoring/grafana/dashboard-provider.yml \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n monitoring create configmap grafana-dashboards \
  --from-file=monitoring/grafana/churn-serving-dashboard.json \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f monitoring/k8s-monitoring.yaml

kubectl -n monitoring rollout status deploy/prometheus --timeout=180s
kubectl -n monitoring rollout status deploy/pushgateway --timeout=180s
kubectl -n monitoring rollout status deploy/grafana --timeout=180s

echo "monitoring stack ready:"
echo "  Prometheus: kubectl -n monitoring port-forward svc/prometheus 9090:9090"
echo "  Grafana:    kubectl -n monitoring port-forward svc/grafana 3000:3000  (dashboard: churn-serving)"
