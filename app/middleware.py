"""Custom middleware for request tracing and logging."""

import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response

from app.logging_config import configure_logging

logger = configure_logging()

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def create_request_id(client_request_id: str | None) -> str:
    """Return a safe client request ID or generate a new UUID."""
    if (
        client_request_id
        and REQUEST_ID_PATTERN.fullmatch(client_request_id)
    ):
        return client_request_id

    return str(uuid4())


async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Add a safe request ID and log request completion details."""
    request_id = create_request_id(
        request.headers.get("X-Request-ID")
    )
    request.state.request_id = request_id

    start_time = time.perf_counter()

    logger.info(
        "request_started request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.exception(
            (
                "request_failed request_id=%s method=%s "
                "path=%s duration_ms=%.2f"
            ),
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000

    response.headers["X-Request-ID"] = request_id

    logger.info(
        (
            "request_completed request_id=%s method=%s "
            "path=%s status_code=%s duration_ms=%.2f"
        ),
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response