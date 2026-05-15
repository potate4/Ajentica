"""Composition root.

The single place where feature flags are translated into concrete component
choices. Adding a bonus = adding one branch here, plus the new file. Nothing
else in the codebase needs to know.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.base import AgentRunner
from app.memory.base import MemoryStore
from app.memory.null import NullMemory
from app.settings import Settings
from app.trace.base import TraceCollector
from app.trace.null import NullTrace


@dataclass
class AppContext:
    runner: AgentRunner
    memory: MemoryStore
    settings: Settings


def build_context(settings: Settings) -> AppContext:
    # ---- Memory ----
    memory: MemoryStore
    if settings.enable_session_memory:
        # Phase 2: in-memory rolling-summary store.
        from app.memory.in_memory import InMemoryStore  # local import keeps Phase 1 self-contained
        memory = InMemoryStore(
            max_turns=settings.session_max_turns,
            max_sessions=settings.session_max_sessions,
        )
    else:
        memory = NullMemory()

    # ---- Agent runner ----
    runner: AgentRunner
    if settings.agent_mode == "crew":
        # Phase 2: 4-agent crew (planner / researcher / module-expert / synthesizer).
        from app.agent.crew import CrewRunner
        runner = CrewRunner(settings=settings, memory=memory)
    else:
        from app.agent.single import SingleAgentRunner
        runner = SingleAgentRunner(settings=settings, memory=memory)

    return AppContext(runner=runner, memory=memory, settings=settings)


def build_trace(settings: Settings) -> TraceCollector:
    """Built per-request, not per-app, since each request needs its own collector."""
    if settings.enable_reasoning_trace:
        from app.trace.live import LiveTrace
        return LiveTrace()
    return NullTrace()
