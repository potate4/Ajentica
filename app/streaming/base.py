"""Event emitter abstraction.

Core mode uses `BatchEmitter` (collect events into a list, return at end).
Bonus mode swaps in an `SSEEmitter` that pushes to an asyncio.Queue for
server-sent events. The runner code is identical either way.
"""

from __future__ import annotations

from typing import Protocol

from app.agent.base import TraceEvent


class EventEmitter(Protocol):
    async def emit(self, event: TraceEvent) -> None: ...
    async def close(self) -> None: ...
    def collected(self) -> list[TraceEvent]:
        """Return events seen so far (mainly for batch mode)."""
        ...
