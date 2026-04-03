from uuid import UUID
from datetime import datetime

from pydantic import Field, BaseModel, field_validator

from itd.client import Client
from itd.base import ITDBaseModel, refresh_wrapper
from itd.utils import to_uuid, parse_datetime
from itd.comment import Comment, Comments
from itd.poll import Poll, NewPoll
from itd.routes.posts import (
    get_post, create_post, like_post, unlike_post, repost, view_post, pin_post, unpin_post,
    delete_post, restore_post, edit_post
)
from itd.models.post import Span, UserPost, PostAttach



class _BasePost(ITDBaseModel):
    id: UUID
    author: UserPost
    created_at: datetime = Field(alias='createdAt')

    content: str
    spans: list[Span] = []
    comments: Comments = Field(default_factory=lambda: Comments(_empty=True))

    likes_count: int = Field(0, alias='likesCount')
    comments_count: int = Field(0, alias='commentsCount')
    reposts_count: int = Field(0, alias='repostsCount')
    views_count: int = Field(0, alias='viewsCount')


    @refresh_wrapper
    def refresh(self, client: Client | None = None):
        return get_post(client or self.client, self.id).json()['data']


    def __str__(self) -> str:
        return self.content

    def __int__(self) -> int:
        return self.likes_count

    def __eq__(self, other) -> bool:
        if isinstance(other, _BasePost):
            return self.id == other.id
        return False

    def __ne__(self, other) -> bool:
        if isinstance(other, _BasePost):
            return self.id != other.id
        return True

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
        post['author'] = (client or self.client).user
        self.reposts_count += 1

        return Post._from_dict(post, client)

    def view(self, client: Client | None = None) -> None:
        """Просмотреть пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.
        """
        view_post(client or self.client, self.id)
        # post can be already viewed, so view will not add; thats why do not change views_count

    def pin(self, client: Client | None = None) -> None:
        """Закрепить пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.
        """
        pin_post(client or self.client, self.id)

    def unpin(self, client: Client | None = None) -> None:
        """Открепить пост

        Args:
            client (Client | None, optional): Клиент. Defaults to None.
        """
        unpin_post(client or self.client, self.id)

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
        updated_at = parse_datetime(edit_post(client or self.client, self.id, content, [span.model_dump(mode="json") for span in spans]).json()['updatedAt'])
        self.content = content
        self.spans = spans
        return updated_at

    def add_comment(self, content: str | None = None, attachment_ids: list[UUID | str] = [], client: Client | None = None) -> Comment:
        """Создать комментарий

        Args:
            content (str | None, optional): Содержимое. Defaults to None.
            attachment_ids (list[UUID | str], optional): Вложения. Defaults to [].
            client (Client | None, optional): Клиент. Defaults to None.

        Returns:
            Comment: Комментарий
        """
        comment = self.comments.new(content, attachment_ids, client or self.client)
        self.comments_count += 1
        return comment

    @property
    def url(self) -> str:
        return f'https://xn--d1ah4a.com/@{self.author.username}/post/{self.id}'



class Post(_BasePost):
    _validator = lambda _: _PostValidate

    id: UUID

    poll: Poll | None = None
    attachments: list[PostAttach] = []
    edited_at: datetime | None = Field(None, alias='editedAt')

    is_liked: bool = Field(False, alias='isLiked')
    is_reposted: bool = Field(False, alias='isReposted')
    is_viewed: bool = Field(False, alias='isViewed')
    is_owner: bool = Field(False, alias='isOwner')
    is_pinned: bool = Field(False, alias='isPinned')  # only for user wall

    dominant: str | None = Field(None, alias='dominantEmoji')
    original_post: 'OriginalPost | None' = Field(None, alias='originalPost')  # for reposts

    wall_recipient_id: UUID | None = Field(None, alias='wallRecipientId')
    wall_recipient: UserPost | None = Field(None, alias='wallRecipient')


    def __init__(self, id: str | UUID, client: Client | None = None) -> None:
        self.id = to_uuid(id)
        super().__init__(client)

        # if self.poll:
        #     self.poll._client = self.client # TODO: add client on poll property
        self.comments._client = self.client # TODO: fix refresh for comments
        self.comments._post_id = self.id
        self.comments.total = self.comments_count


    @classmethod
    def new(
        cls,
        content: str | None = None,
        spans: list[Span] = [],
        wall_recipient_id: UUID | str | None = None,
        attachment_ids: list[UUID | str] = [],
        poll: NewPoll | None = None,
        client: Client | None = None
    ) -> 'Post':
        """Создать новый пост

        Args:
            content (str | None, optional): Содержимое. Defaults to None.
            spans (list[Span], optional): Спаны. Defaults to [].
            wall_recipient_id (UUID | str | None, optional): Получатель (для постов на чужой стене). Defaults to None.
            attachment_ids (list[UUID  |  str], optional): Вложения. Defaults to [].
            poll (NewPoll | None, optional): Опрос. Defaults to None.
            client (Client | None, optional): Клиент. Defaults to None.

        Returns:
            Post: Пост
        """
        instance = cls.__new__(cls)
        super(Post, instance).__init__(client)

        if wall_recipient_id is not None:
            wall_recipient_id = to_uuid(wall_recipient_id)

        post = create_post(
            instance._client,
            content, [span.model_dump(mode="json") for span in spans],
            wall_recipient_id,
            [to_uuid(attachment) for attachment in attachment_ids],
            poll
        ).json()

        post['author'] = instance.client.user # TODO: fix fetching user

        for name, value in _PostValidate.model_validate(post).__dict__.items():
            setattr(instance, name, value)

        if instance.poll:
            instance.poll._client = instance.client
        instance.comments._client = instance.client
        instance.comments._post_id = instance.id
        instance.comments.total = instance.comments_count
        instance._loaded = True

        return instance

    @classmethod
    def _from_dict(cls, data: dict, client: Client | None = None) -> 'Post':
        instance = cls.__new__(cls)
        super(Post, instance).__init__(client)

        for name, value in _PostValidate.model_validate(data).__dict__.items():
            setattr(instance, name, value)

        if instance.poll:
            instance.poll._client = instance.client
        instance.comments._client = instance.client
        instance.comments._post_id = instance.id
        instance.comments.total = instance.comments_count
        instance._loaded = True

        return instance


    def like(self, client: Client | None = None) -> int:
        count = super().like(client)
        self.is_liked = True
        return count

    def unlike(self, client: Client | None = None) -> int:
        count = super().unlike(client)
        self.is_liked = False
        return count

    def repost(self, content: str | None = None, client: Client | None = None) -> 'Post':
        post = super().repost(content, client)
        self.is_reposted = True
        return post

    def pin(self, client: Client | None = None) -> None:
        super().pin(client)
        self.is_pinned = True
        self.client.user.pinned_post_id = self.id # TODO

    def unpin(self, client: Client | None = None) -> None:
        super().unpin(client)
        self.is_pinned = False
        self.client.user.pinned_post_id = None # TODO

    def edit(self, content: str, spans: list[Span] = [], client: Client | None = None) -> datetime:
        updated_at =  super().edit(content, spans, client)
        self.edited_at = updated_at
        return updated_at



class _PostValidate(BaseModel, Post): # BaseModel MUST be first or you ll have some problems with init
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
        return OriginalPost(post)

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




class OriginalPost(_BasePost):
    is_deleted: bool = Field(False, alias='isDeleted')


    def __init__(self, post: dict, client: Client | None = None) -> None:
        super().__init__(client)

        for name, value in _OriginalPostValidate.model_validate(post).__dict__.items():
            setattr(self, name, value)

    def delete(self, client: Client | None = None) -> None:
        super().delete(client)
        self.is_deleted = True

    def restore(self, client: Client | None = None) -> None:
        super().restore(client)
        self.is_deleted = False


class _OriginalPostValidate(BaseModel, OriginalPost):
    @field_validator('created_at', mode='plain')
    @classmethod
    def validate_created_at(cls, v: str):
        return parse_datetime(v)

    @field_validator('comments', mode='plain')
    @classmethod
    def validate_comments(cls, comments: list[dict]):
        return Comments(comments)
