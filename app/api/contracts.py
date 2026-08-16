"""Versioned API envelope and bounded pagination contracts."""

from fastapi import Query
from pydantic import BaseModel, Field


class PageParams:
    def __init__(
        self,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=100000),
    ):
        self.limit, self.offset = limit, offset


class PaginationMeta(BaseModel):
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    has_more: bool


def page_meta(page: PageParams, total: int) -> dict:
    return PaginationMeta(
        limit=page.limit, offset=page.offset, total=total,
        has_more=page.offset + page.limit < total,
    ).model_dump()
