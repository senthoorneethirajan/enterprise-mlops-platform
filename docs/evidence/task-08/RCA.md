# RCA — Simulated Bad Model Deployment (Task 8 Drill)

**Date:** 2026-07-28 · **Severity:** SEV-3 (no customer impact) · **Status:** Resolved

## Summary

A deliberately faulty model version (`v3-bad`, injected via `SIMULATE_UNHEALTHY=1`,
causing `/health` to return 503) was deployed to the canary track. The canary guard
detected the failed rollout and executed an automated rollback. Customer traffic was
served by the stable track (v2) throughout — 0% error rate on the service.

## Timeline (from failure_drill.log)

1. `kubectl apply -f k8s/canary.yaml` + failure env injected — bad pod enters
   CrashLoop/NotReady (readiness probe fails on 503)
2. Canary guard rollout gate: `rollout status` times out (75s) — rollout stuck
3. `ROLLBACK TRIGGERED` — guard deletes the canary Deployment
4. `ROLLBACK COMPLETE` — 100% traffic on stable; service `/health` confirms v2 OK
5. Guard exits 1, signalling the failed rollout to the orchestrating pipeline

## Why traffic was never at risk (defence in depth)

1. **Readiness probe:** the bad pod never passed `/health`, so Kubernetes never
   added it to the Service endpoints — requests never reached it.
2. **Replica weighting:** even a "ready but degraded" canary would only see ~25%
   of traffic (1 of 4 pods).
3. **Canary guard:** automated detection + rollback bounded the exposure window.

## What the first drill attempt exposed (real finding)

The initial guard implementation polled `readyReplicas >= spec.replicas`. During a
**rolling update**, Kubernetes keeps the old healthy canary pod running while the new
bad pod crash-loops — so `readyReplicas` stayed 1/1 and the guard reported *healthy*
while the new version was failing (see the first drill attempt, where the guard
concluded "safe to promote").

**Root cause:** health was measured at the Deployment level, not the rollout level —
the metric answered "is something ready?" instead of "did the new version become ready?"

**Fix:** the guard now runs a rollout gate first (`kubectl rollout status --timeout`),
which fails when the new ReplicaSet never becomes fully available, then falls through
to steady-state readiness polling. Re-run of the drill: detection + rollback in <90s.

## Action items

- [x] Guard gates on rollout completion, not raw readiness (scripts/canary_guard.sh)
- [x] Drill re-run green (failure_drill.log)
- [ ] Alert on `kube_deployment_status_replicas_unavailable` for the canary track
      when the monitoring stack lands (Task 5)
- [ ] Registry-level rollback (alias reassignment) tooling arrives with Task 6
      promotion scripts
