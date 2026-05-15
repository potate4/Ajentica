"""read_file: read the raw content of a file under the indexed repo."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from crewai.tools import tool

from app.agent.tools._common import resolve_safe

log = logging.getLogger(__name__)

MAX_LINES_RETURNED = 400


def build_read_file_tool(repo_root: Path):
    @tool("read_file")
    def read_file(path: str, start_line: int = 1, end_line: int = 0) -> str:
        """Read raw file contents from the indexed repository.

        USE WHEN: you have a file path (e.g., from search_code results) and want
        to see surrounding code, the full body of a function, or imports.

        ARGS:
          path (str): repo-relative path (e.g., "src/flask/app.py").
          start_line (int): 1-based start line (default 1).
          end_line (int): 1-based end line, inclusive. 0 = read to end of file
                          (capped at 400 lines per call).

        RETURNS: JSON {path, start_line, end_line, total_lines, content} or {error}.
        """
        target = resolve_safe(repo_root, path)
        if target is None or not target.exists():
            return json.dumps({"error": f"file not found or outside repo: {path}"})
        if not target.is_file():
            return json.dumps({"error": f"not a file: {path}"})

        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return json.dumps({"error": f"binary or non-utf8 file: {path}"})

        lines = text.splitlines()
        total = len(lines)
        s = max(1, int(start_line))
        e = int(end_line) if end_line and end_line > 0 else total
        e = min(e, s + MAX_LINES_RETURNED - 1, total)

        excerpt = "\n".join(lines[s - 1:e])
        return json.dumps({
            "path": path,
            "start_line": s,
            "end_line": e,
            "total_lines": total,
            "content": excerpt,
        }, ensure_ascii=False)

    return read_file
