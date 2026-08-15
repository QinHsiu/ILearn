from __future__ import annotations

from typing import Any

from ilearn.providers.llm import LLMClient, LLMError
from ilearn.providers.model_router import ModelRouter, RoutingContext, TaskType
from ilearn.providers.model_routing_config import load_model_routing_config


class SmartLLMClient:
    def __init__(
        self,
        llm: LLMClient | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.llm = llm or LLMClient.from_env()
        self.router = router or ModelRouter(config=load_model_routing_config())

    @classmethod
    def from_env(cls) -> SmartLLMClient:
        return cls(
            llm=LLMClient.from_env(),
            router=ModelRouter(config=load_model_routing_config()),
        )

    def chat_json(
        self,
        task_type: TaskType,
        system: str,
        user: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        defaults = self.router.config.defaults
        routing_ctx = RoutingContext(
            task_type=task_type,
            input_text=f"{system}\n{user}",
            student_grade=context.get("grade"),
            student_mastery=context.get("mastery"),
            is_critical=task_type in (TaskType.DIAGNOSIS, TaskType.TUTORING),
            max_latency_ms=context.get("max_latency_ms", defaults.max_latency_ms),
            max_cost=context.get("max_cost", defaults.max_cost_per_call),
        )
        decision = self.router.route(routing_ctx)
        try:
            return self._call_with_model(decision.model_name, system, user)
        except LLMError:
            fb = self.router.config.fallback
            if (
                fb.enabled
                and fb.default != decision.model_name
                and fb.default in self.router.registry
            ):
                return self._call_with_model(fb.default, system, user)
            raise

    def _call_with_model(
        self, model_name: str, system: str, user: str
    ) -> dict[str, Any]:
        llm = self.llm
        if hasattr(llm, "base_url") and hasattr(llm, "api_key"):
            local = LLMClient(
                base_url=llm.base_url, api_key=llm.api_key, model=model_name
            )
            return local.chat_json(system, user)
        previous = getattr(llm, "model", None)
        llm.model = model_name
        try:
            return llm.chat_json(system, user)
        finally:
            llm.model = previous
