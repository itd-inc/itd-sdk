from _io import BufferedReader

from requests import Session
from requests.exceptions import JSONDecodeError

from itd.exceptions import InvalidToken, InvalidCookie, RateLimitExceeded, Unauthorized, AccountBanned, ProfileRequired

s = Session()


def fetch(token: str, method: str, url: str, params: dict = {}, files: dict[str, tuple[str, BufferedReader]] = {}):
    base = f'https://xn--d1ah4a.com/api/{url}'
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Authorization": 'Bearer ' + token,
        "Sec-GPC": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "TE": "trailers"
    }
    method = method.lower()
    if method == "get":
        res = s.get(base, timeout=120 if files else 20, params=params, headers=headers)
    else:
        res = s.request(method.upper(), base, timeout=120 if files else 20, json=params, headers=headers, files=files)

    try:
        if res.json().get('error') == 'Too Many Requests':
            raise RateLimitExceeded(0)
        if res.json().get('error', {}).get('code') == 'RATE_LIMIT_EXCEEDED':
            raise RateLimitExceeded(res.json()['error'].get('retryAfter', 0))
        if res.json().get('error', {}).get('code') == 'UNAUTHORIZED':
            raise Unauthorized()
        if res.json().get('error', {}).get('code') in ('ACCOUNT_BANNED', 'USER_BLOCKED'):
            raise AccountBanned()
        if res.json().get('error', {}).get('code') == 'PROFILE_REQUIRED':
            raise ProfileRequired()
    except (JSONDecodeError, AttributeError):
        pass # todo

    if not res.ok:
        print(res.text)
    return res


def fetch_stream(token: str, url: str):
    """Fetch для SSE streaming запросов"""
    base = f'https://xn--d1ah4a.com/api/{url}'
    headers = {
        "Accept": "text/event-stream",
        "Authorization": 'Bearer ' + token,
        "Cache-Control": "no-cache"
    }
    return s.get(base, headers=headers, stream=True, timeout=None)


def set_cookies(cookies: str):
    for cookie in cookies.split('; '):
        s.cookies.set(cookie.split('=')[0], cookie.split('=')[-1], path='/', domain='xn--d1ah4a.com.com')

def auth_fetch(cookies: str, method: str, url: str, params: dict = {}, token: str | None = None):
    headers = {
        "Host": "xn--d1ah4a.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://xn--d1ah4a.com/",
        "Content-Type": "application/json",
        "Origin": "https://xn--d1ah4a.com",
        "Sec-GPC": "1",
        "Connection": "keep-alive",
        "Cookie": cookies,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=4",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Content-Length": "0",
        "TE": "trailers",
    }
    if token:
        headers['Authorization'] = 'Bearer ' + token

    if method == 'get':
        res = s.get(f'https://xn--d1ah4a.com/api/{url}', timeout=20, params=params, headers=headers)
    else:
        res = s.request(method, f'https://xn--d1ah4a.com/api/{url}', timeout=20, json=params, headers=headers)

    if res.text == 'UNAUTHORIZED':
        raise InvalidToken()
    try:
        if res.json().get('error') == 'Too Many Requests':
            raise RateLimitExceeded(0)
        if res.json().get('error', {}).get('code') == 'RATE_LIMIT_EXCEEDED':
            raise RateLimitExceeded(res.json()['error'].get('retryAfter', 0))
        if res.json().get('error', {}).get('code') in ('SESSION_NOT_FOUND', 'REFRESH_TOKEN_MISSING', 'SESSION_REVOKED', 'SESSION_EXPIRED'):
            raise InvalidCookie(res.json()['error']['code'])
        if res.json().get('error', {}).get('code') == 'UNAUTHORIZED':
            raise Unauthorized()
    except JSONDecodeError:
        print('fail to parse json')

    return res
