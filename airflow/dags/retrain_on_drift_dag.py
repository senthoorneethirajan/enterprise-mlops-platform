"""Airflow DAG: drift-gated automated retraining (Task 6).

Mirrors scripts/retrain_on_drift.sh (the locally-executed equivalent — see
docs/evidence/task-06/README.md for why the logic is validated via the script
rather than a local Airflow deployment).

Flow (cost awareness: retraining runs ONLY when drift is detected):

    check_drift -> [no_drift -> done]
                -> [drift    -> retrain (dvc repro, includes evaluation gate)
                             -> promote (registry alias update)
                             -> notify]
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator

REPO = "{{ var.value.get('mlops_repo_path', '/opt/mlops/enterprise-mlops-platform') }}"


def _check_drift(**_) -> str:
    """Exit 0 = stable, exit 2 = drift. Branch accordingly."""
    proc = subprocess.run(
        ["python", "-m", "src.monitoring.drift"],
        cwd="/opt/mlops/enterprise-mlops-platform",
    )
    if proc.returncode == 2:
        return "retrain"
    if proc.returncode == 0:
        return "no_drift"
    raise RuntimeError(f"drift detector failed rc={proc.returncode}")


with DAG(
    dag_id="retrain_on_drift",
    description="Drift-gated retraining with registry promotion",
    schedule="0 */6 * * *",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["mlops", "task-06"],
) as dag:
    check_drift = BranchPythonOperator(task_id="check_drift", python_callable=_check_drift)

    no_drift = EmptyOperator(task_id="no_drift")

    retrain = BashOperator(
        task_id="retrain",
        bash_command=f"cd {REPO} && dvc repro dvc/dvc.yaml",
    )

    promote = BashOperator(
        task_id="promote",
        bash_command=f"cd {REPO} && python -m src.common.promote promote",
    )

    notify = BashOperator(
        task_id="notify",
        bash_command="echo 'retraining complete, production alias updated'",
    )

    done = EmptyOperator(task_id="done", trigger_rule="none_failed_min_one_success")

    check_drift >> no_drift >> done
    check_drift >> retrain >> promote >> notify >> done
