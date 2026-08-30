"""Feature dependency tiers for offline / hybrid / online transparency."""

from __future__ import annotations

from enum import Enum
from typing import Any


class FeatureTier(str, Enum):
    OFFLINE = "offline"
    HYBRID = "hybrid"
    ONLINE = "online"


class FeatureRegistry:
    """Declare the minimum runtime requirement for product features."""

    FEATURES: dict[str, FeatureTier] = {
        "assessment_generation": FeatureTier.OFFLINE,
        "adaptive_assessment": FeatureTier.OFFLINE,
        "grading": FeatureTier.OFFLINE,
        "diagnosis": FeatureTier.OFFLINE,
        "planning": FeatureTier.OFFLINE,
        "tutor_hint": FeatureTier.HYBRID,
        "llm_enhanced_diagnosis": FeatureTier.ONLINE,
        "llm_item_generation": FeatureTier.ONLINE,
        "pdf_export": FeatureTier.OFFLINE,
        "report_markdown": FeatureTier.OFFLINE,
    }

    @classmethod
    def get_tier(cls, feature_name: str) -> FeatureTier:
        return cls.FEATURES.get(feature_name, FeatureTier.ONLINE)

    @classmethod
    def offline_status(cls) -> dict[str, str]:
        return {name: tier.value for name, tier in cls.FEATURES.items()}

    @classmethod
    def capabilities_payload(cls, *, llm_available: bool) -> dict[str, Any]:
        """API-facing capability document for UI badges."""
        features = []
        for name, tier in cls.FEATURES.items():
            available = True
            if tier == FeatureTier.ONLINE:
                available = llm_available
            elif tier == FeatureTier.HYBRID:
                available = True  # offline rules always work
            features.append(
                {
                    "name": name,
                    "tier": tier.value,
                    "available": available,
                }
            )
        return {
            "llm_available": llm_available,
            "features": features,
            "tiers": cls.offline_status(),
        }
