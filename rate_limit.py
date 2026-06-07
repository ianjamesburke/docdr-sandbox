"""Simple in-memory rate limiter using a sliding window."""
import time
from fastapi import HTTPException, Request


class RateLimiter:
    """Track request counts per client IP within a sliding time window."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def _cleanup(self, client_ip: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        self._requests[client_ip] = [
            t for t in self._requests.get(client_ip, []) if t > cutoff
        ]

    def check(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        self._cleanup(client_ip)
        timestamps = self._requests.setdefault(client_ip, [])
        if len(timestamps) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s.",
            )
        timestamps.append(time.monotonic())

    def get_usage(self, request: Request) -> dict:
        client_ip = request.client.host if request.client else "unknown"
        self._cleanup(client_ip)
        count = len(self._requests.get(client_ip, []))
        return {
            "client_ip": client_ip,
            "requests_used": count,
            "requests_remaining": max(0, self.max_requests - count),
            "window_seconds": self.window_seconds,
        }
