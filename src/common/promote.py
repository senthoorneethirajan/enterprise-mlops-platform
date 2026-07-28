"""Model governance CLI (Tasks 6 & 8): registry-based promotion and rollback.

The `production` alias on the `churn-classifier` registered model is the single
source of truth for which version is blessed for serving.

Usage:
    python -m src.common.promote status
    python -m src.common.promote promote                # newest gated model -> production
    python -m src.common.promote rollback [--to-version N]   # registry rollback
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mlflow
import yaml
from mlflow import MlflowClient

from src.common.tracking import DEFAULT_TRACKING_URI, REGISTERED_MODEL_NAME

REPO_ROOT = Path(__file__).resolve().parents[2]
ALIAS = "production"


def _client() -> MlflowClient:
    mlflow.set_tracking_uri(DEFAULT_TRACKING_URI)
    return MlflowClient()


def _current_alias_version(client: MlflowClient) -> int | None:
    try:
        return int(client.get_model_version_by_alias(REGISTERED_MODEL_NAME, ALIAS).version)
    except Exception:
        return None


def status() -> None:
    client = _client()
    current = _current_alias_version(client)
    versions = sorted(
        client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'"),
        key=lambda v: int(v.version),
    )
    print(json.dumps({
        "model": REGISTERED_MODEL_NAME,
        "production_alias": current,
        "versions": [{"version": int(v.version), "run_id": v.run_id} for v in versions],
    }, indent=2))


def promote() -> None:
    client = _client()

    # Governance gate: only promote a model whose evaluation passed the thresholds.
    gate = yaml.safe_load((REPO_ROOT / "params.yaml").read_text())["evaluate"]
    metrics = json.loads((REPO_ROOT / "reports" / "metrics.json").read_text())
    if metrics["test_roc_auc"] < gate["min_roc_auc"] or metrics["test_f1"] < gate["min_f1"]:
        print(f"REFUSED: metrics below gate ({metrics})", file=sys.stderr)
        sys.exit(1)

    run_id = (REPO_ROOT / "models" / "run_id.txt").read_text().strip()
    candidates = [
        v for v in client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
        if v.run_id == run_id
    ]
    if not candidates:
        print(f"REFUSED: no registered version for run {run_id}", file=sys.stderr)
        sys.exit(1)
    target = max(int(v.version) for v in candidates)

    previous = _current_alias_version(client)
    client.set_registered_model_alias(REGISTERED_MODEL_NAME, ALIAS, str(target))
    print(json.dumps({
        "action": "promote",
        "model": REGISTERED_MODEL_NAME,
        "alias": ALIAS,
        "previous_version": previous,
        "new_version": target,
        "run_id": run_id,
        "gated_on": {k: metrics[k] for k in ("test_roc_auc", "test_f1")},
    }, indent=2))


def rollback(to_version: int | None) -> None:
    client = _client()
    current = _current_alias_version(client)
    if current is None:
        print("REFUSED: no production alias set", file=sys.stderr)
        sys.exit(1)
    target = to_version if to_version is not None else current - 1
    if target < 1:
        print("REFUSED: no earlier version to roll back to", file=sys.stderr)
        sys.exit(1)
    client.get_model_version(REGISTERED_MODEL_NAME, str(target))  # existence check
    client.set_registered_model_alias(REGISTERED_MODEL_NAME, ALIAS, str(target))
    print(json.dumps({
        "action": "rollback",
        "model": REGISTERED_MODEL_NAME,
        "alias": ALIAS,
        "previous_version": current,
        "new_version": target,
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("promote")
    rb = sub.add_parser("rollback")
    rb.add_argument("--to-version", type=int, default=None)
    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "promote":
        promote()
    else:
        rollback(args.to_version)


if __name__ == "__main__":
    main()
