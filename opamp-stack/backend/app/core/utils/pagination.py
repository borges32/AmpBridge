"""Pagination utilities for API responses."""

from typing import TypeVar, Generic, List, Optional, Dict, Any
from math import ceil

from pydantic import BaseModel, Field
from sqlalchemy.orm import Query

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters for API requests."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""
    
    items: List[T] = Field(description="List of items for current page")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        pagination: PaginationParams
    ) -> 'PaginatedResponse[T]':
        """Create paginated response from items and pagination params.
        
        Args:
            items: List of items for current page
            total: Total number of items
            pagination: Pagination parameters
            
        Returns:
            Paginated response
        """
        pages = ceil(total / pagination.size) if total > 0 else 1
        
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages,
            has_next=pagination.page < pages,
            has_prev=pagination.page > 1
        )


def paginate_query(query: Query, pagination: PaginationParams) -> tuple[List[Any], int]:
    """Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query to paginate
        pagination: Pagination parameters
        
    Returns:
        Tuple of (items, total_count)
    """
    # Get total count
    total = query.count()
    
    # Apply pagination
    items = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return items, total


class FilterParams(BaseModel):
    """Base filter parameters."""
    
    search: Optional[str] = Field(default=None, description="Search term")
    sort_by: Optional[str] = Field(default=None, description="Sort field")
    sort_order: Optional[str] = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.dict().items() if v is not None}