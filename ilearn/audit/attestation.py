"""Tamper-evident grading receipt hashes stored outside the receipt payload."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

from ilearn.core.schemas import GradingReceipt

_ATTESTATION_NAME = "attestation_log.jsonl"


def compute_receipt_content_hash(receipt: GradingReceipt) -> str:
    """SHA-256 over canonical receipt fields excluding content_hash itself."""
    body = {
        "paper_created_at": receipt.paper_created_at.isoformat(),
        "grader_version": receipt.grader_version,
        "model_id": receipt.model_id,
        "graded_at": receipt.graded_at.isoformat(),
        "ocr_confidence": receipt.ocr_confidence,
        "ocr_degraded": receipt.ocr_degraded,
        "math_verify_result": receipt.math_verify_result,
        "receipt_kind": receipt.receipt_kind,
        "rubric_version": receipt.rubric_version,
        "judge_trace_snapshot": receipt.judge_trace_snapshot,
    }
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _hmac_key() -> bytes | None:
    raw = os.getenv("ILEARN_ATTESTATION_HMAC_KEY")
    if not raw:
        return None
    return raw.encode("utf-8")


def _chain_mac(content_hash: str, prev_mac: str | None) -> str | None:
    key = _hmac_key()
    if key is None:
        return None
    material = f"{prev_mac or 'genesis'}|{content_hash}".encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def _last_mac(path: Path) -> str | None:
    if not path.is_file():
        return None
    last: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        mac = row.get("hmac")
        if isinstance(mac, str) and mac:
            last = mac
    return last


def append_attestation(
    directory: Path,
    *,
    session_id: str,
    receipt: GradingReceipt,
    item_id: str,
) -> Path:
    """Append one attestation line; file is physically separate from session JSON."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    content_hash = receipt.content_hash or compute_receipt_content_hash(receipt)
    if not receipt.content_hash:
        receipt.content_hash = content_hash
    path = directory / _ATTESTATION_NAME
    prev = _last_mac(path)
    row = {
        "session_id": session_id,
        "item_id": item_id,
        "grader_version": receipt.grader_version,
        "content_hash": content_hash,
        "graded_at": receipt.graded_at.isoformat(),
        "receipt_kind": receipt.receipt_kind,
        "prev_hmac": prev,
        "hmac": _chain_mac(content_hash, prev),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def verify_receipt_against_attestation(
    directory: Path,
    receipt: GradingReceipt,
    *,
    item_id: str,
) -> bool:
    """Return True if an attestation row matches the receipt content hash."""
    path = Path(directory) / _ATTESTATION_NAME
    if not path.is_file():
        return False
    expected = receipt.content_hash or compute_receipt_content_hash(receipt)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("item_id") == item_id and row.get("content_hash") == expected:
            return True
    return False


def verify_attestation_chain(directory: Path) -> bool:
    """Verify optional HMAC chain; returns True when no key or all rows valid."""
    path = Path(directory) / _ATTESTATION_NAME
    if not path.is_file():
        return True
    key = _hmac_key()
    prev: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        content_hash = str(row.get("content_hash") or "")
        if key is None:
            continue
        expected = _chain_mac(content_hash, prev)
        if row.get("hmac") != expected:
            return False
        if row.get("prev_hmac") != prev:
            return False
        prev = row.get("hmac")
    return True
