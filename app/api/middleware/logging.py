"""Request logging middleware — logs every request with timing (like shared-proxy's RequestLoggingMiddleware)."""

import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status code, and latency for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "{method} {path} → {status} ({latency:.1f}ms)",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency=latency_ms,
        )

        # Add latency header for observability
        response.headers["X-Response-Time-Ms"] = f"{latency_ms:.1f}"
        return response

