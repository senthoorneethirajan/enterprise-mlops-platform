"""Data drift detector (Task 6): PSI between the training reference and a live batch.

- Reference: data/raw/churn.csv — the data the current model was trained on (DVC-tracked).
- Live batch: any CSV with the same raw schema (default data/live/current_batch.csv).
- Metric: Population Stability Index per feature. Conventional reading:
    < 0.1 stable · 0.1-0.2 moderate shift · > 0.2 significant shift (retrain).
- Outputs: reports/drift_report.json, drift_psi gauges pushed to the Prometheus
  Pushgateway (feeds the Grafana drift panel + DataDriftDetected alert).
- Exit codes: 0 = no drift · 2 = drift detected (orchestrator triggers retraining).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE = REPO_ROOT / "data" / "raw" / "churn.csv"
REPORT = REPO_ROOT / "reports" / "drift_report.json"

NUMERIC = [
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "num_support_tickets",
    "payment_delay_days",
    "data_usage_gb",
]
CATEGORICAL = ["contract_type"]
THRESHOLD = 0.2
_EPS = 1e-6


def psi_numeric(ref: np.ndarray, cur: np.ndarray, bins: int = 10) -> float:
    edges = np.quantile(ref, np.linspace(0.0, 1.0, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    edges = np.unique(edges)
    ref_pct = np.histogram(ref, edges)[0] / len(ref)
    cur_pct = np.histogram(cur, edges)[0] / len(cur)
    ref_pct = np.clip(ref_pct, _EPS, None)
    cur_pct = np.clip(cur_pct, _EPS, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def psi_categorical(ref: pd.Series, cur: pd.Series) -> float:
    cats = sorted(set(ref.unique()) | set(cur.unique()))
    ref_pct = ref.value_counts(normalize=True).reindex(cats).fillna(0).to_numpy()
    cur_pct = cur.value_counts(normalize=True).reindex(cats).fillna(0).to_numpy()
    ref_pct = np.clip(ref_pct, _EPS, None)
    cur_pct = np.clip(cur_pct, _EPS, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def push_metrics(psi: dict[str, float], drifted: bool) -> str | None:
    """Push drift_psi gauges to the Pushgateway if PUSHGATEWAY_URL is set."""
    gateway = os.environ.get("PUSHGATEWAY_URL")
    if not gateway:
        return None
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

    registry = CollectorRegistry()
    g = Gauge("drift_psi", "PSI vs training reference", ["feature"], registry=registry)
    for feature, value in psi.items():
        g.labels(feature).set(value)
    flag = Gauge("drift_detected", "1 if any feature PSI above threshold", registry=registry)
    flag.set(1 if drifted else 0)
    push_to_gateway(gateway, job="drift-detector", registry=registry)
    return gateway


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path,
                        default=REPO_ROOT / "data" / "live" / "current_batch.csv")
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    args = parser.parse_args()

    ref = pd.read_csv(REFERENCE)
    cur = pd.read_csv(args.batch)

    psi = {c: psi_numeric(ref[c].to_numpy(), cur[c].to_numpy()) for c in NUMERIC}
    psi.update({c: psi_categorical(ref[c], cur[c]) for c in CATEGORICAL})

    drifted_features = sorted(f for f, v in psi.items() if v > args.threshold)
    drifted = bool(drifted_features)

    # Simulation-harness glue (NOT detector logic): in production, retraining would
    # consume the live data-lake window directly. Offline, we estimate the synthetic
    # generator's drift knob from the observed mean shift so `dvc repro` can
    # regenerate an equivalent "new world" for retraining.
    est = (cur["monthly_charges"].mean() - ref["monthly_charges"].mean()) / 15.0
    suggested_drift_level = round(float(np.clip(est, 0.0, 3.0)), 2)

    report = {
        "reference": str(REFERENCE.relative_to(REPO_ROOT)),
        "batch": str(args.batch),
        "n_reference": int(len(ref)),
        "n_batch": int(len(cur)),
        "threshold": args.threshold,
        "psi": {k: round(v, 4) for k, v in psi.items()},
        "max_psi": round(max(psi.values()), 4),
        "drifted_features": drifted_features,
        "drift_detected": drifted,
        "simulated_ingestion": {"suggested_drift_level": suggested_drift_level},
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

    gateway = push_metrics(psi, drifted)
    if gateway:
        print(f"pushed drift_psi metrics to {gateway}", file=sys.stderr)

    sys.exit(2 if drifted else 0)


if __name__ == "__main__":
    main()
