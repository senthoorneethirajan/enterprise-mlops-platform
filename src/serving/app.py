"""FastAPI inference service for the churn classifier (Tasks 3 & 5).

Endpoints
---------
- POST /predict — churn probability for one customer
- GET  /health  — liveness/readiness; used by K8s probes and canary health checks
- GET  /metrics — Prometheus metrics: request counts, latency histogram, error counts

Ops notes
---------
- MODEL_PATH / FEATURE_NAMES_PATH env vars point at the packaged model (see docker/).
- MODEL_VERSION env var tags responses + metrics so canary vs stable traffic is separable.
- SIMULATE_UNHEALTHY=1 makes /health return 503 — used by the Task 8 deployment-failure
  drill to trigger canary failure detection and automated rollback.
"""
from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.environ.get("MODEL_PATH", REPO_ROOT / "models" / "model.pkl"))
FEATURE_NAMES_PATH = Path(
    os.environ.get("FEATURE_NAMES_PATH", REPO_ROOT / "models" / "feature_names.json")
)
MODEL_VERSION = os.environ.get("MODEL_VERSION", "dev")

REQUESTS = Counter(
    "inference_requests_total",
    "Inference requests",
    ["endpoint", "status", "model_version"],
)
LATENCY = Histogram(
    "inference_latency_seconds",
    "Inference latency in seconds",
    ["endpoint", "model_version"],
)

_state: dict = {"model": None, "features": []}


@asynccontextmanager
async def lifespan(_: FastAPI):
    _state["model"] = joblib.load(MODEL_PATH)
    _state["features"] = json.loads(FEATURE_NAMES_PATH.read_text())
    yield


app = FastAPI(title="churn-classifier", version=MODEL_VERSION, lifespan=lifespan)


class Customer(BaseModel):
    tenure_months: int = Field(ge=0, le=1200)
    monthly_charges: float = Field(ge=0)
    total_charges: float = Field(ge=0)
    num_support_tickets: int = Field(ge=0)
    payment_delay_days: float = Field(ge=0)
    data_usage_gb: float = Field(ge=0)
    contract_type: int = Field(ge=0, le=2, description="0=month-to-month, 1=1yr, 2=2yr")


class Prediction(BaseModel):
    churn_probability: float
    churn_predicted: bool
    model_version: str


@app.get("/health")
def health() -> dict:
    if os.environ.get("SIMULATE_UNHEALTHY") == "1":
        raise HTTPException(status_code=503, detail="simulated failure (Task 8 drill)")
    if _state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/predict", response_model=Prediction)
def predict(customer: Customer) -> Prediction:
    start = time.perf_counter()
    try:
        row = customer.model_dump()
        contract = row.pop("contract_type")
        row[f"contract_{contract}"] = 1
        frame = pd.DataFrame([row]).reindex(columns=_state["features"], fill_value=0)

        proba = float(_state["model"].predict_proba(frame)[0, 1])
        REQUESTS.labels("/predict", "200", MODEL_VERSION).inc()
        return Prediction(
            churn_probability=round(proba, 4),
            churn_predicted=proba >= 0.5,
            model_version=MODEL_VERSION,
        )
    except Exception:
        REQUESTS.labels("/predict", "500", MODEL_VERSION).inc()
        raise
    finally:
        LATENCY.labels("/predict", MODEL_VERSION).observe(time.perf_counter() - start)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
