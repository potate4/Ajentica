"""Composition root.

Both runners (single + crew) and a real `InMemoryStore` are always built so
the chat handler can pick per request. The `.env` flags become *defaults* —
clients can override them via the request `options` field. This is what
makes "toggle in the UI" actually do something.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.base import AgentRunner
from app.agent.crew import CrewRunner
from app.agent.single import SingleAgentRunner
from app.memory.base import MemoryStore
from app.memory.in_memory import InMemoryStore
from app.settings import Settings


@dataclass
class AppContext:
    runners: dict[str, AgentRunner]   # always has both "single" and "crew"
    memory: MemoryStore               # always real; runners use it conditionally
    settings: Settings


def build_context(settings: Settings) -> AppContext:
    memory = InMemoryStore(
        max_turns=settings.session_max_turns,
        max_sessions=settings.session_max_sessions,
    )
    runners: dict[str, AgentRunner] = {
        "single": SingleAgentRunner(settings, memory),
        "crew": CrewRunner(settings, memory),
    }
    return AppContext(runners=runners, memory=memory, settings=settings)
