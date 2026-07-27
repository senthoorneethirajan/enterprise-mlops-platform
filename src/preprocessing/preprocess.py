"""Clean the raw churn data and split it into model-ready train/test sets."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW = REPO_ROOT / "data" / "raw" / "churn.csv"
OUT_DIR = REPO_ROOT / "data" / "processed"


def main() -> None:
    params = yaml.safe_load((REPO_ROOT / "params.yaml").read_text())["preprocess"]
    df = pd.read_csv(RAW)

    # Basic hygiene: dedupe, clip impossible values, fill any gaps with medians.
    df = df.drop_duplicates()
    df["payment_delay_days"] = df["payment_delay_days"].clip(lower=0)
    df["total_charges"] = df["total_charges"].clip(lower=0)
    df = df.fillna(df.median(numeric_only=True))

    # One-hot the categorical contract_type so the serving schema stays explicit.
    df = pd.get_dummies(df, columns=["contract_type"], prefix="contract", dtype=int)

    train_df, test_df = train_test_split(
        df,
        test_size=params["test_size"],
        random_state=params["seed"],
        stratify=df["churn"],
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(OUT_DIR / "train.csv", index=False)
    test_df.to_csv(OUT_DIR / "test.csv", index=False)
    print(f"train={len(train_df)} test={len(test_df)} features={df.shape[1] - 1}")


if __name__ == "__main__":
    main()
