import logging
from typing import List, Optional

from fastapi import Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.users.models.permissions import UserPermissions, UserRoles
from app.users.models.users import UserProfile
from base.exceptions import APIException, NotFoundException, ValidationError
from base.repos.base import SQLAlchemyBaseRepository
from base.schemas import CursorPaginatedResponse
from base.utils.hashing import Hasher
from base.utils.pagination.cursor import CursorPaginator

from ..models import User
from ..schemas import user as user_schemas
from ..schemas.user import (
    GenericUserResponse,
    UserCreateRequest,
    UserCreateResponse,
    UserOrderingField,
)

logger = logging.getLogger(__name__)


class UserServiceRepository(SQLAlchemyBaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def create(self, user: UserCreateRequest) -> UserCreateResponse:
        logger.info(f"Creating user with email: {user.email}")

        sql_stmt = select(User).filter(
            or_(
                User.username == user.username,
                User.email == user.email,
            )
        )
        user_result = await self.session.execute(sql_stmt)
        existing_user = user_result.scalar_one_or_none()
        if existing_user:
            logger.error(
                f"User with given email ({user.email}) or username({user.username}) already exists."
            )
            error_detail: dict[str, str] = {}
            if existing_user.email == user.email:
                error_detail["email"] = "User already exists with this email."
            if existing_user.username == user.username:
                error_detail["username"] = "User already exists with this username."

            # raise ValidationException(
            #     # status_code=status.HTTP_400_BAD_REQUEST,
            #     message="User with given email or username already exists.",
            #     errors=error_detail,
            # )
            raise ValidationError(
                # message="User with given email or username already exists.",
                errors=error_detail,
            )

        user_data = user.model_dump(exclude_unset=True)
        role_ids = user_data.pop("role_ids", [])
        permission_ids = user_data.pop("permission_ids", [])

        user = self.model(
            password=Hasher.hash_password(user_data.pop("password")),
            **user_data,
        )

        if role_ids:
            stmt = select(UserRoles).where(UserRoles.id.in_(role_ids))
            user.roles = list((await self.session.scalars(stmt)).all())

        if permission_ids:
            stmt = select(UserPermissions).where(UserPermissions.id.in_(permission_ids))
            user.permissions = list((await self.session.scalars(stmt)).all())
        self.session.add(user)

        await (
            self.session.flush()
        )  # retrieves user id before commiting on db to assign in user profile
        user_profile = UserProfile(user_id=user.id)
        self.session.add(user_profile)

        await self.session.commit()
        await self.session.refresh(user)

        return UserCreateResponse.model_validate(user, from_attributes=True)

    async def retrieve(self, user_id: str) -> Optional[GenericUserResponse]:
        logger.info(f"Retrieving user with ID: {user_id}")
        user = await self.get(
            id=user_id,
            load_options=[
                joinedload(User.profile),
                selectinload(User.refresh_tokens),
                selectinload(User.roles),
                selectinload(User.permissions),
            ],
        )
        if not user:
            return None

        return GenericUserResponse.model_validate(user, from_attributes=True)

    async def patch(
        self,
        user_id: int,
        user_update: user_schemas.UserUpdateRequest,
    ) -> user_schemas.UserUpdateResponse:
        # checking if username duplicates
        logger.info(f"Checking for duplicate username, and email for user ID {user_id}")

        sql_stmt = select(User).filter(
            or_(
                User.username == user_update.username,
                User.email == user_update.email,
            ),
            self.model.id != user_id,
        )
        user_result = await self.session.execute(sql_stmt)
        existing_user = user_result.scalar_one_or_none()
        if existing_user:
            error_detail: dict[str, str] = {}
            if existing_user.email == user_update.email:
                error_detail["email"] = "User already exists with this email."
                logger.error(f"User with email {user_update.email} already exists.")
            if existing_user.username == user_update.username:
                error_detail["username"] = "User already exists with this username."
                logger.error(
                    f"User with username {user_update.username} already exists."
                )
            raise ValidationError(
                errors=error_detail,
            )

        # stmt = (
        #     select(self.model)
        #     .options(
        #         selectinload(self.model.roles), selectinload(self.model.permissions)
        #     )
        #     .where(self.model.id == user_id)
        # )

        # stmt = select(self.model).where(self.model.id == user_id)

        # if user_update.role_ids is not None or not user_update.role_ids == []:
        #     stmt = stmt.options(selectinload(self.model.roles))
        # if (
        #     user_update.permission_ids is not None
        #     or not user_update.permission_ids == []
        # ):
        #     stmt = stmt.options(selectinload(self.model.permissions))
        user = await self.get(
            id=user_id,
            load_options=[
                selectinload(User.roles),
                selectinload(User.permissions),
            ],
        )

        # user = await self.session.scalar(stmt)
        if not user:
            logger.info(f"User with ID {user_id} not found for patch request.")

            raise APIException(
                message="User not found.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Handle Role updates
        if user_update.role_ids is not None:
            logger.info(f"Updating roles for user ID {user_id}")
            roles_result = await self.session.execute(
                select(UserRoles).where(UserRoles.id.in_(user_update.role_ids))
            )
            roles = roles_result.scalars().all()
            if len(roles) != len(user_update.role_ids):
                logger.error(
                    f"One or more roles not found for IDs: {user_update.role_ids}"
                )
                raise APIException(message="One or more provided roles were not found.")
            user.roles = list(roles)

        # Handle Permission updates
        if user_update.permission_ids is not None:
            logger.info(f"Updating permissions for user ID {user_id}")
            permissions_result = await self.session.execute(
                select(UserPermissions).where(
                    UserPermissions.id.in_(user_update.permission_ids)
                )
            )
            permissions = permissions_result.scalars().all()
            if len(permissions) != len(user_update.permission_ids):
                logger.error(
                    f"One or more permissions not found for IDs: {user_update.permission_ids}"
                )
                raise APIException(
                    message="One or more provided permissions were not found."
                )
            user.permissions = list(permissions)

        # Exclude relationship IDs from direct attribute setting
        update_data = user_update.model_dump(
            exclude_unset=True, exclude={"role_ids", "permission_ids"}
        )

        logger.info(f"Committing updates for user ID {user_id}")
        for key, value in update_data.items():
            setattr(user, key, value)

        # session.add(user)
        await self.session.commit()
        logger.info(f"Committed updates for user ID {user_id}")
        stmt = (
            select(User)
            .options(selectinload(User.roles), selectinload(User.permissions))
            .where(User.id == user_id)
        )
        user = await self.session.scalar(stmt)

        # Map ORM objects to Pydantic schema

        logger.info(f"Mapping updated user ID {user_id} to response schema")
        response_model = user_schemas.UserUpdateResponse.model_validate(
            user, from_attributes=True
        )

        # Manually populate relationship IDs since Pydantic doesn't map 'roles' -> 'role_ids' automatically
        logger.info(f"Populating role and permission IDs for user ID {user_id}")
        response_data = response_model.model_dump()
        response_data["role_ids"] = [role.id for role in user.roles]
        response_data["permission_ids"] = [perm.id for perm in user.permissions]

        logger.info(f"User ID {user_id} updated successfully")
        logger.info("Sending response data")

        # return APIResponse(
        #     message="User updated successfully",
        #     data=response_data,
        #     status_code=status.HTTP_200_OK,
        # )

        return user_schemas.UserUpdateResponse.model_validate(
            user, from_attributes=True
        )

    async def deactivate_user(
        self,
        user_id: int,
    ):
        """Deactivate user from system. This leads to fail to login."""
        logger.info(f"Deleting (deactivating) user with ID: {user_id}")
        user = await self.get(id=user_id)
        if not user:
            raise NotFoundException(
                message="User not found.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        await self.session.commit()

    async def delete_user(
        self,
        user_id: int,
    ):
        """Soft delete user from system."""
        logger.info(f"Deactivating user with ID: {user_id}")
        user = await self.get(id=user_id)
        if not user:
            raise NotFoundException(
                message="User not found.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        await self.soft_delete(user)
        logger.info(f"User with ID: {user_id} deactivated successfully")
        return None

    async def delete_user_permanently(
        self,
        user_id: int,
    ):
        logger.warning(f"Deleting user with ID: {user_id}")
        user = await self.get(id=user_id)
        if not user:
            raise NotFoundException(
                message="User not found.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        await self.delete(user)
        logger.info(f"User with ID: {user_id} deleted successfully")
        return None

    # Listing services with cursor, and limit-offset pagination

    async def list_users_cursor(
        self,
        request: Request,
        filters: Optional[user_schemas.UserFilters] = None,
        search: str = "",
        limit: int = 10,
        cursor: Optional[str] = None,
    ) -> CursorPaginatedResponse[user_schemas.UserListResponse]:
        """List users with cursor pagination."""
        logger.info("Listing users with cursor pagination called")
        base_query = select(User).options(
            joinedload(User.profile),  # Forcing LEFT OUTER JOIN
            selectinload(User.refresh_tokens),  # Eager load roles relationship
        )

        additional_filters: List = []
        logger.info(f"Filtering users based on provided filters, {filters}")

        if filters.profile_id is not None:
            logger.info(f"Applying filters for list_users, {filters}")
            additional_filters.append(User.profile.has(id=filters.profile_id))

        paginator = CursorPaginator(
            model=User,
            session=self.session,
            request=request,
            cursor_query_param="cursor",
            additional_filters=additional_filters,
            page_size=limit,
            ordering=("-id",),
            filter_fields=[
                ("id", "str"),
                ("is_active", "boolean"),
                ("profile_id", "str"),
            ],
            base_query=base_query,
        )
        return await paginator.get_paginated_response(
            message="User list retrieved successfully.",
            schema=user_schemas.UserListResponse,
        )

    async def list_users(
        self,
        request: Request,
        filters: Optional[user_schemas.UserFilters],
        search: str = "",
        limit: int = 10,
        offset: int = 0,
        ordering: UserOrderingField = UserOrderingField.CREATED_AT_DESC,
    ):
        logger.info("Listing users with limit-offset pagination called")
        base_query = select(self.model).options(
            joinedload(User.profile),
            # selectinload(User.permissions),
            # selectinload(User.roles),
        )
        additional_filters: List = []

        logger.info(f"Filtering users based on provided filters, {filters}")

        if filters.profile_id is not None:
            logger.info(f"Applying filters for list_users, {filters}")
            additional_filters.append(User.profile.has(id=filters.profile_id))

        from base.utils.pagination.limit_offset import LimitOffsetPaginator

        paginator = LimitOffsetPaginator(
            model=User,
            session=self.session,
            request=request,
            additional_filters=additional_filters,
            limit=limit,
            search_query=search,
            offset=offset,
            base_query=base_query,
            ordering_fields=["created_at", "id"],
            default_ordering=ordering,
        )
        return await paginator.get_paginated_response(
            message="User list retrieved successfully.",
            schema=user_schemas.UserListResponse,
        )
