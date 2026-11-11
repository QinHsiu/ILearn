"""GradingReceipt content hash + physically separate attestation log."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ilearn.audit.attestation import (
    append_attestation,
    compute_receipt_content_hash,
    verify_receipt_against_attestation,
)
from ilearn.core.grader import ItemGrader
from ilearn.core.schemas import AssessmentItem, GradingReceipt


def test_receipt_content_hash_is_deterministic():
    receipt = GradingReceipt(
        paper_created_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
        grader_version="1.0.0",
        model_id=None,
        graded_at=datetime(2026, 8, 10, 1, 0, tzinfo=timezone.utc),
        math_verify_result={"equivalent": True},
    )
    h1 = compute_receipt_content_hash(receipt)
    h2 = compute_receipt_content_hash(receipt)
    assert h1 == h2
    assert len(h1) == 64


def test_grade_item_populates_content_hash():
    grader = ItemGrader(llm=None)
    item = AssessmentItem(
        id="c1",
        stem="1+1=?",
        type="choice",
        difficulty="easy",
        knowledge_ids=["dec_mult"],
        answer_key="2",
        choices=["2", "3", "4", "5"],
    )
    result = grader.grade_item(item, "2")
    assert result.receipt is not None
    assert result.receipt.content_hash
    assert result.receipt.content_hash == compute_receipt_content_hash(result.receipt)


def test_attestation_log_physically_separated(tmp_path: Path):
    grader = ItemGrader(llm=None)
    item = AssessmentItem(
        id="c1",
        stem="1+1=?",
        type="choice",
        difficulty="easy",
        knowledge_ids=["dec_mult"],
        answer_key="2",
        choices=["2", "3", "4", "5"],
    )
    result = grader.grade_item(item, "2")
    assert result.receipt is not None
    path = append_attestation(tmp_path, session_id="s1", receipt=result.receipt, item_id="c1")
    assert path.name == "attestation_log.jsonl"
    assert path.parent == tmp_path
    assert verify_receipt_against_attestation(tmp_path, result.receipt, item_id="c1") is True
