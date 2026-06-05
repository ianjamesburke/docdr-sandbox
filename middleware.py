"""Request logging, timing, and rate limiting middleware."""
import time
import logging
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("sandbox.access")

# In-memory sliding window: {ip: [timestamp, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = 60.0  # seconds


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request and enforces per-IP rate limiting (60 req/min)."""

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.perf_counter()

        # Evict old timestamps outside the window
        window_start = now - RATE_LIMIT_WINDOW
        _request_log[ip] = [t for t in _request_log[ip] if t > window_start]

        if len(_request_log[ip]) >= RATE_LIMIT_REQUESTS:
            logger.warning("Rate limit exceeded for %s", ip)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Limit: 60/min."},
                headers={"Retry-After": "60"},
            )

        _request_log[ip].append(now)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
