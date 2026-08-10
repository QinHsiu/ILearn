"""OpenAI-compatible LLM client for ILearn."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


class LLMError(Exception):
    """Raised when the LLM client cannot complete a request."""


def _strip_json_fences(text: str) -> str:
    """Remove optional ```json ... ``` wrappers from model output."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    first_newline = stripped.find("\n")
    if first_newline == -1:
        return stripped.strip("`").removeprefix("json").strip()
    body = stripped[first_newline + 1 :]
    if body.rstrip().endswith("```"):
        body = body.rstrip()[:-3]
    return body.strip()


def _parse_json_content(content: str) -> dict[str, Any]:
    data = json.loads(_strip_json_fences(content))
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


class LLMClient:
    """Thin wrapper around an OpenAI-compatible chat completions API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"
        self._client: OpenAI | None = None

    @classmethod
    def from_env(cls) -> LLMClient:
        return cls(
            base_url=os.getenv("ILEARN_LLM_BASE_URL") or None,
            api_key=os.getenv("ILEARN_LLM_API_KEY") or None,
            model=os.getenv("ILEARN_LLM_MODEL") or None,
        )

    def available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self) -> OpenAI:
        if not self.available():
            raise LLMError("LLM client is not available (missing API key)")
        if self._client is None:
            kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def _call_chat(self, system: str, user: str) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMError("empty response from LLM")
        return content

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        """Request a chat completion and parse a JSON object from the reply."""
        last_error: Exception | None = None
        for _ in range(2):
            try:
                content = self._call_chat(system, user)
                return _parse_json_content(content)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
        raise LLMError(
            f"failed to parse JSON from LLM response after retry: {last_error}"
        )
