# Kubeflow Pipelines

Placeholder per the spec's repository layout. The training pipeline is expressed with
DVC (dvc/dvc.yaml) and orchestrated by Airflow (airflow/dags/); a KFP v2 pipeline
definition mirroring the same stages can be added here if cluster-native execution is
wanted (compile with `kfp.compiler` and run on a Kubeflow deployment).
