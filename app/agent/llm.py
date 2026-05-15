"""Provider-agnostic LLM factory.

Any provider supported by LiteLLM works — just set `LLM_MODEL` to the
appropriate string (e.g. `gemini/gemini-1.5-flash`, `openai/gpt-4o-mini`,
`openrouter/anthropic/claude-3.5-sonnet`, `ollama/qwen2.5-coder:7b`).
API keys are read by LiteLLM from standard env var names.
"""

from __future__ import annotations

from crewai import LLM

from app.settings import Settings


def make_llm(s: Settings) -> LLM:
    kwargs: dict = {
        "model": s.llm_model,
        "temperature": s.llm_temperature,
        "timeout": s.llm_timeout_s,
    }
    if s.llm_api_base:
        kwargs["api_base"] = s.llm_api_base
    if s.llm_max_tokens:
        kwargs["max_tokens"] = s.llm_max_tokens
    return LLM(**kwargs)
