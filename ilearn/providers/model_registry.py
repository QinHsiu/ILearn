from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModelTier(Enum):
    LITE = "lite"
    STANDARD = "standard"
    PREMIUM = "premium"


class ModelCapability(Enum):
    REASONING = "reasoning"
    CODE = "code"
    INSTRUCTION = "instruction"
    MULTILINGUAL = "multilingual"
    VISION = "vision"


@dataclass(frozen=True)
class ModelConfig:
    name: str
    tier: ModelTier
    capabilities: tuple[ModelCapability, ...]
    context_window: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    avg_latency_ms: int
    provider: str = "openai"


MODEL_REGISTRY: dict[str, ModelConfig] = {
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        tier=ModelTier.LITE,
        capabilities=(ModelCapability.INSTRUCTION, ModelCapability.MULTILINGUAL),
        context_window=128000,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        avg_latency_ms=800,
    ),
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        tier=ModelTier.STANDARD,
        capabilities=(
            ModelCapability.REASONING,
            ModelCapability.INSTRUCTION,
            ModelCapability.MULTILINGUAL,
            ModelCapability.VISION,
        ),
        context_window=128000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        avg_latency_ms=2500,
    ),
    "gpt-4.1": ModelConfig(
        name="gpt-4.1",
        tier=ModelTier.PREMIUM,
        capabilities=(
            ModelCapability.REASONING,
            ModelCapability.CODE,
            ModelCapability.INSTRUCTION,
            ModelCapability.MULTILINGUAL,
            ModelCapability.VISION,
        ),
        context_window=1048576,
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.008,
        avg_latency_ms=3500,
    ),
}
