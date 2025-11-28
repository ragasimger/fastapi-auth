from base64 import b64decode, b64encode
from collections import namedtuple
from datetime import datetime
from typing import Generic, List, Optional, Type, TypeVar
from urllib import parse

from pydantic import BaseModel, Field
from sqlalchemy import asc, desc

from .base import BasePaginator, ModelType

Cursor = namedtuple("Cursor", ["offset", "reverse", "position"])
T = TypeVar("T")


class CursorInfo(BaseModel):
    has_next: bool
    has_previous: bool
    next_cursor: Optional[str] = None
    previous_cursor: Optional[str] = None


class CursorPaginatedResponse(BaseModel, Generic[T]):
    message: Optional[str] = Field(None, description="Response message")

    cursor_info: Optional[CursorInfo] = None  # Add this

    next: Optional[str] = Field(None, description="URL to next page")
    previous: Optional[str] = Field(None, description="URL to previous page")
    data: List[T] = Field(description="Paginated data")

    class Config:
        json_schema_extra = {
            "example": {
                "next": "https://api.example.com/feed?cursor=12345&page_size=20",
                "previous": "https://api.example.com/feed?cursor=12340&page_size=20",
                "data": [],
            }
        }


class CursorPaginator(BasePaginator):
    """
    Implements the same logic as Django REST Framework's CursorPagination.

    Usage:
        paginator = CursorPaginator(
            model=Post,
            session=session,
            request=request,
            cursor_query_param="cursor",
            page_size=20,
            ordering=("id",),  # or ("-created_at", "id")
            filter_fields=[("is_published", "boolean")],
        )
        return await paginator.get_paginated_response(schema=PostSchema)
    """

    def __init__(
        self,
        *args,
        cursor_query_param: str = "cursor",
        page_size: int = 10,
        ordering: tuple = ("-id",),
        offset_cutoff: int = 1000,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.cursor_query_param = cursor_query_param
        self.page_size = page_size
        self.ordering = ordering if isinstance(ordering, tuple) else (ordering,)
        self.offset_cutoff = offset_cutoff

        # These will be set during pagination
        self.cursor = None
        self.has_next = False
        self.has_previous = False
        self.next_position = None
        self.previous_position = None
        self.page = []
        self.base_url = None

    def _reverse_ordering(self, ordering_tuple):
        """
        Given an order_by tuple such as `('-created', 'id')` reverse the
        ordering and return a new tuple, eg. `('created', '-id')`.
        """

        def invert(x):
            return x[1:] if x.startswith("-") else "-" + x

        return tuple([invert(item) for item in ordering_tuple])

    def decode_cursor(self) -> Optional[Cursor]:
        """
        Given a request with a cursor, return a `Cursor` instance.
        """
        # Get cursor from query params
        encoded = self.request.query_params.get(self.cursor_query_param)
        if encoded is None:
            return None

        try:
            querystring = b64decode(encoded.encode("ascii")).decode("ascii")
            tokens = parse.parse_qs(querystring, keep_blank_values=True)

            offset = tokens.get("o", ["0"])[0]
            offset = int(offset)
            if offset < 0:
                offset = 0
            if offset > self.offset_cutoff:
                offset = self.offset_cutoff

            reverse = tokens.get("r", ["0"])[0]
            reverse = bool(int(reverse))

            position = tokens.get("p", [None])[0]
        except (TypeError, ValueError):
            return None

        return Cursor(offset=offset, reverse=reverse, position=position)

    def _encode_cursor(self, cursor: Cursor) -> str:
        """
        Given a Cursor instance, return a URL with encoded cursor.
        """
        tokens = {}
        if cursor.offset != 0:
            tokens["o"] = str(cursor.offset)
        if cursor.reverse:
            tokens["r"] = "1"
        if cursor.position is not None:
            tokens["p"] = cursor.position

        querystring = parse.urlencode(tokens, doseq=True)
        encoded = b64encode(querystring.encode("ascii")).decode("ascii")

        # Build URL manually to avoid double encoding
        base_url = str(self.request.url)
        parsed = parse.urlparse(base_url)

        # Get existing query params as dict
        query_dict = parse.parse_qs(parsed.query, keep_blank_values=True)

        # Remove cursor from existing params
        if self.cursor_query_param in query_dict:
            del query_dict[self.cursor_query_param]

        # Build query string manually without encoding the cursor value
        query_parts = []
        for key, values in query_dict.items():
            for value in values:
                query_parts.append(f"{key}={value}")

        # Add cursor without URL encoding
        query_parts.append(f"{self.cursor_query_param}={encoded}")

        new_query = "&".join(query_parts)

        return parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    def _get_position_from_instance(self, instance, ordering):
        """Extract the position value from an instance based on ordering."""
        field_name = ordering[0].lstrip("-")
        attr = getattr(instance, field_name)

        # Convert datetime to ISO string for position
        if isinstance(attr, datetime):
            return attr.isoformat()
        return str(attr)

    def _convert_position_to_value(self, position_str: str, field_name: str):
        """Convert position string back to the proper Python type for comparison."""
        if not hasattr(self.model, field_name):
            return position_str

        # Get the column type
        column = getattr(self.model, field_name)
        column_type = column.type

        # Check if it's a datetime field
        if hasattr(column_type, "python_type"):
            if column_type.python_type is datetime:
                try:
                    return datetime.fromisoformat(position_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return position_str
            elif column_type.python_type is int:
                try:
                    return int(position_str)
                except (ValueError, TypeError):
                    return position_str

        return position_str

    def _extract_cursor_from_url(self, url: Optional[str]) -> Optional[str]:
        """Extract just the cursor parameter from a URL"""
        if not url:
            return None

        parsed = parse.urlparse(url)
        query_dict = parse.parse_qs(parsed.query)
        cursor_list = query_dict.get(self.cursor_query_param, [])
        return cursor_list[0] if cursor_list else None

    async def paginate(self) -> List[ModelType]:
        """
        Execute cursor pagination following DRF's logic.
        Returns the paginated data.
        """
        self.base_url = str(self.request.url)
        self.cursor = self.decode_cursor()

        if self.cursor is None:
            offset, reverse, current_position = 0, False, None
        else:
            offset, reverse, current_position = self.cursor

        # Build base query
        stmt = self._build_data_stmt()

        # Apply ordering based on reverse flag
        if reverse:
            reversed_ordering = self._reverse_ordering(self.ordering)
            for order_field in reversed_ordering:
                field_name = order_field.lstrip("-")
                if not hasattr(self.model, field_name):
                    raise ValueError(f"Model does not have field: {field_name}")

                order_attr = getattr(self.model, field_name)
                if order_field.startswith("-"):
                    stmt = stmt.order_by(desc(order_attr))
                else:
                    stmt = stmt.order_by(asc(order_attr))
        else:
            for order_field in self.ordering:
                field_name = order_field.lstrip("-")
                if not hasattr(self.model, field_name):
                    raise ValueError(f"Model does not have field: {field_name}")

                order_attr = getattr(self.model, field_name)
                if order_field.startswith("-"):
                    stmt = stmt.order_by(desc(order_attr))
                else:
                    stmt = stmt.order_by(asc(order_attr))

        # Filter by cursor position if we have one
        if current_position is not None:
            order = self.ordering[0]
            is_reversed = order.startswith("-")
            order_attr_name = order.lstrip("-")
            order_attr = getattr(self.model, order_attr_name)

            # Convert position string back to proper type
            position_value = self._convert_position_to_value(
                current_position, order_attr_name
            )

            # XOR logic: (cursor reversed) XOR (queryset reversed)
            if self.cursor.reverse != is_reversed:
                stmt = stmt.filter(order_attr < position_value)
            else:
                stmt = stmt.filter(order_attr > position_value)

        # Fetch page_size + 1 items with offset
        stmt = stmt.offset(offset).limit(self.page_size + 1)

        result = await self.session.scalars(stmt)
        data = list(result.unique().all())

        self.page = list(data[: self.page_size])

        # Determine if there's a following position
        if len(data) > len(self.page):
            has_following_position = True
            following_position = self._get_position_from_instance(
                data[-1], self.ordering
            )
        else:
            has_following_position = False
            following_position = None

        # Reverse the page if we're in reverse mode
        if reverse:
            self.page = list(reversed(self.page))

            # Determine next and previous for reverse cursors
            self.has_next = (current_position is not None) or (offset > 0)
            self.has_previous = has_following_position

            if self.has_next:
                self.next_position = current_position
            if self.has_previous:
                self.previous_position = following_position
        else:
            # Determine next and previous for forward cursors
            self.has_next = has_following_position
            self.has_previous = (current_position is not None) or (offset > 0)

            if self.has_next:
                self.next_position = following_position
            if self.has_previous:
                self.previous_position = current_position

        return self.page

    def get_next_link(self) -> Optional[str]:
        """Generate the next page link."""
        if not self.has_next:
            return None

        if (
            self.page
            and self.cursor
            and self.cursor.reverse
            and self.cursor.offset != 0
        ):
            compare = self._get_position_from_instance(self.page[-1], self.ordering)
        else:
            compare = self.next_position

        offset = 0
        has_item_with_unique_position = False

        for item in reversed(self.page):
            position = self._get_position_from_instance(item, self.ordering)
            if position != compare:
                has_item_with_unique_position = True
                break
            compare = position
            offset += 1

        if self.page and not has_item_with_unique_position:
            if not self.has_previous:
                offset = self.page_size
                position = None
            elif self.cursor.reverse:
                offset = 0
                position = self.previous_position
            else:
                offset = self.cursor.offset + self.page_size
                position = self.previous_position

        if not self.page:
            position = self.next_position

        cursor = Cursor(offset=offset, reverse=False, position=position)
        return self._encode_cursor(cursor)

    def get_previous_link(self) -> Optional[str]:
        """Generate the previous page link."""
        if not self.has_previous:
            return None

        if (
            self.page
            and self.cursor
            and not self.cursor.reverse
            and self.cursor.offset != 0
        ):
            compare = self._get_position_from_instance(self.page[0], self.ordering)
        else:
            compare = self.previous_position

        offset = 0
        has_item_with_unique_position = False

        for item in self.page:
            position = self._get_position_from_instance(item, self.ordering)
            if position != compare:
                has_item_with_unique_position = True
                break
            compare = position
            offset += 1

        if self.page and not has_item_with_unique_position:
            if not self.has_next:
                offset = self.page_size
                position = None
            elif self.cursor.reverse:
                offset = self.cursor.offset + self.page_size
                position = self.next_position
            else:
                offset = 0
                position = self.next_position

        if not self.page:
            position = self.previous_position

        cursor = Cursor(offset=offset, reverse=True, position=position)
        return self._encode_cursor(cursor)

    async def get_paginated_response(
        self,
        schema: Type[BaseModel],
        message: str = "",
    ) -> CursorPaginatedResponse[T]:
        """Get cursor-based paginated response (no count)"""
        data = await self.paginate()

        # Serialize data
        serialized_data = [
            schema.model_validate(obj, from_attributes=True) for obj in data
        ]
        next_link = self.get_next_link()
        previous_link = self.get_previous_link()
        cursor_info = CursorInfo(
            has_next=self.has_next,
            has_previous=self.has_previous,
            next_cursor=self._extract_cursor_from_url(next_link),
            previous_cursor=self._extract_cursor_from_url(previous_link),
        )

        return CursorPaginatedResponse(
            message=message,
            next=next_link,
            previous=previous_link,
            data=serialized_data,
            cursor_info=cursor_info.model_dump(),
        )
