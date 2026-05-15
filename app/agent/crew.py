"""Multi-agent runner — the **bonus** crew shape.

Four specialized agents in a sequential pipeline, each with a focused goal
and a subset of the tools:

  Planner          (no tools)            classify the question, write a brief plan
  Researcher       (search / read / ls)  execute code-level lookups
  Module Expert    (summarize / read)    optionally produce a high-level overview
  Synthesizer      (no tools)            write the final cited answer

Each agent's output flows into the next via Task.context. agent_started /
agent_finished events get pushed into the same trace collector that tools
use, so the UI shows a per-agent timeline alongside per-tool calls.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from crewai import Agent, Crew, Process, Task

from app.agent._extract import extract_citations, looks_like_refusal
from app.agent.base import AgentRunner, RunRequest, RunResult, TraceEvent
from app.agent.llm import make_llm
from app.agent.tools.registry import build_tools
from app.memory.base import MemoryStore, Turn
from app.settings import Settings
from app.trace.live import LiveTrace

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent backstories
# ---------------------------------------------------------------------------

PLANNER_BACKSTORY = """\
You are a research planner. You receive a user question about a Python
codebase. Your job is to produce a SHORT plan that the rest of the team
can act on. You do not have tools — you only think.

Output a compact plan in this exact format:

  Classification: <structural | behavioral | module-level | out-of-scope>
  Strategy: <one sentence>
  Search hints: <1-3 short queries the Researcher should try>
  Module overview needed: <true | false>
  Reasoning: <one sentence why>

Rules:
- Use "out-of-scope" if the question is not about this Python codebase.
- "Module overview needed: true" only if the user asks for a high-level
  explanation of a module/class (e.g. "what does X do", "explain Y module").
"""

RESEARCHER_BACKSTORY = """\
You are a code researcher with three tools: search_code, read_file, list_directory.
You receive a Plan from the Planner. Execute the research it calls for.

Rules:
- Always start with search_code unless you already know the exact path.
- After a promising search hit, use read_file to see the full function/class.
- Stop after 4-6 tool calls; pass what you have to the Synthesizer.
- Output bullet findings, each with a `path:start-end` ref.
- If searches return nothing relevant, say so plainly. Do NOT guess.
"""

MODULE_EXPERT_BACKSTORY = """\
You produce module-level summaries. You have summarize_module and read_file.

If the Plan says "Module overview needed: false", output exactly:
  NO MODULE OVERVIEW NEEDED

Otherwise, identify the module/class the user is asking about (from the Plan
or the question), call summarize_module, and return a 5-7 bullet overview.
"""

SYNTHESIZER_BACKSTORY = """\
You are the answer synthesizer. You have NO tools — you only write.

You receive: the Plan, the Researcher's findings, and the Module Expert's
overview (which may be "NO MODULE OVERVIEW NEEDED").

Your job: produce the final answer in Markdown.

Rules:
1. Ground every claim in the Researcher / Module Expert outputs.
2. Cite every claim with `path:start-end` line references.
3. End with a "Sources:" section listing each cited file with a line range.
4. If the inputs say no evidence was found, OR the Plan classified the
   question as "out-of-scope", give a one-line refusal and write
   "Sources: none". Do NOT invent code.
5. Keep the answer concise — bullet points, short code blocks.
"""


# ---------------------------------------------------------------------------
# Task description builders
# ---------------------------------------------------------------------------

def _planner_task(question: str, history: str) -> str:
    parts = ["Plan how the team should answer the following question."]
    if history:
        parts.append("Prior conversation (most recent last):\n" + history)
    parts.append(f"Question:\n{question}")
    return "\n\n".join(parts)


_RESEARCHER_TASK = (
    "Carry out the research portion of the Plan above. Use search_code first "
    "to find relevant code, then read_file to fetch full context. Output "
    "bullet findings with `path:start-end` line references."
)

_MODULE_TASK = (
    "Read the Plan above. If 'Module overview needed: true', call "
    "summarize_module on the relevant module/class and produce a 5-7 bullet "
    "overview. Otherwise output exactly: NO MODULE OVERVIEW NEEDED."
)


def _synth_task(question: str, history: str) -> str:
    parts = [
        f"Write the final answer to the user's CURRENT question:\n\n  {question}",
    ]
    if history:
        parts.append(
            "Prior conversation (oldest first; for context if the question refers "
            "back to it):\n" + history
        )
    parts.append(
        "Use the Plan, Researcher findings, and Module Expert overview above "
        "as your sources of truth for any code claims. Format: Markdown body, "
        "then a 'Sources:' section listing each cited file with a line range. "
        "If the question is meta (about prior turns) and needs no code, you may "
        "answer from the conversation context and write 'Sources: none'."
    )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Trace callbacks (push agent_started / agent_finished into LiveTrace)
# ---------------------------------------------------------------------------

def _make_first_step_callback(agent_name: str, trace: LiveTrace):
    fired = [False]

    def cb(_step: Any) -> None:
        if not fired[0]:
            trace.record(TraceEvent("agent_started", {"agent": agent_name}))
            fired[0] = True

    return cb


def _make_task_finished_callback(agent_name: str, trace: LiveTrace):
    def cb(task_output: Any) -> None:
        preview = ""
        try:
            preview = str(task_output).strip().replace("\n", " ")[:200]
        except Exception:
            pass
        trace.record(TraceEvent("agent_finished", {
            "agent": agent_name,
            "output_preview": preview,
        }))

    return cb


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class CrewRunner(AgentRunner):
    def __init__(self, settings: Settings, memory: MemoryStore) -> None:
        self.settings = settings
        self.memory = memory
        self._llm = make_llm(settings)

    def _build_crew(self, question: str, history: str, trace: LiveTrace) -> Crew:
        # Tools rebuilt per request so each request gets its own trace
        # collector — no event bleed between concurrent users.
        search, read, list_dir, summarize = build_tools(self.settings, trace=trace)

        planner = Agent(
            role="Research Planner",
            goal="Decompose the user's question into a brief plan the team can act on.",
            backstory=PLANNER_BACKSTORY,
            tools=[],
            llm=self._llm,
            allow_delegation=False,
            verbose=False,
            max_iter=2,
            step_callback=_make_first_step_callback("Planner", trace),
        )
        researcher = Agent(
            role="Codebase Researcher",
            goal="Gather code-level evidence by calling search_code, read_file, and list_directory.",
            backstory=RESEARCHER_BACKSTORY,
            tools=[search, read, list_dir],
            llm=self._llm,
            allow_delegation=False,
            verbose=False,
            max_iter=self.settings.researcher_max_iters,
            step_callback=_make_first_step_callback("Researcher", trace),
        )
        module_expert = Agent(
            role="Module Expert",
            goal="Produce a high-level overview of a module or class when the plan calls for it.",
            backstory=MODULE_EXPERT_BACKSTORY,
            tools=[summarize, read],
            llm=self._llm,
            allow_delegation=False,
            verbose=False,
            max_iter=2,
            step_callback=_make_first_step_callback("Module Expert", trace),
        )
        synthesizer = Agent(
            role="Answer Synthesizer",
            goal="Write the final cited answer using the team's research.",
            backstory=SYNTHESIZER_BACKSTORY,
            tools=[],
            llm=self._llm,
            allow_delegation=False,
            verbose=False,
            max_iter=2,
            step_callback=_make_first_step_callback("Synthesizer", trace),
        )

        plan_task = Task(
            description=_planner_task(question, history),
            expected_output=(
                "A short plan with: Classification, Strategy, Search hints, "
                "'Module overview needed: true|false', and Reasoning."
            ),
            agent=planner,
            callback=_make_task_finished_callback("Planner", trace),
        )
        research_task = Task(
            description=_RESEARCHER_TASK,
            expected_output="Bullet findings with `path:start-end` references; raw code excerpts where useful.",
            agent=researcher,
            context=[plan_task],
            callback=_make_task_finished_callback("Researcher", trace),
        )
        module_task = Task(
            description=_MODULE_TASK,
            expected_output="A 5-7 bullet module summary OR the literal string 'NO MODULE OVERVIEW NEEDED'.",
            agent=module_expert,
            context=[plan_task],
            callback=_make_task_finished_callback("Module Expert", trace),
        )
        synth_task = Task(
            description=_synth_task(question, history),
            expected_output=(
                "A grounded answer in Markdown ending with a 'Sources:' "
                "section listing each cited file with a line range."
            ),
            agent=synthesizer,
            context=[plan_task, research_task, module_task],
            callback=_make_task_finished_callback("Synthesizer", trace),
        )

        return Crew(
            agents=[planner, researcher, module_expert, synthesizer],
            tasks=[plan_task, research_task, module_task, synth_task],
            process=Process.sequential,
            verbose=False,
        )

    async def run(self, request: RunRequest, trace: LiveTrace | None = None) -> RunResult:
        use_memory = bool(request.options.get(
            "enable_session_memory", self.settings.enable_session_memory,
        ))
        history = ""
        if use_memory and request.session_id:
            history = self.memory.context_summary(request.session_id)

        if trace is None:
            trace = LiveTrace()
        crew = self._build_crew(request.question, history, trace)

        log.info("crew run started — question=%r", request.question[:120])
        try:
            result = await asyncio.to_thread(crew.kickoff)
        except Exception as e:
            log.exception("Crew run failed")
            return RunResult(
                answer=f"The crew encountered an error: `{type(e).__name__}: {e}`.",
                citations=[],
                events=trace.events(),
                refused=True,
            )

        answer = str(result).strip()
        citations = extract_citations(answer)
        refused = looks_like_refusal(answer) and not citations
        events = trace.events()
        log.info(
            "crew run finished — %d agent steps, %d tool calls, %d citations, refused=%s",
            sum(1 for e in events if e.kind == "agent_finished"),
            sum(1 for e in events if e.kind == "tool_call"),
            len(citations),
            refused,
        )

        if use_memory and request.session_id:
            self.memory.append(request.session_id, Turn(role="user", content=request.question))
            self.memory.append(request.session_id, Turn(role="assistant", content=answer))

        return RunResult(
            answer=answer,
            citations=citations,
            events=events,
            refused=refused,
        )
