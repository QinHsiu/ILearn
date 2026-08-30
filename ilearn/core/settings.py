"""Central ILearn settings loaded from ILEARN_* environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ILearnSettings(BaseModel):
    """ILearn global configuration (env prefix ILEARN_)."""

    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    vision_model: str | None = None

    mastery_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_hint_per_question: int = Field(default=3, ge=0)

    data_dir: str = "data"
    knowledge_graph_path: str = "data/knowledge_graph.json"
    cognitive_skills_path: str = "data/cognitive_skills.json"
    progress_mapping_path: str = "data/curriculum/progress_mapping.json"
    sessions_dir: str | None = None

    retriever_backend: str = "keyword"
    api_base: str = "http://127.0.0.1:8000"

    rate_limit_enabled: bool = True
    rate_limit_max_requests: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    request_timeout: int = Field(default=30, ge=1)
    max_concurrent_requests: int = Field(default=10, ge=1)

    parent_username: str = "parent-demo"
    parent_password: str = "parent-demo-password"
    parent_user_id: str = "parent-demo"
    teacher_username: str = "teacher-demo"
    teacher_password: str = "teacher-demo-password"
    teacher_user_id: str = "teacher-demo"

    def resolve_path(self, relative: str) -> Path:
        path = Path(relative)
        if path.is_absolute():
            return path
        return _PROJECT_ROOT / path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_optional(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    return raw


def load_settings() -> ILearnSettings:
    """Build settings from the current process environment."""
    return ILearnSettings(
        llm_base_url=_env_optional("ILEARN_LLM_BASE_URL"),
        llm_api_key=_env_optional("ILEARN_LLM_API_KEY"),
        llm_model=os.getenv("ILEARN_LLM_MODEL") or "gpt-4o-mini",
        vision_model=_env_optional("ILEARN_VISION_MODEL"),
        mastery_threshold=float(os.getenv("ILEARN_MASTERY_THRESHOLD", "0.7")),
        max_hint_per_question=int(os.getenv("ILEARN_MAX_HINT_PER_QUESTION", "3")),
        data_dir=os.getenv("ILEARN_DATA_DIR", "data"),
        knowledge_graph_path=os.getenv(
            "ILEARN_KNOWLEDGE_GRAPH_PATH", "data/knowledge_graph.json"
        ),
        cognitive_skills_path=os.getenv(
            "ILEARN_COGNITIVE_SKILLS_PATH", "data/cognitive_skills.json"
        ),
        progress_mapping_path=os.getenv(
            "ILEARN_PROGRESS_MAPPING_PATH",
            "data/curriculum/progress_mapping.json",
        ),
        sessions_dir=_env_optional("ILEARN_SESSIONS_DIR"),
        retriever_backend=os.getenv("ILEARN_RETRIEVER_BACKEND", "keyword"),
        api_base=os.getenv("ILEARN_API_BASE", "http://127.0.0.1:8000"),
        rate_limit_enabled=_env_bool("ILEARN_RATE_LIMIT_ENABLED", True),
        rate_limit_max_requests=int(os.getenv("ILEARN_RATE_LIMIT_MAX_REQUESTS", "100")),
        rate_limit_window_seconds=int(
            os.getenv("ILEARN_RATE_LIMIT_WINDOW_SECONDS", "60")
        ),
        request_timeout=int(os.getenv("ILEARN_REQUEST_TIMEOUT", "30")),
        max_concurrent_requests=int(os.getenv("ILEARN_MAX_CONCURRENT_REQUESTS", "10")),
        parent_username=os.getenv("ILEARN_PARENT_USERNAME", "parent-demo"),
        parent_password=os.getenv("ILEARN_PARENT_PASSWORD", "parent-demo-password"),
        parent_user_id=os.getenv("ILEARN_PARENT_USER_ID", "parent-demo"),
        teacher_username=os.getenv("ILEARN_TEACHER_USERNAME", "teacher-demo"),
        teacher_password=os.getenv("ILEARN_TEACHER_PASSWORD", "teacher-demo-password"),
        teacher_user_id=os.getenv("ILEARN_TEACHER_USER_ID", "teacher-demo"),
    )


@lru_cache(maxsize=1)
def get_settings() -> ILearnSettings:
    return load_settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
