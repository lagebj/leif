import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from config import load_dotenv
from ask import load_system_prompt, load_embeddings, retrieve_context, build_user_prompt, chat

load_dotenv()

HOST = "127.0.0.1"
PORT = 8787

print("Loading system prompt...")
SYSTEM_PROMPT = load_system_prompt()
print("Loading embeddings...")
EMBEDDING_ROWS = load_embeddings()
print(f"Loaded {len(EMBEDDING_ROWS)} embedding rows")


def extract_message(payload: dict) -> str:
    if isinstance(payload.get("message"), str) and payload["message"].strip():
        return payload["message"].strip()

    if isinstance(payload.get("input"), str) and payload["input"].strip():
        return payload["input"].strip()

    context = payload.get("context")
    if isinstance(context, dict):
        title = context.get("title")
        description = context.get("description")
        parts = []
        if isinstance(title, str) and title.strip():
            parts.append(title.strip())
        if isinstance(description, str) and description.strip():
            parts.append(description.strip())
        if parts:
            return "\n\n".join(parts)

    raise ValueError("No usable message found in request payload")


class LeifHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[http] {self.address_string()} - {format % args}")

    def _send_json(self, status: int, body: dict) -> None:
        response = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()

    def do_POST(self):
        print(f"POST {self.path}")

        if self.path not in ("/invoke", "/webhook/adapter"):
            self._send_json(404, {"error": "not_found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length)
            print(f"Raw body: {raw.decode('utf-8') if raw else '<empty>'}")

            payload = json.loads(raw.decode("utf-8")) if raw else {}
            message = extract_message(payload)
            print(f"Extracted message: {message}")

            print("Retrieving context...")
            context_rows = retrieve_context(message, EMBEDDING_ROWS, top_k=5)
            print(f"Retrieved {len(context_rows)} context rows")

            print("Building prompt...")
            user_prompt = build_user_prompt(message, context_rows)

            print("Calling chat model...")
            answer = chat(SYSTEM_PROMPT, user_prompt)
            print("Chat model returned successfully")

            self._send_json(
                200,
                {
                    "ok": True,
                    "message": answer,
                    "sources": [
                        {"source": row["source"], "id": row["id"]}
                        for row in context_rows
                    ],
                },
            )

        except Exception as exc:
            print("Request handling failed:")
            traceback.print_exc()
            self._send_json(500, {"ok": False, "error": str(exc)})

    def do_GET(self):
        print(f"GET {self.path}")

        if self.path == "/health":
            self._send_json(200, {"ok": True, "service": "leif"})
            return

        self._send_json(404, {"error": "not_found"})


def main() -> None:
    server = HTTPServer((HOST, PORT), LeifHandler)
    print(f"Leif server listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
