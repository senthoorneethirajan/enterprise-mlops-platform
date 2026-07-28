# Task 4 Evidence — Safe Deployment Strategy

Collected 2026-07-28 on the local Colima k3s cluster (Kubernetes v1.35.0+k3s1).

| File | What it shows |
| --- | --- |
| `traffic_split_40_requests.txt` | 40 in-cluster requests through the Service: 29 answered by v1 (stable), 9 by v2 (canary) — the ~25% replica-weighted canary split (plus 2 requests during pod churn) |
| `canary_bluegreen_demo.txt` | Full lifecycle: healthy-canary guard check -> blue/green flip to v2 (10/10 responses green) -> instant selector rollback to v1 (10/10 blue) -> promotion of v2 to stable -> canary retired |
| `../task-08/failure_drill.log` | Automated rollback on failure (shared with Task 8's drill) |
| Config | `k8s/canary.yaml` (canary track), `k8s/service.yaml` (selector-based traffic control), `scripts/canary_guard.sh` (automated rollback) |

## Mechanisms demonstrated

- **Canary:** stable (3 replicas) + canary (1 replica) behind one Service selector —
  ~25% traffic to the new version, confirmed empirically.
- **Blue/green:** scale green to full size, flip the Service `track` selector — 100%
  cutover in one patch; rollback is the same patch reversed (verified both directions).
- **Automated rollback on failure:** `scripts/canary_guard.sh` gates on rollout
  completion then steady-state readiness; on failure it deletes the canary and exits
  non-zero. Exercised for real in the Task 8 drill.
- **Model version in play:** v2 was a genuine retrain (params.yaml iteration,
  registry version 3), not a relabelled image.
