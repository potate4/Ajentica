"""Server-sent-event helpers."""

from __future__ import annotations

import json
from typing import Any


def sse(event: str, data: Any) -> str:
    """Format a single SSE message.

    `data` is JSON-encoded if it's not a string. We always emit the `event:`
    field so the client can dispatch with addEventListener('trace', …) etc.
    """
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    # Each line of `data` must be prefixed with "data: " per the SSE spec.
    payload = "\n".join(f"data: {line}" for line in data.split("\n"))
    return f"event: {event}\n{payload}\n\n"
