"""RAG pipeline over the platform's own operational documentation (Task 7).

Corpus: project spec, execution plan, RCAs, and evidence READMEs — so the LLM layer
answers real operational questions about this platform ("what is the rollback
procedure?", "which features drifted?").

Usage (from repo root, venv active, ollama running):
    python -m llm.rag.pipeline build              # ingest + chunk + embed -> index
    python -m llm.rag.pipeline ask "question"     # retrieve top-k + generate answer
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from llm import ollama_client

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = Path(__file__).resolve().parent / "index.json"
CORPUS_GLOBS = [
    "README.md",
    "docs/*.md",
    "docs/evidence/*/README.md",
    "docs/evidence/task-08/RCA.md",
    "llm/README.md",
    "monitoring/grafana/README.md",
]
TOP_K = 4

ANSWER_SYSTEM = (
    "You are the on-call assistant for an enterprise MLOps platform. Answer ONLY "
    "from the provided context. If the context does not contain the answer, say so. "
    "Be concise and specific."
)


def _chunk(text: str, source: str, max_chars: int = 900) -> list[dict]:
    """Split on markdown headings, then pack paragraphs up to max_chars."""
    chunks: list[dict] = []
    section = ""
    buf: list[str] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if len(body) > 80:  # skip trivial fragments
            chunks.append({"source": source, "section": section, "text": body})
        buf.clear()

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            section = line.lstrip("# ").strip()
        buf.append(line)
        if sum(len(x) + 1 for x in buf) > max_chars:
            flush()
    flush()
    return chunks


def build() -> None:
    docs: list[dict] = []
    for pattern in CORPUS_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            rel = str(path.relative_to(REPO_ROOT))
            docs.extend(_chunk(path.read_text(), rel))

    embeddings = ollama_client.embed([d["text"] for d in docs])
    INDEX_PATH.write_text(json.dumps({
        "embed_model": ollama_client.EMBED_MODEL,
        "chunks": docs,
        "embeddings": embeddings,
    }))
    print(f"indexed {len(docs)} chunks from {len(set(d['source'] for d in docs))} files "
          f"-> {INDEX_PATH.relative_to(REPO_ROOT)}")


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    index = json.loads(INDEX_PATH.read_text())
    matrix = np.array(index["embeddings"])
    matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    q = np.array(ollama_client.embed([question])[0])
    q = q / np.linalg.norm(q)
    scores = matrix @ q
    order = np.argsort(scores)[::-1][:k]
    return [
        {**index["chunks"][i], "score": round(float(scores[i]), 4)}
        for i in order
    ]


def ask(question: str) -> dict:
    contexts = retrieve(question)
    context_block = "\n\n".join(
        f"[{i + 1}] ({c['source']} — {c['section']})\n{c['text']}"
        for i, c in enumerate(contexts)
    )
    answer = ollama_client.chat(
        f"Context:\n{context_block}\n\nQuestion: {question}\nAnswer:",
        system=ANSWER_SYSTEM,
    )
    return {"question": question, "answer": answer, "contexts": contexts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    ask_p = sub.add_parser("ask")
    ask_p.add_argument("question")
    args = parser.parse_args()

    if args.command == "build":
        build()
    else:
        print(json.dumps(ask(args.question), indent=2))


if __name__ == "__main__":
    main()
