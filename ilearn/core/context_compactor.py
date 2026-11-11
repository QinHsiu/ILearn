"""Three-layer context compaction — compress presentation, never delete evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CompactedContext:
    messages: list[dict[str, Any]]
    placeholders: dict[str, str]
    layer: str


class ContextCompactor:
    """Micro → Auto → Full compact. Evidence remains in event/evidence stores."""

    def __init__(self, *, occupancy_trigger: float = 0.8) -> None:
        self.occupancy_trigger = occupancy_trigger

    def micro_compact(self, messages: list[dict[str, Any]]) -> CompactedContext:
        """Layer 1: drop bulky tool payloads, keep short placeholders + evidence ids."""
        compacted: list[dict[str, Any]] = []
        placeholders: dict[str, str] = {}
        for index, message in enumerate(messages):
            role = str(message.get("role", ""))
            content = message.get("content")
            evidence_id = message.get("evidence_id")
            if role == "tool" and isinstance(content, str) and len(content) > 400:
                key = f"tool:{index}"
                placeholders[key] = str(evidence_id or key)
                compacted.append(
                    {
                        **message,
                        "content": f"[compacted:{placeholders[key]}]",
                    }
                )
            else:
                compacted.append(message)
        return CompactedContext(messages=compacted, placeholders=placeholders, layer="micro")

    def auto_compact(
        self,
        messages: list[dict[str, Any]],
        *,
        occupancy: float,
    ) -> CompactedContext:
        """Layer 2: frequency/occupancy triggered; still keeps evidence refs."""
        base = self.micro_compact(messages)
        if occupancy < self.occupancy_trigger:
            return base
        # Collapse consecutive compacted tool placeholders into one summary slot.
        summary_refs = list(base.placeholders.values())
        if not summary_refs:
            return base
        head = [m for m in base.messages if m.get("role") != "tool"]
        head.append(
            {
                "role": "system",
                "content": f"[autocompact evidence_refs={','.join(summary_refs[:20])}]",
                "evidence_id": summary_refs[0],
            }
        )
        return CompactedContext(
            messages=head,
            placeholders=base.placeholders,
            layer="auto",
        )

    def full_compact(self, messages: list[dict[str, Any]], summary: str) -> CompactedContext:
        """Layer 3: replace history presentation with an LLM/rule summary + refs."""
        refs = [
            str(m.get("evidence_id"))
            for m in messages
            if m.get("evidence_id")
        ]
        return CompactedContext(
            messages=[
                {
                    "role": "system",
                    "content": summary,
                    "evidence_refs": refs,
                }
            ],
            placeholders={ref: ref for ref in refs},
            layer="full",
        )

    def present_for_agent(
        self,
        messages: list[dict[str, Any]],
        *,
        occupancy: float,
    ) -> CompactedContext:
        """Choose micro/auto based on occupancy; never deletes underlying evidence ids."""
        if occupancy >= 0.95 and len(messages) >= 8:
            refs = [str(m.get("evidence_id") or "") for m in messages if m.get("evidence_id")]
            summary = f"证据呈现已全量压缩，保留 {len(refs)} 条原始证据引用。"
            return self.full_compact(messages, summary)
        return self.auto_compact(messages, occupancy=occupancy)
