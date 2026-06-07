"""Request metrics collection for monitoring and alerting."""
import time
from dataclasses import dataclass, field
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class EndpointMetrics:
    total_requests: int = 0
    total_errors: int = 0
    total_latency_ms: float = 0.0
    status_codes: dict[int, int] = field(default_factory=dict)

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.total_latency_ms / self.total_requests, 2)

    @property
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(self.total_errors / self.total_requests, 4)


class MetricsCollector:
    """Collects per-endpoint request metrics: latency, status codes, error rates."""

    def __init__(self):
        self._endpoints: dict[str, EndpointMetrics] = {}

    def record(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        key = f"{method} {path}"
        metrics = self._endpoints.setdefault(key, EndpointMetrics())
        metrics.total_requests += 1
        metrics.total_latency_ms += latency_ms
        metrics.status_codes[status_code] = metrics.status_codes.get(status_code, 0) + 1
        if status_code >= 400:
            metrics.total_errors += 1

    def summary(self) -> dict:
        total_reqs = sum(m.total_requests for m in self._endpoints.values())
        return {
            "total_requests": total_reqs,
            "endpoints": {
                key: {
                    "requests": m.total_requests,
                    "avg_latency_ms": m.avg_latency_ms,
                    "error_rate": m.error_rate,
                    "status_codes": m.status_codes,
                }
                for key, m in sorted(self._endpoints.items(), key=lambda x: -x[1].total_requests)
            },
        }

    def reset(self) -> None:
        self._endpoints.clear()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records latency and status for every request."""

    def __init__(self, app, collector: MetricsCollector):
        super().__init__(app)
        self.collector = collector

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = (time.monotonic() - start) * 1000
        self.collector.record(request.method, request.url.path, response.status_code, latency_ms)
        return response
