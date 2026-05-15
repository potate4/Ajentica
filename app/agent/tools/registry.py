"""Tool registry. The single place where new tools are registered."""

from __future__ import annotations

from app.agent.tools.list_directory import build_list_directory_tool
from app.agent.tools.read_file import build_read_file_tool
from app.agent.tools.search_code import build_search_code_tool
from app.agent.tools.summarize_module import build_summarize_module_tool
from app.ingest.store import get_client, get_or_create_collection
from app.settings import Settings


def build_tools(settings: Settings) -> list:
    """Construct all four tools, sharing the same Chroma collection."""
    client = get_client(settings.chroma_dir)
    coll = get_or_create_collection(
        client,
        settings.embedding_collection,
        settings.embedding_model,
    )
    return [
        build_search_code_tool(coll, default_k=settings.retrieval_top_k),
        build_read_file_tool(repo_root=settings.repo_dir),
        build_list_directory_tool(repo_root=settings.repo_dir),
        build_summarize_module_tool(
            coll,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_s,
        ),
    ]
