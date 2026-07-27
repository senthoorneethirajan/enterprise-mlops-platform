# LLM Integration (Phase 4, Task 7)

Planned layout:

- `rag/` — RAG pipeline over the platform's own ops documentation (spec, runbooks,
  RCA docs): ingestion, chunking, embedding index, retrieval + generation chain.
- `agents/` — agent workflow: an incident-triage agent that reads current metrics,
  drift reports, and registry state, then recommends actions (e.g. rollback vs retrain).
- `evaluation/` — RAGAS/TruLens evaluation harness; scores logged to MLflow so LLM
  experiments share the same tracking store as the classical ML system.

Open decision (needed before implementation): LLM provider — OpenAI API, AWS Bedrock,
or local Ollama. RAGAS needs an LLM judge, so the choice applies to evaluation too.
Prompts are versioned files under `agents/prompts/` — prompt management deliverable.
