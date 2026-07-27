# Task 2 Evidence — CI Pipeline for ML Training

Collected 2026-07-27.

| Item | Where |
| --- | --- |
| CI pipeline YAML | `.github/workflows/ci.yml` (symlinked from `ci-cd/github-actions.yml`) |
| Successful training log from CI | `ci_run_30251369242.log` (full job log, 827 lines) |
| Live run | https://github.com/senthoorneethirajan/enterprise-mlops-platform/actions/runs/30251369242 |

## What the run demonstrates

- **Triggered on code push:** run 30251369242 fired automatically on push of commit
  `883542c` to `main` (event: `push`).
- **Automated training:** the `train-and-validate` job ran `dvc repro dvc/dvc.yaml`
  on a clean `ubuntu-latest` runner — data generation, preprocessing, training with
  MLflow tracking, model registration (`churn-classifier` version 1 in the runner's
  local store).
- **Evaluation validation:** the evaluate stage enforced the quality gate and passed
  ("quality gate passed" in the log). A model below thresholds exits non-zero and
  fails the job — verified locally in Task 1 where a weak model blocked the pipeline.
- **Artifact logging:** the job uploaded the `model-and-metrics` artifact
  (model.pkl, feature_names.json, metrics.json, dvc.lock). Job completed in 1m23s.

## Observed cross-platform note

CI metrics: test ROC-AUC `0.862513`, F1 `0.706306`.
Local (macOS ARM) metrics: test ROC-AUC `0.862516`, F1 `0.704104`.

Runs are byte-identical when repeated on the *same* platform (see Task 1 evidence);
the small cross-platform delta comes from floating-point/BLAS differences between
macOS ARM and the Linux x86 runner — a known property of numerical ML workloads and
the reason the platform pins exact dependency versions and treats the CI environment
as the canonical one for release decisions.
