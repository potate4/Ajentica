"""AST-aware code chunker.

Brief requirement: *"chunk source code files intelligently — respecting code
structure, not arbitrary character limits. Do NOT split in the middle of a
function or class."*

Strategy:
  - For Python (`.py`), use `ast` to walk the module. Each function and class
    becomes one chunk. Decorators are kept with their target. Module-level
    imports/assignments before the first def/class become a "prelude" chunk.
    Large classes (> MAX_CLASS_LINES) are split into a class header + one
    chunk per method, never inside a method body.
  - For text-shaped non-code (`.md`, `.rst`, `.cfg`, …), fall back to
    fixed-line chunks (40 lines each). Binaries are filtered upstream.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

MAX_CLASS_LINES = 200       # split into header + per-method above this
TEXT_CHUNK_LINES = 40       # fallback chunk size for non-Python text


@dataclass
class Chunk:
    text: str
    path: str
    start_line: int
    end_line: int
    kind: str       # function | method | class | class-header | module-prelude | text
    symbol: str     # qualified name (e.g., "Flask.run" for methods); "" for non-symbols


# ---------------------------------------------------------------------------
# Python chunker
# ---------------------------------------------------------------------------

_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def chunk_python_source(source: str, rel_path: str) -> list[Chunk]:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        log.debug("SyntaxError in %s (%s); falling back to text chunking", rel_path, e)
        return chunk_text(source, rel_path)

    lines = source.splitlines()
    if not lines:
        return []

    chunks: list[Chunk] = []

    # 1. Module prelude: everything before the first def/class
    first_def_line = next(
        (n.lineno for n in tree.body if isinstance(n, _DEF_NODES)),
        None,
    )
    if first_def_line is None:
        # Whole file is just imports / module-level code
        chunks.append(Chunk(
            text="\n".join(lines),
            path=rel_path, start_line=1, end_line=len(lines),
            kind="module-prelude", symbol="",
        ))
        return chunks

    if first_def_line > 1:
        prelude_end = first_def_line - 1
        prelude_text = "\n".join(lines[0:prelude_end]).rstrip()
        if prelude_text.strip():
            chunks.append(Chunk(
                text=prelude_text,
                path=rel_path, start_line=1, end_line=prelude_end,
                kind="module-prelude", symbol="",
            ))

    # 2. One chunk per top-level function / class
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(_chunk_from_def(node, lines, rel_path, kind="function"))
        elif isinstance(node, ast.ClassDef):
            chunks.extend(_chunk_class(node, lines, rel_path))

    return chunks


def _node_start(node: ast.AST) -> int:
    """First line including any decorators."""
    decorators = getattr(node, "decorator_list", []) or []
    if decorators:
        return min(d.lineno for d in decorators)
    return node.lineno


def _chunk_from_def(node: ast.AST, lines: list[str], rel_path: str, kind: str, qualifier: str = "") -> Chunk:
    start = _node_start(node)
    end = node.end_lineno or start
    name = getattr(node, "name", "")
    symbol = f"{qualifier}.{name}" if qualifier else name
    return Chunk(
        text="\n".join(lines[start - 1:end]),
        path=rel_path, start_line=start, end_line=end,
        kind=kind, symbol=symbol,
    )


def _chunk_class(cls: ast.ClassDef, lines: list[str], rel_path: str) -> list[Chunk]:
    cls_start = _node_start(cls)
    cls_end = cls.end_lineno or cls_start

    # Small class: keep as one chunk to preserve context
    if cls_end - cls_start + 1 <= MAX_CLASS_LINES:
        return [Chunk(
            text="\n".join(lines[cls_start - 1:cls_end]),
            path=rel_path, start_line=cls_start, end_line=cls_end,
            kind="class", symbol=cls.name,
        )]

    # Large class: header chunk + one chunk per method
    chunks: list[Chunk] = []
    methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    # Header = class declaration through last non-method line
    header_end = (methods[0].lineno - 1) if methods else cls_end
    if header_end >= cls_start:
        chunks.append(Chunk(
            text="\n".join(lines[cls_start - 1:header_end]),
            path=rel_path, start_line=cls_start, end_line=header_end,
            kind="class-header", symbol=cls.name,
        ))

    for m in methods:
        chunks.append(_chunk_from_def(m, lines, rel_path, kind="method", qualifier=cls.name))

    return chunks


# ---------------------------------------------------------------------------
# Text fallback (markdown, rst, config files)
# ---------------------------------------------------------------------------

def chunk_text(source: str, rel_path: str, target_lines: int = TEXT_CHUNK_LINES) -> list[Chunk]:
    lines = source.splitlines()
    if not lines:
        return []
    chunks: list[Chunk] = []
    i = 0
    while i < len(lines):
        end = min(i + target_lines, len(lines))
        text = "\n".join(lines[i:end]).strip()
        if text:
            chunks.append(Chunk(
                text=text,
                path=rel_path, start_line=i + 1, end_line=end,
                kind="text", symbol="",
            ))
        i = end
    return chunks
