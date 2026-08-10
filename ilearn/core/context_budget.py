"""Lightweight context trimming without tokenizer dependencies."""

from __future__ import annotations

from dataclasses import replace

from pydantic import BaseModel

from ilearn.agents.protocol import AgentContext


def _model_size(value: BaseModel) -> int:
    return len(value.model_dump_json())


def _rough_size(ctx: AgentContext) -> int:
    return (
        len(repr(ctx.profile))
        + sum(_model_size(event) for event in ctx.evidence_log)
    )


def trim_context(
    ctx: AgentContext,
    *,
    max_chars: int = 12000,
    max_evidence: int = 40,
) -> AgentContext:
    """Return a new AgentContext with truncated evidence/lists and optional summary."""
    evidence = (
        list(ctx.evidence_log[-max_evidence:])
        if max_evidence > 0
        else []
    )
    grades = list(ctx.grades)
    answers = list(ctx.answers)
    metadata = dict(ctx.metadata)
    trimmed_evidence = len(ctx.evidence_log) - len(evidence)
    trimmed_grades = 0
    trimmed_answers = 0

    out = replace(
        ctx,
        evidence_log=evidence,
        grades=grades,
        answers=answers,
        image_answers=list(ctx.image_answers),
        metadata=metadata,
    )

    while grades and _rough_size(out) > max_chars:
        grades.pop(0)
        trimmed_grades += 1
    while answers and _rough_size(out) > max_chars:
        answers.pop(0)
        trimmed_answers += 1

    if _rough_size(out) > max_chars:
        metadata["context_summary"] = (
            f"trimmed evidence={trimmed_evidence} grades={trimmed_grades} "
            f"answers={trimmed_answers}"
        )

    return out
