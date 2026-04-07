import json
import os
import urllib.request
from pathlib import Path

from config import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_FILE = ROOT / "data" / "processed" / "chunks.jsonl"
OUTPUT_FILE = ROOT / "data" / "processed" / "embeddings.json"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("LEIF_EMBED_MODEL", "embeddinggemma")


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


def main() -> None:
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(f"Chunks file does not exist: {CHUNKS_FILE}")

    rows = []

    with CHUNKS_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue

            chunk = json.loads(line)
            vector = embed_text(chunk["text"])

            rows.append(
                {
                    "id": chunk["id"],
                    "source": chunk["source"],
                    "text": chunk["text"],
                    "embedding": vector,
                }
            )

    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False)

    print(f"Embedding model: {EMBED_MODEL}")
    print(f"Rows written: {len(rows)}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
