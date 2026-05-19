from __future__ import annotations
from typing import TYPE_CHECKING, Literal, cast, Iterator
from uuid import UUID
from datetime import datetime
from json import loads
from threading import Thread

from pydantic import Field, BaseModel, field_validator
from sseclient import SSEClient

from itd.base import ITDBaseModel, ITDList
from itd.client import Client
from itd.enums import NotificationTargetType, NotificationType, All, ALL
from itd.user import User
from itd.api.notifications import (
    mark_as_read, mark_all_as_read, get_notifications, get_unread_notifications_count,
    stream_notifications
)
from itd.logger import get_logger
if TYPE_CHECKING:
    from itd.client import Client


l = get_logger('notifications')

class Notification(ITDBaseModel):
    _refreshable = False
    _notifications: Notifications | None = None

    id: UUID
    type: NotificationType

    target_type: NotificationTargetType | None = Field(None, alias='targetType') # none - follows, other - NotificationTragetType.POST
    target_id: UUID | None = Field(None, alias='targetId') # none - follows

    preview: str | None = None # follow - none, comment/reply - content, repost - original post content, like - post content, wall_post - wall post content

    is_read: bool = Field(False, alias='read')
    read_at: datetime | None = Field(None, alias='readAt')
    created_at: datetime = Field(alias='createdAt')

    actor: User
    sound: bool = False # for notifications from stream

    def __init__(self, notification: dict, notifications: Notifications | None = None, client: Client | None = None) -> None:
        super().__init__(client)
        self._notifications = notifications

        for name, value in _NotificationValidate.model_validate(notification).__dict__.items():
            setattr(self, name, value)

    def read(self, client: Client | None = None) -> None:
        mark_as_read(client or self.client, self.id)

        if not self.is_read and self._notifications and self._notifications._unread: # check if already read and has notifications and unread loaded
            self._notifications._unread -= 1

        self.is_read = True
        self.read_at = datetime.now()

    def get_text(self, avatar: bool = False) -> str:
        text = ''
        if avatar:
            text += self.actor.avatar + ' '
        text += self.actor.display_name + ' '

        match self.type:
            case NotificationType.FOLLOW:
                text += 'подписался(-ась) на вас'
            case NotificationType.FOLLOW_REQUEST:
                text += 'хочет подписаться на вас'
            case NotificationType.FOLLOW_ACCEPTED:
                text += 'принял(а) вашу заявку на подписку'
            case NotificationType.LIKE:
                text += 'оценил(а) ваш пост'
            case NotificationType.COMMENT:
                text += 'прокомментировал(а) ваш пост'
            case NotificationType.REPOST:
                text += 'сделал(а) репост вашего поста'
            case NotificationType.COMMENT_LIKE:
                text += 'оценил(а) ваш комментарий'
            case NotificationType.REPLY:
                text += 'ответил(а) на ваш комментарий'
            case NotificationType.MENTION:
                text += 'упомянул(а) вас в посте'
            case NotificationType.COMMENT_MENTION:
                text += 'упомянул(а) вас в комментарии'
            case NotificationType.WALL_POST:
                text += 'написал(а) на вашей стене'

        return text

    def get_color(self) -> Literal['blue'] | Literal['green'] | Literal['red'] | Literal['purple']:
        match self.type:
            case NotificationType.FOLLOW | NotificationType.FOLLOW_REQUEST | NotificationType.REPOST | NotificationType.WALL_POST:
                return 'blue'

            case NotificationType.FOLLOW_ACCEPTED | NotificationType.COMMENT | NotificationType.REPLY:
                return 'green'

            case NotificationType.LIKE | NotificationType.COMMENT_LIKE:
                return 'red'

            case NotificationType.MENTION | NotificationType.COMMENT_MENTION:
                return 'purple'


class _NotificationValidate(BaseModel, Notification):
    @field_validator('actor', mode='plain')
    @classmethod
    def validate_actor(cls, actor: dict):
        return User._from_dict(actor, False)



class Notifications(ITDList[Notification]):
    _limit = 1000
    _unread: int | None = None


    def _fetch(self, client: Client, limit: int) -> dict:
        return get_notifications(client, limit, len(self)).json()

    @staticmethod
    def _get_objects(data: dict) -> list[dict]:
        return data['notifications']

    @staticmethod
    def _get_has_more(data: dict) -> bool:
        return data['hasMore']

    def _extend(self, objects: list, client: Client):
        return self.extend([Notification(notification, self, client) for notification in objects])

    def __setattr__(self, name: str, value) -> None:
        if name == '_client':
            for notification in self.copy():
                notification._client = value
        super().__setattr__(name, value)

    def read_all(self):
        mark_all_as_read(self.client)
        self._unread = 0

    @property
    def unread_count(self):
        if self._unread is None:
            self._unread = get_unread_notifications_count(self.client).json()['count']
        return self._unread

    def stream(self) -> Iterator[Notification]:
        self._stream = stream_notifications(self.client)
        l.info('start stream')

        for event in SSEClient(cast(Iterator[bytes], self._stream)).events():
            data = loads(event.data)

            if 'userId' in data and 'timestamp' in data and 'type' not in data:
                l.debug('got init message')
                continue # initial message

            notification = Notification(data, self, self.client)
            self.insert(0, notification)

            l.info('new notification type=%s', notification.type.value)
            exec(f'self.on_{notification.type.value}(notification)')
            self.on_notification(notification)

            yield notification

        l.info('stop stream')

    def stream_bg(self) -> Thread:
        def _stream():
            for _ in self.stream():
                continue

        thread = Thread(target=_stream)
        thread.start()
        return thread

    def stop_stream(self) -> None:
        if getattr(self, '_stream', None) is not None:
            assert self._stream
            self._stream.close()
            self._stream = None


    # redefine this for your needs (eg notifications.on_like = my_function)
    def on_like(self, notification: Notification, /) -> None: ...

    def on_comment(self, notification: Notification, /) -> None: ...

    def on_reply(self, notification: Notification, /) -> None: ...

    def on_repost(self, notification: Notification, /) -> None: ...

    def on_mention(self, notification: Notification, /) -> None: ...

    def on_follow(self, notification: Notification, /) -> None: ...

    def on_follow_request(self, notification: Notification, /) -> None: ...

    def on_follow_accepted(self, notification: Notification, /) -> None: ...

    def on_comment_like(self, notification: Notification, /) -> None: ...

    def on_comment_mention(self, notification: Notification, /) -> None: ...

    def on_wall_post(self, notification: Notification, /) -> None: ...

    def on_notification(self, notification: Notification, /) -> None: ...
