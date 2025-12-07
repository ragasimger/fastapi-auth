import re
from typing import Annotated, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

from base.utils.pagination.cursor import CursorInfo

T = TypeVar("T")


class PydanticBaseModel(BaseModel):
    class Config:
        extra = "forbid"


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Generic cursor-paginated response that works with any data type."""

    message: Optional[str] = Field(None, description="Response message")
    next: Optional[str] = Field(None, description="URL to next page")
    previous: Optional[str] = Field(None, description="URL to previous page")
    cursor_info: Optional[CursorInfo] = None
    data: List[T] = Field(default_factory=list, description="Paginated data")


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    total_count: int = Field(description="Total number of data")
    page_count: int = Field(description="Total number of pages")
    current_page: int = Field(description="Current page number")
    page_size: int = Field(description="Data per page")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


class LimitOffsetListPaginatedResponse(BaseModel, Generic[T]):
    message: Optional[str] = Field(None, description="Response message")
    next: Optional[str] = Field(None, description="URL to next page")
    previous: Optional[str] = Field(None, description="URL to previous page")
    meta: Optional[PaginationMeta] = Field(
        None, description="Additional pagination metadata"
    )
    data: List[T] = Field(default_factory=list, description="Paginated data")
