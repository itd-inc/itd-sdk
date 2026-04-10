from uuid import UUID

from pydantic import BaseModel, Field

from itd.routes.hashtags import get_hashtags, get_posts_by_hashtag
from itd.base import ITDBaseModel, refresh_wrapper
from itd.client import Client


class Hashtag(ITDBaseModel):
    _validator = lambda _: _HashtagValidate

    id: UUID
    name: str
    posts_count: int = Field(alias='postsCount')

    def __init__(self, name: str, client: Client | None = None) -> None:
        super().__init__(client)
        self.name = name.lstrip('#')

    @refresh_wrapper
    def refresh(self, client: Client | None = None):
        return get_posts_by_hashtag(client or self.client, self.name, limit=1).json()['data']['hashtag']

    def __str__(self) -> str:
        return '#' + self.name

    def __int__(self) -> int:
        return self.posts_count



class _HashtagValidate(BaseModel, Hashtag):
    pass