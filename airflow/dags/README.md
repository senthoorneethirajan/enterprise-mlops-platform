# Airflow DAGs

Task 6 deliverable. `retrain_on_drift_dag.py` will orchestrate:

check_drift (PSI on live vs training distributions) -> branch:
  no drift  -> end (cost awareness: retrain only on drift)
  drift     -> dvc repro (retrain + evaluation gate) -> register new model version
            -> promote via MLflow registry alias -> notify
