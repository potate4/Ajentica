"""FastAPI entry point.

Routes:
  GET  /api/health     — status + indexed-chunk count
  GET  /api/config     — feature flags (consumed by the React UI)
  POST /api/chat       — ask one question, get one grounded answer

If `frontend/dist/` exists (i.e. the React app has been built), it is served
at the root path with SPA fallback. Otherwise `/` returns instructions.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent.base import RunRequest
from app.factory import build_context
from app.ingest.store import get_client, get_or_create_collection
from app.settings import PROJECT_ROOT, get_settings
from app.streaming.sse import sse
from app.trace.queue import QueueTrace

log = logging.getLogger(__name__)

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


# ---- App state ----------------------------------------------------------

settings = get_settings()
ctx = build_context(settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("Codebase Q&A Agent — agent_mode=%s, llm=%s",
             settings.agent_mode, settings.llm_model)
    yield


app = FastAPI(title="Codebase Q&A Agent", lifespan=lifespan)

# CORS for the Vite dev server (production is same-origin, no CORS needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Schemas ------------------------------------------------------------


class CitationOut(BaseModel):
    path: str
    start_line: int
    end_line: int


class TraceEventOut(BaseModel):
    kind: str
    payload: dict[str, Any]


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    options: dict[str, Any] | None = None  # reserved for per-request overrides


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    refused: bool
    session_id: str
    events: list[TraceEventOut]


class ConfigResponse(BaseModel):
    agent_mode: str
    llm_model: str
    target_repo_url: str
    target_repo_ref: str
    enable_streaming: bool
    enable_reasoning_trace: bool
    enable_session_memory: bool


# ---- API ----------------------------------------------------------------


@app.get("/api/health")
async def health() -> dict:
    try:
        client = get_client(settings.chroma_dir)
        coll = get_or_create_collection(
            client, settings.embedding_collection, settings.embedding_model,
        )
        n = coll.count()
    except Exception as e:
        log.warning("health check could not reach Chroma: %s", e)
        return {"status": "degraded", "error": str(e), "indexed_chunks": 0, "ingested": False}
    return {"status": "ok", "indexed_chunks": n, "ingested": n > 0}


@app.get("/api/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    s = ctx.settings
    return ConfigResponse(
        agent_mode=s.agent_mode,
        llm_model=s.llm_model,
        target_repo_url=s.target_repo_url,
        target_repo_ref=s.target_repo_ref,
        enable_streaming=s.enable_streaming,
        enable_reasoning_trace=s.enable_reasoning_trace,
        enable_session_memory=s.enable_session_memory,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not req.question.strip():
        raise HTTPException(400, "question must not be blank")

    session_id = req.session_id or str(uuid.uuid4())
    run_req = RunRequest(
        question=req.question,
        session_id=session_id,
        options=req.options or {},
    )
    result = await ctx.runner.run(run_req)
    return ChatResponse(
        answer=result.answer,
        citations=[
            CitationOut(path=c.path, start_line=c.start_line, end_line=c.end_line)
            for c in result.citations
        ],
        refused=result.refused,
        session_id=session_id,
        events=[TraceEventOut(kind=e.kind, payload=e.payload) for e in result.events],
    )


# ---- Streaming chat (SSE) — bonus -------------------------------------


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """Server-sent-event variant of /api/chat.

    Tool events stream live as they fire. The final answer + citations ship
    as a single `done` event when the agent finishes.

    Event types:
      session  — { session_id }                          (first event)
      trace    — { kind, payload }                       (per tool/agent step)
      done     — { answer, citations, refused, ... }    (last event)
      error    — { error }                               (terminal on failure)
    """
    if not req.question.strip():
        raise HTTPException(400, "question must not be blank")

    session_id = req.session_id or str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    trace = QueueTrace(loop, queue)

    run_req = RunRequest(
        question=req.question, session_id=session_id, options=req.options or {},
    )
    runner_task = asyncio.create_task(ctx.runner.run(run_req, trace=trace))

    async def event_stream():
        yield sse("session", {"session_id": session_id})

        # Drain trace events until the runner finishes AND the queue is empty.
        while not runner_task.done() or not queue.empty():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            yield sse("trace", {"kind": event.kind, "payload": event.payload})

        try:
            result = runner_task.result()
        except Exception as e:
            log.exception("streaming agent run failed")
            yield sse("error", {"error": f"{type(e).__name__}: {e}"})
            return

        yield sse("done", {
            "answer": result.answer,
            "citations": [
                {"path": c.path, "start_line": c.start_line, "end_line": c.end_line}
                for c in result.citations
            ],
            "refused": result.refused,
            "session_id": session_id,
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
    })


# ---- Static (built React app, optional in dev) -------------------------


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        # Real files (favicon.svg, vite.svg, etc.) get served as-is
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        # Everything else falls back to index.html for SPA routing
        return FileResponse(FRONTEND_DIST / "index.html")

else:
    @app.get("/")
    async def root() -> JSONResponse:
        return JSONResponse({
            "message": (
                "React frontend not built yet. Two options:\n"
                "  • Dev:    cd frontend && npm install && npm run dev   "
                "(open http://localhost:5173)\n"
                "  • Bundle: cd frontend && npm run build                "
                "(then refresh this page)\n"
            ),
            "api_docs": "/docs",
        })
