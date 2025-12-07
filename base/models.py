import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    # CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
    relationship,
)

# from typing_extensions import TYPE_CHECKING
# if TYPE_CHECKING:
#     from ..apps.users.models.user import User


class DeclarativeBaseModel(AsyncAttrs, DeclarativeBase):
    pass


class AbstractBaseModel(DeclarativeBaseModel):
    """Abstract base model with audit fields and automatic user tracking."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    @declared_attr
    def created_by_id(cls) -> Mapped[Optional[str]]:
        """Foreign key to User who created this record."""
        return mapped_column(
            "created_by_id",
            ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        )

    @declared_attr
    def updated_by_id(cls) -> Mapped[Optional[str]]:
        """Foreign key to User who last updated this record."""
        return mapped_column(
            "updated_by_id",
            ForeignKey("auth_users.id", ondelete="SET NULL"),
            nullable=True,
        )

    @declared_attr
    def created_by(cls) -> Mapped[Optional["User"]]:  # noqa # type: ignore
        """Relationship to User who created this record."""
        # Check if this is the User model itself (self-referential)
        is_user_model = cls.__name__ == "User"

        if is_user_model:
            # Self-referential relationship for User model
            return relationship(
                "User",
                foreign_keys=lambda: cls.created_by_id,
                remote_side=lambda: [cls.id],
                backref="created_users",
                post_update=True,  # Prevents circular dependency issues
            )
        else:
            # Regular relationship to User model except (for User) model
            return relationship(
                "User",
                foreign_keys=lambda: cls.created_by_id,
                backref=f"{cls.__tablename__}_created",
            )

    @declared_attr
    def updated_by(cls) -> Mapped[Optional["User"]]:  # noqa # type: ignore
        """Relationship to User who last updated this record."""
        is_user_model = cls.__name__ == "User"

        if is_user_model:
            return relationship(
                "User",
                foreign_keys=lambda: cls.updated_by_id,
                remote_side=lambda: [cls.id],
                backref="updated_users",
                post_update=True,
            )
        else:
            return relationship(
                "User",
                foreign_keys=lambda: cls.updated_by_id,
                backref=f"{cls.__tablename__}_updated",
            )

    # In case of int only IDs, uncomment the following constraints
    # @declared_attr
    # def __table_args__(cls):
    #     return (
    #         CheckConstraint(
    #             "created_by_id >= 0 OR created_by_id IS NULL",
    #             name=f"check_{cls.__tablename__}_created_by_positive",
    #         ),
    #         CheckConstraint(
    #             "updated_by_id >= 0 OR updated_by_id IS NULL",
    #             name=f"check_{cls.__tablename__}_updated_by_positive",
    #         ),
    #     )
