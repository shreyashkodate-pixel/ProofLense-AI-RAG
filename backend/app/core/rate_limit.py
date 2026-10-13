"""ProofLens AI — In-Memory Rate Limiting Middleware.

Implements local sliding-window request throttling as an anti-flooding heuristic.
Note: As documented in TECHNICAL-DESIGN.md, per-instance counters reset on process
restart and do not provide distributed guarantees without an external store.
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Tuple
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter per client IP."""

    def __init__(self) -> None:
        self._lock = Lock()
        # Key: (client_ip, bucket_type) -> List[timestamps]
        self._requests: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str, bucket_type: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """Check if request is allowed under the sliding window.

        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._requests[(client_ip, bucket_type)]
            # Prune old timestamps
            self._requests[(client_ip, bucket_type)] = [t for t in timestamps if t > cutoff]
            current_timestamps = self._requests[(client_ip, bucket_type)]

            if len(current_timestamps) >= max_requests:
                oldest = current_timestamps[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                return False, retry_after

            current_timestamps.append(now)
            return True, 0

    def reset(self) -> None:
        """Reset all in-memory counters (primarily for testing)."""
        with self._lock:
            self._requests.clear()


rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware to throttle requests per client IP."""

    async def dispatch(self, request: Request, call_next):
        # Exclude documentation, OpenAPI schema, and health endpoints
        path = request.url.path
        if path.startswith("/health") or path in ("/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Check app state settings or fall back to global get_settings()
        app_settings = getattr(request.app.state, "settings", None)
        settings: Settings = app_settings if app_settings is not None else get_settings()

        if settings.ENVIRONMENT == "test" and getattr(settings, "DISABLE_RATE_LIMIT_FOR_TESTS", False):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        # Extract X-Forwarded-For if behind a proxy
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        # Classify route category
        if "/queries" in path:
            allowed, retry_after = rate_limiter.is_allowed(
                client_ip=client_ip,
                bucket_type="queries",
                max_requests=settings.RATE_LIMIT_QUERIES_PER_MINUTE,
                window_seconds=60,
            )
        elif "/upload" in path:
            allowed, retry_after = rate_limiter.is_allowed(
                client_ip=client_ip,
                bucket_type="upload",
                max_requests=settings.RATE_LIMIT_UPLOADS_PER_HOUR,
                window_seconds=3600,
            )
        else:
            allowed, retry_after = rate_limiter.is_allowed(
                client_ip=client_ip,
                bucket_type="general",
                max_requests=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
                window_seconds=60,
            )

        if not allowed:
            payload = ErrorResponse(
                error_code="RATE_LIMIT_EXCEEDED",
                message=f"Rate limit exceeded. Please wait {retry_after} seconds before retrying.",
                details={"retry_after_seconds": retry_after},
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=payload.model_dump(),
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
