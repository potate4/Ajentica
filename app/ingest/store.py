"""ChromaDB persistent vector store wrapper.

One collection holds all chunks. Embeddings come from
sentence-transformers via Chroma's built-in helper, so there is exactly one
embedding code path used at both ingest and query time.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from app.ingest.chunker import Chunk

log = logging.getLogger(__name__)


def get_client(chroma_dir: Path) -> chromadb.ClientAPI:
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(chroma_dir))


def get_embedding_function(model_name: str):
    # Chroma's wrapper around sentence-transformers — same model is used
    # for both indexing and querying.
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model_name,
    )


def get_or_create_collection(client: chromadb.ClientAPI, name: str, model_name: str) -> Collection:
    return client.get_or_create_collection(
        name=name,
        embedding_function=get_embedding_function(model_name),
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection(client: chromadb.ClientAPI, name: str) -> None:
    try:
        client.delete_collection(name)
        log.info("Deleted existing collection %r", name)
    except Exception:
        log.debug("No existing collection %r to delete", name)


def chunk_id(c: Chunk) -> str:
    raw = f"{c.path}:{c.start_line}-{c.end_line}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def upsert_chunks(coll: Collection, chunks: list[Chunk], batch_size: int = 128) -> int:
    """Upsert in batches; returns total upserted."""
    total = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        coll.upsert(
            ids=[chunk_id(c) for c in batch],
            documents=[c.text for c in batch],
            metadatas=[{
                "path": c.path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "kind": c.kind,
                "symbol": c.symbol,
            } for c in batch],
        )
        total += len(batch)
    return total
