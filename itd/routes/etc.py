from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from itd.client import Client

def get_top_clans(client: Client):
    return client.request('get', 'users/stats/top-clans')

def get_who_to_follow(client: Client):
    return client.request('get', 'users/suggestions/who-to-follow')
