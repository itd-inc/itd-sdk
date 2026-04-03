from __future__ import annotations
from uuid import UUID
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from itd.client import Client

def get_hashtags(client: Client, limit: int = 10):
    return client.request('get', 'hashtags/trending', {'limit': limit})

def get_posts_by_hashtag(client: Client, hashtag: str, limit: int = 20, cursor: UUID | None = None):
    return client.request('get', f'hashtags/{hashtag}/posts', {'limit': limit, 'cursor': cursor})
