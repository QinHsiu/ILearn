"""Optional HMAC chain for attestation rows when key is configured."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ilearn.audit.attestation import (
    append_attestation,
    compute_receipt_content_hash,
    verify_attestation_chain,
)
from ilearn.core.schemas import GradingReceipt


def _receipt(n: int) -> GradingReceipt:
    return GradingReceipt(
        paper_created_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
        grader_version="1.0.0",
        graded_at=datetime(2026, 8, 10, n, 0, tzinfo=timezone.utc),
        receipt_kind="objective",
    )


def test_attestation_hmac_chain_when_key_set(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ILEARN_ATTESTATION_HMAC_KEY", "test-hmac-secret")
    for i, item_id in enumerate(["a", "b"], start=1):
        receipt = _receipt(i)
        receipt.content_hash = compute_receipt_content_hash(receipt)
        append_attestation(tmp_path, session_id="s1", receipt=receipt, item_id=item_id)
    assert verify_attestation_chain(tmp_path) is True


def test_attestation_hmac_optional_when_key_unset(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ILEARN_ATTESTATION_HMAC_KEY", raising=False)
    receipt = _receipt(1)
    receipt.content_hash = compute_receipt_content_hash(receipt)
    append_attestation(tmp_path, session_id="s1", receipt=receipt, item_id="a")
    assert verify_attestation_chain(tmp_path) is True
