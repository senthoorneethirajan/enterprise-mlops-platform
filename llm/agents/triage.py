"""Incident-triage agent (Task 7): reads live platform state through tool functions,
reasons over it with the local LLM, and recommends an action.

Every invocation is logged to MLflow (experiment `llm-agent-triage`) with the prompt
version, model, input state, and decision — the same audit standard as model training.

Usage: python -m llm.agents.triage [--drift-report PATH]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mlflow

from llm import ollama_client
from src.common.promote import REGISTERED_MODEL_NAME  # noqa: F401 (context for readers)
from src.common.tracking import setup_mlflow

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_VERSION = "v1"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / f"triage_{PROMPT_VERSION}.md"
DRIFT_THRESHOLD = 0.2
EXPERIMENT = "llm-agent-triage"


# ---- tools: each reads one slice of real platform state ----

def tool_evaluation_metrics() -> dict:
    return json.loads((REPO_ROOT / "reports" / "metrics.json").read_text())


def tool_drift_report(path: Path) -> dict:
    if not path.exists():
        return {"drift_detected": False, "note": "no drift report available"}
    report = json.loads(path.read_text())
    return {k: report[k] for k in ("psi", "max_psi", "drifted_features", "drift_detected")}


def tool_registry_status() -> dict:
    from mlflow import MlflowClient

    from src.common.promote import ALIAS, _client, _current_alias_version

    client: MlflowClient = _client()
    versions = sorted(
        client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'"),
        key=lambda v: int(v.version),
    )
    return {
        "production_alias": _current_alias_version(client),
        "alias_name": ALIAS,
        "versions": [int(v.version) for v in versions],
    }


def run(drift_report_path: Path) -> dict:
    state = {
        "evaluation_metrics": tool_evaluation_metrics(),
        "drift_report": tool_drift_report(drift_report_path),
        "registry": tool_registry_status(),
    }

    template = PROMPT_PATH.read_text()
    # strip the comment header lines starting with '# prompt:' block
    body = "\n".join(l for l in template.splitlines() if not l.startswith("# "))
    prompt = body.format(threshold=DRIFT_THRESHOLD, state=json.dumps(state, indent=2))

    raw = ollama_client.chat(prompt, temperature=0.0)
    # tolerate models that wrap JSON in code fences
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError:
        decision = {"action": "escalate", "confidence": 0.0,
                    "reasoning": f"non-JSON model output: {raw[:200]}"}

    setup_mlflow(EXPERIMENT)
    with mlflow.start_run(run_name=f"triage-{PROMPT_VERSION}"):
        mlflow.log_params({
            "prompt_version": PROMPT_VERSION,
            "chat_model": ollama_client.CHAT_MODEL,
            "drift_threshold": DRIFT_THRESHOLD,
        })
        mlflow.log_metrics({"confidence": float(decision.get("confidence", 0.0))})
        mlflow.log_dict(state, "input_state.json")
        mlflow.log_dict(decision, "decision.json")
        mlflow.log_artifact(str(PROMPT_PATH))

    return {"state": state, "decision": decision, "prompt_version": PROMPT_VERSION}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drift-report", type=Path,
                        default=REPO_ROOT / "reports" / "drift_report.json")
    args = parser.parse_args()
    print(json.dumps(run(args.drift_report), indent=2))


if __name__ == "__main__":
    main()
