from typing import List

from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from base.models import AbstractBaseModel

user_role_permissions = Table(
    "auth_users_role_permissions",
    AbstractBaseModel.metadata,
    Column(
        "role_id",
        String,
        ForeignKey("auth_users_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        String,
        ForeignKey("auth_users_permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


user_roles_association = Table(
    "auth_users_roles_association",
    AbstractBaseModel.metadata,
    Column(
        "user_id",
        String,
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        String,
        ForeignKey("auth_users_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_permissions_association = Table(
    "auth_users_permissions_association",
    AbstractBaseModel.metadata,
    Column(
        "user_id",
        String,
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        String,
        ForeignKey("auth_users_permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class UserPermissionCategory(AbstractBaseModel):
    __tablename__ = "auth_users_permissions_category"
    name: Mapped[str] = mapped_column(String(length=50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions: Mapped[List["UserPermissions"]] = relationship(
        "UserPermissions",
        back_populates="permission_category",
    )


class UserPermissions(AbstractBaseModel):
    __tablename__ = "auth_users_permissions"
    name: Mapped[str] = mapped_column(String(length=50), nullable=False)
    permission_category_id: Mapped[str] = mapped_column(
        ForeignKey("auth_users_permissions_category.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code_name: Mapped[str] = mapped_column(
        String(length=50),
        nullable=False,
        unique=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    permission_category: Mapped["UserPermissionCategory"] = relationship(
        "UserPermissionCategory",
        back_populates="permissions",
    )
    roles: Mapped[List["UserRoles"]] = relationship(
        "UserRoles",
        secondary=user_role_permissions,
        back_populates="permissions",
    )

    users: Mapped[List["User"]] = relationship(  # noqa # type: ignore
        "User",
        secondary=user_permissions_association,
        back_populates="permissions",
    )


class UserRoles(AbstractBaseModel):
    __tablename__ = "auth_users_roles"
    name: Mapped[str] = mapped_column(String(length=50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[List["User"]] = relationship(  # noqa # type: ignore
        "User",
        secondary=user_roles_association,
        back_populates="roles",
    )

    permissions: Mapped[List["UserPermissions"]] = relationship(
        "UserPermissions",
        secondary=user_role_permissions,
        back_populates="roles",
    )
