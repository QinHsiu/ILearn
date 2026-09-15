"""Free OpenAI-compatible LLM endpoints for Socrates / TutorAgent.

Platforms and defaults follow ``doc/free/free.txt``. Explicit
``ILEARN_LLM_*`` settings always win; otherwise the first configured
provider key is used.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FreeProvider:
    name: str
    env_keys: tuple[str, ...]
    base_url: str
    default_model: str


@dataclass(frozen=True)
class ResolvedLLM:
    provider: str
    api_key: str
    base_url: str | None
    model: str


FREE_PROVIDERS: tuple[FreeProvider, ...] = (
    FreeProvider(
        name="openrouter",
        env_keys=("OPENROUTER_API_KEY", "ILEARN_OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        default_model="deepseek/deepseek-chat-v3.1:free",
    ),
    FreeProvider(
        name="groq",
        env_keys=("GROQ_API_KEY", "ILEARN_GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
    ),
    FreeProvider(
        name="cerebras",
        env_keys=("CEREBRAS_API_KEY", "ILEARN_CEREBRAS_API_KEY"),
        base_url="https://api.cerebras.ai/v1",
        default_model="llama-3.3-70b",
    ),
    FreeProvider(
        name="gemini",
        env_keys=("GEMINI_API_KEY", "GOOGLE_API_KEY", "ILEARN_GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-2.5-flash",
    ),
    FreeProvider(
        name="deepseek",
        env_keys=("DEEPSEEK_API_KEY", "ILEARN_DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
    ),
    FreeProvider(
        name="mistral",
        env_keys=("MISTRAL_API_KEY", "ILEARN_MISTRAL_API_KEY"),
        base_url="https://api.mistral.ai/v1",
        default_model="mistral-small-latest",
    ),
    FreeProvider(
        name="github",
        env_keys=("GITHUB_MODELS_TOKEN", "GITHUB_TOKEN"),
        base_url="https://models.github.ai/inference",
        default_model="openai/gpt-4o",
    ),
    FreeProvider(
        name="huggingface",
        env_keys=("HF_TOKEN", "HUGGINGFACE_API_KEY", "ILEARN_HF_TOKEN"),
        base_url="https://router.huggingface.co/v1",
        default_model="Qwen/Qwen2.5-7B-Instruct",
    ),
)

_PROVIDER_BY_NAME = {item.name: item for item in FREE_PROVIDERS}


def _env(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return raw.strip()


def _first_key(env_keys: tuple[str, ...]) -> str | None:
    for name in env_keys:
        value = _env(name)
        if value:
            return value
    return None


def _from_provider(spec: FreeProvider, *, model_override: str | None = None) -> ResolvedLLM | None:
    api_key = _first_key(spec.env_keys)
    if not api_key:
        return None
    return ResolvedLLM(
        provider=spec.name,
        api_key=api_key,
        base_url=spec.base_url,
        model=model_override or spec.default_model,
    )


def resolve_free_llm() -> ResolvedLLM | None:
    """Resolve a single LLM endpoint: explicit ILearn key, then free catalog."""
    model_override = _env("ILEARN_LLM_MODEL")
    ilearn_key = _env("ILEARN_LLM_API_KEY")
    if ilearn_key:
        return ResolvedLLM(
            provider="ilearn",
            api_key=ilearn_key,
            base_url=_env("ILEARN_LLM_BASE_URL"),
            model=model_override or "gpt-4o-mini",
        )

    requested = (_env("ILEARN_LLM_PROVIDER") or "").strip().lower()
    if requested:
        spec = _PROVIDER_BY_NAME.get(requested)
        if spec is None:
            return None
        return _from_provider(spec, model_override=model_override)

    for spec in FREE_PROVIDERS:
        resolved = _from_provider(spec, model_override=model_override)
        if resolved:
            return resolved
    return None


def _provider_order() -> list[FreeProvider]:
    named = [p.strip().lower() for p in (_env("ILEARN_LLM_PROVIDERS") or "").split(",") if p.strip()]
    requested = (_env("ILEARN_LLM_PROVIDER") or "").strip().lower()
    if requested:
        named = [requested, *[n for n in named if n != requested]]
    if named:
        ordered = [_PROVIDER_BY_NAME[n] for n in named if n in _PROVIDER_BY_NAME]
        rest = [p for p in FREE_PROVIDERS if p.name not in {x.name for x in ordered}]
        return ordered + rest
    return list(FREE_PROVIDERS)


def resolve_free_llm_chain() -> list[ResolvedLLM]:
    """All configured free providers, used as a failover chain."""
    primary = resolve_free_llm()
    if primary and primary.provider == "ilearn":
        return [primary]

    model_override = _env("ILEARN_LLM_MODEL")
    chain: list[ResolvedLLM] = []
    seen: set[str] = set()
    for spec in _provider_order():
        resolved = _from_provider(spec, model_override=model_override)
        if resolved and resolved.provider not in seen:
            seen.add(resolved.provider)
            chain.append(resolved)
    return chain


class FreeLLMGateway:
    """In-process failover across free OpenAI-compatible providers.

    This is the lightweight alternative to deploying an extra gateway
    (e.g. neurogate): try Groq / OpenRouter / others in order, then
    let TutorAgent fall back to the rule engine.
    """

    def __init__(self, clients: list[object] | None = None) -> None:
        self._clients = list(clients or [])

    @classmethod
    def from_env(cls) -> FreeLLMGateway:
        from ilearn.providers.llm import LLMClient

        clients = [
            LLMClient(
                base_url=item.base_url,
                api_key=item.api_key,
                model=item.model,
            )
            for item in resolve_free_llm_chain()
        ]
        return cls(clients)

    def available(self) -> bool:
        return any(getattr(client, "available", lambda: False)() for client in self._clients)

    def chat_text(self, system: str, user: str) -> str:
        from ilearn.providers.llm import LLMError

        last_error: Exception | None = None
        for client in self._clients:
            if not getattr(client, "available", lambda: False)():
                continue
            try:
                return client.chat_text(system, user)
            except Exception as exc:
                last_error = exc
                continue
        raise LLMError(f"all free LLM providers failed: {last_error}") from last_error
