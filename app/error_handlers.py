"""Centralized exception handlers for the FastAPI application."""

from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_config import configure_logging
from app.schemas import ErrorResponse

logger = configure_logging()


def get_request_id(request: Request) -> str:
    """Return the middleware request ID or generate a fallback UUID."""
    return getattr(
        request.state,
        "request_id",
        str(uuid4()),
    )


async def http_exception_handler(
    request: Request,
    exception: HTTPException,
) -> JSONResponse:
    """Convert an HTTP exception into a standard JSON error response."""
    request_id = get_request_id(request)
    error_message = str(exception.detail)

    logger.warning(
        (
            "http_error request_id=%s method=%s path=%s "
            "status_code=%s error=%s"
        ),
        request_id,
        request.method,
        request.url.path,
        exception.status_code,
        error_message,
    )

    error_response = ErrorResponse(
        error=error_message,
        status_code=exception.status_code,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=exception.status_code,
        content=error_response.model_dump(),
        headers={
            "X-Request-ID": request_id,
        },
    )


async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    """Convert request-validation failures into a standard response."""
    request_id = get_request_id(request)

    logger.warning(
        (
            "validation_error request_id=%s method=%s path=%s "
            "status_code=422 error_count=%s"
        ),
        request_id,
        request.method,
        request.url.path,
        len(exception.errors()),
    )

    error_response = ErrorResponse(
        error="Request validation failed.",
        status_code=422,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=422,
        content={
            **error_response.model_dump(),
            "details": exception.errors(),
        },
        headers={
            "X-Request-ID": request_id,
        },
    )