# Пользователи / Аккаунт

## Получить пользователя
```python
user = c.get_user(
    username='itd_sdk'
)
```

### Параметры

#### username <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span> <span class="mdx-badge mdx-badge_required"><span class="mdx-badge__icon">:material-information:</span><span class="mdx-badge__text">Required</span></span>
Username пользователя или `"me"` для текущего пользователя.

### Ошибки
 - `NotFound` - пользователь не найден.
 - `UserBanned` - пользователь заблокирован.

---

## Обновить профиль
```python
profile = c.update_profile(
    username='username12345',
    display_name='Имя',
    bio='Био 123',
    banner_id=None
)
```

### Параметры

#### username <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span>
Новый username.

!!! warning

    При смене username старый освобождается и может быть занят другими пользователями.

#### display_name <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span>
Новое имя.

#### bio <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span>
Биография (о себе).

#### banner_id <span class="mdx-badge"><span class="mdx-badge__icon">:material-identifier:</span><span class="mdx-badge__text">UUID</span></span>
ID баннера (должен быть загружен через `upload_file`).

!!! tip "Удалить баннер"

    Для удаления баннера используйте `UNSET`:

    ```python
    from itd.models.user import UNSET

    c.update_profile(banner_id=UNSET)
    ```

### Ошибки
 - `ValidationError` - ошибка валидации (например слишком длинное имя).
 - `InvalidFileType` - баннер может быть только изображением.
 - `RequiresVerification` - требуется верификация для GIF-баннера.
 - `UsernameTaken` - username уже занят.

---

## Получить текущего пользователя
```python
user = c.get_me()
```
Тоже самое, что и `c.get_user('me')`.

---

## Обновить настройки приватности
```python
from itd.models.user import UserPrivacyData
from itd.enums import AccessType

privacy = c.update_privacy_new(
    privacy=UserPrivacyData(
        private=False,
        wall_access=AccessType.EVERYONE,
        likes_visibility=AccessType.EVERYONE,
        show_last_seen=True
    )
)
```

### Параметры

#### privacy <span class="mdx-badge"><span class="mdx-badge__icon">:material-shield-account:</span><span class="mdx-badge__text">UserPrivacyData</span></span> <span class="mdx-badge mdx-badge_required"><span class="mdx-badge__icon">:material-information:</span><span class="mdx-badge__text">Required</span></span>
Объект с настройками приватности.

!!! example

    ```python
    from itd.models.user import UserPrivacyData
    from itd.enums import AccessType

    c.update_privacy_new(UserPrivacyData(
        private=True,
        wall_access=AccessType.NOBODY,
        likes_visibility=AccessType.NOBODY,
        show_last_seen=False
    ))
    ```

#### Параметры UserPrivacyData
 -  `private` <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span> - Закрыть профиль (Скрыть от неподписчиков).
 - `wall_access` <span class="mdx-badge"><span class="mdx-badge__icon">:material-form-select:</span><span class="mdx-badge__text">AccessType</span></span> - Доступ к стен.
 - `likes_visibility` <span class="mdx-badge"><span class="mdx-badge__icon">:material-form-select:</span><span class="mdx-badge__text">AccessType</span></span> - Видимость лайков.
 - `show_last_seen` <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span> - Показывать время последнего посещения.

#### AccessType

 - `NOBODY` - никто
 - `MUTUAL` - взаимные подписки
 - `FOLLOWERS` - подписчики
 - `EVERYONE` - все

---

## Подписаться
```python
followers_count = c.follow(
    username='itd_sdk'
)
```

### Параметры

#### username <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span> <span class="mdx-badge mdx-badge_required"><span class="mdx-badge__icon">:material-information:</span><span class="mdx-badge__text">Required</span></span>
Username пользователя.

### Ошибки
 - `NotFound` - пользователь не найден.
 - `AlreadyFollowing` - вы уже подписаны.
 - `CantFollowYourself` - нельзя подписаться на самого себя.
 - `UserBlocked` - вы заблокировали пользователя или он заблокировал вас.

---

## Отписаться
```python
followers_count = c.unfollow(
    username='itd_sdk'
)
```

### Параметры

#### username <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span> <span class="mdx-badge mdx-badge_required"><span class="mdx-badge__icon">:material-information:</span><span class="mdx-badge__text">Required</span></span>
Username пользователя.

### Ошибки
 - `NotFound` - пользователь не найден.

!!! note
    Если вы заблокировали пользователя или он заблокировал вас, при отписке вернется `0` (количество подписчиков после отписки).
    ```python
    print(c.unfollow('nowkie')) # 0, если вы заблокировали nowkie
    ```

---

## Получить подписчиков
```python
followers, pagination = c.get_followers(
    username='itd_sdk',
    limit=30,
    page=1
)
```

### Параметры

#### username <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span> <span class="mdx-badge mdx-badge_required"><span class="mdx-badge__icon">:material-information:</span><span class="mdx-badge__text">Required</span></span>
Username пользователя.

#### limit <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">int</span></span>
Лимит подписчиков.

#### page <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">int</span></span>
Номер страницы для пагинации.

!!! example Получить всех подписчиков

    ```python
    page = 1
    all_followers = []

    while True:
        followers, pagination = c.get_followers('itd_sdk', page=page)
        all_followers.extend(followers)

        if not pagination.has_more:
            break
        page += 1
    ```

### Ошибки
 - `NotFound` - пользователь не найден.

!!! note
    Если вы заблокировали пользователя или он заблокировал вас, вернется ошибка `NotFound`.

---

## Получить подписки
```python
following, pagination = c.get_following(
    username='itd_sdk',
    limit=30,
    page=1
)
```

### Параметры

#### username <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span> <span class="mdx-badge mdx-badge_required"><span class="mdx-badge__icon">:material-information:</span><span class="mdx-badge__text">Required</span></span>
Username пользователя.

#### limit <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">int</span></span>
Лимит пользователей.

#### page <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">int</span></span>
Номер страницы для пагинации.

### Ошибки
 - `NotFound` - пользователь не найден.

!!! note
    Если вы заблокировали пользователя или он заблокировал вас, вернется ошибка `NotFound`.

---

## Заблокировать пользователя
```python
c.unblock(
    username_or_id='nowkie'
)
```

### Параметры

#### username <span class="mdx-badge"><span class="mdx-badge__icon">:material-text: | :material-identifier:</span><span class="mdx-badge__text">str | UUID</span></span> <span class="mdx-badge mdx-badge_required"><span class="mdx-badge__icon">:material-information:</span><span class="mdx-badge__text">Required</span></span>
Username или UUID пользователя.

### Ошибки
 - `AlreadyBlocked` - пользователь уже заблокирован.
 - `NotFound` - пользователь не найден.
 - `CantBlockYourself` - нельзя заблокировать самого себя.

---

## Разблокировать пользователя
```python
c.block(
    username_or_id='nowkie'
)
```

### Параметры

#### username <span class="mdx-badge"><span class="mdx-badge__icon">:material-text: | :material-identifier:</span><span class="mdx-badge__text">str | UUID</span></span> <span class="mdx-badge mdx-badge_required"><span class="mdx-badge__icon">:material-information:</span><span class="mdx-badge__text">Required</span></span>
Username или UUID пользователя.

### Ошибки
 - `NotBlocked` - пользователь итак не заблокирован.
 - `NotFound` - пользователь не найден.

---

## Получить список заблокированных пользователей
```python
c.get_blocked(
    limit=20,
    page=1
)
```

### Параметры
#### limit <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">int</span></span>
Лимит пользователей.

#### page <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">int</span></span>
Номер страницы для пагинации.

---

## Удалить аккаунт
```python
c.delete_account()
```

!!! danger
    У вас будет 30 дней на восстановление аккаунта (см. восстановление аккунта ниже). После этого аккаунт безвозратно удалится.

### Ошибки
 - `AccountAlreadyDeleted`: Аккаунт уже удален.

---

## Восстановить аккаунт
```python
c.restore_account()
```

### Ошибки
 - `AccountNotDeleted`: Аккаунт итак не удален.

!!! note
    Здесь также должна быть ошибка, что уже слишком поздно, но к сожалению у меня нет дополнительного аккаунта для удаления, чтобы посмотреть как она называется 🫤.
