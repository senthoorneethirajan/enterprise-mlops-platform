PY  := .venv/bin/python
DVC := .venv/bin/dvc

.PHONY: venv install repro repro-force mlflow-ui serve clean

venv:
	python3 -m venv .venv

install: venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

# Reproduce the full ML pipeline (generate -> preprocess -> train -> evaluate).
# Venv activation matters: stage commands call `python`, which must resolve to .venv
# so runs use the locked dependency set (in CI the runner python has the same pins).
repro:
	. .venv/bin/activate && dvc repro dvc/dvc.yaml

repro-force:
	. .venv/bin/activate && dvc repro --force dvc/dvc.yaml

# Experiment tracking UI (http://127.0.0.1:5001)
mlflow-ui:
	.venv/bin/mlflow ui --backend-store-uri sqlite:///mlflow/mlflow.db --port 5001

# Local inference API (http://127.0.0.1:8000/docs)
serve:
	.venv/bin/uvicorn src.serving.app:app --host 0.0.0.0 --port 8000

clean:
	rm -rf data/processed/* models/* reports/*
