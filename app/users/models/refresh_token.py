from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from base.models import AbstractBaseModel


class RefreshToken(AbstractBaseModel):
    __tablename__ = "refresh_tokens"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("auth_users.id", ondelete="CASCADE")
    )

    token: Mapped[str] = mapped_column(String(length=255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    user: Mapped["User"] = relationship(  # noqa # type: ignore
        "User",
        back_populates="refresh_tokens",
        # primaryjoin="RefreshToken.user_id == User.id",  # Explicit join
        foreign_keys=[user_id],
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
