# Task 7 Evidence — LLM Pipeline

Collected 2026-07-28. Fully local stack (Ollama): answerer `llama3.2:latest` (3B),
judge `llama3.1:latest` (8B), embeddings `nomic-embed-text` — zero hosted-API
credentials, appropriate for a corporate machine.

| File | What it shows |
| --- | --- |
| `llm_pipeline_transcript.txt` | Grounded RAG answer with retrieved sources + triage agent runs on two real scenarios (drift incident -> `retrain` @ 0.8 confidence; healthy state -> `no_action` @ 0.8) |
| `rag_eval_report.json` | Per-question and aggregate evaluation: faithfulness 0.90, answer_relevancy 0.90, answer_correctness 0.88, context_relevancy 0.845 (5-question eval set) |
| Code | `llm/rag/pipeline.py` (ingest/chunk/embed/retrieve/generate), `llm/agents/triage.py` (+ versioned prompt `llm/agents/prompts/triage_v1.md`), `llm/evaluation/evaluate_rag.py` |
| Logged experiments | MLflow experiments `llm-agent-triage` and `llm-rag-evaluation` in the same tracking store as classical training (params: models + prompt version; metrics: confidence / eval scores; artifacts: input state, decisions, eval set, report) |

## Spec mapping

- **RAG pipeline:** corpus = the platform's own operational docs (spec, plan, RCAs,
  evidence READMEs); markdown-aware chunking; cosine retrieval over local embeddings;
  answer generation constrained to retrieved context.
- **Agent workflow:** the triage agent gathers state through three tools (evaluation
  metrics, drift report, registry status), reasons with the LLM, and returns a
  structured action recommendation — validated on a real incident snapshot and a
  healthy snapshot with correct, opposite decisions.
- **Prompt management:** prompts are versioned files (`prompts/triage_v1.md`) with a
  copy-on-change policy; the version is logged with every MLflow run.
- **Evaluation (RAGAS methodology):** faithfulness, answer relevancy, answer
  correctness, context relevancy via LLM-as-judge, logged to MLflow. The official
  `ragas` package was intentionally not used (heavy langchain dependency tree +
  hosted-judge defaults); the methodology is replicated offline.

## A finding worth reading

The first evaluation run scored faithfulness 0.1 despite visibly grounded answers.
Root cause: the 3B judge model couldn't follow the rating rubric (it returned a flat
`0` even for a trivially supported answer — verified with a minimal probe). Fix:
stronger 8B judge + a clearer rubric with an explicit "Rating:" cue. Lesson recorded:
**evaluate your evaluator** — judge choice is part of the eval design, and the judge
model is now a logged parameter of every eval run.
