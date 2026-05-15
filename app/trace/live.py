"""LiveTrace — collects tool-call / tool-result events during a single run.

Used in core mode now (always visible in the UI) and reused by Phase 2's
streaming bonus (where events also get pushed to an SSE queue as they fire).
"""

from __future__ import annotations

import threading

from app.agent.base import TraceEvent
from app.trace.base import TraceCollector


class LiveTrace(TraceCollector):
    def __init__(self) -> None:
        self._events: list[TraceEvent] = []
        # CrewAI may invoke tools from worker threads; guard the list.
        self._lock = threading.Lock()

    def record(self, event: TraceEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events(self) -> list[TraceEvent]:
        with self._lock:
            return list(self._events)
