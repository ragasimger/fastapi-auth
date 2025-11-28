from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from base.models import AbstractBaseModel

from .permissions import user_permissions_association, user_roles_association

if TYPE_CHECKING:
    from .refresh_token import RefreshToken


class User(AbstractBaseModel):
    """
    User model with automatic audit tracking.

    Inherited fields from AbstractBaseModel:
    - id (Primary Key, uuid)
    - created_at, modified_at (Timestamps)
    - created_by, updated_by (Audit relationships to User)
    """

    __tablename__ = "auth_users"

    username: Mapped[str] = mapped_column(
        String(length=50), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(length=100), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(length=255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(length=300), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,  # One-to-One
        cascade="all, delete-orphan",
        single_parent=True,
        foreign_keys="[UserProfile.user_id]",
    )

    # One-to-Many relationship with RefreshToken
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(  # noqa # type: ignore
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[RefreshToken.user_id]",
    )

    # Many-to-Many relationships
    roles: Mapped[List["UserRoles"]] = relationship(  # noqa # type: ignore
        "UserRoles",
        secondary=user_roles_association,
        back_populates="users",
    )

    permissions: Mapped[List["UserPermissions"]] = relationship(  # noqa # type: ignore
        "UserPermissions",
        secondary=user_permissions_association,
        back_populates="users",
    )

    def __repr__(self):
        return f"<User ({self.id}), username={self.username}, email={self.email}>"


class UserProfile(AbstractBaseModel):
    __tablename__ = "auth_users_profile"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    profile_image_url: Mapped[str] = mapped_column(String(length=255), default="")

    user: Mapped["User"] = relationship(
        back_populates="profile",
        uselist=False,
        # Explicitly stating this relationship uses 'user_id' column,
        # not 'created_by_id' or 'updated_by_id' from AbstractBaseModel
        foreign_keys=[user_id],
    )

    def __repr__(self):
        return f"<UserProfile ({self.id}), user_id={self.user_id}>"
