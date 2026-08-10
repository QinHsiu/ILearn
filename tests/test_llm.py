from unittest.mock import MagicMock, patch

import pytest

from ilearn.providers.llm import LLMClient, LLMError, _parse_json_content, _strip_json_fences


def test_available_false_without_key(monkeypatch):
    monkeypatch.delenv("ILEARN_LLM_API_KEY", raising=False)
    assert LLMClient.from_env().available() is False


def test_available_false_with_empty_key():
    assert LLMClient(api_key="").available() is False
    assert LLMClient(api_key="   ").available() is False


def test_available_true_with_key():
    assert LLMClient(api_key="sk-test").available() is True


def test_from_env_reads_config(monkeypatch):
    monkeypatch.setenv("ILEARN_LLM_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("ILEARN_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("ILEARN_LLM_MODEL", "test-model")
    client = LLMClient.from_env()
    assert client.base_url == "https://example.com/v1"
    assert client.api_key == "sk-test"
    assert client.model == "test-model"
    assert client.available() is True


def test_chat_json_raises_when_unavailable():
    client = LLMClient(api_key=None)
    with pytest.raises(LLMError, match="not available"):
        client.chat_json("system", "user")


def test_strip_json_fences():
    assert _strip_json_fences('{"a": 1}') == '{"a": 1}'
    assert _strip_json_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _strip_json_fences('```\n{"a": 1}\n```') == '{"a": 1}'


def test_parse_json_content_rejects_non_object():
    with pytest.raises(ValueError, match="expected JSON object"):
        _parse_json_content("[1, 2, 3]")


def _mock_completion(content: str) -> MagicMock:
    response = MagicMock()
    response.choices[0].message.content = content
    return response


@patch("ilearn.providers.llm.OpenAI")
def test_chat_json_parses_plain_json(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_completion('{"score": 1}')

    client = LLMClient(api_key="sk-test", model="test-model")
    result = client.chat_json("grade", "answer")

    assert result == {"score": 1}
    mock_client.chat.completions.create.assert_called_once_with(
        model="test-model",
        messages=[
            {"role": "system", "content": "grade"},
            {"role": "user", "content": "answer"},
        ],
    )


@patch("ilearn.providers.llm.OpenAI")
def test_chat_json_strips_markdown_fences(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = _mock_completion(
        '```json\n{"ok": true}\n```'
    )

    client = LLMClient(api_key="sk-test")
    assert client.chat_json("s", "u") == {"ok": True}


@patch("ilearn.providers.llm.OpenAI")
def test_chat_json_retries_on_json_parse_failure(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        _mock_completion("not json"),
        _mock_completion('{"retried": true}'),
    ]

    client = LLMClient(api_key="sk-test")
    assert client.chat_json("s", "u") == {"retried": True}
    assert mock_client.chat.completions.create.call_count == 2


@patch("ilearn.providers.llm.OpenAI")
def test_chat_json_raises_after_two_parse_failures(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.side_effect = [
        _mock_completion("still not json"),
        _mock_completion("{bad json"),
    ]

    client = LLMClient(api_key="sk-test")
    with pytest.raises(LLMError, match="after retry"):
        client.chat_json("s", "u")
    assert mock_client.chat.completions.create.call_count == 2
