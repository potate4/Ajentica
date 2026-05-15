"""End-to-end ingest pipeline.

Run as:
    python -m app.ingest.pipeline                # incremental upsert
    python -m app.ingest.pipeline --rebuild      # drop collection first

Steps:
  1. Clone (or fast-forward) the target repository
  2. Walk indexable files (skip binaries, build dirs, .git, etc.)
  3. AST-chunk Python; line-chunk other text formats
  4. Upsert into the persistent Chroma collection
"""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Iterator
from pathlib import Path

from app.ingest.chunker import Chunk, chunk_python_source, chunk_text
from app.ingest.clone import clone_or_update
from app.ingest.store import (
    get_client,
    get_or_create_collection,
    reset_collection,
    upsert_chunks,
)
from app.settings import get_settings

log = logging.getLogger(__name__)

INDEXABLE_EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".rst": "text",
    ".md": "text",
    ".txt": "text",
    ".cfg": "text",
    ".ini": "text",
    ".toml": "text",
    ".yaml": "text",
    ".yml": "text",
}

SKIP_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".tox",
    "build", "dist", "node_modules", ".venv", "venv",
    ".mypy_cache", ".ruff_cache", ".idea", ".vscode",
    "site-packages",
}

# Hard size cap to avoid pathological files (generated code, large fixtures).
MAX_FILE_BYTES = 2_000_000  # 2 MB


def is_probably_binary(path: Path) -> bool:
    """Cheap binary sniff: null byte in the first 1 KB."""
    try:
        with path.open("rb") as f:
            sample = f.read(1024)
        return b"\x00" in sample
    except OSError:
        return True


def iter_indexable_files(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in INDEXABLE_EXTENSIONS:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        if is_probably_binary(path):
            continue
        yield path


def chunk_file(path: Path, rel_path: str) -> list[Chunk]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    if path.suffix.lower() in {".py", ".pyi"}:
        return chunk_python_source(text, rel_path)
    return chunk_text(text, rel_path)


def run_ingest(rebuild: bool = False) -> dict:
    settings = get_settings()
    t0 = time.time()

    log.info("Phase 1/4: clone")
    repo_path = clone_or_update(
        settings.target_repo_url, settings.target_repo_ref, settings.repo_dir
    )

    log.info("Phase 2/4: connect Chroma at %s", settings.chroma_dir)
    client = get_client(settings.chroma_dir)
    if rebuild:
        reset_collection(client, settings.embedding_collection)
    coll = get_or_create_collection(
        client, settings.embedding_collection, settings.embedding_model
    )

    log.info("Phase 3/4: walk + chunk")
    all_chunks: list[Chunk] = []
    file_count = 0
    for path in iter_indexable_files(repo_path):
        file_count += 1
        rel = path.relative_to(repo_path).as_posix()
        all_chunks.extend(chunk_file(path, rel))

    log.info("Phase 4/4: upsert %d chunks from %d files", len(all_chunks), file_count)
    upserted = upsert_chunks(coll, all_chunks)

    elapsed = time.time() - t0
    summary = {
        "repo": settings.target_repo_url,
        "files_indexed": file_count,
        "chunks_indexed": upserted,
        "collection": settings.embedding_collection,
        "elapsed_seconds": round(elapsed, 1),
    }
    log.info("Done: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the target repo into Chroma.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop and recreate the collection before indexing.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    summary = run_ingest(rebuild=args.rebuild)
    print()
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
