"""No-op memory store. Used when ENABLE_SESSION_MEMORY=false (the core default)."""

from __future__ import annotations

from app.memory.base import MemoryStore, Turn


class NullMemory(MemoryStore):
    def get(self, session_id: str) -> list[Turn]:
        return []

    def append(self, session_id: str, turn: Turn) -> None:
        return None

    def context_summary(self, session_id: str) -> str:
        return ""
