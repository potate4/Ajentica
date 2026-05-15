# Codebase Q&A Agent

An agentic Q&A system that answers natural-language questions about a public
GitHub codebase (default target: [pallets/flask](https://github.com/pallets/flask))
using retrieval-augmented generation, AST-aware code chunking, and an LLM
agent that picks among four tools per query.

> **Status:** Phase 1 — core complete. Phase 2 (bonuses) wires in next.

---

## Architecture (one-liner)

A CrewAI agent has access to four tools — `search_code`, `read_file`,
`list_directory`, `summarize_module` — and decides per-query which to call,
grounding every answer in the indexed Chroma vector store of AST-chunked
source. The LLM is provider-agnostic via LiteLLM (Gemini, OpenAI,
OpenRouter, Anthropic, Ollama, Groq, …). All bonuses are feature flags.

```
React UI ──► FastAPI ──► CrewAI Agent ──► [search_code | read_file | list_directory | summarize_module]
                                                     │
                                                     ▼
                                  ChromaDB (AST-chunked Flask source)
```

---

## Setup

### 1. Backend

```powershell
# From the repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure env
copy .env.example .env
# Then edit .env — at minimum set GEMINI_API_KEY=...
# (or pick a different provider via LLM_MODEL — see .env.example)

# One-time: clone Flask + build the vector index (~2 min on first run)
python -m app.ingest.pipeline

# Start the API
uvicorn app.main:app --reload
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev    # opens http://localhost:5173 with proxy to :8000
```

For a single-port production-style run, build instead:

```powershell
cd frontend
npm run build  # outputs to frontend/dist
# Now uvicorn serves the built UI from http://localhost:8000
```

---

## LLM provider — pick anything LiteLLM supports

The `LLM_MODEL` env var is just a LiteLLM model string. Examples:

| Provider | `LLM_MODEL`                                   | Required env key      |
|----------|-----------------------------------------------|-----------------------|
| Gemini   | `gemini/gemini-1.5-flash`                     | `GEMINI_API_KEY`      |
| OpenAI   | `openai/gpt-4o-mini`                          | `OPENAI_API_KEY`      |
| OpenRouter | `openrouter/anthropic/claude-3.5-sonnet`    | `OPENROUTER_API_KEY`  |
| Anthropic | `anthropic/claude-3-5-haiku-latest`          | `ANTHROPIC_API_KEY`   |
| Ollama   | `ollama/qwen2.5-coder:7b`                     | (none — local)        |
| Groq     | `groq/llama-3.1-70b-versatile`                | `GROQ_API_KEY`        |

No code changes — flip `LLM_MODEL` and restart.

---

## Roadmap

- **Phase 1 (this commit) — Core:** ingest, AST chunker, 4 tools, single
  CrewAI agent, FastAPI backend, React + Tailwind UI, citations, refusal.
- **Phase 2 — Bonuses (next):** multi-agent crew, reasoning trace UI,
  SSE token streaming, in-memory session context. Each ships behind a flag
  in `.env` so you can mix and match.

(Full README — sample queries, screenshots, AI-tool disclosure — finalized
at the end of Phase 2.)
