"""Reasoning-trace collector. Receives events from the agent loop."""

from __future__ import annotations

from typing import Protocol

from app.agent.base import TraceEvent


class TraceCollector(Protocol):
    def record(self, event: TraceEvent) -> None: ...
    def events(self) -> list[TraceEvent]: ...
