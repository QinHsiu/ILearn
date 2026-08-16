"""Demo authentication endpoints for the ILearn web application."""

from __future__ import annotations

from collections.abc import Mapping

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class LoginRequest(BaseModel):
    role: str
    username: str
    password: str


class LoginResponse(BaseModel):
    role: str
    user_id: str


def create_auth_router(
    credentials: Mapping[str, Mapping[str, str]],
) -> APIRouter:
    """Create the demo role login router with the supplied credentials."""
    router = APIRouter(prefix="/auth")

    @router.post("/login", response_model=LoginResponse)
    def login(request: LoginRequest) -> LoginResponse:
        selected = credentials.get(request.role)
        if selected is None:
            raise HTTPException(status_code=400, detail="invalid role")
        if (
            request.username != selected["username"]
            or request.password != selected["password"]
        ):
            raise HTTPException(status_code=401, detail="invalid credentials")
        return LoginResponse(role=request.role, user_id=selected["user_id"])

    return router
