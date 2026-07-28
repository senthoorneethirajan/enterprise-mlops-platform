"""Generate the synthetic customer churn dataset (deterministic, params-driven).

Stands in for the "Data Sources" box in the architecture diagram so the whole platform
is reproducible offline. Phase 5 reuses this generator with --drift > 0 to simulate
covariate shift for the drift-incident task.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = REPO_ROOT / "data" / "raw" / "churn.csv"


def generate(n_samples: int, seed: int, drift: float = 0.0) -> pd.DataFrame:
    """Build a churn dataset. `drift` shifts feature distributions (0.0 = baseline)."""
    rng = np.random.default_rng(seed)

    tenure = rng.integers(0, 73, n_samples)
    monthly = rng.normal(65 + 15 * drift, 22, n_samples).clip(15, 160)
    tickets = rng.poisson(1.4 + drift, n_samples)
    contract = rng.choice([0, 1, 2], n_samples, p=[0.55, 0.25, 0.20])  # mtm / 1yr / 2yr
    delay = rng.exponential(2.5 + 2 * drift, n_samples)
    usage = rng.gamma(2.2, 24, n_samples)
    total = monthly * np.maximum(tenure, 1) * rng.normal(1.0, 0.05, n_samples)

    # Churn propensity: short tenure, pricey plans, support pain, flexible contracts,
    # and late payments all push towards churn.
    logit = (
        1.5
        - 0.075 * tenure
        + 0.030 * (monthly - 65)
        + 0.45 * tickets
        - 1.10 * contract
        + 0.18 * delay
        - 0.004 * usage
    )
    churn = rng.binomial(1, 1.0 / (1.0 + np.exp(-logit)))

    return pd.DataFrame(
        {
            "tenure_months": tenure,
            "monthly_charges": monthly.round(2),
            "total_charges": total.round(2),
            "num_support_tickets": tickets,
            "contract_type": contract,
            "payment_delay_days": delay.round(1),
            "data_usage_gb": usage.round(1),
            "churn": churn,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drift", type=float, default=None,
                        help="drift intensity override (default: params.yaml data.drift)")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed override (live batches should use a non-training seed)")
    parser.add_argument("--out", type=Path, default=RAW_PATH)
    args = parser.parse_args()

    params = yaml.safe_load((REPO_ROOT / "params.yaml").read_text())["data"]
    drift = params.get("drift", 0.0) if args.drift is None else args.drift
    seed = params["seed"] if args.seed is None else args.seed
    df = generate(params["n_samples"], seed, drift=drift)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"wrote {len(df)} rows -> {args.out} "
          f"(churn rate {df['churn'].mean():.3f}, drift {drift}, seed {seed})")


if __name__ == "__main__":
    main()
