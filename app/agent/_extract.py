"""Citation parsing + refusal detection. Shared by single + crew runners."""

from __future__ import annotations

import re

from app.agent.base import Citation

CITATION_RE = re.compile(r"([\w./\\-]+\.[A-Za-z]{1,5}):(\d+)-(\d+)")

REFUSAL_NEEDLES = (
    "sources: none",
    "could not find",
    "no relevant evidence",
    "outside the scope",
    "not in this repository",
    "unable to find",
)


def extract_citations(text: str) -> list[Citation]:
    seen: set[tuple[str, int, int]] = set()
    out: list[Citation] = []
    for m in CITATION_RE.finditer(text):
        path = m.group(1).replace("\\", "/").lstrip("./")
        try:
            s, e = int(m.group(2)), int(m.group(3))
        except ValueError:
            continue
        key = (path, s, e)
        if key in seen:
            continue
        seen.add(key)
        out.append(Citation(path=path, start_line=s, end_line=e))
    return out


def looks_like_refusal(text: str) -> bool:
    lowered = text.lower()
    return any(n in lowered for n in REFUSAL_NEEDLES)
