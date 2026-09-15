"""Free OpenAI-compatible provider resolution for Socrates / TutorAgent."""

from unittest.mock import MagicMock

import pytest

from ilearn.core.settings import clear_settings_cache, load_settings
from ilearn.providers.free_llm import (
    FREE_PROVIDERS,
    resolve_free_llm,
    resolve_free_llm_chain,
)

_FREE_KEY_ENVS = (
    "ILEARN_LLM_API_KEY",
    "ILEARN_LLM_BASE_URL",
    "ILEARN_LLM_MODEL",
    "ILEARN_LLM_PROVIDER",
    "ILEARN_LLM_PROVIDERS",
    "OPENROUTER_API_KEY",
    "ILEARN_OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "ILEARN_GROQ_API_KEY",
    "CEREBRAS_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "GITHUB_MODELS_TOKEN",
    "GITHUB_TOKEN",
    "HF_TOKEN",
    "HUGGINGFACE_API_KEY",
)


def _clear_llm_env(monkeypatch) -> None:
    for name in _FREE_KEY_ENVS:
        monkeypatch.delenv(name, raising=False)


def test_catalog_covers_doc_platforms():
    names = {item.name for item in FREE_PROVIDERS}
    assert names >= {
        "openrouter",
        "groq",
        "cerebras",
        "gemini",
        "deepseek",
        "mistral",
        "github",
        "huggingface",
    }


def test_resolve_prefers_explicit_ilearn_key(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ILEARN_LLM_API_KEY", "sk-ilearn")
    monkeypatch.setenv("ILEARN_LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("ILEARN_LLM_MODEL", "custom-model")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-ignored")
    resolved = resolve_free_llm()
    assert resolved is not None
    assert resolved.api_key == "sk-ilearn"
    assert resolved.base_url == "https://example.com/v1"
    assert resolved.model == "custom-model"
    assert resolved.provider == "ilearn"


def test_resolve_groq_when_ilearn_key_missing(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    resolved = resolve_free_llm()
    assert resolved is not None
    assert resolved.provider == "groq"
    assert resolved.api_key == "gsk-test"
    assert resolved.base_url == "https://api.groq.com/openai/v1"
    assert "llama" in resolved.model.lower()


def test_resolve_respects_provider_override(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setenv("ILEARN_LLM_PROVIDER", "openrouter")
    resolved = resolve_free_llm()
    assert resolved is not None
    assert resolved.provider == "openrouter"
    assert resolved.base_url == "https://openrouter.ai/api/v1"
    assert resolved.model.endswith(":free")


def test_resolve_chain_skips_missing_keys(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test")
    chain = resolve_free_llm_chain()
    assert [item.provider for item in chain] == ["openrouter", "deepseek"]


def test_gateway_failsover_to_next_provider():
    from ilearn.providers.free_llm import FreeLLMGateway
    from ilearn.providers.llm import LLMError

    failing = MagicMock()
    failing.available.return_value = True
    failing.chat_text.side_effect = LLMError("quota")
    working = MagicMock()
    working.available.return_value = True
    working.chat_text.return_value = "分母相同了吗？"
    gateway = FreeLLMGateway([failing, working])
    assert gateway.chat_text("sys", "user") == "分母相同了吗？"
    failing.chat_text.assert_called_once()
    working.chat_text.assert_called_once()


def test_gateway_raises_when_all_fail():
    from ilearn.providers.free_llm import FreeLLMGateway
    from ilearn.providers.llm import LLMError

    failing = MagicMock()
    failing.available.return_value = True
    failing.chat_text.side_effect = LLMError("down")
    gateway = FreeLLMGateway([failing])
    with pytest.raises(LLMError, match="all free LLM providers failed"):
        gateway.chat_text("sys", "user")


def test_load_settings_picks_up_free_provider(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-settings")
    clear_settings_cache()
    settings = load_settings()
    assert settings.llm_api_key == "gsk-settings"
    assert settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert settings.llm_provider == "groq"
