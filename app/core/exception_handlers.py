"""Global exception handlers for FastAPI application.

This module provides centralized exception handling that converts all exceptions
to standardized APIResponse format with proper logging.
"""

import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions.base import AppException
from app.core.responses import APIResponse, ErrorResponse

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle AppException and all its subclasses.

    Logs the exception at WARNING level and returns a standardized error response.

    Args:
        request: The FastAPI request object
        exc: The AppException instance

    Returns:
        JSONResponse with APIResponse[None] format
    """
    logger.warning(
        f"AppException raised: {exc.code} - {exc.message}",
        extra={
            "error_code": exc.code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )

    error_response = ErrorResponse(
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )

    response_data = APIResponse[None](
        success=False,
        data=None,
        error=error_response,
        meta=None,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data.model_dump(exclude_none=False),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTPException.

    Converts HTTPException to standardized APIResponse format.

    Args:
        request: The FastAPI request object
        exc: The HTTPException instance

    Returns:
        JSONResponse with APIResponse[None] format
    """
    logger.warning(
        f"HTTPException raisedsssss: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Map HTTP status code to error code
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }

    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")

    error_response = ErrorResponse(
        code=error_code,
        message=str(exc.detail),
        details=None,
    )

    response_data = APIResponse[None](
        success=False,
        data=None,
        error=error_response,
        meta=None,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data.model_dump(exclude_none=False),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all unhandled exceptions.

    Logs the full traceback at ERROR level and returns a generic error response.
    In production, hides internal error details from the client.

    Args:
        request: The FastAPI request object
        exc: The unhandled Exception instance

    Returns:
        JSONResponse with APIResponse[None] format and 500 status
    """
    # Log the full exception with traceback
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
    )

    # In production, don't expose internal error details
    # You can check environment variable here if needed
    error_response = ErrorResponse(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        details=None,  # Don't expose internal details in production
    )

    response_data = APIResponse[None](
        success=False,
        data=None,
        error=error_response,
        meta=None,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data.model_dump(exclude_none=False),
    )


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle Pydantic validation exceptions.

    Converts validation errors to standardized APIResponse format.

    Args:
        request: The FastAPI request object
        exc: The validation exception instance

    Returns:
        JSONResponse with APIResponse[None] format and 422 status
    """
    logger.warning(
        f"Validation error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Extract validation errors if available
    details = None
    if hasattr(exc, "errors"):
        raw_errors = exc.errors()
        # Pydantic v2 puts the raw ValueError instance in ctx["error"], which
        # is not JSON-serializable. Convert any non-primitive ctx values to str.
        sanitized = []
        for err in raw_errors:
            if "ctx" in err and isinstance(err.get("ctx"), dict):
                err = {**err, "ctx": {k: str(v) for k, v in err["ctx"].items()}}
            sanitized.append(err)
        details = {"validation_errors": sanitized}

    error_response = ErrorResponse(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=details,
    )

    response_data = APIResponse[None](
        success=False,
        data=None,
        error=error_response,
        meta=None,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response_data.model_dump(exclude_none=False),
    )
