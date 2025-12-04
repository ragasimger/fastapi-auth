import logging
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    APIException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
)
from base.camelize import CamelAPIResponse

logger = logging.getLogger(__name__)


# Map exception types to status codes
EXCEPTION_STATUS_MAP = {
    NotFoundException: status.HTTP_404_NOT_FOUND,
    ConflictException: status.HTTP_409_CONFLICT,
    UnauthorizedException: status.HTTP_401_UNAUTHORIZED,
    ForbiddenException: status.HTTP_403_FORBIDDEN,
    RateLimitException: status.HTTP_429_TOO_MANY_REQUESTS,
}


class APIResponse(CamelAPIResponse):
    """Unified API response wrapper (CamelCase + success/message/errors/data)."""

    def __init__(
        self,
        data: Any = None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
        errors: Optional[Dict[str, Any]] = None,
        success: Optional[bool] = None,
        **kwargs,
    ):
        if success is None:
            success = status_code < 400

        content = {"success": success}

        if message:
            content["message"] = message

        if data is not None:
            content["data"] = data

        if errors:
            content["errors"] = errors

        super().__init__(content=content, status_code=status_code, **kwargs)


def _log_context(request: Request) -> dict:
    """Metadata for logs."""
    return {
        "client_ip": request.client.host if request.client else None,
        "method": request.method,
        "path": request.url.path,
    }


# APIException handler
async def app_exception_handler(request: Request, exc: APIException) -> APIResponse:
    status_code = EXCEPTION_STATUS_MAP.get(type(exc), exc.status_code)

    logger.exception(
        f"<< !-- APIException: {exc.__class__.__name__}: {exc.message} -- >>",
        extra={
            **_log_context(request),
            "error_code": getattr(exc, "error_code", exc.__class__.__name__),
            "details": getattr(exc, "details", None),
            "status_code": status_code,
        },
    )

    return APIResponse(
        message=exc.message,
        status_code=status_code,
        errors=exc.errors or {},
    )


# Validation errors (Pydantic)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> APIResponse:
    logger.info(
        "Request validation failed",
        extra={**_log_context(request), "errors": exc.errors()},
    )

    errors = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])
        errors[field] = f"{error['msg']}."

    return APIResponse(
        message="Request validation failed.",
        errors=errors,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


# Starlette HTTP errors
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> APIResponse:
    logger.warning(
        f"HTTPException: {exc.detail}",
        extra={**_log_context(request), "status_code": exc.status_code},
    )

    return APIResponse(
        message=str(exc.detail),
        status_code=exc.status_code,
    )


# Catch-all handler for unexpected errors
async def generic_exception_handler(request: Request, exc: Exception) -> APIResponse:
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,  # includes stacktrace
        extra={**_log_context(request), "exception_type": exc.__class__.__name__},
    )

    return APIResponse(
        message="Internal server error.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        errors={"error": str(exc)},
    )
