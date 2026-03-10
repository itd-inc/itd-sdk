from uuid import UUID

from itd.request import fetch
from itd.models.user import UserPrivacyData
from itd.enums import Unset, UNSET


def get_user(token: str, username: str):
    return fetch(token, 'get', f'users/{username}')

def update_profile(token: str, bio: str | None = None, display_name: str | None = None, username: str | None = None, banner_id: UUID | Unset | None = None):
    data = {}
    if bio is not None:
        data['bio'] = bio
    if display_name:
        data['displayName'] = display_name
    if username:
        data['username'] = username
    if banner_id is not None:
        data['bannerId'] = str(banner_id) if banner_id != UNSET else None
    return fetch(token, 'put', 'users/me', data)

def update_privacy(token: str, wall_closed: bool = False, private: bool = False):
    data = {}
    if wall_closed is not None:
        data['wallClosed'] = wall_closed
    if private is not None:
        data['isPrivate'] = private
    return fetch(token, 'put', 'users/me/privacy', data)

def update_privacy_new(token: str, privacy: UserPrivacyData):
    return fetch(token, 'put', 'users/me/privacy', privacy.to_dict())

def follow(token: str, username: str):
    return fetch(token, 'post', f'users/{username}/follow')

def unfollow(token: str, username: str):
    return fetch(token, 'delete', f'users/{username}/follow')

def get_followers(token: str, username: str, limit: int = 30, page: int = 1):
    return fetch(token, 'get', f'users/{username}/followers', {'limit': limit, 'page': page})

def get_following(token: str, username: str, limit: int = 30, page: int = 1):
    return fetch(token, 'get', f'users/{username}/following', {'limit': limit, 'page': page})

def delete_account(token: str):
    return fetch(token, 'delete', 'users/me')

def restore_account(token: str):
    return fetch(token, 'post', 'users/me/restore')

def block(token: str, username_or_id: str | UUID):
    return fetch(token, 'post', f'users/{username_or_id}/block')

def unblock(token: str, username_or_id: str | UUID):
    return fetch(token, 'delete', f'users/{username_or_id}/block')

def get_blocked(token: str, limit: int = 20, page: int = 1):
    return fetch(token, 'get', 'users/me/blocked', {'limit': limit, 'page': page})
