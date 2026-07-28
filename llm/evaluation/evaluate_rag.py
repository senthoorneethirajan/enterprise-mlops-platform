"""RAG evaluation harness (Task 7) — RAGAS-methodology metrics with a local judge.

Metrics (all LLM-as-judge with the local Ollama model, scored 0-1):
- faithfulness:      is the answer supported by the retrieved contexts?
- answer_relevancy:  does the answer address the question?
- answer_correctness: does the answer agree with the ground truth?
- context_relevancy: fraction of retrieved chunks relevant to the question.

Why not the official `ragas` package: it pulls a heavy langchain dependency tree and
defaults to hosted judge models; this harness applies the same methodology fully
offline. Scores are logged to MLflow (experiment `llm-rag-evaluation`) next to the
classical ML experiments — one tracking store for the whole platform.

Usage: python -m llm.evaluation.evaluate_rag
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import mlflow

from llm import ollama_client
from llm.rag.pipeline import ask
from src.common.tracking import setup_mlflow

EVAL_SET = Path(__file__).resolve().parent / "eval_set.json"
REPORT = Path(__file__).resolve().parent / "rag_eval_report.json"
EXPERIMENT = "llm-rag-evaluation"

# The judge should be a stronger model than the answerer where possible.
# (Discovered empirically: a 3B judge scored trivially-supported answers as 0.)
JUDGE_MODEL = os.environ.get("OLLAMA_JUDGE_MODEL", ollama_client.CHAT_MODEL)

JUDGE_SYSTEM = (
    "You are a careful evaluator. Reply with ONLY a decimal rating between 0.0 and "
    "1.0 (for example: 1.0, 0.8, 0.3). No words, no explanation."
)


def _judge(prompt: str) -> float:
    raw = ollama_client.chat(prompt, system=JUDGE_SYSTEM, temperature=0.0,
                             model=JUDGE_MODEL)
    match = re.search(r"(?:\d+\.\d+|[01])", raw)
    return min(max(float(match.group()) if match else 0.0, 0.0), 1.0)


def score_case(case: dict) -> dict:
    result = ask(case["question"])
    answer = result["answer"]
    contexts = "\n\n".join(c["text"] for c in result["contexts"])

    faithfulness = _judge(
        f"Context:\n{contexts}\n\nAnswer:\n{answer}\n\n"
        "Rate 0.0-1.0 how well the Answer's claims are supported by the Context "
        "(1.0 = every claim supported, 0.0 = contradicted or fabricated). Rating:"
    )
    answer_relevancy = _judge(
        f"Question: {case['question']}\n\nAnswer: {answer}\n\n"
        "Rate 0.0-1.0 how directly the Answer addresses the Question "
        "(1.0 = fully on-topic, 0.0 = unrelated). Rating:"
    )
    answer_correctness = _judge(
        f"Reference answer: {case['ground_truth']}\n\nCandidate answer: {answer}\n\n"
        "Rate 0.0-1.0 how well the Candidate agrees with the Reference on key facts "
        "(1.0 = same facts, 0.0 = contradicts). Rating:"
    )
    per_context = [
        _judge(
            f"Question: {case['question']}\n\nPassage:\n{c['text']}\n\n"
            "Rate 0.0-1.0 how relevant this Passage is for answering the Question "
            "(1.0 = directly relevant, 0.0 = unrelated). Rating:"
        )
        for c in result["contexts"]
    ]
    context_relevancy = sum(per_context) / len(per_context) if per_context else 0.0

    return {
        "question": case["question"],
        "answer": answer,
        "retrieved_sources": [c["source"] for c in result["contexts"]],
        "scores": {
            "faithfulness": round(faithfulness, 3),
            "answer_relevancy": round(answer_relevancy, 3),
            "answer_correctness": round(answer_correctness, 3),
            "context_relevancy": round(context_relevancy, 3),
        },
    }


def main() -> None:
    cases = json.loads(EVAL_SET.read_text())
    results = [score_case(c) for c in cases]

    aggregate = {
        metric: round(sum(r["scores"][metric] for r in results) / len(results), 3)
        for metric in results[0]["scores"]
    }
    report = {
        "chat_model": ollama_client.CHAT_MODEL,
        "embed_model": ollama_client.EMBED_MODEL,
        "judge_model": JUDGE_MODEL,
        "n_cases": len(results),
        "aggregate": aggregate,
        "results": results,
    }
    REPORT.write_text(json.dumps(report, indent=2))

    setup_mlflow(EXPERIMENT)
    with mlflow.start_run(run_name="rag-eval"):
        mlflow.log_params({
            "chat_model": ollama_client.CHAT_MODEL,
            "embed_model": ollama_client.EMBED_MODEL,
            "judge_model": JUDGE_MODEL,
            "n_cases": len(results),
            "methodology": "RAGAS-style, local LLM judge",
        })
        mlflow.log_metrics(aggregate)
        mlflow.log_artifact(str(EVAL_SET))
        mlflow.log_artifact(str(REPORT))

    print(json.dumps({"aggregate": aggregate, "report": str(REPORT)}, indent=2))


if __name__ == "__main__":
    main()
