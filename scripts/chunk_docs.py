import json
import os
from pathlib import Path

from config import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "data" / "examples"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_FILE = PROCESSED_DIR / "chunks.jsonl"

SUPPORTED_EXTENSIONS = {".md", ".jsonl"}


def get_data_dir() -> Path:
    env_path = os.getenv("LEIF_DATA_DIR")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return DEFAULT_DATA_DIR.resolve()


def chunk_markdown(text: str, source: str, max_chars: int = 1200) -> list[dict]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    index = 0

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(
                    {
                        "id": f"{source}-{index}",
                        "source": source,
                        "text": current,
                    }
                )
                index += 1
            current = paragraph

    if current:
        chunks.append(
            {
                "id": f"{source}-{index}",
                "source": source,
                "text": current,
            }
        )

    return chunks


def chunk_jsonl(path: Path) -> list[dict]:
    chunks = []
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            chunks.append(
                {
                    "id": f"{path.name}-{index}",
                    "source": path.name,
                    "text": json.dumps(item, ensure_ascii=False),
                }
            )
    return chunks


def main() -> None:
    data_dir = get_data_dir()

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    all_chunks = []

    for path in sorted(data_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        if path.suffix.lower() == ".md":
            text = path.read_text(encoding="utf-8")
            all_chunks.extend(chunk_markdown(text, path.name))
        elif path.suffix.lower() == ".jsonl":
            all_chunks.extend(chunk_jsonl(path))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        for chunk in all_chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Data directory: {data_dir}")
    print(f"Chunks written: {len(all_chunks)}")
    print(f"Output file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
