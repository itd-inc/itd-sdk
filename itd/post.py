from __future__ import annotations
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from typing import Literal, overload, TYPE_CHECKING
from time import sleep
from threading import Thread
from atexit import register

from pydantic import Field, BaseModel, field_validator, field_serializer

from itd.comment import Comment, Comments
from itd.file import PostAttach
from itd.hashtag import Hashtag
from itd.poll import Poll, NewPoll, PollOption
from itd.report import Report
from itd.span import Span
from itd.user import User, _UserBase, Me

from itd.api.posts import (
    get_post, create_post, like_post, unlike_post, repost, view_post, pin_post, unpin_post,
    delete_post, restore_post, edit_post, get_posts, get_user_posts, get_liked_posts
)
from itd.api.hashtags import get_posts_by_hashtag
from itd.api.dwell import send_views, send_interactions
from itd.base import ITDBaseModel, refresh_wrapper, ITDList
from itd.enums import PostsTab, UserPostSorting, ReportReason, ReportTargetType, ParseMode, ALL, ViewReason, ViewSource, InteractionType
from itd.logger import get_logger
from itd.utils import to_uuid, parse_datetime, format_attachments, ATTACHMENTS, parse_html, parse_md
if TYPE_CHECKING:
    from itd.client import Client

l = get_logger('post')

class DwellEvent(BaseModel):
    vs: str = Field(alias='v')
    source: ViewSource = Field(alias='s')


class InteractionEvent(DwellEvent):
    type: InteractionType = Field(alias='t')
    attachment_id: UUID = Field(alias='ai')

class PhotoOpenEvent(InteractionEvent):
    index: int | None = Field(None, alias='mi')

class VideoProgressEvent(InteractionEvent):
    played: int = Field(alias='pm')
    duration: int = Field(alias='dm')


class ViewEvent(DwellEvent):
    duration: int = Field(alias='md')
    entered_at: int = Field(alias='et')
    exited_at: int = Field(alias='xt')
    reason: ViewReason = Field(alias='r')
    source_context: str | None = Field(None, alias='sc')
    has_seen: bool = Field(False, alias='b')

    @field_serializer('has_seen', mode='plain')
    @classmethod
    def serialize_has_seen(cls, value: bool):
        return int(value)


class DwellTracker(ITDBaseModel):
    def __init__(self, client: Client | None = None) -> None:
        super().__init__(client)
        self.views: list[ViewEvent] = []
        self.interactions: list[InteractionEvent] = []
        self.seen_posts: set[UUID] = set()
        self.sid = uuid4()
        self._thread: Thread | None = None

    def send_views(self) -> bool: # call on app visibilitychange
        """Отправить просмотры (api/v1/i) и очистить буффер

        Returns:
            bool: Статус (False если буффер пустой и ничего не было отправлено)
        """
        if not self.views:
            return False
        l.info('dwell send view batch')
        send_views(self.client, [event.model_dump(mode='json', by_alias=True) for event in self.views], self.sid)
        self.views.clear()
        return True

    def send_interactions(self) -> bool: # call on app visibilitychange
        """Отправить события взаимодействий с вложениями (api/v1/x) и очистить буффер

        Returns:
            bool: Статус (False если буффер пустой и ничего не было отправлено)
        """
        if not self.interactions:
            return False
        l.info('dwell send interactions batch')
        send_interactions(self.client, [event.model_dump(mode='json', by_alias=True) for event in self.interactions], self.sid)
        self.interactions.clear()
        return True

    def record_view(self, id: UUID, vs: str, duration: int, entered_at: datetime, source: ViewSource, source_context: str | None = None, reason: ViewReason = ViewReason.NORMAL):
        """Записать событие просмотра

        Args:
            id (UUID): ID поста
            vs (str): VS
            duration (int): Время на просмотр (сколько времени пользователь читал пост) (мс). Желательно должно быть 250+
            entered_at (datetime): Дата открытия поста (когда пользователь увидел пост)
            reason (ViewReason): Причина просмотра
            source (ViewSource): Страница, с которой произошел просмотр
        """
        l.info(
            'dwell add view record id=%s vs=%s duration=%s entered_at=%s exited_at=%s source=%s source_context=%s reason=%s',
            id, vs, duration, entered_at.strftime('%m.%d %H:%M:%S'),
            (entered_at + timedelta(milliseconds=duration)).strftime('%m.%d %H:%M:%S'),
            source.value, source_context, reason.value
        )

        self.views.append(
            ViewEvent( # stupid pydantic i want validate by name
                v=vs,
                md=duration,
                et=round(entered_at.timestamp() * 1000),
                xt=round(entered_at.timestamp() * 1000) + duration,
                r=reason,
                s=source,
                sc=source_context,
                b=id in self.seen_posts
            )
        )
        self.seen_posts.add(id)
        if len(self.views) >= self.client.config.dwell_max_buffer:
            self.send_views()

    def record_photo_open(self, vs: str, source: ViewSource, attachment_id: UUID, index: int):
        """Записать событие просомтра фото

        Args:
            vs (str): VS
            source (ViewSource): Страница, с которой проищошел просмотр
            attachment_id (UUID): ID вложения
            index (int): Индекс вложения
        """
        l.info('dwell add photo open record vs=%s source=%s id=%s index=%s', vs, source.value, attachment_id, index)

        self.interactions.append(
            PhotoOpenEvent(
                v=vs,
                s=source,
                t=InteractionType.PHOTO_OPEN,
                ai=attachment_id,
                mi=index
            )
        )
        if len(self.interactions) >= self.client.config.dwell_max_buffer:
            self.send_interactions()

    def record_video_progress(self, vs: str, source: ViewSource, attachment_id: UUID, played: int, duration: int):
        """Записать событие просмотра видео (отправлять каждые 2-3 сек пока запущено видео)

        Args:
            vs (str): VS
            source (ViewSource): Страница, с которой произошел просмотр
            attachment_id (UUID): ID просмотренного вложения
            played (int): Сколько было просмотренно (мс) с учетом перепросмотров
            duration (int): Общая длительность видео (константа) (мс)
        """
        l.info('dwell add video progress record vs=%s source=%s id=%s played=%s duration=%s', vs, source, attachment_id, played, duration)

        self.interactions.append(
            VideoProgressEvent(
                v=vs,
                s=source,
                t=InteractionType.VIDEO_PROGRESS,
                ai=attachment_id,
                pm=played,
                dm=duration
            )
        )
        if len(self.interactions) >= self.client.config.dwell_max_buffer:
            self.send_interactions()


    def _start_timer(self):
        if not self.client.config.dwell_send_interval:
            return

        def loop():
            while True:
                sleep(self.client.config.dwell_send_interval)
                self.send_views()
                self.send_interactions()

        self._thread = Thread(target=loop)
        self._thread.daemon = True
        self._thread.start()

        def on_exit():
            l.debug('stop dwell timer')
            if self._thread:
                self._thread.join(timeout=0)
            self.send_views()
            self.send_interactions()

        if self.client.config.dwell_save_on_quit:
            register(on_exit)



class Post(ITDBaseModel):
    _validator = lambda _: _PostValidate

    id: UUID
    author: User
    created_at: datetime = Field(alias='createdAt')

    content: str
    spans: list[Span] = []
    attachments: list[PostAttach]
    poll: Poll | None = None

    comments: Comments = Field(default_factory=lambda: Comments())

    likes_count: int = Field(0, alias='likesCount')
    comments_count: int = Field(0, alias='commentsCount') # ! Comments + replies, so len(comments) != comments_count
    reposts_count: int = Field(0, alias='repostsCount')
    views_count: int = Field(0, alias='viewsCount')

    edited_at: datetime | None = Field(None, alias='editedAt')

    is_liked: bool = Field(False, alias='isLiked')
    is_reposted: bool = Field(False, alias='isReposted')
    is_viewed: bool = Field(False, alias='isViewed')
    is_owner: bool = Field(False, alias='isOwner')
    is_pinned: bool = Field(False, alias='isPinned')

    dominant: str | None = Field(None, alias='dominantEmoji')
    original_post: 'Post | None' = Field(None, alias='originalPost')  # for reposts

    wall_recipient_id: UUID | None = Field(None, alias='wallRecipientId')
    wall_recipient: User | None = Field(None, alias='wallRecipient')
    # vs: ViewerSession
    vs: str = Field('') # from 13.05 it is string token


    def __init__(self, id: str | UUID, source: ViewSource = ViewSource.POST_PAGE, source_context: str | None = None, client: Client | None = None) -> None:
        self.id = to_uuid(id)
        self.source = source
        self.source_context = source_context

        super().__init__(client)

    def for_client(self, client: Client):
        return Post(self.id, client=client)

    def _post_refresh(self):
        self.comments = Comments()
        self.comments._post_id = self.id
        for attachment in self.attachments:
            attachment._post = self


    @classmethod
    def new(
        cls,
        content: str | None = None,
        spans: list[Span] = [],
        attachments: ATTACHMENTS = [],
        poll: NewPoll | None = None,
        wall_recipient: UUID | str | User | None = None,
        client: Client | None = None
    ) -> 'Post':
        """Создать новый пост

        Args:
            content (str | None, optional): Содержимое. Defaults to None.
            spans (list[Span], optional): Спаны. Defaults to [].
            wall_recipient (UUID | str | User | None, optional): Получатель (для постов на чужой стене). Defaults to None.
            attachments (ATTACHMENTS, optional): Вложения. Defaults to [].
            poll (NewPoll | None, optional): Опрос. Defaults to None.
            client (Client | None, optional): Клиент. Defaults to None.

        Returns:
            Post: Пост
        """
        instance = cls.__new__(cls)
        super(Post, instance).__init__(client)

        if isinstance(wall_recipient, User):
            wall_recipient = wall_recipient.id
        elif wall_recipient is not None:
            wall_recipient = to_uuid(wall_recipient)

        if (client or instance.client).config.parse_mode == ParseMode.HTML and not spans and content:
            content, spans = parse_html(content)
        if (client or instance.client).config.parse_mode == ParseMode.MARKDOWN and not spans and content:
            content, spans = parse_md(content)

        post = create_post(
            instance._client,
            content, [span.model_dump(mode="json") for span in spans],
            wall_recipient,
            format_attachments(attachments),
            poll
        ).json()

        validated = _PostValidate.model_validate(post)
        instance._fields_from_data = validated.model_fields_set
        for name, value in validated.__dict__.items():
            setattr(instance, name, value)

        instance._loaded = False
        instance._post_refresh()

        return instance

    @classmethod
    def _from_dict(cls, data: dict, source: ViewSource = ViewSource.POST_PAGE, source_context: str | None = None, set_loaded: bool = True, client: Client | None = None) -> 'Post':
        instance = cls.__new__(cls)
        super(Post, instance).__init__(client)

        validated = _PostValidate.model_validate(data)
        instance._fields_from_data = validated.model_fields_set
        for name, value in validated.__dict__.items():
            setattr(instance, name, value)

        instance._loaded = set_loaded
        instance.source = source
        instance.source_context = source_context
        instance._post_refresh()
        return instance


    def vote(self, options: list[str | UUID | PollOption] | str | UUID | PollOption, client: Client | None = None) -> None:
        assert self.poll, 'No poll'
        self.poll.vote(options, client or self.client)

    @refresh_wrapper
    def refresh(self, client: Client | None = None):
        return get_post(client or self.client, self.id).json()['data']


    def __str__(self) -> str:
        return self.content

    def __int__(self) -> int:
        return self.likes_count

    def __eq__(self, other) -> bool:
        if isinstance(other, Post):
            return self.id == other.id
        return False

    def __contains__(self, item) -> bool:
        return item in self.content

    def __lt__(self, other) -> bool:
        if isinstance(other, Post):
            return self.created_at < other.created_at
        return NotImplemented

    def __gt__(self, other) -> bool:
        if isinstance(other, Post):
            return self.created_at > other.created_at
        return NotImplemented

    def __len__(self) -> int:
        return len(self.content)


    def like(self, client: Client | None = None) -> int:
        """Лайкнуть пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.

        Returns:
            int: Количество лайков после лайка
        """
        likes = like_post(client or self.client, self.id).json()['likesCount']
        self.likes_count = likes
        if (client or self.client) == self.client:
            self.is_liked = True
        return likes

    def unlike(self, client: Client | None = None) -> int:
        """Убрать лайк с поста

        Args:
            client (Client | None, optional): Клиент. Defaults to None.

        Returns:
            int: Количество лайков после убирания лайка
        """
        likes = unlike_post(client or self.client, self.id).json()['likesCount']
        self.likes_count = likes
        if (client or self.client) == self.client:
            self.is_liked = False
        return likes

    def repost(self, content: str | None = None, client: Client | None = None) -> 'Post':
        """Репостнуть пост

        Args:
            content (str | None, optional): Содержимое. Defaults to None.
            client (Client | None, optional): Клиент. Defaults to None.

        Returns:
            Post: Пост
        """
        post = repost(client or self.client, self.id, content).json()
        self.reposts_count += 1
        if (client or self.client) == self.client:
            self.is_reposted = True

        return Post._from_dict(post, client=client)

    def view(self, client: Client | None = None, entered_at: datetime | None = None, duration: int = 250, reason: ViewReason = ViewReason.NORMAL) -> None:
        """Просмотреть пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.
        """
        c = client or self.client
        if c.dwell_tracker is not None:
            if self.vs is None:
                self.refresh(c)
                assert self.vs
            c.dwell_tracker.record_view(self.id, self.vs, duration, entered_at or datetime.now() - timedelta(milliseconds=duration), self.source, self.source_context, reason)
        else:
            view_post(c, self.id)
        if c == self.client:
            self.is_viewed = True
        # post can be already viewed, so view will not add; thats why do not change views_count

    def pin(self, client: Client | None = None) -> None:
        """Закрепить пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.
        """
        pin_post(client or self.client, self.id)
        self.is_pinned = True
        (client or self.client).user.pinned_post_id = self.id

    def unpin(self, client: Client | None = None) -> None:
        """Открепить пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.
        """
        unpin_post(client or self.client, self.id)
        self.is_pinned = False
        (client or self.client).user.pinned_post_id = None

    def delete(self, client: Client | None = None) -> None:
        """Удалить пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.
        """
        delete_post(client or self.client, self.id)

    # def __del__(self) -> None:
    #     self.delete()

    def restore(self, client: Client | None = None) -> None:
        """Вернуть удаленный пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.
        """
        restore_post(client or self.client, self.id)

    def edit(self, content: str, spans: list[Span] = [], client: Client | None = None) -> datetime:
        """Редактировать пост

        Args:
            content (str): Содержимое
            spans (list[Span], optional): Спаны. Defaults to [].
            client (Client | None, optional): Клиент. Defaults to None.

        Returns:
            datetime: Время обновления (updatedAt)
        """
        if (client or self.client).config.parse_mode == ParseMode.HTML and not spans:
            content, spans = parse_html(content)
        if (client or self.client).config.parse_mode == ParseMode.MARKDOWN and not spans:
            content, spans = parse_md(content)

        updated_at = parse_datetime(edit_post(client or self.client, self.id, content, [span.model_dump(mode="json") for span in spans]).json()['updatedAt'])
        self.edited_at = updated_at
        self.content = content
        self.spans = spans
        return updated_at

    def add_comment(self, content: str | None = None, attachments: ATTACHMENTS = [], client: Client | None = None) -> Comment:
        """Создать комментарий

        Args:
            content (str | None, optional): Содержимое. Defaults to None.
            attachments (list[UUID | str], optional): Вложения. Defaults to [].
            client (Client | None, optional): Клиент. Defaults to None.

        Returns:
            Comment: Комментарий
        """
        comment = self.comments.new(content, attachments, client or self.client)
        self.comments_count += 1
        return comment

    def report(self, reason: ReportReason, description: str | None = None, client: Client | None = None) -> Report:
        return Report(self.id, ReportTargetType.POST, reason, description, client or self.client)

    @property
    def url(self) -> str:
        return f'https://xn--d1ah4a.com/@{self.author.username}/post/{self.id}'

    @property
    def link(self) -> str:
        return self.url



class _PostValidate(BaseModel, Post): # BaseModel MUST be first or you ll have some problems with init
    @field_validator('attachments', mode='plain')
    @classmethod
    def validate_attachments(cls, attachments: list[dict]):
        return [PostAttach(attach) for attach in attachments]

    @field_validator('edited_at', mode='plain')
    @classmethod
    def validate_edited_at(cls, v: str | None):
        if v is None:
            return
        return parse_datetime(v)

    @field_validator('created_at', mode='plain')
    @classmethod
    def validate_created_at(cls, v: str):
        return parse_datetime(v)

    @field_validator('original_post', mode='plain')
    @classmethod
    def validate_original_post(cls, post: dict | None = None):
        if post is None:
            return
        return Post._from_dict(post, set_loaded=False)

    @field_validator('poll', mode='plain')
    @classmethod
    def validate_poll(cls, poll: dict | None = None):
        if poll is None:
            return
        return Poll(poll)

    @field_validator('comments', mode='plain')
    @classmethod
    def validate_comments(cls, comments: list[dict]):
        return Comments(comments)

    @field_validator('author', mode='plain')
    @classmethod
    def validate_author(cls, author: dict | _UserBase | None):
        if author is None:
            return None
        if isinstance(author, _UserBase):
            return author
        return User._from_dict(author, False)

    @field_validator('wall_recipient', mode='plain')
    @classmethod
    def validate_wall_recipient(cls, wall_recipient: dict | None):
        if wall_recipient is not None:
            return User._from_dict(wall_recipient, False)

    # @field_validator('vs', mode='plain')
    # @classmethod
    # def validate_vs(cls, vs: str):
    #     return ViewerSession(decode_jwt_payload(vs))



class _BasePosts(ITDList[Post]):
    _limit = 50
    source: ViewSource
    source_context: str | None = None

    @staticmethod
    def _get_cursor(data: dict):
        return data['pagination']['nextCursor']

    @staticmethod
    def _get_has_more(data: dict):
        return data['pagination']['hasMore']

    @staticmethod
    def _get_objects(data: dict) -> list[dict]:
        return data['posts']

    def _extend(self, objects: list, client: Client):
        self.extend([Post._from_dict(post, self.source, self.source_context, client=client) for post in objects])

    def __setattr__(self, name: str, value) -> None:
        if name == '_client':
            for post in self.copy():
                post._client = value
        super().__setattr__(name, value)



class Posts(_BasePosts):
    cursor: str | datetime | None = None

    def __init__(self, tab: PostsTab = PostsTab.POPULAR, client: Client | None = None) -> None:
        super().__init__(client)
        self.tab = tab
        match tab:
            case PostsTab.POPULAR:
                self.source = ViewSource.FEED_GLOBAL
            case PostsTab.FOLLOWING:
                self.source = ViewSource.FEED_FOLLOWING
            case PostsTab.CLAN:
                self.source = ViewSource.FEED_CLAN

    def _fetch(self, client: Client, limit: int) -> dict:
        return get_posts(client, self.cursor, limit, self.tab).json()['data']

    @classmethod
    def popular(cls, client: Client | None = None): # i think no one will use it (cuz it is equals just to "Posts()") but why not
        return cls(PostsTab.POPULAR, client)

    @classmethod
    def trending(cls, client: Client | None = None): # same as "popular"
        return cls.popular(client)

    @classmethod
    def following(cls, client: Client | None = None):
        return cls(PostsTab.FOLLOWING, client)

    @classmethod
    def clan(cls, client: Client | None = None):
        return cls(PostsTab.CLAN, client)


class UserPosts(_BasePosts):
    _load_with_parent = False
    cursor: datetime | None = None
    _force_remove_pinned_post: bool = False
    source = ViewSource.PROFILE

    # ! not includes posts from other users (wall posts)
    # def _get_total(self, data: dict):
    #     return self.user.posts_count

    def __init__(self, user: str | UUID | _UserBase, sorting: UserPostSorting = UserPostSorting.NEW, client: Client | None = None) -> None:
        super().__init__(client)
        if isinstance(user, Me):
            self.user = user.to_user()
        elif isinstance(user, User):
            self.user = user
        elif isinstance(user, str | UUID):
            self.user = User(user, client)
        else:
            raise ValueError('User must be instance of User or Me class')

        self.sorting = sorting # sort is busy
        self.source_context = str(self.user.id)

    def _fetch(self, client: Client, limit: int) -> dict:
        if self.sorting == UserPostSorting.NEW and client.config.userposts_add_pinned_post and not self._force_remove_pinned_post:
            return get_user_posts(client, self.user._identifier, self.cursor, limit, self.user.pinned_post_id, self.sorting).json()['data']
        return get_user_posts(client, self.user._identifier, self.cursor, limit, sort=self.sorting).json()['data'] # you dont need pinned post for popular

    @classmethod
    def popular(cls, user: str | UUID | _UserBase, client: Client | None = None):
        return cls(user, UserPostSorting.POPULAR, client)

    @classmethod
    def new(cls, user: str | UUID | _UserBase, client: Client | None = None):
        return cls(user, UserPostSorting.NEW, client)

    def wait_for_post(self, delay: float = 5, include_pinned_post: bool = False) -> Post:
        self._force_remove_pinned_post = not include_pinned_post
        post = self[0]
        l.info('userposts wait_for_post init')
        while True:
            sleep(delay)
            l.debug('userposts wait_for_post check for new posts')
            self.refresh()
            if self[0].id != post.id:
                l.debug('userposts wait_for_post found diff old=%s new=%s', post.id, self[0].id)
                self._force_remove_pinned_post = include_pinned_post
                return self[0]


class LikedPosts(_BasePosts): # [] if forbidden
    _load_with_parent = False
    cursor: datetime | None = None # actually datetime but in runtime its string

    def __init__(self, user: str | UUID | _UserBase, client: Client | None = None) -> None:
        super().__init__(client)
        if isinstance(user, _UserBase):
            self.user = user
        else:
            self.user = User(user)

    def _fetch(self, client: Client, limit: int) -> dict:
        return get_liked_posts(client, self.user._identifier, self.cursor, limit).json()['data']

    @staticmethod
    def _get_has_more(data: dict):
        return data['pagination']['hasMore']

    def wait_for_post(self, delay: float = 5) -> Post:
        post = self[0]
        l.info('likedposts wait_for_post init')
        while True:
            sleep(delay)
            l.debug('likedposts wait_for_post check for new posts')
            self.refresh()
            if self[0].id != post.id:
                l.debug('likedposts wait_for_post found diff old=%s new=%s', post.id, self[0].id)
                return self[0]


class HashtagPosts(_BasePosts):
    hashtag: Hashtag
    cursor: UUID | None = None
    source = ViewSource.HASHTAG

    def __init__(self, hashtag: Hashtag | str, client: Client | None = None) -> None:
        super().__init__(client)

        if isinstance(hashtag, str):
            hashtag = Hashtag(hashtag, self.client)
        self.hashtag = hashtag
        self.source_context = self.hashtag.name

    def _fetch(self, client: Client, limit: int) -> dict:
        return get_posts_by_hashtag(client, self.hashtag.name, self.cursor, limit).json()['data']

    def _extend(self, objects: list, client: Client):
        self.extend([Post._from_dict(post, self.source, self.source_context, set_loaded=False, client=client) for post in objects])

    def _get_total(self, data: dict):
        return data['hashtag']['postsCount']

    @staticmethod
    def _get_has_more(data: dict):
        return data['pagination']['hasMore']


    @overload
    def wait_for_posts(self, delay: float, *, client: Client | None) -> list[Post]: ...

    @overload
    def wait_for_posts(self, delay: float, find_post: Literal[True], client: Client | None) -> list[Post]: ...

    @overload
    def wait_for_posts(self, delay: float, find_post: Literal[False], client: Client | None) -> None: ...

    def wait_for_posts(self, delay: float = 5, find_post: bool = True, client: Client | None = None) -> list[Post] | None:
        count = self.hashtag.posts_count

        posts = set([post.id for post in self]) if find_post else ()

        l.info('hashtagposts wait_for_post init')
        while True:
            sleep(delay)
            l.debug('hashtagposts wait_for_post check for new posts')
            self.hashtag.refresh(client=client)
            if count < self.hashtag.posts_count:
                l.info('hashtagposts wait_for_post found diff old=%s new=%s', count, self.hashtag.posts_count)
                if find_post:
                    self.refresh(ALL, client=client)
                    l.debug('%s %s', [post.id for post in self], posts)
                    return [post for post in self if post.id not in posts]
                return
            count = self.hashtag.posts_count

    def wait_for_post(self, delay: float = 5, client: Client | None = None) -> Post | None:
        return self.wait_for_posts(delay, client=client)[0]
