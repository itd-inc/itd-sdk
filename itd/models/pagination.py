from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

# TODO: refactor paginations
class Pagination(BaseModel):
    page: int | None = 1
    limit: int = 20
    total: int | None = None
    has_more: bool = Field(True, alias='hasMore')
    next_cursor: UUID | None = Field(None, alias='nextCursor')


class PostsPagintaion(BaseModel):
    limit: int = 20
    next_cursor: int | datetime | None = Field(1, alias='nextCursor')
    has_more: bool = Field(True, alias='hasMore')


class LikedPostsPagintaion(BaseModel):
    limit: int = 20
    next_cursor: datetime | None = Field(None, alias='nextCursor')
    has_more: bool = Field(True, alias='hasMore')


class PagePagination(BaseModel):
    page: int = 1
    limit: int = 20
    total: int = 0
    has_more: bool = Field(False, validation_alias='hasMore')