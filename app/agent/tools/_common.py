"""Helpers shared by tool implementations."""

from __future__ import annotations

from pathlib import Path


def resolve_safe(repo_root: Path, rel: str) -> Path | None:
    """Resolve `rel` under `repo_root` and refuse anything that escapes the root.

    Defends `read_file` and `list_directory` from path-traversal inputs like
    `../../etc/passwd`.
    """
    try:
        repo_resolved = repo_root.resolve()
        candidate = (repo_root / rel).resolve()
    except (OSError, ValueError):
        return None
    try:
        candidate.relative_to(repo_resolved)
    except ValueError:
        return None
    return candidate
