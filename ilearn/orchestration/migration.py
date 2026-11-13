"""Cross-template LearnerState migration contracts and receipts."""

from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from ilearn.core.datetime_utils import utc_now


class SkillMapping(BaseModel):
    source_skill: str
    target_skill: str
    confidence: float = 1.0


class StateMigrationContract(BaseModel):
    contract_id: str = Field(default_factory=lambda: f"ctr-{uuid4().hex[:12]}")
    source_template_id: str
    target_template_id: str
    skill_mappings: list[SkillMapping] = Field(default_factory=list)
    default_target_skill: str | None = None
    # Keep user-spec spelling for wire format; alias preferred spelling too.
    misconcepiton_prefix_map: dict[str, str] = Field(default_factory=dict)
    misconception_prefix_map: dict[str, str] = Field(default_factory=dict)

    def contract_hash(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode("utf-8")).hexdigest()

    def prefix_map(self) -> dict[str, str]:
        merged = dict(self.misconcepiton_prefix_map)
        merged.update(self.misconception_prefix_map)
        return merged


class MigrationReceipt(BaseModel):
    receipt_id: str = Field(default_factory=lambda: f"mig-{uuid4().hex[:12]}")
    learner_id: str
    contract_id: str
    contract_hash: str
    source_version: int
    target_version: int
    source_state_hash: str
    target_state_hash: str
    mapped_skills: dict[str, str] = Field(default_factory=dict)
    orphaned_skills: list[str] = Field(default_factory=list)
    migrated_at: datetime = Field(default_factory=utc_now)
    receipt_hash: str = ""

    def compute_hash(self) -> str:
        return hashlib.sha256(
            self.model_dump_json(exclude={"receipt_hash"}).encode("utf-8")
        ).hexdigest()

    def seal(self) -> MigrationReceipt:
        sealed = self.model_copy(deep=True)
        sealed.receipt_hash = sealed.compute_hash()
        return sealed

    @model_validator(mode="after")
    def _auto_seal(self) -> MigrationReceipt:
        if not self.receipt_hash:
            self.receipt_hash = self.compute_hash()
        return self
