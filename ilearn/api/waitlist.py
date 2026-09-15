"""Commercial soft-launch waitlist capture."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class WaitlistRequest(BaseModel):
    email: str
    role: Literal["parent", "teacher", "other"] = "parent"
    note: str | None = Field(default=None, max_length=500)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not _EMAIL_RE.match(email):
            raise ValueError("invalid email")
        return email


class WaitlistResponse(BaseModel):
    ok: bool = True


def create_waitlist_router(*, path: Path) -> APIRouter:
    router = APIRouter(tags=["waitlist"])

    @router.post("/waitlist", response_model=WaitlistResponse)
    def submit_waitlist(body: WaitlistRequest) -> WaitlistResponse:
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "email": body.email,
            "role": body.role,
            "note": body.note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            raise HTTPException(status_code=500, detail="waitlist write failed") from exc
        return WaitlistResponse(ok=True)

    return router
