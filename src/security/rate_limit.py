from __future__ import annotations

from collections import defaultdict, deque
import os
import threading
import time
from typing import Deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from src.security.audit import append_audit_event_from_request


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _extract_token(request: Request) -> str | None:
    authorization = str(request.headers.get("authorization") or "").strip()
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token

    api_key = str(request.headers.get("x-api-key") or "").strip()
    return api_key or None


class _SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = max(1, int(limit))
        self._window_seconds = max(1, int(window_seconds))
        self._buckets: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int, int]:
        now = time.time()
        window_start = now - float(self._window_seconds)

        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= self._limit:
                retry_after = max(1, int(bucket[0] + self._window_seconds - now))
                return False, 0, retry_after

            bucket.append(now)
            remaining = max(0, self._limit - len(bucket))
            if not bucket:
                self._buckets.pop(key, None)
            return True, remaining, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._enabled = _as_bool(os.getenv("RATE_LIMIT_ENABLED"), False)
        self._limit = int(os.getenv("RATE_LIMIT_REQUESTS", "180"))
        self._window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        self._limiter = _SlidingWindowLimiter(limit=self._limit, window_seconds=self._window_seconds)

    def _refresh_config(self) -> None:
        enabled = _as_bool(os.getenv("RATE_LIMIT_ENABLED"), False)
        limit = int(os.getenv("RATE_LIMIT_REQUESTS", "180"))
        window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

        if enabled == self._enabled and limit == self._limit and window == self._window_seconds:
            return

        self._enabled = enabled
        self._limit = limit
        self._window_seconds = window
        self._limiter = _SlidingWindowLimiter(limit=self._limit, window_seconds=self._window_seconds)

    @staticmethod
    def _is_exempt_path(path: str) -> bool:
        if path in {"/", "/health", "/metrics", "/docs", "/openapi.json"}:
            return True
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True
        return False

    @staticmethod
    def _request_key(request: Request) -> str:
        token = _extract_token(request)
        if token is not None:
            return f"token:{token}"
        ip = request.client.host if request.client is not None else "unknown"
        return f"ip:{ip}"

    async def dispatch(self, request: Request, call_next):
        self._refresh_config()

        if not self._enabled or self._is_exempt_path(request.url.path):
            return await call_next(request)

        key = self._request_key(request)
        allowed, remaining, retry_after = self._limiter.check(key)

        if not allowed:
            append_audit_event_from_request(
                request,
                event_type="RATE_LIMIT_EXCEEDED",
                status_code=429,
                details={
                    "rate_limit_requests": self._limit,
                    "rate_limit_window_seconds": self._window_seconds,
                    "retry_after_seconds": retry_after,
                    "key_type": "token" if key.startswith("token:") else "ip",
                },
            )
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(self._limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Window-Seconds"] = str(self._window_seconds)
            return response

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window-Seconds"] = str(self._window_seconds)
        return response
