"""In-process per-session conversation memory.

Bounded by `max_turns` (most recent turns kept; older ones drop) and
`max_sessions` (oldest session evicted when the cap is hit). Lives only as
long as the uvicorn process — the bonus brief calls for "in-memory"
specifically, not durable persistence.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from threading import Lock

from app.memory.base import MemoryStore, Turn

MAX_PROMPT_CHARS_PER_TURN = 600


class InMemoryStore(MemoryStore):
    def __init__(self, max_turns: int = 6, max_sessions: int = 100) -> None:
        self.max_turns = max_turns
        self.max_sessions = max_sessions
        # OrderedDict so we can evict the oldest session in O(1)
        self._sessions: OrderedDict[str, deque[Turn]] = OrderedDict()
        self._lock = Lock()

    def get(self, session_id: str) -> list[Turn]:
        with self._lock:
            return list(self._sessions.get(session_id, ()))

    def append(self, session_id: str, turn: Turn) -> None:
        with self._lock:
            if session_id in self._sessions:
                self._sessions.move_to_end(session_id)
            else:
                if len(self._sessions) >= self.max_sessions:
                    self._sessions.popitem(last=False)
                self._sessions[session_id] = deque(maxlen=self.max_turns)
            self._sessions[session_id].append(turn)

    def context_summary(self, session_id: str) -> str:
        """Render history for prompt injection. Empty string = no prior context."""
        turns = self.get(session_id)
        if not turns:
            return ""
        lines: list[str] = []
        for t in turns:
            content = t.content.strip()
            if len(content) > MAX_PROMPT_CHARS_PER_TURN:
                content = content[:MAX_PROMPT_CHARS_PER_TURN].rstrip() + "…"
            lines.append(f"{t.role}: {content}")
        return "\n".join(lines)
