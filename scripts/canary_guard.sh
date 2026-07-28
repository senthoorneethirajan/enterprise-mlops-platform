#!/usr/bin/env bash
# Automated canary rollback on failure (Tasks 4 & 8).
#
# Polls the canary Deployment's readiness. Readiness is driven by the /health probe,
# so a bad model (crashing, failing health, SIMULATE_UNHEALTHY=1 drill) drops
# readyReplicas. After 3 consecutive unhealthy checks the canary Deployment is
# deleted — traffic instantly reverts 100% to the stable track — and the script
# exits non-zero so CI/orchestration can flag the failed rollout.
#
# Usage: scripts/canary_guard.sh   (env overrides: CANARY_DEPLOY, CHECKS, INTERVAL)
set -euo pipefail

NAMESPACE=${NAMESPACE:-default}
DEPLOY=${CANARY_DEPLOY:-churn-serving-canary}
CHECKS=${CHECKS:-6}
INTERVAL=${INTERVAL:-10}
ROLLOUT_TIMEOUT=${ROLLOUT_TIMEOUT:-75s}

# Phase 1: rollout gate.
# Lesson from the first failure drill: during a rolling update the OLD healthy pod
# keeps readyReplicas at the desired count, masking a crash-looping new version.
# `rollout status` fails when the rollout is stuck, catching exactly that case.
ts=$(date '+%Y-%m-%dT%H:%M:%S')
echo "$ts rollout gate: waiting up to $ROLLOUT_TIMEOUT for $DEPLOY rollout to complete"
if ! kubectl -n "$NAMESPACE" rollout status deploy "$DEPLOY" --timeout="$ROLLOUT_TIMEOUT"; then
  ts=$(date '+%Y-%m-%dT%H:%M:%S')
  echo "$ts ROLLBACK TRIGGERED: rollout stuck (new version never became ready)"
  kubectl -n "$NAMESPACE" delete deploy "$DEPLOY"
  echo "$ts ROLLBACK COMPLETE: canary deleted, 100% traffic on stable track"
  exit 1
fi

# Phase 2: steady-state readiness polling.
failures=0
for i in $(seq 1 "$CHECKS"); do
  desired=$(kubectl -n "$NAMESPACE" get deploy "$DEPLOY" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo 0)
  ready=$(kubectl -n "$NAMESPACE" get deploy "$DEPLOY" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
  ready=${ready:-0}
  ts=$(date '+%Y-%m-%dT%H:%M:%S')

  if [ "${desired:-0}" -eq 0 ] || [ "$ready" -lt "$desired" ]; then
    failures=$((failures + 1))
    echo "$ts check $i/$CHECKS: UNHEALTHY ready=$ready/$desired (consecutive: $failures)"
  else
    failures=0
    echo "$ts check $i/$CHECKS: healthy ready=$ready/$desired"
  fi

  if [ "$failures" -ge 3 ]; then
    echo "$ts ROLLBACK TRIGGERED: canary unhealthy for $failures consecutive checks"
    kubectl -n "$NAMESPACE" delete deploy "$DEPLOY"
    echo "$ts ROLLBACK COMPLETE: canary deleted, 100% traffic on stable track"
    exit 1
  fi
  sleep "$INTERVAL"
done

echo "canary healthy after $CHECKS checks — safe to promote"
