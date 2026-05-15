"""Helpers shared by tool implementations."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable

from app.agent.base import TraceEvent
from app.trace.base import TraceCollector

log = logging.getLogger("app.tools")


def resolve_safe(repo_root: Path, rel: str) -> Path | None:
    """Resolve `rel` under `repo_root` and refuse anything that escapes the root.

    Defends `read_file` and `list_directory` from path-traversal inputs like
    `../../etc/passwd`.
    """
    try:
        repo_resolved = repo_root.resolve()
        candidate = (repo_root / rel).resolve()
    except (OSError, ValueError):
        return None
    try:
        candidate.relative_to(repo_resolved)
    except ValueError:
        return None
    return candidate


def trace_tool(
    name: str,
    args: dict[str, Any],
    fn: Callable[[], str],
    trace: TraceCollector | None = None,
) -> str:
    """Wrap a tool body with structured logging + trace events.

    Logs to the uvicorn console *and* (if a trace collector was passed)
    records `tool_call` / `tool_result` events that the API surfaces back to
    the frontend so the user can see what happened.
    """
    args_preview = _truncate_json(args, 240)
    log.info("→ %s(%s)", name, args_preview)
    if trace is not None:
        trace.record(TraceEvent("tool_call", {"tool": name, "args": args}))

    t0 = time.perf_counter()
    try:
        result = fn()
    except Exception as e:
        log.exception("✗ %s raised", name)
        if trace is not None:
            trace.record(TraceEvent("tool_result", {"tool": name, "error": f"{type(e).__name__}: {e}"}))
        return json.dumps({"error": f"{type(e).__name__}: {e}"})

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    preview = _truncate_json(result, 280)
    log.info("← %s ok (%d ms, %d chars)", name, elapsed_ms, len(result))
    if trace is not None:
        trace.record(TraceEvent("tool_result", {
            "tool": name,
            "elapsed_ms": elapsed_ms,
            "preview": preview,
        }))
    return result


def _truncate_json(obj: Any, max_chars: int) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False) if not isinstance(obj, str) else obj
    except (TypeError, ValueError):
        s = str(obj)
    return s if len(s) <= max_chars else s[:max_chars] + "…"
