"""Minimal Ollama HTTP client (no extra dependencies — uses requests).

Local-first LLM stack: chosen over hosted APIs so the capstone runs fully offline
on a corporate machine with zero credentials (see docs/PROJECT_OUTLINE.md).
"""
from __future__ import annotations

import os

import requests

BASE_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("OLLAMA_CHAT_MODEL", "llama3.2:1b")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
TIMEOUT = 300


def chat(prompt: str, system: str | None = None, temperature: float = 0.0,
         model: str | None = None) -> str:
    """Single-turn chat completion; temperature 0 for reproducible-ish outputs."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "model": model or CHAT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def embed(texts: list[str]) -> list[list[float]]:
    resp = requests.post(
        f"{BASE_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]
