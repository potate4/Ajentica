"""list_directory: shallow directory listing under the indexed repo."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from crewai.tools import tool

from app.agent.tools._common import resolve_safe

log = logging.getLogger(__name__)

SKIP = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}


def build_list_directory_tool(repo_root: Path):
    @tool("list_directory")
    def list_directory(path: str = ".") -> str:
        """List the immediate contents of a directory in the indexed repo.

        USE WHEN: you want to understand the repo's layout — top-level packages,
        a module's submodules, or what files live next to a known file.

        ARGS:
          path (str): repo-relative directory (default ".", the repo root).

        RETURNS: JSON {path, directories: [...], files: [{name, size}], total_*}.
        """
        target = resolve_safe(repo_root, path)
        if target is None or not target.exists():
            return json.dumps({"error": f"path not found or outside repo: {path}"})
        if not target.is_dir():
            return json.dumps({"error": f"not a directory: {path}"})

        dirs: list[str] = []
        files: list[dict] = []
        try:
            for entry in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if entry.name in SKIP or entry.name.startswith(".") and entry.is_dir():
                    continue
                if entry.is_dir():
                    dirs.append(entry.name + "/")
                else:
                    try:
                        files.append({"name": entry.name, "size": entry.stat().st_size})
                    except OSError:
                        files.append({"name": entry.name, "size": -1})
        except OSError as e:
            return json.dumps({"error": f"cannot read directory: {e}"})

        return json.dumps({
            "path": path,
            "directories": dirs,
            "files": files,
            "total_directories": len(dirs),
            "total_files": len(files),
        }, ensure_ascii=False)

    return list_directory
