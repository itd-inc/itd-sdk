from uuid import UUID
from _io import BufferedReader
from datetime import datetime
from dataclasses import dataclass, field

from requests import Session
from requests.utils import default_user_agent
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

from itd._default import _default_client, set_default_client
from itd.exceptions import UnauthorizedError, InsufficientAuthLevelError, AccessTokenExpiredError, RateLimitError, InternalError
from itd.hashtag import Hashtag
from itd.request import fetch, decode_jwt_payload
from itd.enums import RateLimitMode, All, DebugResponseMode, ParseMode, Batch, BATCH, UserAgent, AuthLevel
from itd.user import Me, User
from itd.api.auth import refresh_token, change_password, logout
from itd.api.search import search
from itd.api.users import get_follow_status
from itd.utils import to_uuid, get_sdk_user_agent
from itd.logger import get_logger


l = get_logger('client')


@dataclass
class Config:
    rate_limit: RateLimitMode = RateLimitMode.MID
    rate_limit_default: int | None = None # overrides ratelimit mode  # rate limit for standard actions
    rate_limit_actions: dict[str, float | int] = field(default_factory=lambda: {}) # overrides ratelimit mode  # custom rate limits for specific actions (eg. {'add_comment': 10})
    # is_logging_enabled: bool = True # TODO
    # logging_level = 'DEBUG'
    is_default: bool = False
    userposts_add_pinned_post: bool = True
    auto_load: bool = True
    load_on_getitem: int | All | Batch | None = 1
    load_on_iter: int | All | Batch | None = BATCH
    force_load_lists: bool = False # load lists even if has_more is False
    debug_response: DebugResponseMode = DebugResponseMode.NO
    timeout: float = 30
    timeout_file: float = 120
    url: str = 'xn--d1ah4a.com'
    url_api: str | None = None
    user_agent: UserAgent | str = UserAgent.BROWSER
    solve_challenge: bool = True
    load_comments_from_post: bool = False
    parse_mode: ParseMode = ParseMode.NO
    rate_limit_wait: int | None = None # DEPRECATED
    retry_on_rate_limits: bool | None = None # DEPRECATED
    retry_enabled: bool = True
    retry_delay: float = 10 # delay before next attempt (after rate limit error) if retry_after is not provided in request
    retry_max_retries: int | None = None # none for no limit
    retry_exceptions: tuple[type[Exception]] | list[type[Exception]] | None = None
    bypass_auth_level: bool = False

    def __post_init__(self):
        if self.rate_limit_default:
            self._rate_limit_default = self.rate_limit_default
        elif self.rate_limit == RateLimitMode.MIN:
            self._rate_limit_default = 0
        elif self.rate_limit == RateLimitMode.MID:
            self._rate_limit_default = 0.2
        else:
            self._rate_limit_default = 0.4

        self._url_api = self.url_api if self.url_api else f'https://{self.url}/api'
        self.url = self.url.split('https://')[0].split('http://')[0]

        match self.user_agent:
            case UserAgent.DEFAULT:
                self._user_agent = default_user_agent()
            case UserAgent.SDK:
                self._user_agent = get_sdk_user_agent()
            case UserAgent.EMPTY:
                self._user_agent = ''
            case UserAgent.BROWSER:
                self._user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0'
            case _:
                self._user_agent = self.user_agent

        if self.rate_limit_wait is not None:
            l.warning('config.rate_limit_wait is deprecated and will be removed in 2.4.0. Please use config.retry_delay')
            self.retry_delay = self.rate_limit_wait
        if self.retry_on_rate_limits is not None:
            l.warning('config.retry_on_rate_limits is deprecated and will be removed in 2.4.0. Please use config.retry_enabled')
            self.retry_enabled = self.retry_on_rate_limits

        self._retry_exceptions = (tuple(self.retry_exceptions) if isinstance(self.retry_exceptions, list) else self.retry_exceptions) or (RateLimitError, InternalError, RequestException)



class Client:
    auth_level: AuthLevel = AuthLevel.NO
    access_token: str | None = None
    refresh_token: str | None = None
    _user = None
    _refreshing: bool = False

    def __init__(self, refresh: str | None = None, access: str | None = None, config: Config = Config()):
        l.info('init client refresh=%s access=%s', refresh is not None, access is not None)
        self.config = config
        self.last_actions: dict[str, datetime] = {}

        self.session = Session()
        adapter = HTTPAdapter(pool_connections=1, pool_maxsize=10, pool_block=False) # idk what is this, (claude added) just for better stability
        self.session.mount('https://', adapter)

        if access:
            self.auth_level = AuthLevel.ACCESS
            self.access_token = access.replace('Bearer ', '')

        if refresh:
            self.auth_level = AuthLevel.REFRESH
            self.refresh_token = refresh
            self.session.cookies.set('refresh_token', refresh, path='/', domain=self.config.url)
            # if access is None:
            #     self.refresh_auth()

        if _default_client is None or config.is_default:
            set_default_client(self)

    def request(self, method: str, url: str, params: dict = {}, files: dict[str, tuple[str, BufferedReader | bytes]] = {}, level=AuthLevel.ACCESS):
        """Сделать запрос

        Args:
            method (str): Метод
            url (str): URL
            params (dict, optional): Параметры. Defaults to {}.
            files (dict[str, tuple[str, BufferedReader | bytes]], optional): Файлы. Defaults to {}.
        """
        l.debug('%s %s params=%s authlevel=%s', method.upper(), url, params, level.value)

        if level > self.auth_level and not self.config.bypass_auth_level:
            raise InsufficientAuthLevelError(self.auth_level, level)

        if level >= AuthLevel.ACCESS and self.access_token is None and url != 'v1/auth/refresh':
            self.refresh_auth()

        def _fetch():
            return fetch(self, method, url, params, files)

        if not self.refresh_token or url == 'v1/auth/refresh':
            return _fetch()

        try:
            return _fetch()
        except (UnauthorizedError, AccessTokenExpiredError):
            self.refresh_auth()
            return _fetch()

    def refresh_auth(self) -> str:
        """Обновить access token

        Returns:
            str: Токен
        """
        l.debug('refresh token')

        res = refresh_token(self)
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
            self._user = Me(self)
        return self._user


    def logout(self):
        """Выход из аккаунта
        """
        res = logout(self)
        res.raise_for_status()


    def change_password(self, old: str, new: str) -> None:
        """Смена пароля

        Args:
            old (str): Старый пароль
            new (str): Новый пароль

        Raises:
            NoCookie: Нет cookie
            SamePasswordError: Одинаковые пароли
            InvalidOldPasswordError: Старый пароль неверный

        """
        # if not self.refresh_token:
            # raise InsufficientAuthLevelError()

        change_password(self, old, new)


    def search(self, query: str, hashtags_limit: int = 20, users_limit: int = 20) -> tuple[list[User], list[Hashtag]]:
        """Поиск пользователей и хэштэгов

        Args:
            query (str): Запрос
            hashtags_limit (int, optional): Лимит хэштэгов. Defaults to 20.
            users_limit (int, optional): Лимит пользователей. Defaults to 20.

        Returns:
            tuple[list[User], list[Hashtag]]: Результат поиска
        """
        res = search(self, query, users_limit, hashtags_limit).json()['data']
        return [User._from_dict(user, False, self) for user in res['users']], [Hashtag._from_dict(hashtag, self) for hashtag in res['hashtags']]

    def search_users(self, query: str, limit: int = 20) -> list[User]:
        """Поиск пользователей

        Args:
            query (str): Запрос
            limit (int, optional): Лимит. Defaults to 20.

        Returns:
            list[User]: Список пользователей
        """
        return self.search(query, 1, limit)[0] # cant hashtags_limit=9 because it gives validation, ну это вам только хуже будет так что сервера страдайте

    def search_hashtags(self, query: str, limit: int = 20) -> list[Hashtag]:
        """Поиск хэштэгов

        Args:
            query (str): Запрос
            limit (int, optional): Лимит. Defaults to 20.

        Returns:
            list[Hashtag]: Список хэштэгов
        """
        return self.search(query, limit, 1)[1]

    def search_user(self, query: str) -> User | None:
        """Поиск пользователя

        Args:
            query (str): Запрос

        Returns:
            User | None: Пользователь
        """
        user = self.search_users(query, 1)
        if user:
            return user[0]

    def search_hashtag(self, query: str) -> Hashtag | None:
        """Поиск хэштэга

        Args:
            query (str): Запрос

        Returns:
            Hashtag | None: Хэштэг
        """
        hashtag = self.search_hashtags(query, 1)
        if hashtag:
            return hashtag[0]

    def get_follow_status(self, users: list[User | UUID | str] | User | UUID | str) -> dict[UUID, bool] | bool:
        """Получить статус подписки

        Args:
            users (list[User | UUID | str] | User | UUID | str): Пользователи для проверки (можно как и списком, так и как одиночным объектом)

        Returns:
            dict[UUID, bool] | bool: Результат
        """
        user_ids: list[UUID] = []
        if isinstance(users, list):
            for user in users:
                if isinstance(user, User):
                    user_ids.append(user.id)
                else:
                    user_ids.append(to_uuid(user))
        elif isinstance(users, User):
            user_ids = [users.id]
        else:
            user_ids = [to_uuid(users)]

        res = {UUID(k): v for k, v in get_follow_status(self, user_ids).json()['data'].items()}
        if not isinstance(users, list):
            return list(res.values())[0]
        return res
