from uuid import UUID
from _io import BufferedReader
from datetime import datetime

from requests import Session
from requests.adapters import HTTPAdapter

from itd._default import _default_client, set_default_client
from itd.exceptions import NoCookie, SamePassword, InvalidOldPassword, Unauthorized
from itd.hashtag import Hashtag
from itd.request import fetch, decode_jwt_payload
from itd.routes.auth import refresh_token, change_password, logout
from itd.routes.search import search
from itd.user import Me, User


class Client:
    access_token: str | None = None
    refresh_token: str | None = None
    last_actions: dict[str, datetime] = {}
    default_delay: float = 0.2
    _user = None

    def __init__(self, refresh_token: str | None = None, access_token: str | None = None):
        self._stream_active = False  # Флаг для остановки stream_notifications
        self.session = Session()
        adapter = HTTPAdapter(pool_connections=1, pool_maxsize=10, pool_block=False)
        self.session.mount('https://', adapter)

        if access_token:
            self.access_token = access_token.replace('Bearer ', '')

        elif refresh_token:
            self.refresh_token = refresh_token
            self.session.cookies.set('refresh_token', refresh_token, path='/', domain='xn--d1ah4a.com')
            self.refresh_auth()


        if _default_client is None:
            set_default_client(self)

    def request(self, method: str, url: str, params: dict = {}, files: dict[str, tuple[str, BufferedReader | bytes]] = {}):
        """Сделать запрос

        Args:
            method (str): Метод
            url (str): URL
            params (dict, optional): Параметры. Defaults to {}.
            files (dict[str, tuple[str, BufferedReader | bytes]], optional): Файлы. Defaults to {}.
        """
        def _fetch():
            return fetch(self.token, method, url, params, files, session=self.session)

        if not self.refresh_token:
            return _fetch()

        try:
            return _fetch()
        except Unauthorized:
            self.refresh_auth()
            return _fetch()

    def refresh_auth(self) -> str:
        """Обновить access token

        Raises:
            NoCookie: Нет cookie

        Returns:
            str: Токен
        """
        print('refresh token')
        if not self.refresh_token:
            raise NoCookie()

        res = refresh_token(self.session)
        res.raise_for_status()

        self.access_token = res.json()['accessToken']

        assert self.access_token
        return self.access_token


    @property
    def token(self) -> str:
        assert self.access_token, 'Access token not refreshed yet'
        return self.access_token

    @property
    def user_id(self) -> UUID:
        return UUID(decode_jwt_payload(self.token)['sub'])

    @property
    def user(self):
        if not self._user:
            self._user = Me()
        return self._user


    def logout(self) -> dict:
        """Выход из аккаунта

        Raises:
            NoCookie: Нет cookie

        Returns:
            dict: Ответ API
        """
        # if not self.cookies:
            # raise NoCookie()

        res = logout(self)
        res.raise_for_status()

        return res.json()


    def change_password(self, old: str, new: str) -> dict:
        """Смена пароля

        Args:
            old (str): Старый пароль
            new (str): Новый пароль

        Raises:
            NoCookie: Нет cookie
            SamePassword: Одинаковые пароли
            InvalidOldPassword: Старый пароль неверный

        Returns:
            dict: Ответ API `{'message': 'Password changed successfully'}`
        """
        if not self.refresh_token:
            raise NoCookie()

        res = change_password(self, old, new)
        if res.json().get('error', {}).get('code') == 'SAME_PASSWORD':
            raise SamePassword()
        if res.json().get('error', {}).get('code') == 'INVALID_OLD_PASSWORD':
            raise InvalidOldPassword()
        res.raise_for_status()

        return res.json()
