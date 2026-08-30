"""OpenAI-compatible LLM client for ILearn."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, OpenAIError


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

    _MAX_FALLBACK_DEPTH = 3

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
        self._fallback_depth = 0

    @classmethod
    def from_env(cls) -> LLMClient:
        from ilearn.core.settings import load_settings

        settings = load_settings()
        return cls(
            base_url=settings.llm_base_url or None,
            api_key=settings.llm_api_key or None,
            model=settings.llm_model or None,
        )

    def available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def vision_available(self) -> bool:
        """Return whether an authenticated vision-capable model is configured."""
        from ilearn.core.settings import load_settings

        return self.available() and bool(load_settings().vision_model or self.model)

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
        from ilearn.core.logging_utils import RetryHandler

        def _once() -> str:
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

        try:
            return RetryHandler.with_retry(
                _once,
                max_retries=3,
                delay=0.05,
                exceptions=(OpenAIError, OSError, LLMError),
            )
        except (OpenAIError, OSError, LLMError) as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        fallback: bool = False,
    ) -> dict[str, Any]:
        """Request a chat completion and parse a JSON object from the reply."""
        if not self.available():
            if fallback:
                return self._safe_fallback_json(system, user)
            raise LLMError("LLM client is not available (missing API key)")
        last_error: Exception | None = None
        for _ in range(2):
            try:
                content = self._call_chat(system, user)
                return _parse_json_content(content)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
            except LLMError as exc:
                last_error = exc
                break
        if fallback:
            return self._safe_fallback_json(system, user)
        raise LLMError(
            f"failed to parse JSON from LLM response after retry: {last_error}"
        )

    def _safe_fallback_json(self, system: str, user: str) -> dict[str, Any]:
        if self._fallback_depth >= self._MAX_FALLBACK_DEPTH:
            return {
                "message": "系统目前无法处理您的请求，请稍后再试。",
                "fallback": True,
                "fallback_exhausted": True,
            }
        self._fallback_depth += 1
        try:
            return self._fallback_json(system, user)
        finally:
            self._fallback_depth -= 1

    @staticmethod
    def _fallback_json(system: str, user: str) -> dict[str, Any]:
        """Rule-based JSON when the remote LLM is unavailable (never calls LLM)."""
        blob = f"{system}\n{user}"
        if "题目" in blob or "assessment" in blob.lower() or "items" in blob.lower():
            return {
                "items": [
                    {
                        "stem": "一个苹果分给3个人，每人分到多少？",
                        "type": "choice",
                        "difficulty": "easy",
                        "knowledge_ids": [],
                        "answer_key": "1/3",
                        "choices": ["1/2", "1/3", "1/4", "1/5"],
                    }
                ],
                "fallback": True,
            }
        if "诊断" in blob or "diagnosis" in blob.lower():
            return {
                "mastery": 0.5,
                "weak_skills": [],
                "advice": "建议复习基本概念",
                "fallback": True,
            }
        return {
            "message": "系统目前无法处理您的请求，请稍后再试。",
            "fallback": True,
        }

    def grade_image_json(
        self,
        system: str,
        image_base64: str,
        mime_type: str,
        user: str,
    ) -> dict[str, Any]:
        """Grade an image through an OpenAI-compatible multimodal completion."""
        if not self.vision_available():
            raise LLMError("vision client is not available")

        from ilearn.core.settings import load_settings

        last_error: Exception | None = None
        for _ in range(2):
            try:
                response = self._get_client().chat.completions.create(
                    model=load_settings().vision_model or self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{image_base64}"
                                    },
                                },
                            ],
                        },
                    ],
                )
                content = response.choices[0].message.content
                if not content:
                    raise LLMError("empty response from vision LLM")
                return _parse_json_content(content)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
            except (OpenAIError, OSError) as exc:
                raise LLMError(f"vision LLM request failed: {exc}") from exc
        raise LLMError(
            f"failed to parse JSON from vision LLM response after retry: {last_error}"
        )
