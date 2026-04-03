from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from itd.client import Client

def get_pins(client: Client):
    return client.request('get', 'users/me/pins')

def remove_pin(client: Client):
    return client.request('delete', 'users/me/pin')

def set_pin(client: Client, slug: str):
    return client.request('put', 'users/me/pin', {'slug': slug})
