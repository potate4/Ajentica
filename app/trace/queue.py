"""LiveTrace that *also* pushes events into an asyncio.Queue.

Used by the SSE streaming endpoint: the runner runs in a worker thread
(via `asyncio.to_thread`); tools record events from that thread; the queue
bridges them back into the asyncio loop so the SSE generator can drain them
and send to the client as they fire.
"""

from __future__ import annotations

import asyncio
import logging

from app.agent.base import TraceEvent
from app.trace.live import LiveTrace

log = logging.getLogger(__name__)


class QueueTrace(LiveTrace):
    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
        super().__init__()
        self._loop = loop
        self._queue = queue

    def record(self, event: TraceEvent) -> None:
        super().record(event)
        # Bridge worker thread → asyncio loop. put_nowait can raise QueueFull;
        # log + drop rather than blocking the agent.
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except RuntimeError:
            # Loop closed — nothing to do.
            log.debug("event queue loop closed; dropping event")
