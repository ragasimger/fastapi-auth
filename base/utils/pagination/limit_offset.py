from typing import Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

from base.models import DeclarativeBase

from .base import BasePaginator

T = TypeVar("T")
ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    total_count: int = Field(description="Total number of items")
    page_count: int = Field(description="Total number of pages")
    current_page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """

    Used for both page-based and offset-based pagination.
    """

    message: Optional[str] = Field(None, description="Response message")
    count: int = Field(description="Total number of items")
    next: Optional[str] = Field(None, description="URL to next page")
    previous: Optional[str] = Field(None, description="URL to previous page")
    meta: Optional[PaginationMeta] = Field(
        None, description="Additional pagination metadata"
    )
    data: List[T] = Field(description="Paginated data")

    class Config:
        json_schema_extra = {
            "example": {
                "count": 100,
                "next": "https://api.example.com/users?page=3",
                "previous": "https://api.example.com/users?page=1",
                "meta": {
                    "total_count": 100,
                    "page_count": 10,
                    "current_page": 2,
                    "page_size": 10,
                    "has_next": True,
                    "has_previous": True,
                },
                "data": [],
            }
        }


class LimitOffsetPaginator(BasePaginator):
    """
    Offset-based paginator (DRF LimitOffsetPagination style).

    Best for: APIs that need precise control over offset.

    Usage:
        paginator = LimitOffsetPaginator(
            model=User,
            session=session,
            request=request,
            limit=10,
            offset=0,
            search_query=search,
            filter_fields=[("is_active", "boolean")],
            search_fields=["name", "email"],
            ordering_fields=["created_at", "name"],
            default_ordering="-created_at",
        )
        return await paginator.get_paginated_response(schema=UserSchema)
    """

    def __init__(
        self,
        *args,
        limit: int = 10,
        offset: int = 0,
        max_limit: int = 100,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.limit = min(max(1, limit), max_limit)
        self.offset = max(0, offset)
        self.max_limit = max_limit

    async def paginate(self) -> tuple[List[ModelType], int]:
        """Execute pagination and return data with total count"""
        # Get total count
        total_count = await self._get_total_count()

        # Build and execute data query
        data_stmt = self._build_data_stmt()
        data_stmt = data_stmt.offset(self.offset).limit(self.limit)

        result = await self.session.scalars(data_stmt)
        data = list(result.unique().all())

        return data, total_count

    async def get_paginated_response(
        self,
        schema: Type[BaseModel],
        include_meta: bool = True,
        message="",
    ) -> PaginatedResponse[T]:
        """Get DRF-style paginated response with offset/limit"""
        data, total_count = await self.paginate()

        # Serialize data
        serialized_data = [
            schema.model_validate(obj, from_attributes=True) for obj in data
        ]

        # Build navigation URLs
        next_url = None
        previous_url = None

        # Only generate pagination links if there are data
        if total_count > 0:
            # Generate next URL if there are more items
            if (self.offset + self.limit) < total_count:
                next_url = self._build_url(
                    limit=self.limit, offset=self.offset + self.limit
                )

            # Generate previous URL
            if self.offset > 0:
                prev_offset = max(0, self.offset - self.limit)
                previous_url = self._build_url(limit=self.limit, offset=prev_offset)

        # Calculate page info for meta
        current_page = (self.offset // self.limit) + 1 if self.limit > 0 else 1
        total_pages = (
            (total_count + self.limit - 1) // self.limit
            if self.limit > 0 and total_count > 0
            else 0
        )

        # Build response
        response_data = {
            "message": message,
            "count": total_count,
            "next": next_url,
            "previous": previous_url,
            "data": serialized_data,
        }

        # Add metadata if requested
        if include_meta:
            response_data["meta"] = PaginationMeta(
                total_count=total_count,
                page_count=total_pages,
                current_page=current_page if total_count > 0 else 1,
                page_size=self.limit,
                has_next=(self.offset + self.limit) < total_count,
                has_previous=self.offset > 0 and total_count > 0,
            )

        return PaginatedResponse(**response_data)
