"""No-op trace collector. Used when ENABLE_REASONING_TRACE=false (core)."""

from __future__ import annotations

from app.agent.base import TraceEvent
from app.trace.base import TraceCollector


class NullTrace(TraceCollector):
    def record(self, event: TraceEvent) -> None:
        return None

    def events(self) -> list[TraceEvent]:
        return []
