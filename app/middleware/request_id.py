import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.observability.logging import get_logger
from app.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)


logger = get_logger("http")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        request.state.request_id = request_id

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_seconds = time.perf_counter() - start

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                path=request.url.path,
            ).observe(duration_seconds)

            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                path=request.url.path,
                status="500",
            ).inc()

            duration_ms = duration_seconds * 1000

            logger.error(
                "%s %s failed duration_ms=%.2f",
                request.method,
                request.url.path,
                duration_ms,
                extra={"request_id": request_id},
                exc_info=True,
            )

            raise

        duration_seconds = time.perf_counter() - start

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            path=request.url.path,
        ).observe(duration_seconds)

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            path=request.url.path,
            status=str(response.status_code),
        ).inc()

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "%s %s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_seconds * 1000,
            extra={"request_id": request_id},
        )

        return response
