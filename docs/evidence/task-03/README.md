# Task 3 Evidence — Model Packaging & Deployment

Collected 2026-07-27/28 on the local Colima k3s cluster.

| File | What it shows |
| --- | --- |
| `docker_build_v1.log` | Docker build of the serving image (pickle-packaged model + FastAPI, non-root user, healthcheck) |
| `k8s_deployment_evidence.txt` | 3/3 pods Running with readiness/liveness probes, Service up, live `/health` + `/predict` responses through the Service |

## Highlights

- **Packaging:** model trained by the DVC pipeline is pickled (`models/model.pkl`)
  and baked into the image with serving deps pinned exactly to the training
  environment (`docker/requirements-serving.txt` == `requirements.lock.txt` subset),
  so predictions are bit-identical container vs local (verified: 0.9961 both).
- **Deployment:** `k8s/deployment.yaml` + `k8s/service.yaml` on Kubernetes
  (k3s via Colima — Docker Desktop avoided for licensing reasons).
- **Endpoint:** `/predict` returns churn probability + model version; `/health`
  drives probes; `/metrics` exposes Prometheus series (used in Task 5).
