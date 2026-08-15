from ilearn.providers.llm import LLMError
from ilearn.providers.model_router import TaskType
from ilearn.providers.smart_llm import SmartLLMClient


class FakeLLM:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self.calls: list[str] = []
        self.fail_models: set[str] = set()

    def chat_json(self, system: str, user: str) -> dict:
        self.calls.append(self.model)
        if self.model in self.fail_models:
            raise LLMError(f"boom:{self.model}")
        return {"ok": True, "model": self.model}


def test_chat_json_uses_routed_override_model():
    from ilearn.providers.model_router import ModelRouter
    from ilearn.providers.model_routing_config import (
        ModelRoutingConfig,
        RoutingFallback,
    )

    fake = FakeLLM(model="gpt-4o-mini")
    router = ModelRouter(
        config=ModelRoutingConfig(
            overrides={"tutoring": "gpt-4.1"},
            fallback=RoutingFallback(default="gpt-4o-mini"),
        )
    )
    client = SmartLLMClient(llm=fake, router=router)  # type: ignore[arg-type]
    result = client.chat_json(TaskType.TUTORING, "sys", "user")
    assert result["model"] == "gpt-4.1"
    assert fake.calls == ["gpt-4.1"]
    assert fake.model == "gpt-4o-mini"  # restored


def test_chat_json_falls_back_on_llm_error():
    from ilearn.providers.model_router import ModelRouter
    from ilearn.providers.model_routing_config import (
        ModelRoutingConfig,
        RoutingFallback,
    )

    fake = FakeLLM(model="gpt-4o-mini")
    fake.fail_models.add("gpt-4.1")
    router = ModelRouter(
        config=ModelRoutingConfig(
            overrides={"tutoring": "gpt-4.1"},
            fallback=RoutingFallback(enabled=True, default="gpt-4o-mini"),
        )
    )
    client = SmartLLMClient(llm=fake, router=router)  # type: ignore[arg-type]
    result = client.chat_json(TaskType.TUTORING, "sys", "user")
    assert result["model"] == "gpt-4o-mini"
    assert fake.calls == ["gpt-4.1", "gpt-4o-mini"]
