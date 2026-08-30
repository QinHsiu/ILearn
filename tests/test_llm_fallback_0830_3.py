"""LLM fallback behavior."""

from __future__ import annotations

from ilearn.providers.llm import LLMClient


def test_chat_json_fallback_when_unavailable():
    client = LLMClient(api_key=None)
    data = client.chat_json("出题", "请生成题目", fallback=True)
    assert data.get("fallback") is True
    assert "items" in data or "message" in data
