"""Single-agent runner — the **core** agent shape.

One CrewAI agent has access to all four tools and decides per-query which to
call. The system prompt enforces (a) citation of every factual claim with a
`path:start-end` reference and (b) explicit refusal when tools can't find
evidence. The crew bonus runner reuses these helpers.
"""

from __future__ import annotations

import asyncio
import logging
import re

from crewai import Agent, Crew, Process, Task

from app.agent.base import AgentRunner, Citation, RunRequest, RunResult
from app.agent.llm import make_llm
from app.agent.tools.registry import build_tools
from app.memory.base import MemoryStore, Turn
from app.settings import Settings

log = logging.getLogger(__name__)


SYSTEM_BACKSTORY = """\
You are a senior software engineer specialized in answering questions about a
single Python codebase that has been indexed for you in a vector store.

Your four tools — search_code, read_file, list_directory, summarize_module —
are the ONLY way you can see the actual code. Your training data does NOT
contain this specific repository. You must therefore call tools to gather
evidence before making claims.

Rules you MUST follow:

1. GROUND every factual claim in a tool result. No tool call -> no evidence.
2. CITE every claim using `path/to/file.py:START-END` line references. End your
   answer with a "Sources:" section listing all citations.
3. REFUSE gracefully. If your tools cannot find relevant code (low similarity
   scores, empty results, or the question is about something not in this repo),
   say so plainly. Write "Sources: none" and stop. Do NOT invent or guess.
4. BE EFFICIENT. Don't run the same search twice. After search_code finds a
   promising file, prefer read_file to see the full context rather than more
   semantic searches.
5. BE CONCISE. Use bullet points and short code blocks. The user is reading
   this in a chat UI.
"""


CITATION_RE = re.compile(r"([\w./\\-]+\.[A-Za-z]{1,5}):(\d+)-(\d+)")


def _build_task_description(question: str, history: str) -> str:
    sections = [
        "Answer the user's question about the indexed codebase. "
        "Use your tools to gather evidence first; never speculate.",
    ]
    if history:
        sections.append("Prior conversation (most recent last):\n" + history)
    sections.append(f"User's current question:\n{question}")
    sections.append(
        "Required output format:\n"
        "  1. A direct answer in Markdown (bullets / short code blocks ok).\n"
        "  2. A final 'Sources:' section. Format each source as a bullet:\n"
        "       - path/to/file.py:120-180\n"
        "     Use the exact path returned by your tools (do NOT prefix with the repo URL).\n"
        "  3. If no relevant evidence was found, give a one-line refusal and write 'Sources: none.'"
    )
    return "\n\n".join(sections)


def _extract_citations(text: str) -> list[Citation]:
    seen: set[tuple[str, int, int]] = set()
    citations: list[Citation] = []
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
        citations.append(Citation(path=path, start_line=s, end_line=e))
    return citations


def _looks_like_refusal(text: str) -> bool:
    lowered = text.lower()
    needles = (
        "sources: none",
        "could not find",
        "no relevant evidence",
        "outside the scope",
        "not in this repository",
        "unable to find",
    )
    return any(n in lowered for n in needles)


class SingleAgentRunner(AgentRunner):
    def __init__(self, settings: Settings, memory: MemoryStore) -> None:
        self.settings = settings
        self.memory = memory
        self._llm = make_llm(settings)
        self._tools = build_tools(settings)

    def _build_crew(self, question: str, history: str) -> Crew:
        agent = Agent(
            role="Codebase Researcher",
            goal=(
                "Answer the user's question about the indexed codebase, citing "
                "every claim with exact file paths and line ranges."
            ),
            backstory=SYSTEM_BACKSTORY,
            tools=self._tools,
            llm=self._llm,
            verbose=False,
            allow_delegation=False,
            max_iter=self.settings.researcher_max_iters,
        )
        task = Task(
            description=_build_task_description(question, history),
            expected_output=(
                "A grounded answer in Markdown ending with a 'Sources:' section "
                "that lists each cited file with a line range."
            ),
            agent=agent,
        )
        return Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

    async def run(self, request: RunRequest) -> RunResult:
        history = ""
        if request.session_id:
            history = self.memory.context_summary(request.session_id)

        crew = self._build_crew(request.question, history)

        try:
            result = await asyncio.to_thread(crew.kickoff)
        except Exception as e:
            log.exception("Agent run failed")
            return RunResult(
                answer=f"The agent encountered an error: `{type(e).__name__}: {e}`.",
                citations=[],
                events=[],
                refused=True,
            )

        answer = str(result).strip()
        citations = _extract_citations(answer)
        refused = _looks_like_refusal(answer) and not citations

        if request.session_id:
            self.memory.append(request.session_id, Turn(role="user", content=request.question))
            self.memory.append(request.session_id, Turn(role="assistant", content=answer))

        return RunResult(
            answer=answer,
            citations=citations,
            events=[],  # populated by Phase-2 trace collector
            refused=refused,
        )
