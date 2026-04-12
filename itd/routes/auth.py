from __future__ import annotations
from typing import TYPE_CHECKING

from requests import Response, Session

from itd.request import fetch
from itd.exceptions import catch_errors, InvalidPassword, SamePassword, InvalidOldPassword
if TYPE_CHECKING:
    from itd.client import Client

def refresh_token(session: Session) -> Response:
    return fetch(None, 'post', 'v1/auth/refresh', session=session)

@catch_errors(InvalidPassword(), SamePassword(), InvalidOldPassword())
def change_password(client: Client, old: str, new: str) -> Response:
    return client.request('post', 'v1/auth/change-password', {'newPassword': new, 'oldPassword': old})

@catch_errors()
def logout(client: Client) -> Response:
    return client.request('post', 'v1/auth/logout')
