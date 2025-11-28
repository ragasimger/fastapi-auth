from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from fastapi import Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import Select

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

T = TypeVar("T")
ModelType = TypeVar("ModelType", bound=DeclarativeBase)


# ============================================================================
# FASTAPI DEPENDENCIES (Query Parameters)
# ============================================================================


def SearchParam(
    default: Optional[str] = None,
    description: str = "Search query across multiple fields",
    example: str = "john doe",
) -> Optional[str]:
    """
    Search parameter for FastAPI routes.

    Usage in route:
        search: Annotated[Optional[str], Depends(lambda: SearchParam())] = None

    Or directly:
        search: Optional[str] = Query(None, description="Search query")
    """
    return Query(
        default,
        description=description,
        example=example,
        alias="q",  # Also accepts ?q=...
    )


def OrderingParam(
    default: Optional[str] = None,
    description: str = "Order data by field(s). Prefix with '-' for descending. Comma-separated for multiple.",
    example: str = "-created_at,name",
) -> Optional[str]:
    """Ordering parameter for FastAPI routes"""
    return Query(
        default,
        description=description,
        example=example,
    )


# ============================================================================
# Pydantic Response MODELS
# ============================================================================


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


# ============================================================================
# QUERY PARAMETER EXTRACTOR
# ============================================================================


class QueryParamExtractor:
    """Extract and parse query parameters for filtering, searching, and ordering"""

    FILTER_TYPES = {
        "str": str,
        "text": str,
        "int": int,
        "integer": int,
        "id": int,
        "float": float,
        "bool": lambda x: x.lower() in ["true", "1", "yes", "on"],
        "boolean": lambda x: x.lower() in ["true", "1", "yes", "on"],
        "date": lambda x: datetime.strptime(x, "%Y-%m-%d").date(),
        "datetime": lambda x: datetime.fromisoformat(x),
    }

    @staticmethod
    def extract_filters(request: Request, filter_fields: List[tuple]) -> Dict[str, Any]:
        """
        Extract filter parameters from request.

        Supports multiple patterns:
        - Direct: ?status=active
        - Bracketed: ?filter[status]=active
        - Operators: ?age__gte=18, ?created_at__lte=2024-01-01
        """
        query_params = request.query_params
        filter_params = {}

        for field_name, field_type in filter_fields:
            # Try multiple patterns
            param_value = query_params.get(field_name) or query_params.get(
                f"filter[{field_name}]"
            )

            if param_value is not None:
                try:
                    converter = QueryParamExtractor.FILTER_TYPES.get(field_type, str)
                    filter_params[field_name] = converter(param_value)
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Invalid format for field '{field_name}': {param_value}. "
                        f"Expected type: {field_type}"
                    ) from e

            # Check for operator-based filters (e.g., age__gte=18)
            for operator in ["gt", "gte", "lt", "lte", "ne", "in", "like", "ilike"]:
                operator_key = f"{field_name}__{operator}"
                operator_value = query_params.get(operator_key)

                if operator_value is not None:
                    try:
                        converter = QueryParamExtractor.FILTER_TYPES.get(
                            field_type, str
                        )
                        # Handle 'in' operator (comma-separated values)
                        if operator == "in":
                            filter_params[operator_key] = [
                                converter(v.strip()) for v in operator_value.split(",")
                            ]
                        else:
                            filter_params[operator_key] = converter(operator_value)
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f"Invalid format for field '{operator_key}': {operator_value}"
                        ) from e

        return filter_params

    @staticmethod
    def extract_search(request: Request, search_fields: List[str]) -> Optional[str]:
        """
        Extract search parameter from request.

        Supports: ?search=john or ?q=john
        """
        query_params = request.query_params
        return query_params.get("search") or query_params.get("q")

    @staticmethod
    def extract_ordering(
        request: Request,
        ordering_fields: List[str],
        default_ordering: Optional[str] = None,
    ) -> List[str]:
        """
        Extract ordering parameters from request.

        Supports:
        - DRF-style: ?ordering=-created_at,name
        - Alternative: ?order_by=-created_at,name
        """
        query_params = request.query_params
        ordering_list = []

        # Try DRF-style first
        ordering_param = query_params.get("ordering") or query_params.get("order_by")
        if ordering_param:
            ordering_list = [o.strip() for o in ordering_param.split(",")]
            # Validate fields
            ordering_list = [
                order for order in ordering_list if order.lstrip("-") in ordering_fields
            ]

        # Apply default if nothing specified
        if not ordering_list and default_ordering:
            ordering_list = [default_ordering]

        return ordering_list


# ============================================================================
# QUERY BUILDER
# ============================================================================


class BaseQueryBuilder:
    """Base query builder with common filtering logic"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def apply_filters(self, stmt: Select, filter_params: Dict[str, Any]) -> Select:
        """
        Apply filters with operator support.

        Supports:
        - Exact: field=value
        - Greater than: field__gt=value
        - Less than: field__lt=value
        - In list: field__in=val1,val2
        - Like: field__like=%pattern%
        """
        for key, value in filter_params.items():
            if "__" in key:
                field_name, operator = key.split("__", 1)
                if not hasattr(self.model, field_name):
                    continue

                field = getattr(self.model, field_name)

                if operator == "gt":
                    stmt = stmt.where(field > value)
                elif operator == "gte":
                    stmt = stmt.where(field >= value)
                elif operator == "lt":
                    stmt = stmt.where(field < value)
                elif operator == "lte":
                    stmt = stmt.where(field <= value)
                elif operator == "ne":
                    stmt = stmt.where(field != value)
                elif operator == "in":
                    stmt = stmt.where(field.in_(value))
                elif operator == "like":
                    stmt = stmt.where(field.like(value))
                elif operator == "ilike":
                    stmt = stmt.where(field.ilike(value))
            else:
                if hasattr(self.model, key):
                    field = getattr(self.model, key)
                    stmt = stmt.where(field == value)

        return stmt

    def apply_search(
        self, stmt: Select, search_query: Optional[str], search_fields: List[str]
    ) -> Select:
        """Apply search across multiple fields (case-insensitive)"""
        if not search_query or not search_fields:
            return stmt

        search_conditions = []
        for field_name in search_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                search_conditions.append(field.ilike(f"%{search_query}%"))

        if search_conditions:
            stmt = stmt.where(or_(*search_conditions))

        return stmt

    def apply_ordering(self, stmt: Select, ordering_list: List[str]) -> Select:
        """Apply ordering to query"""
        for order_item in ordering_list:
            descending = order_item.startswith("-")
            field_name = order_item.lstrip("-")

            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                stmt = stmt.order_by(desc(field) if descending else asc(field))

        return stmt


# ============================================================================
# BASE PAGINATOR
# ============================================================================


class BasePaginator:
    """Base paginator with shared functionality"""

    def __init__(
        self,
        model: Type[ModelType],
        session: AsyncSession,
        request: Request,
        filter_fields: Optional[List[tuple]] = None,  # For same model filtering.
        search_fields: Optional[List[str]] = None,
        ordering_fields: Optional[List[str]] = None,
        default_ordering: Optional[str] = None,
        base_query: Optional[Select] = None,
        additional_filters: Optional[
            List[Any]
        ] = None,  # Additional filters are used for related data. Like reverse data filtering.
        count_query: Optional[Select] = None,
        search_query: Optional[str] = None,
    ):
        """
        Args:
            model: SQLAlchemy model class
            session: AsyncSession instance
            request: FastAPI Request object
            filter_fields: List of tuples [(field_name, field_type), ...]
            search_fields: List of field names to search
            ordering_fields: List of field names allowed for ordering
            default_ordering: Default ordering (e.g., '-created_at')
            base_query: Optional base query (useful for joins, eager loading)
            additional_filters: Additional filter conditions
            count_query: Optional custom count query (useful for complex joins)
            search_query: Search query string (passed from route Query parameter)
        """
        self.model = model
        self.session = session
        self.request = request
        self.filter_fields = filter_fields or []
        self.search_fields = search_fields or []
        self.ordering_fields = ordering_fields or []
        self.default_ordering = default_ordering
        self.base_query = base_query
        self.additional_filters = additional_filters or []
        self.count_query = count_query
        self.search_query = search_query

        self.query_builder = BaseQueryBuilder(model)

    def _build_base_stmt(self) -> Select:
        """Build base statement"""
        if self.base_query is not None:
            return self.base_query
        return select(self.model)

    def _build_data_stmt(self) -> Select:
        """Build data query statement with all filters"""
        stmt = self._build_base_stmt()

        # Apply additional filters
        for filter_condition in self.additional_filters:
            stmt = stmt.where(filter_condition)

        # Extract and apply filters
        filter_params = QueryParamExtractor.extract_filters(
            self.request, self.filter_fields
        )
        stmt = self.query_builder.apply_filters(stmt, filter_params)

        # Use search query from route parameter OR extract from request
        search = self.search_query or QueryParamExtractor.extract_search(
            self.request, self.search_fields
        )
        stmt = self.query_builder.apply_search(stmt, search, self.search_fields)

        # Extract and apply ordering
        ordering_list = QueryParamExtractor.extract_ordering(
            self.request, self.ordering_fields, self.default_ordering
        )
        stmt = self.query_builder.apply_ordering(stmt, ordering_list)

        return stmt

    async def _get_total_count(self) -> int:
        """Get total count of items"""
        if self.count_query is not None:
            count_stmt = self.count_query
        else:
            count_stmt = select(func.count()).select_from(self.model)

        # Apply same filters as data query
        for filter_condition in self.additional_filters:
            count_stmt = count_stmt.where(filter_condition)

        filter_params = QueryParamExtractor.extract_filters(
            self.request, self.filter_fields
        )
        count_stmt = self.query_builder.apply_filters(count_stmt, filter_params)

        search = self.search_query or QueryParamExtractor.extract_search(
            self.request, self.search_fields
        )
        count_stmt = self.query_builder.apply_search(
            count_stmt, search, self.search_fields
        )

        result = await self.session.scalar(count_stmt)
        return result or 0

    def _build_url(self, **params) -> str:
        """Build URL with updated query parameters"""
        parsed_url = urlparse(str(self.request.url))
        query_params = dict(parse_qs(parsed_url.query, keep_blank_values=True))

        # Update with new params
        for key, value in params.items():
            if value is not None:
                query_params[key] = [str(value)]
            else:
                query_params.pop(key, None)

        query_string = urlencode(query_params, doseq=True)
        return urlunparse(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                "",
                query_string,
                "",
            )
        )
