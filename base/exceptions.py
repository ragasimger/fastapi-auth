import logging
from typing import Any, Dict, Optional, Union

from fastapi import status

logger = logging.getLogger(__name__)


class APIException(Exception):
    """
    Base exception for application errors.

    All custom exceptions inherit from this.
    Exception handler catches this base class.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        errors: Optional[Dict[str, Any]] = None,
    ):
        logger.error(f"APIException: {self.__class__.__name__} - {message}")
        self.message = message
        self.status_code = status_code
        self.errors = errors or {}
        # self.error_code = self.__class__.__name__
        # self.details = self.errors
        super().__init__(message)


class NotFoundException(APIException):
    """Resource not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        status_code: int = status.HTTP_404_NOT_FOUND,
    ):
        logger.error(f"NotFoundException: {self.__class__.__name__} - {message}")

        super().__init__(message, status_code=status_code)


class ConflictException(APIException):
    """Resource conflict (e.g., duplicate email)."""

    def __init__(
        self,
        message: str = "Resource conflict",
        status_code: int = status.HTTP_409_CONFLICT,
    ):
        logger.error(f"ConflictException: {self.__class__.__name__} - {message}")
        super().__init__(message, status_code=status_code)


class UnauthorizedException(APIException):
    """Authentication required or failed."""

    def __init__(
        self,
        message: str = "Authentication required",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
    ):
        logger.error(f"UnauthorizedException: {self.__class__.__name__} - {message}")
        super().__init__(message, status_code=status_code)


class ForbiddenException(APIException):
    """Authenticated but not authorized."""

    def __init__(
        self,
        message: str = "Permission denied",
        status_code: int = status.HTTP_403_FORBIDDEN,
    ):
        logger.error(f"ForbiddenException: {self.__class__.__name__} - {message}")
        super().__init__(message, status_code=status_code)


class ValidationException(APIException):
    """Business validation failed."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
    ):
        details = {"field": field} if field else {}
        logger.error(
            f"ValidationException: {self.__class__.__name__} - {message} - Details: {details}"
        )
        super().__init__(message, status_code=status_code, errors=details)


class ValidationError(APIException):
    """Field-level validation exception (like DRF ValidationError)."""

    def __init__(
        self,
        errors: Dict[str, Union[str, list]],
        message: str = "Validation error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        super().__init__(message=message, status_code=status_code, errors=errors)


class RateLimitException(APIException):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        status_code: int = status.HTTP_429_TOO_MANY_REQUESTS,
    ):
        logger.error(f"RateLimitException: {self.__class__.__name__} - {message}")
        super().__init__(message, status_code=status_code)
