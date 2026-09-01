"""Split markdown documents for two-column report layouts."""

from __future__ import annotations


def split_markdown_at_heading(markdown: str, heading: str) -> tuple[str, str]:
    """Split at a level-2 heading (## heading). Returns (before, from_heading)."""
    marker = f"## {heading}"
    normalized = markdown.replace("\r\n", "\n")
    needle = f"\n{marker}"
    idx = normalized.find(needle)
    if idx >= 0:
        return normalized[:idx].strip(), normalized[idx + 1 :].strip()
    if normalized.startswith(marker):
        return "", normalized.strip()
    return normalized.strip(), ""


def split_learning_report(markdown: str) -> tuple[str, str]:
    """Diagnosis block vs plan block for full session reports."""
    return split_markdown_at_heading(markdown, "学习计划")


def split_plan_report(markdown: str) -> tuple[str, str]:
    """Daily schedule vs scientific-methods block within a plan."""
    return split_markdown_at_heading(markdown, "科学学习方法")
