"""Single source of truth for all runtime configuration.

Defaults ship the **core** behavior (no bonuses) so the system satisfies the
brief out of the box. Each bonus is an additive flag.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPO_DIR = DATA_DIR / "repo"
CHROMA_DIR = DATA_DIR / "chroma"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- LLM (provider-agnostic via LiteLLM model strings) -----
    llm_model: str = "gemini/gemini-2.0-flash"
    llm_api_base: str | None = None
    llm_temperature: float = 0.2
    llm_max_tokens: int | None = None
    llm_timeout_s: int = 60

    # ----- Embeddings -----
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_collection: str = "codebase"

    # ----- Target repository -----
    target_repo_url: str = "https://github.com/pallets/flask.git"
    target_repo_ref: str = "main"

    # ----- Retrieval tunables -----
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.0  # informational; agent decides on relevance

    # ----- Agent shape -----
    agent_mode: Literal["single", "crew"] = "single"
    researcher_max_iters: int = 6

    # ----- Bonus toggles (default OFF) -----
    enable_streaming: bool = False
    enable_reasoning_trace: bool = False
    enable_session_memory: bool = False

    # ----- Memory tunables (used only when memory is enabled) -----
    session_max_turns: int = 6
    session_max_sessions: int = 100

    # ----- Paths (computed; not configurable via env) -----
    repo_dir: Path = Field(default=REPO_DIR)
    chroma_dir: Path = Field(default=CHROMA_DIR)


def get_settings() -> Settings:
    """Lazy accessor so tests can monkey-patch env before import."""
    return Settings()


# (touch this comment to trigger uvicorn --reload after changing .env)

