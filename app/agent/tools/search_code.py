"""search_code: semantic search over the indexed Chroma collection."""

from __future__ import annotations

import json

from chromadb.api.models.Collection import Collection
from crewai.tools import tool

from app.agent.tools._common import trace_tool
from app.trace.base import TraceCollector

MAX_SNIPPET_CHARS = 1200


def build_search_code_tool(coll: Collection, default_k: int, trace: TraceCollector | None = None):
    @tool("search_code")
    def search_code(query: str, k: int = default_k) -> str:
        """Semantic search over the indexed codebase.

        USE WHEN: you need to find code related to a concept, behavior, or symbol
        and you do NOT already know the file path. Examples:
          - "where is URL routing handled"
          - "how does the request context get pushed onto a stack"
          - "find the WSGI entry point"

        ARGS:
          query (str): natural-language question or keywords.
          k (int): number of chunks to return (default 5, max 10).

        RETURNS: JSON list of {path, start_line, end_line, kind, symbol, score, snippet}.
        Each result includes precise file path and line range so you can cite it.
        Lower `score` (cosine distance) = better match.
        """
        try:
            n = max(1, min(int(k), 10))
        except (TypeError, ValueError):
            n = default_k

        def _run() -> str:
            res = coll.query(query_texts=[query], n_results=n)
            ids = res.get("ids", [[]])[0]
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

            results = []
            for _id, doc, meta, dist in zip(ids, docs, metas, dists):
                snippet = doc[:MAX_SNIPPET_CHARS]
                if len(doc) > MAX_SNIPPET_CHARS:
                    snippet += "\n... [truncated]"
                results.append({
                    "path": meta.get("path"),
                    "start_line": meta.get("start_line"),
                    "end_line": meta.get("end_line"),
                    "kind": meta.get("kind"),
                    "symbol": meta.get("symbol"),
                    "score": round(float(dist), 4),
                    "snippet": snippet,
                })
            return json.dumps({"results": results}, ensure_ascii=False)

        return trace_tool("search_code", {"query": query, "k": n}, _run, trace=trace)

    return search_code
