"""
Reusable pagination helpers for list endpoints.
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy.orm import Query

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list[Any], total: int, params: PageParams) -> "PagedResponse[Any]":
        pages = max(1, -(-total // params.page_size))  # ceiling division
        return cls(items=items, total=total, page=params.page, page_size=params.page_size, pages=pages)
