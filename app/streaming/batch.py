"""Non-streaming emitter: just appends events to an in-memory list.

Used by the core /chat endpoint, which returns a single JSON response.
"""

from __future__ import annotations

from app.agent.base import TraceEvent
from app.streaming.base import EventEmitter


class BatchEmitter(EventEmitter):
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    async def emit(self, event: TraceEvent) -> None:
        self._events.append(event)

    async def close(self) -> None:
        return None

    def collected(self) -> list[TraceEvent]:
        return list(self._events)
