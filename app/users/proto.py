import typing as ty
from typing import Annotated, Optional

from fastapi import Depends, Query, Request
from pydantic import BaseModel

from base.schemas import CursorPaginatedResponse

from .schemas import user as user_schemas
from .services.user import UserServiceRepository


class UserFilters(BaseModel):
    id: Optional[int] = None
    is_active: Optional[bool] = None
    profile: Optional[int] = None


class UserProto(ty.Protocol):
    async def _create(
        self, user: user_schemas.UserCreateRequest
    ) -> user_schemas.UserCreateResponse:
        """Create a new user."""
        ...

    async def create(
        self, user: user_schemas.UserCreateRequest
    ) -> user_schemas.UserCreateResponse:
        """Create a new user."""
        ...

    async def _list_users(
        self,
        request: Request,
        filters: Annotated[UserFilters, Depends()],
        search: Annotated[
            str,
            Query(description="Search by name, email, or username", example="john"),
        ] = "",
        limit: int = Query(10, ge=1, le=100),
    ) -> CursorPaginatedResponse[user_schemas.UserListResponse]:
        """List all users with cursor pagination."""
        ...

    async def list_users(
        self,
        request: Request,
        filters: Annotated[UserFilters, Depends()],
        search: Annotated[
            str,
            Query(description="Search by name, email, or username", example="john"),
        ] = "",
        limit: int = Query(10, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ) -> CursorPaginatedResponse[user_schemas.UserListResponse]:
        """List all users with cursor pagination."""
        ...

    # Cursor pagination methods
    async def _list_users_cursor(
        self,
        request: Request,
        filters: Annotated[UserFilters, Depends()],
        search: Annotated[
            str,
            Query(description="Search by name, email, or username", example="john"),
        ] = "",
        limit: int = Query(10, ge=1, le=100),
        cursor: Optional[str] = Query(None),
    ) -> CursorPaginatedResponse[user_schemas.UserListResponse]:
        """List all users with cursor pagination."""
        ...

    async def list_users_cursor(
        self,
        request: Request,
        filters: Annotated[UserFilters, Depends()],
        search: Annotated[
            str,
            Query(description="Search by name, email, or username", example="john"),
        ] = "",
        limit: int = Query(10, ge=1, le=100),
        cursor: Optional[str] = Query(None),
    ) -> CursorPaginatedResponse[user_schemas.UserListResponse]:
        """List all users with cursor pagination."""
        ...

    async def _retrieve(self, user_id: int) -> user_schemas.UserResponseForRetrieval:
        """Retrieve user details by ID."""
        ...

    async def retrieve(self, user_id: int) -> user_schemas.UserResponseForRetrieval:
        """Retrieve user details by ID."""
        ...

    async def _patch(
        self, user_id: int, user_update: user_schemas.UserUpdateRequest
    ) -> user_schemas.UserUpdateResponse:
        """Patch user details by ID."""
        ...

    async def patch(
        self, user_id: int, user_update: user_schemas.UserUpdateRequest
    ) -> user_schemas.UserUpdateResponse:
        """Patch user details by ID."""
        ...

    async def _delete(
        self,
        user_id: int,
    ) -> None:
        """Patch user details by ID."""
        ...

    async def delete(
        self,
        user_id: int,
    ) -> None:
        """Patch user details by ID."""
        ...

    # async def get_user_by_id(self, user_id: int) -> UserResponseForRetrieval: ...

    # async def update_user(
    #     self, user_id: int, user_update: user_schemas.UserUpdateRequest
    # ) -> user_schemas.UserResponseForRetrieval: ...
    # async def delete_user(self, user_id: int) -> None: ...
    # async def activate_user(self, user_id: int) -> None: ...
    # async def deactivate_user(self, user_id: int) -> None: ...
    # async def get_user_by_email(self, email: str) -> user_schemas.UserResponseForRetrieval: ...
    # async def _get_user_by_username(self, username: str) -> user_schemas.UserResponseForRetrieval: ...
