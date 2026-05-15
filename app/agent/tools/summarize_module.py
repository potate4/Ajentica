"""summarize_module: produce a plain-English summary of a module or class.

Resolution strategy:
  1. Treat `name` as a dotted Python path → look for matching file paths in
     the index (handles both "flask.app" and "src/flask/app.py" style).
  2. Otherwise (or as a fallback) treat `name` as a class/function symbol →
     filter the collection by metadata.symbol.
  3. As a last resort, do a semantic query for the name.

Once chunks are gathered, a single small LiteLLM call synthesizes the summary.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from chromadb.api.models.Collection import Collection
from crewai.tools import tool
from litellm import completion

log = logging.getLogger(__name__)

MAX_CONTEXT_CHUNKS = 8
MAX_CHUNK_CHARS = 1500


def _gather_chunks(coll: Collection, name: str) -> list[dict]:
    parts = name.split(".")

    # Strategy 1 — file-path candidates
    candidates: list[str] = []
    for prefix in ("", "src/"):
        joined = "/".join(parts)
        candidates.extend([
            f"{prefix}{joined}.py",
            f"{prefix}{joined}/__init__.py",
        ])

    for path in candidates:
        try:
            res = coll.get(where={"path": path}, limit=MAX_CONTEXT_CHUNKS)
        except Exception:
            continue
        ids = res.get("ids") or []
        if ids:
            return _zip_get(res)

    # Strategy 2 — symbol match (e.g., "Flask" or "Flask.run")
    try:
        res = coll.get(where={"symbol": name}, limit=MAX_CONTEXT_CHUNKS)
        if res.get("ids"):
            return _zip_get(res)
    except Exception:
        pass

    # Strategy 3 — semantic search
    try:
        res = coll.query(query_texts=[f"module or class {name}"], n_results=MAX_CONTEXT_CHUNKS)
        return _zip_query(res)
    except Exception as e:
        log.warning("summarize_module: semantic fallback failed: %s", e)
        return []


def _zip_get(res: dict) -> list[dict]:
    docs = res.get("documents") or []
    metas = res.get("metadatas") or []
    return [{"text": d, **(m or {})} for d, m in zip(docs, metas)]


def _zip_query(res: dict) -> list[dict]:
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    return [{"text": d, **(m or {})} for d, m in zip(docs, metas)]


def build_summarize_module_tool(coll: Collection, model: str, temperature: float, timeout: int):
    @tool("summarize_module")
    def summarize_module(name: str) -> str:
        """Produce a plain-English summary of a Python module or class.

        USE WHEN: the user asks "what does X do?", "give me an overview of the
        Y module", or "explain the Z class". Prefer this over many search_code
        calls when the question is module-level rather than line-level.

        ARGS:
          name (str): dotted module path (e.g., "flask.app") OR a class name
                      (e.g., "Flask") OR a method name (e.g., "Flask.run").

        RETURNS: JSON {name, summary, sources: [{path, start_line, end_line}]}
                 or {error} if no matching code is found.
        """
        chunks = _gather_chunks(coll, name)
        if not chunks:
            return json.dumps({
                "error": f"no chunks found for '{name}'. Try search_code first to discover the right name."
            })

        sources = [
            {
                "path": c.get("path"),
                "start_line": c.get("start_line"),
                "end_line": c.get("end_line"),
                "symbol": c.get("symbol"),
                "kind": c.get("kind"),
            }
            for c in chunks
        ]

        ctx_blocks = []
        for c in chunks[:MAX_CONTEXT_CHUNKS]:
            text = (c.get("text") or "")[:MAX_CHUNK_CHARS]
            ctx_blocks.append(f"--- {c.get('path')}:{c.get('start_line')}-{c.get('end_line')} ({c.get('kind')}: {c.get('symbol')}) ---\n{text}")

        prompt = (
            f"Summarize the following code unit named '{name}' in 5-7 concise bullet points. "
            "Cover: purpose, key classes/functions, important external dependencies, "
            "and how it relates to the rest of the codebase based on what you can see. "
            "Do not invent details that are not in the snippets.\n\n"
            + "\n\n".join(ctx_blocks)
        )

        try:
            resp = completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                timeout=timeout,
            )
            summary = resp.choices[0].message.content.strip()
        except Exception as e:
            log.exception("summarize_module LLM call failed")
            return json.dumps({"error": f"LLM call failed: {e}", "sources": sources})

        return json.dumps({
            "name": name,
            "summary": summary,
            "sources": sources,
        }, ensure_ascii=False)

    return summarize_module
