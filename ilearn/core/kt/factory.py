"""KT service factory — select backend by configuration."""

from __future__ import annotations

import logging
from typing import Any

from .bkt import BKTKnowledgeTracing
from .protocol import KnowledgeTracingService

logger = logging.getLogger(__name__)

try:
    from .pykt_adapter import PyKTKnowledgeTracing

    PY_KT_AVAILABLE = True
except ImportError:
    PY_KT_AVAILABLE = False
    PyKTKnowledgeTracing = None  # type: ignore[misc, assignment]


def create_kt_service(
    backend: str = "bkt",
    checkpoint_path: str | None = None,
    concept_map: dict[str, int] | None = None,
    bkt_params: dict[str, float] | None = None,
    **kwargs: Any,
) -> KnowledgeTracingService:
    """Create a KT service instance."""
    if backend == "bkt":
        params = {
            "p_l0": 0.5,
            "p_t": 0.1,
            "p_s": 0.1,
            "p_g": 0.2,
        }
        if bkt_params:
            params.update(bkt_params)
        return BKTKnowledgeTracing(**params)

    if backend == "pykt":
        if not PY_KT_AVAILABLE:
            logger.warning("pyKT not available, falling back to BKT")
            return create_kt_service("bkt", bkt_params=bkt_params)

        if not checkpoint_path:
            raise ValueError("pyKT backend requires checkpoint_path")
        if not concept_map:
            raise ValueError("pyKT backend requires concept_map")
        if PyKTKnowledgeTracing is None:
            raise ImportError("PyKTKnowledgeTracing not available")

        return PyKTKnowledgeTracing(
            checkpoint_path=checkpoint_path,
            concept_map=concept_map,
            **kwargs,
        )

    raise ValueError(f"Unknown KT backend: {backend}")


def create_kt_service_from_session(
    session: object,
    backend: str = "bkt",
    **kwargs: Any,
) -> KnowledgeTracingService:
    """Restore KT service from session metadata when present."""
    service = create_kt_service(backend, **kwargs)

    try:
        metadata = getattr(session, "metadata", None)
        if metadata and isinstance(metadata, dict):
            enhanced = metadata.get("enhanced", {})
            if isinstance(enhanced, dict):
                kt_state = enhanced.get("kt", {})
                if kt_state:
                    service.load_state(kt_state)
                    logger.debug("Loaded KT state from session")
    except Exception as exc:
        logger.warning("Failed to load KT state from session: %s", exc)

    return service
