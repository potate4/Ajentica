"""Per-session conversation memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    content: str


class MemoryStore(Protocol):
    def get(self, session_id: str) -> list[Turn]: ...
    def append(self, session_id: str, turn: Turn) -> None: ...
    def context_summary(self, session_id: str) -> str:
        """Render the session's history into a string suitable for prompt injection."""
        ...
