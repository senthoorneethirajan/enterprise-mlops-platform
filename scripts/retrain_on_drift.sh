#!/usr/bin/env bash
# Drift-gated retraining orchestrator (Task 6) — the locally-executed equivalent of
# airflow/dags/retrain_on_drift_dag.py.
#
#   1. Run the drift detector against the latest live batch.
#   2. No drift  -> exit (cost awareness: no unnecessary retraining).
#   3. Drift     -> repoint the pipeline at the new data world, `dvc repro`
#                   (retrain + evaluation gate), then registry promotion.
#
# Usage: scripts/retrain_on_drift.sh [batch_csv]
set -uo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate

BATCH=${1:-data/live/current_batch.csv}

echo "== [1/3] drift check: $BATCH vs training reference =="
python -m src.monitoring.drift --batch "$BATCH"
rc=$?

if [ "$rc" -eq 0 ]; then
  echo "== RESULT: no drift -> retraining skipped (cost awareness) =="
  exit 0
elif [ "$rc" -ne 2 ]; then
  echo "== ERROR: drift detector failed rc=$rc ==" >&2
  exit "$rc"
fi

echo "== [2/3] DRIFT DETECTED -> automated retraining =="
LEVEL=$(python -c "import json; print(json.load(open('reports/drift_report.json'))['simulated_ingestion']['suggested_drift_level'])")
echo "   simulated ingestion: pointing pipeline at new data world (drift level $LEVEL)"
python - "$LEVEL" <<'EOF'
import sys, pathlib, yaml
p = pathlib.Path("params.yaml")
d = yaml.safe_load(p.read_text())
d["data"]["drift"] = float(sys.argv[1])
p.write_text(yaml.safe_dump(d, sort_keys=False))
EOF

if ! dvc repro dvc/dvc.yaml; then
  echo "== ERROR: retraining or evaluation gate FAILED -> no promotion ==" >&2
  exit 1
fi

echo "== [3/3] registry promotion =="
python -m src.common.promote promote
echo "== RESULT: retraining complete, production alias updated =="
