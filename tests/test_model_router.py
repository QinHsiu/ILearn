from ilearn.providers.model_registry import MODEL_REGISTRY, ModelCapability, ModelConfig, ModelTier
from ilearn.providers.model_router import ModelRouter, RoutingContext, TaskType
from ilearn.providers.model_routing_config import ModelRoutingConfig, RoutingDefaults, RoutingFallback


def _router(**kwargs) -> ModelRouter:
    cfg = ModelRoutingConfig(
        defaults=RoutingDefaults(max_latency_ms=5000, max_cost_per_call=0.05),
        overrides=kwargs.get("overrides", {}),
        fallback=RoutingFallback(enabled=True, default="gpt-4o-mini"),
    )
    return ModelRouter(config=cfg, registry=MODEL_REGISTRY)


def test_override_wins_for_tutoring():
    router = _router(overrides={"tutoring": "gpt-4.1"})
    decision = router.route(
        RoutingContext(task_type=TaskType.TUTORING, input_text="hint please")
    )
    assert decision.model_name == "gpt-4.1"


def test_unknown_override_falls_through_to_rules():
    router = _router(overrides={"diagnosis": "not-a-real-model"})
    decision = router.route(
        RoutingContext(task_type=TaskType.DIAGNOSIS, input_text="diagnose")
    )
    assert decision.model_name in MODEL_REGISTRY
    assert decision.model_name != "not-a-real-model"
    assert MODEL_REGISTRY[decision.model_name].tier == ModelTier.PREMIUM


def test_grading_objective_allows_lite():
    router = _router(overrides={})
    decision = router.route(
        RoutingContext(task_type=TaskType.GRADING_OBJECTIVE, input_text="1+1")
    )
    assert decision.model_name in MODEL_REGISTRY
    assert decision.model_config.tier in (ModelTier.LITE, ModelTier.STANDARD, ModelTier.PREMIUM)


def test_fallback_when_registry_filtered_empty():
    tiny = {
        "tiny": ModelConfig(
            name="tiny",
            tier=ModelTier.LITE,
            capabilities=(ModelCapability.INSTRUCTION,),
            context_window=10,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
            avg_latency_ms=1,
        ),
        "gpt-4o-mini": MODEL_REGISTRY["gpt-4o-mini"],
    }
    cfg = ModelRoutingConfig(
        overrides={},
        fallback=RoutingFallback(default="gpt-4o-mini"),
    )
    router = ModelRouter(config=cfg, registry=tiny)
    decision = router.route(
        RoutingContext(
            task_type=TaskType.REPORT_SUMMARY,
            input_text="这是一段足够长的中文输入用来挤爆极小上下文窗口" * 20,
        )
    )
    assert decision.model_name == "gpt-4o-mini"
