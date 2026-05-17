from __future__ import annotations
from typing import TYPE_CHECKING

from requests import Response

from itd.base import catch_errors, rate_limit
from itd.enums import AuthLevel
from itd.exceptions import (
    InvalidPasswordError, SamePasswordError, InvalidOldPasswordError, SessionNotFoundError,
    SessionExpiredError, SessionRevokedError, InvalidCredentials, CaptchaFailedError,
    EmailDomainNotAllowed
)
if TYPE_CHECKING:
    from itd.client import Client

@rate_limit()
@catch_errors(SessionExpiredError(), SessionNotFoundError(), SessionRevokedError())
def refresh_token(client: Client) -> Response:
    return client.request('post', 'v1/auth/refresh', level=AuthLevel.REFRESH)

@rate_limit()
@catch_errors(InvalidPasswordError(), SamePasswordError(), InvalidOldPasswordError())
def change_password(client: Client, old: str, new: str) -> Response:
    return client.request('post', 'v1/auth/change-password', {'newPassword': new, 'oldPassword': old})

@rate_limit()
@catch_errors()
def logout(client: Client) -> Response:
    return client.request('post', 'v1/auth/logout', level=AuthLevel.REFRESH)


@rate_limit()
@catch_errors(InvalidCredentials(), CaptchaFailedError(), EmailDomainNotAllowed())
def sign_in(client: Client, email: str, password: str, turnstile: str):
    return client.request('post', 'v1/auth/sign-in', {'email': email, 'password': password, 'turnstileToken': turnstile}, level=AuthLevel.NO)
