"""Protocol + data shapes shared by every agent runner.

A runner takes a `RunRequest` and produces a `RunResult`. It MAY also push
intermediate `TraceEvent`s into a `TraceCollector` so the UI can render the
agent's reasoning. In core mode the collector is `NullTrace` (no-op).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Citation:
    path: str
    start_line: int
    end_line: int


@dataclass
class TraceEvent:
    """A single observable step in the agent's reasoning."""
    kind: str  # agent_started | agent_thought | tool_call | tool_result | agent_finished | answer_token
    payload: dict[str, Any]


@dataclass
class RunRequest:
    question: str
    session_id: str | None = None
    options: dict[str, Any] = field(default_factory=dict)  # per-request flag overrides


@dataclass
class RunResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    events: list[TraceEvent] = field(default_factory=list)
    refused: bool = False


class AgentRunner(Protocol):
    """Anything that can answer one question."""

    async def run(self, request: RunRequest) -> RunResult: ...
