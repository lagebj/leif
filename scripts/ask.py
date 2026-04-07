import json
import math
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_FILE = ROOT / "prompts" / "system.txt"
EMBEDDINGS_FILE = ROOT / "data" / "processed" / "embeddings.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("LEIF_CHAT_MODEL", "leif")
EMBED_MODEL = os.getenv("LEIF_EMBED_MODEL", "embeddinggemma")


def load_system_prompt() -> str:
    if not SYSTEM_FILE.exists():
        raise FileNotFoundError(f"System prompt file does not exist: {SYSTEM_FILE}")
    return SYSTEM_FILE.read_text(encoding="utf-8").strip()


def load_embeddings() -> list[dict]:
    if not EMBEDDINGS_FILE.exists():
        raise FileNotFoundError(f"Embeddings file does not exist: {EMBEDDINGS_FILE}")
    with EMBEDDINGS_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def embed_text(text: str) -> list[float]:
    payload = json.dumps(
        {
            "model": EMBED_MODEL,
            "input": text,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url=f"{OLLAMA_BASE_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read().decode("utf-8"))

    embeddings = data.get("embeddings")
    if not embeddings or not isinstance(embeddings, list):
        raise ValueError("No embeddings returned from Ollama")

    return embeddings[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def retrieve_context(question: str, rows: list[dict], top_k: int = 5) -> list[dict]:
    question_embedding = embed_text(question)

    scored = []
    for row in rows:
        score = cosine_similarity(question_embedding, row["embedding"])
        scored.append((score, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in scored[:top_k]]


def build_user_prompt(question: str, context_rows: list[dict]) -> str:
    context_blocks = []
    for row in context_rows:
        context_blocks.append(f"[Source: {row['source']}]\n{row['text']}")

    context_text = "\n\n---\n\n".join(context_blocks)

    return f"""Use the context below when relevant. Do not quote it mechanically. Use it to strengthen reasoning and phrasing.

Context:
{context_text}

Question:
{question}
"""


def chat(system_prompt: str, user_prompt: str) -> str:
    payload = json.dumps(
        {
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url=f"{OLLAMA_BASE_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read().decode("utf-8"))

    message = data.get("message", {})
    content = message.get("content")
    if not content:
        raise ValueError("No response content returned from Ollama")

    return content.strip()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python3 scripts/ask.py "your question here"')

    question = sys.argv[1]

    system_prompt = load_system_prompt()
    rows = load_embeddings()
    context_rows = retrieve_context(question, rows, top_k=5)
    user_prompt = build_user_prompt(question, context_rows)
    answer = chat(system_prompt, user_prompt)

    print("\n=== Retrieved context ===\n")
    for row in context_rows:
        print(f"- {row['source']} :: {row['id']}")

    print("\n=== Answer ===\n")
    print(answer)


if __name__ == "__main__":
    main()
