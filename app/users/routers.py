"""Authentication routes."""

import logging
from enum import Enum
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel

from base.exception_handlers import APIResponse
from base.exceptions import NotFoundException
from base.schemas import CursorPaginatedResponse, LimitOffsetListPaginatedResponse

from .dependencies import UserServiceDependency
from .schemas import user as user_schemas

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/auth/users",
    tags=["Authentication"],
)


@router.post("/create", response_model=user_schemas.UserCreateResponse)
async def create_user(
    user: user_schemas.UserCreateRequest, user_repo: UserServiceDependency
) -> user_schemas.UserCreateResponse:
    logger.info("create_user endpoint called")
    user_data = await user_repo.create(user)

    return APIResponse(
        message="User created successfully.",
        data=user_data.model_dump(),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/retrieve/{user_id}", response_model=user_schemas.UserResponseForRetrieval)
async def retrieve_user_detail(
    user_id: str,
    user_repo: UserServiceDependency,
) -> user_schemas.UserResponseForRetrieval:
    logger.info(
        f"Retrieving User: retrieve_user_detail endpoint called for user_id: {user_id}"
    )
    user_data = await user_repo.retrieve(user_id)
    if not user_data:
        logger.error(f"User with id {user_id} not found.")
        raise NotFoundException(message="User not found.")

    return APIResponse(
        message="User retrieved successfully.",
        data=user_data.model_dump(),
        status_code=status.HTTP_200_OK,
    )


# @router.get(
#     "/list",
#     response_model=CursorPaginatedResponse[user_schemas.UserListResponse],
# )
# async def list_users(
#     user_repo: UserServiceDependency,
# ) -> CursorPaginatedResponse[user_schemas.UserListResponse]:
#     logger.info("list_users endpoint called")
#     users = await user_repo.list_users()

#     user_list = [user.model_dump() for user in users]

#     return APIResponse(
#         message="Users listed successfully.",
#         data=user_list,
#         status_code=status.HTTP_200_OK,
#     )


@router.patch("/update/{user_id}", response_model=user_schemas.UserResponseForRetrieval)
async def update_user(
    user_id: str,
    user_update: user_schemas.UserUpdateRequest,
    user_repo: UserServiceDependency,
) -> user_schemas.UserResponseForRetrieval:
    logger.info(f"update_user endpoint called for user_id: {user_id}")
    user_data = await user_repo.patch(user_id, user_update)
    if not user_data:
        logger.error(f"User with id {user_id} not found for update.")
        raise NotFoundException(message="User not found.")

    return APIResponse(
        message="User updated successfully.",
        data=user_data.model_dump(),
        status_code=status.HTTP_200_OK,
    )


@router.delete(
    "/delete/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_user(
    user_id: str,
    user_repo: UserServiceDependency,
) -> None:
    logger.info(f"delete_user endpoint called for user_id: {user_id}")
    await user_repo.delete(user_id)

    return APIResponse(
        message="User deleted successfully.",
        data=None,
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get(
    "/list",
    response_model=LimitOffsetListPaginatedResponse[user_schemas.UserListResponse],
)
async def list_users(
    request: Request,
    filters: Annotated[user_schemas.UserFilters, Depends()],
    user_repo: UserServiceDependency,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ordering: Annotated[
        user_schemas.UserOrderingField, Query(description="Order by fields")
    ] = user_schemas.UserOrderingField.CREATED_AT_DESC,
) -> LimitOffsetListPaginatedResponse[user_schemas.UserListResponse]:
    logger.info("list_users endpoint called")
    return await user_repo.list_users(
        filters=filters,
        request=request,
        limit=limit,
        offset=offset,
        ordering=ordering,
    )


@router.get(
    "/list-cursor",
    response_model=CursorPaginatedResponse[user_schemas.UserListResponse],
)
async def list_users_cursor(
    request: Request,
    filters: Annotated[user_schemas.UserFilters, Depends()],
    user_repo: UserServiceDependency,
    limit: int = Query(10, ge=1, le=100),
    cursor: Optional[str] = Query(None),
) -> CursorPaginatedResponse[user_schemas.UserListResponse]:
    logger.info("list_users_cursor endpoint called")
    return await user_repo.list_users_cursor(
        request=request,
        filters=filters,
        limit=limit,
        cursor=cursor,
    )
