"""Tool registry. The single place where new tools are registered."""

from __future__ import annotations

from app.agent.tools.list_directory import build_list_directory_tool
from app.agent.tools.read_file import build_read_file_tool
from app.agent.tools.search_code import build_search_code_tool
from app.agent.tools.summarize_module import build_summarize_module_tool
from app.ingest.store import get_client, get_or_create_collection
from app.settings import Settings
from app.trace.base import TraceCollector


def build_tools(settings: Settings, trace: TraceCollector | None = None) -> list:
    """Construct all four tools, sharing the same Chroma collection.

    `trace` is per-request: pass a fresh LiveTrace for each chat call so
    tool_call / tool_result events aren't mixed across concurrent users.
    """
    client = get_client(settings.chroma_dir)
    coll = get_or_create_collection(
        client,
        settings.embedding_collection,
        settings.embedding_model,
    )
    return [
        build_search_code_tool(coll, default_k=settings.retrieval_top_k, trace=trace),
        build_read_file_tool(repo_root=settings.repo_dir, trace=trace),
        build_list_directory_tool(repo_root=settings.repo_dir, trace=trace),
        build_summarize_module_tool(
            coll,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_s,
            trace=trace,
        ),
    ]
