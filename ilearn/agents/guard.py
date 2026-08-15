from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


SAFE_FALLBACK = "先别着急看答案。先写下已知条件，再选择运算，最后自己验算一遍。"


@dataclass(frozen=True)
class GuardVerdict:
    is_leak: bool
    confidence: float
    reason: str = ""


class GuardAgent:
    name = "guard"

    STRONG_PATTERNS = (
        (r"(答案|结果|得数|最终值)\s*[是为：:]\s*(?P<answer>[^\n，。！？,!?]+)", "direct_answer"),
        (r"(正确答案|正确结果)\s*[是为：:]\s*(?P<answer>[^\n，。！？,!?]+)", "direct_answer"),
        (r"(?P<answer>[+-]?\d+(?:\.\d+)?|[\d.]+\s*/\s*[\d.]+)\s*(是|就是)\s*(正确)?答案", "direct_answer"),
        (r"(因此|所以|最终)\s*(答案|结果)\s*[是为：:]\s*(?P<answer>[^\n，。！？,!?]+)", "direct_answer"),
        (r"(填|写|选)\s*(?P<answer>[+-]?\d+(?:\.\d+)?|[\d.]+\s*/\s*[\d.]+)", "direct_answer"),
    )
    MEDIUM_PATTERNS = (
        (r"你(的|这个)?结果\s*[应该为约是]*\s*(?P<answer>[+-]?\d+(?:\.\d+)?)", "suggest_answer"),
        (r"应该(等于|得到|算出)\s*(?P<answer>[+-]?\d+(?:\.\d+)?)", "suggest_answer"),
        (r"结果\s*[约为是]\s*(?P<answer>[+-]?\d+(?:\.\d+)?)", "suggest_answer"),
        (r"最终值\s*[约为是]\s*(?P<answer>[+-]?\d+(?:\.\d+)?)", "suggest_answer"),
        (r"可以[写填]成\s*(?P<answer>[^\n，。！？,!?]+)", "suggest_answer"),
    )

    def __init__(self, use_llm_judge: bool = False) -> None:
        self.use_llm_judge = use_llm_judge

    def check(self, message: str, answer_key: str | None) -> GuardVerdict:
        key = (answer_key or "").strip()
        if not key:
            return GuardVerdict(False, 0.0)

        text = message or ""
        compact_msg = re.sub(r"\s+", "", text)
        compact_key = re.sub(r"\s+", "", key)
        numeric_key = bool(re.fullmatch(r"[+-]?\d+(?:\.\d+)?", compact_key))
        if compact_key and compact_key in compact_msg and not numeric_key:
            return GuardVerdict(True, 1.0, "answer_key_substring")

        for pattern, label in self.STRONG_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            extracted = match.groupdict().get("answer", match.group(0))
            if self._is_answer_equivalent(extracted, key):
                return GuardVerdict(True, 0.95, f"strong_pattern_{label}")
            return GuardVerdict(True, 0.7, f"strong_pattern_suspicious_{label}")

        for pattern, label in self.MEDIUM_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and self._is_answer_equivalent(
                match.groupdict().get("answer", ""), key
            ):
                return GuardVerdict(True, 0.8, f"medium_pattern_{label}")

        if self._contains_exact_number(text, key):
            return GuardVerdict(True, 0.6, "exact_number_match")
        return GuardVerdict(False, 0.0)

    @staticmethod
    def _is_answer_equivalent(extracted: str, answer_key: str) -> bool:
        left = re.sub(r"[\s,，。.!！?？:：]", "", extracted).lower()
        right = re.sub(r"[\s,，。.!！?？:：]", "", answer_key).lower()
        if left == right:
            return True
        try:
            return Fraction(left) == Fraction(right)
        except (ValueError, ZeroDivisionError):
            try:
                return abs(float(left) - float(right)) < 1e-6
            except ValueError:
                return False

    @staticmethod
    def _contains_exact_number(text: str, answer_key: str) -> bool:
        key = re.sub(r"\s+", "", answer_key)
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", key):
            return False
        pattern = rf"(?<![\d.]){re.escape(key)}(?![\d.])"
        return re.search(pattern, text) is not None


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
