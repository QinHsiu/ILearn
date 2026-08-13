from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GuardVerdict:
    is_leak: bool
    confidence: float
    reason: str = ""


class GuardAgent:
    name = "guard"

    def check(self, message: str, answer_key: str | None) -> GuardVerdict:
        key = (answer_key or "").strip()
        if not key:
            return GuardVerdict(False, 0.0)
        compact_msg = message.replace(" ", "")
        compact_key = key.replace(" ", "")
        if compact_key and compact_key in compact_msg:
            return GuardVerdict(True, 1.0, "answer_key_substring")
        return GuardVerdict(False, 0.0)


def load_leak_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def leak_miss_rate(cases: list[dict], check) -> float:
    leaks = [row for row in cases if row["expect_leak"]]
    if not leaks:
        return 0.0
    missed = sum(
        1
        for row in leaks
        if not check(row["message"], row["answer_key"]).is_leak
    )
    return missed / len(leaks)
