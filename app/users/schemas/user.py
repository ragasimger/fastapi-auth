import re
from enum import Enum
from typing import List, Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from base.schemas import CursorPaginatedResponse, PydanticBaseModel
from base.utils.pagination import PaginationMeta

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 20
PASSWORD_ERROR_MSG = "Password must include uppercase, lowercase, digit, and special symbol with no space"


def validate_password_strength(value: str) -> str:
    """Shared password strength validation logic."""
    if (
        not re.search(r"[A-Z]", value)  # missing uppercase
        or not re.search(r"[a-z]", value)  # missing lowercase
        or not re.search(r"\d", value)  # missing number
        or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value)  # missing special char
        or " " in value  # contains whitespace
    ):
        raise ValueError(PASSWORD_ERROR_MSG)
    return value


class UserBase(PydanticBaseModel):
    """Core identity fields shared across most schemas."""

    username: str = Field(..., description="A unique username for the user")
    name: str = Field(..., description="The full name of the user")
    email: EmailStr = Field(..., description="A valid user email address")


class UserAccessBase(PydanticBaseModel):
    """Fields related to user status and privileges."""

    is_active: bool = False
    is_admin: bool = False
    is_superuser: bool = False


class UserProfileResponse(PydanticBaseModel):
    id: str
    profile_image_url: Optional[str] = ""


class UserResponseBase(UserBase, UserAccessBase):
    """Base schema for reading user data from DB."""

    id: str


class UserListResponse(UserResponseBase):
    profile: Optional[UserProfileResponse] = None


class GenericUserResponse(UserResponseBase):
    """
    Detailed schema for Single User Retrieval.
    Includes relationships like refresh tokens.
    """

    profile: Optional[UserProfileResponse] = None
    # refresh_tokens: Optional[List[RefreshTokenResponse]] = None


class UserResponseForRetrieval(UserResponseBase):
    """Schema for retrieving user details."""

    profile: Optional[UserProfileResponse] = None
    role: Optional[List[str]] = None
    permission: Optional[List[str]] = None


class UserCreateRequest(UserBase, UserAccessBase):
    """Schema for creating a new user."""

    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description=PASSWORD_ERROR_MSG,
    )
    role_ids: Optional[List[str]] = None
    permission_ids: Optional[List[str]] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserCreateResponse(UserBase):
    """Response after successful creation."""

    id: str
    role_ids: Optional[List[str]] = None
    permission_ids: Optional[List[str]] = None


class UserUpdateRequest(PydanticBaseModel):
    """Schema for partial updates (PATCH)."""

    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    # password: Optional[str] = Field(default=None, min_length=PASSWORD_MIN_LENGTH)
    is_active: Optional[bool] = False
    is_admin: Optional[bool] = False
    is_superuser: Optional[bool] = False

    role_ids: Optional[List[str]] = []
    permission_ids: Optional[List[str]] = []

    # validate username if provided


class UserUpdateResponse(UserUpdateRequest):
    """Response after update."""

    username: Optional[str] = ""
    name: Optional[str] = ""
    email: Optional[EmailStr] = ""
    is_active: Optional[bool] = False
    is_admin: Optional[bool] = False
    is_superuser: Optional[bool] = False

    role_ids: Optional[List[str]] = []
    permission_ids: Optional[List[str]] = []


class UpdatePasswordRequest(PydanticBaseModel):
    """Schema for password change operations."""

    old_password: str
    new_password: str = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
    password_repeat: str = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password == self.old_password:
            raise ValueError("New password cannot be the same as the old password")
        if self.new_password != self.password_repeat:
            raise ValueError("Passwords do not match")
        return self

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str, info: ValidationInfo) -> str:
        validate_password_strength(value)

        if "old_password" in info.data and value == info.data["old_password"]:
            raise ValueError("New password cannot be the same as the old password")

        return value

    @field_validator("password_repeat")
    @classmethod
    def validate_passwords_match(cls, value: str, info: ValidationInfo) -> str:
        # info.data will contain 'new_password' because it is defined higher up
        if "new_password" in info.data and value != info.data["new_password"]:
            raise ValueError("Passwords do not match")

        return value


class UpdatePasswordResponse(PydanticBaseModel):
    """Response after password update."""

    success: bool = True
    message: str = "Password updated successfully."


# --- Pagination Schemas ---


class UserListPaginatedResponse(PydanticBaseModel):
    message: Optional[str] = Field(None, description="Response message")
    next: Optional[str] = Field(None, description="URL to next page")
    previous: Optional[str] = Field(None, description="URL to previous page")
    meta: Optional[PaginationMeta] = Field(
        None, description="Additional pagination metadata"
    )
    data: List[UserListResponse] = Field(description="Paginated data")


class CursorInfo(PydanticBaseModel):
    has_next: bool
    has_previous: bool
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None


UserListCursorPaginatedResponse = CursorPaginatedResponse[UserListResponse]


class UserFilters(BaseModel):
    id: Optional[str] = None
    is_active: Optional[bool] = None
    profile_id: Optional[str] = None


class UserOrderingField(str, Enum):
    # ID_ASC = "id"
    # ID_DESC = "-id"
    CREATED_AT_ASC = "created_at"
    CREATED_AT_DESC = "-created_at"
    NAME_ASC = "name"
    NAME_DESC = "-name"
    USERNAME_ASC = "username"
    USERNAME_DESC = "-username"
