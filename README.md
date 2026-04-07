# Leif

Leif is a local AI assistant framework built for grounded, principle-driven reasoning.

It is designed to run locally with Ollama and to be shaped by a private or public knowledge base of principles, heuristics, examples, and case patterns.

## What this repo is

This public repo contains:

- Ollama model configuration
- system prompt files
- local retrieval scripts
- evaluation scaffolding
- example data only

This repo does not contain any private or sensitive source material.

## Architecture

Leif is split into two parts:

- **public repo**: code, prompts, config, eval files, example data
- **private data folder**: your real principles, notes, examples, rewrites, and case material

The scripts in this repo are designed to read from a path defined in an environment variable.

## Repo structure

```text
leif/
├── .env.example
├── .gitignore
├── README.md
├── data/
│   ├── examples/
│   │   ├── sample-heuristics.md
│   │   ├── sample-principles.md
│   │   └── sample-rewrites.jsonl
│   └── processed/
├── eval/
│   ├── eval_cases.jsonl
│   └── rubric.md
├── ollama/
│   └── Modelfile
├── prompts/
│   ├── system.txt
│   └── system.txt.nice
└── scripts/
    ├── ask.py
    ├── chunk_docs.py
    └── embed_docs.py
    └── eval.py
```

## Requirements

* macOS or Linux
* Python 3.10+
* Ollama installed locally
* one local chat model pulled
* one local embedding model pulled

## Local setup

### 1. Clone the repo

```bash
git clone https://github.com/lagebj/leif.git
cd leif
```

### 2. Start Ollama

If you installed Ollama with Homebrew and want it in the background:

```bash
brew services start ollama
```

If you want to stop it later:

```bash
brew services stop ollama
```

### 3. Pull the required models

```bash
ollama pull gemma3:4b
ollama pull embeddinggemma
```

### 4. Build the Leif model

```bash
ollama create leif -f ollama/Modelfile
```

### 5. Set up your environment

Copy the example environment file if you want a local version:

```bash
cp .env.example .env
```

Example values:

```bash
LEIF_DATA_DIR=/absolute/path/to/leif-private-data
OLLAMA_BASE_URL=http://localhost:11434
LEIF_CHAT_MODEL=leif
LEIF_EMBED_MODEL=embeddinggemma
```

## Data layout

If `LEIF_DATA_DIR` is set, Leif reads from that directory.

If `LEIF_DATA_DIR` is not set, Leif falls back to the public example files in `data/examples/`.

A typical private data folder can look like this:

```text
leif-private-data/
├── principles.md
├── heuristics.md
├── examples-good.md
├── examples-bad.md
├── case-patterns.md
└── rewrites.jsonl
```

Supported file formats:

* `.md`
* `.jsonl`

## Usage

### 1. Chunk the source material

```bash
python3 scripts/chunk_docs.py
```

This writes:

```text
data/processed/chunks.jsonl
```

### 2. Create embeddings

```bash
python3 scripts/embed_docs.py
```

This writes:

```text
data/processed/embeddings.json
```

### 3. Ask Leif something

```bash
python3 scripts/ask.py "Explain why abstraction can create operational risk."
```

## Local HTTP interface

Leif can be exposed as a small local HTTP service for integration with external agent frameworks such as Paperclip.

### Start the server

```bash
python3 scripts/server.py
```

### Health check

```bash
curl http://127.0.0.1:8787/health
```

Example response:

```json
{"ok": true, "service": "leif"}
```

### Invoke endpoint

```bash
curl -X POST http://127.0.0.1:8787/invoke \
  -H "Content-Type: application/json" \
  -d '{"message":"Why does process theater create drag?"}'
```

Example response:

```json
{
  "ok": true,
  "message": "...",
  "sources": [
    {"source": "principles.md", "id": "principles.md-0"}
  ]
}
```

### Webhook-style endpoint

Leif also exposes:

```text
POST /webhook/adapter
```

This exists as a Paperclip-facing path for HTTP adapter integration.

### Current limitations

* synchronous only
* single-process server
* embeddings are loaded at startup
* restart the server after regenerating embeddings

## Day 2 operations

Leif is not a one-time setup. It needs maintenance if you want the behavior to stay sharp and the context to stay relevant.

### When new context is added

If you add or change source material in your private data folder:

- update or add `.md` and `.jsonl` files
- rerun chunking
- rerun embeddings

Commands:

```bash
python3 scripts/chunk_docs.py
python3 scripts/embed_docs.py
```

This rebuilds the local retrieval index from the current source material.

### When behavior drifts

If Leif starts sounding vague, soft, generic, or too polished:

* review `prompts/system.txt`
* review the quality of your source material
* add better examples
* add more rewrite pairs
* tighten evaluation cases

Do not fine-tune first. Fix the prompt and corpus before touching weights.

### When adding new source files

Keep source material separated by role.

Recommended private data layout:

```text
leif-private-data/
├── principles.md
├── heuristics.md
├── examples-good.md
├── examples-bad.md
├── case-patterns.md
└── rewrites.jsonl
```

Use:

* `principles.md` for durable beliefs and operating rules
* `heuristics.md` for decision rules
* `examples-good.md` for strong answer examples
* `examples-bad.md` for anti-patterns and contrast
* `case-patterns.md` for real situations and tradeoffs
* `rewrites.jsonl` for input/output rewrite pairs

### When changing the model

If you change the chat model in Ollama:

* update `OLLAMA_CHAT_MODEL`
* rebuild the Ollama model if needed
* rerun a small set of evaluation cases

If you change the embedding model:

* update `LEIF_EMBED_MODEL`
* rerun embeddings

Commands:

```bash
ollama create leif -f ollama/Modelfile
python3 scripts/embed_docs.py
```

### When updating the prompt

If `prompts/system.txt` changes:

* rebuild the Ollama model if the same behavior is also embedded in `ollama/Modelfile`
* rerun a few manual checks
* rerun evaluation cases

The system prompt and the Modelfile should not silently drift apart.

### Operational loop

A simple maintenance loop looks like this:

1. update source material
2. rebuild chunks
3. rebuild embeddings
4. run manual questions
5. run evaluation cases
6. adjust prompt or corpus
7. repeat

### What not to store in this public repo

Do not commit:

* private principles or notes
* employer or client material
* sensitive case details
* real internal examples unless cleared for publication

Keep the public repo reusable and the private corpus separate.

### Signs the corpus needs work

The source material likely needs improvement if Leif:

* answers in a way that sounds generic
* misses your decision posture
* becomes too soft or explanatory
* retrieves context that is technically related but cognitively weak
* repeats concepts without sharpening them

That usually means the problem is in the material, not the retrieval code.

## Evaluation

Evaluation files live in `eval/`.

* `eval/eval_cases.jsonl` contains test prompts and expected traits
* `eval/rubric.md` defines how responses should be judged

This is the first layer of quality control. It helps expose drift, vagueness, softness, and style regression.

## Design choices

### Public repo, private data

The public repo is meant to be shareable.
The actual reasoning material can stay private.

### Retrieval before fine-tuning

Leif starts with:

* a system prompt
* a local corpus
* retrieval over that corpus

This keeps the assistant editable and transparent.

### Fine-tuning later

Only fine-tune when the same behavioral failure keeps repeating after:

* prompt refinement
* corpus improvement
* better examples
* evaluation feedback

## Current limitations

* no vector database
* no reranking
* no conversation memory
* no structured evaluation runner yet
* no Paperclip wrapper yet

That is deliberate. The first version should stay small and understandable.

## License

This repository is licensed under the Apache License 2.0.
See `LICENSE`.
