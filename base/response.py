from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .camelize import CamelAPIResponse


class APIException(Exception):
    """Generic API exception for custom app-level errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        errors: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.errors = errors or {}
        self.data = data or {}
        super().__init__(self.message)


class ValidationError(APIException):
    """Field-level validation exception (like DRF ValidationError)."""

    def __init__(
        self,
        errors: Dict[str, Union[str, list]],
        message: str = "Validation error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        super().__init__(message=message, status_code=status_code, errors=errors)


class NotFoundException(APIException):
    """Exception for 404 not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        status_code: int = status.HTTP_404_NOT_FOUND,
    ):
        super().__init__(message=message, status_code=status_code)


class PermissionDeniedException(APIException):
    """Exception for permission/access errors."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


class APIResponse(CamelAPIResponse):
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


# ============================================
# Exception Handlers
# ============================================
def setup_exception_handlers(app: FastAPI):
    """Attach all custom exception handlers to FastAPI."""

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return APIResponse(
            message=exc.message,
            errors=exc.errors,
            status_code=exc.status_code,
            data=exc.data,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
            errors[field] = f"{error['msg']}."

        return APIResponse(
            errors=errors,
            message="Request validation failed.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return APIResponse(
            message=str(exc.detail),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unexpected exceptions."""
        return APIResponse(
            message="Internal server error.",
            errors={"error": str(exc)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
