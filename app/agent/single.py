"""Single-agent runner — the **core** agent shape.

One CrewAI agent has access to all four tools and decides per-query which to
call. The system prompt enforces (a) citation of every factual claim with a
`path:start-end` reference and (b) explicit refusal when tools can't find
evidence.

A fresh `LiveTrace` is created per request so the FastAPI handler can return
the agent's tool-call timeline alongside the answer (no concurrent-request
bleed). The Phase-2 streaming bonus reuses the same hook.
"""

from __future__ import annotations

import asyncio
import logging

from crewai import Agent, Crew, Process, Task

from app.agent._extract import extract_citations, looks_like_refusal
from app.agent.base import AgentRunner, RunRequest, RunResult
from app.agent.llm import make_llm
from app.agent.tools.registry import build_tools
from app.memory.base import MemoryStore, Turn
from app.settings import Settings
from app.trace.live import LiveTrace

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


class SingleAgentRunner(AgentRunner):
    def __init__(self, settings: Settings, memory: MemoryStore) -> None:
        self.settings = settings
        self.memory = memory
        self._llm = make_llm(settings)

    def _build_crew(self, question: str, history: str, trace: LiveTrace) -> Crew:
        # Tools are rebuilt per request so each request gets its own trace
        # collector — no event bleed between concurrent users.
        tools = build_tools(self.settings, trace=trace)
        agent = Agent(
            role="Codebase Researcher",
            goal=(
                "Answer the user's question about the indexed codebase, citing "
                "every claim with exact file paths and line ranges."
            ),
            backstory=SYSTEM_BACKSTORY,
            tools=tools,
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

    async def run(self, request: RunRequest, trace: LiveTrace | None = None) -> RunResult:
        history = ""
        if request.session_id:
            history = self.memory.context_summary(request.session_id)

        if trace is None:
            trace = LiveTrace()
        crew = self._build_crew(request.question, history, trace)

        log.info("agent run started — question=%r", request.question[:120])
        try:
            result = await asyncio.to_thread(crew.kickoff)
        except Exception as e:
            log.exception("Agent run failed")
            return RunResult(
                answer=f"The agent encountered an error: `{type(e).__name__}: {e}`.",
                citations=[],
                events=trace.events(),
                refused=True,
            )

        answer = str(result).strip()
        citations = extract_citations(answer)
        refused = looks_like_refusal(answer) and not citations
        events = trace.events()
        log.info("agent run finished — %d tool calls, %d citations, refused=%s",
                 sum(1 for e in events if e.kind == "tool_call"),
                 len(citations), refused)

        if request.session_id:
            self.memory.append(request.session_id, Turn(role="user", content=request.question))
            self.memory.append(request.session_id, Turn(role="assistant", content=answer))

        return RunResult(
            answer=answer,
            citations=citations,
            events=events,
            refused=refused,
        )
