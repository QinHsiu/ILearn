"""In-memory sliding-window rate limiter and FastAPI middleware."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp


class RateLimiter:
    """Sliding-window rate limiter keyed by client id."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        now = time.time()
        window = [
            t
            for t in self.requests[client_id]
            if now - t < self.window_seconds
        ]
        self.requests[client_id] = window
        if len(window) >= self.max_requests:
            return False, 0
        window.append(now)
        self.requests[client_id] = window
        remaining = self.max_requests - len(window)
        return True, remaining

    def reset(self) -> None:
        self.requests.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, limiter: RateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_host = request.client.host if request.client else "unknown"
        allowed, remaining = self.limiter.is_allowed(client_host)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"X-RateLimit-Remaining": "0"},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
