from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ilearn.providers.model_registry import (
    MODEL_REGISTRY,
    ModelCapability,
    ModelConfig,
    ModelTier,
)
from ilearn.providers.model_routing_config import ModelRoutingConfig


class TaskType(Enum):
    GRADING_OBJECTIVE = "grading_objective"
    GRADING_SUBJECTIVE = "grading_subjective"
    DIAGNOSIS = "diagnosis"
    TUTORING = "tutoring"
    PLANNING = "planning"
    REPORT_SUMMARY = "report_summary"
    EXPLANATION = "explanation"


@dataclass
class RoutingContext:
    task_type: TaskType
    input_text: str
    student_grade: int | None = None
    student_mastery: float | None = None
    is_critical: bool = False
    required_capabilities: list[ModelCapability] | None = None
    max_latency_ms: int | None = None
    max_cost: float | None = None


@dataclass
class RoutingDecision:
    model_name: str
    model_config: ModelConfig
    reason: str
    estimated_cost: float
    estimated_latency: int


_TIER_ORDER = [ModelTier.LITE, ModelTier.STANDARD, ModelTier.PREMIUM]

_TASK_RULES: dict[TaskType, dict] = {
    TaskType.GRADING_OBJECTIVE: {
        "min_tier": ModelTier.LITE,
        "need_capabilities": [ModelCapability.INSTRUCTION],
    },
    TaskType.GRADING_SUBJECTIVE: {
        "min_tier": ModelTier.STANDARD,
        "need_capabilities": [ModelCapability.REASONING, ModelCapability.INSTRUCTION],
    },
    TaskType.DIAGNOSIS: {
        "min_tier": ModelTier.PREMIUM,
        "need_capabilities": [ModelCapability.REASONING, ModelCapability.MULTILINGUAL],
    },
    TaskType.TUTORING: {
        "min_tier": ModelTier.PREMIUM,
        "need_capabilities": [
            ModelCapability.REASONING,
            ModelCapability.INSTRUCTION,
            ModelCapability.MULTILINGUAL,
        ],
    },
    TaskType.PLANNING: {
        "min_tier": ModelTier.STANDARD,
        "need_capabilities": [ModelCapability.REASONING, ModelCapability.INSTRUCTION],
    },
    TaskType.REPORT_SUMMARY: {
        "min_tier": ModelTier.STANDARD,
        "need_capabilities": [ModelCapability.INSTRUCTION],
    },
    TaskType.EXPLANATION: {
        "min_tier": ModelTier.STANDARD,
        "need_capabilities": [ModelCapability.REASONING, ModelCapability.INSTRUCTION],
    },
}


def estimate_token_count(text: str) -> int:
    if not text:
        return 0
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4) + 10


class ModelRouter:
    def __init__(
        self,
        config: ModelRoutingConfig | None = None,
        registry: dict[str, ModelConfig] | None = None,
    ) -> None:
        self.config = config or ModelRoutingConfig()
        self.registry = registry or MODEL_REGISTRY
        if self.config.fallback.default not in self.registry:
            raise ValueError(
                f"fallback model not in registry: {self.config.fallback.default}"
            )

    def route(self, context: RoutingContext) -> RoutingDecision:
        override = self.config.overrides.get(context.task_type.value)
        if override and override in self.registry:
            return self._decision(
                override,
                context,
                reason=f"override for {context.task_type.value}",
            )

        candidates = self._select_candidates(context)
        if not candidates:
            fb = self.config.fallback.default
            return self._decision(
                fb, context, reason="fallback: no eligible candidates"
            )

        ranked = self._rank_candidates(candidates, context)
        return self._decision(
            ranked[0],
            context,
            reason=f"task {context.task_type.value} ranked {ranked[0]}",
        )

    def _effective_limits(self, context: RoutingContext) -> tuple[int, float]:
        max_latency = (
            context.max_latency_ms
            if context.max_latency_ms is not None
            else self.config.defaults.max_latency_ms
        )
        max_cost = (
            context.max_cost
            if context.max_cost is not None
            else self.config.defaults.max_cost_per_call
        )
        return max_latency, max_cost

    def _default_output_tokens(self, context: RoutingContext) -> int:
        if context.task_type in (TaskType.PLANNING, TaskType.DIAGNOSIS):
            return 500
        if context.task_type == TaskType.TUTORING:
            return 100
        return 200

    def _select_candidates(self, context: RoutingContext) -> list[str]:
        rule = _TASK_RULES.get(context.task_type)
        if not rule:
            return list(self.registry.keys())

        min_tier = rule["min_tier"]
        need_caps: list[ModelCapability] = rule.get("need_capabilities", [])
        required_caps = context.required_capabilities or []
        max_latency, max_cost = self._effective_limits(context)
        input_tokens = estimate_token_count(context.input_text)
        output_tokens = self._default_output_tokens(context)

        candidates: list[str] = []
        for name, config in self.registry.items():
            if _TIER_ORDER.index(config.tier) < _TIER_ORDER.index(min_tier):
                continue
            if need_caps and not all(c in config.capabilities for c in need_caps):
                continue
            if required_caps and not all(
                c in config.capabilities for c in required_caps
            ):
                continue
            if input_tokens > config.context_window * 0.8:
                continue
            if config.avg_latency_ms > max_latency:
                continue
            if self._estimate_cost(config, context.input_text, output_tokens) > max_cost:
                continue
            candidates.append(name)

        return candidates

    def _rank_candidates(
        self, candidates: list[str], context: RoutingContext
    ) -> list[str]:
        max_latency, max_cost = self._effective_limits(context)
        output_tokens = self._default_output_tokens(context)

        def score(name: str) -> float:
            config = self.registry[name]
            tier_score = {
                ModelTier.LITE: 1.0,
                ModelTier.STANDARD: 2.0,
                ModelTier.PREMIUM: 3.0,
            }[config.tier]

            if context.required_capabilities:
                has_all = all(
                    c in config.capabilities for c in context.required_capabilities
                )
                tier_score += 1.0 if has_all else -1.0

            est_cost = self._estimate_cost(config, context.input_text, output_tokens)
            if est_cost > max_cost:
                tier_score -= 0.5
            if config.avg_latency_ms > max_latency:
                tier_score -= 0.3

            return tier_score

        return sorted(candidates, key=score, reverse=True)

    def _estimate_cost(
        self, config: ModelConfig, input_text: str, output_tokens: int
    ) -> float:
        input_tokens = estimate_token_count(input_text)
        return (input_tokens / 1000) * config.cost_per_1k_input + (
            output_tokens / 1000
        ) * config.cost_per_1k_output

    def _decision(
        self, model_name: str, context: RoutingContext, reason: str
    ) -> RoutingDecision:
        config = self.registry[model_name]
        output_tokens = self._default_output_tokens(context)
        return RoutingDecision(
            model_name=model_name,
            model_config=config,
            reason=reason,
            estimated_cost=self._estimate_cost(config, context.input_text, output_tokens),
            estimated_latency=config.avg_latency_ms,
        )
