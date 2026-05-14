# Конфигурация

У `ITDClient` можно настраивать конфигурацию:

```python
from itd import ITDClient, ITDConfig

config = ITDConfig()

ITDClient('xxx', config=config)
```

## Параметры

#### rate_limit <span class="mdx-badge"><span class="mdx-badge__icon">:material-form-select:</span><span class="mdx-badge__text">RateLimitMode</span></span>
Устанавливает дефолтные значения задержек.

 - `RateLmitMode.NO`: 0 сек - для простых скриптов
 - `RateLimitMode.MIN`: Небольшие задержки (0 сек для обычных запросов) - для кастомных клиентов или маленьких скриптов
 - `RateLimitMode.MID`: Средние задержки (0.2 сек для обычных запросов) - для обычных скриптов
 - `RateLimitMode.MAX`: Большие задержки (0.4 сек для обычных запросов) - для больших ботов, парсеров
<!-- Также планируется режим `SMART`, который будет выставлять динамическую задержку (например при первых трех комментариях не делать задержку). -->
По умолчанию `RateLimitMode.MID`.

#### rate_limit_default <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">float</span></span>
Задержка для обычных запросов (overrides rate_limit_mode). Значение по умолчанию зависит от [rate_limit](#rate_limit-ratelimitmode).

#### rate_limit_actions <span class="mdx-badge"><span class="mdx-badge__icon">:material-code-braces: :material-text:: :octicons-number-16:</span><span class="mdx-badge__text">dict[str, float]</span></span>
Кастомная задержка для каждого вида запроса (например `get_user`). Названия фукнций можно посмотреть в `itd.api`. Можно использовать, если ваш скрипт повторяет одно и тоже действие (например, постоянно комментирует).

!!! example
    ```python
    {'get_me': 5, 'get_followers': 6, 'add_comment': 15.4}
    ```

#### is_default <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
Сделать ли клиент дефолтным по умолчанию. По умолчанию дефолтным становится первый инициализированный клиент.

#### userposts_add_pinned_post <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
Добавлять ли закрепленный пост при получении постов пользователя (`UserPosts`). Для этого потребуется отдельный запрос. По умолчанию `True`.

#### auto_load <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
Нужно ли автоматически загружать данные при попытке получение (перехват в `__getattribute__`). Если выключено, то для получения данных придется перед получением писать `obj.refresh()`. По умолчанию `True`.

#### load_on_getitem <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16: | ALL | BATCH</span><span class="mdx-badge__text">int | All | Batch</span></span>
Количество загружаемых объектов при попытке получить еще не загруженный элемент списка (например `Posts()[10]`). Может выдать `AttributeError`, если даже после загрузки всех объектов количество меньше желаемого индекса, или если известно общее количество объектов и индекс будет больше него. По умолчанию `1`. `All` - загрузить все. `Batch` - загрузить следующий батч (следующий по курсору). `None` - выключить авто загрузку.

!!! example
    ```python
    config.load_on_getitem = 1
    posts[5]
    len(posts) # 6

    config.load_on_getitem = 5
    posts[6]
    len(posts) # 12

    config.load_on_getitem = ALL
    posts[7]
    len(posts) # 50

    posts.clear()
    config.load_on_getitem = None
    posts[8] # AttributeError
    ```

#### load_on_iter <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16: | ALL | BATCH</span><span class="mdx-badge__text">int | All | Batch</span></span>
Количество загружаемых объектов при итерации списка (например `for post in Posts()`). По умолчанию `BATCH`. `All` - загрузить все. `Batch` - загрузить следующий батч (следующий по курсору). `None` - выключить авто загрузку.

#### force_load_lists <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
Загружать список, даже если `has_more = False`. Может уйти в бесконечный цикл при итерации. По умолчанию `False`.

#### debug_response <span class="mdx-badge"><span class="mdx-badge__icon">:material-form-select:</span><span class="mdx-badge__text">DebugResponseMode</span></span>
Режим показа сырых данных ответа API (response). Для работы должен быть установлен логгер с режимом `DEBUG`.
 - `DebugResponseMode.NO`: Не показывать ответ.
 - `DebugResponseMode.BEFORE`: Показывать ответ до обработки (сырой).
 - `DebugResponseMode.AFTER`: Показывать ответ после обработки (если при обработке возникла ошибка, ответ не выведется).
 - `DebugResponseMode.KEYS`: Показывать только ключи ответа (после обработки).
!!! warning
    Может раскрыть ваши ключи (при `refresh_auth` в терминале будет виден `access_token`)
По умолчанию `DebugResponseMode.NO`.

#### timeout <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">float</span></span>
Таймаут обычного запроса. По умолчанию `30`.

#### timeout_file <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">float</span></span>
Таймаут при загрузке файла. По умолчанию `120`.

#### url <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span>
Базовый URL ИТД (`xn--d1ah4a.com`).

#### url_api <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span>
URL к API ИТД (`https://xn--d1ah4a.com/api`). Если не указан, берется из [url](#url-str).

#### user_agent <span class="mdx-badge"><span class="mdx-badge__icon">:material-text:</span><span class="mdx-badge__text">str</span></span>
User-Agent, под которым обращатся к API ИТД. Если вы делаете свой клиент, можете поставить агент как его имя. По умолчанию стоит дефолтный браузерный user-agent.

#### solve_challenge <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
Нужно ли проходить JS-challenge (защита от скриптов). Иногда включается при запросах к API. Если выключена, скрипт может упасть с ошибкой `fail to parse json`.

#### load_comments_from_post <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
Нужно ли брать комментарии из уже полученного поста (ИТД дает 3-4 комментария при получении поста). При загрузке следующего батча комментарии могут дублироваться. По умолчанию `False`.

#### parse_mode <span class="mdx-badge"><span class="mdx-badge__icon">:simple-markdown:</span><span class="mdx-badge__text">ParseMode</span></span>
Режим парсинга (автоматически генерирует `spans` при создании или редоктаировании постов).
 - `ParseMode.NO`: Выключить парсинг
 - `ParseMode.MARKDOWN`: Markdown парсинг
 - `ParseMode.HTML`: HTML парсинг
По умолчанию `ParseMode.NO`

#### rate_limit_wait <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">int</span></span>
!!! danger "Deprecated"
    Параметр будет удален в 2.4.0. Используйте [retry_delay](#retry_delay-float).
Время ожидания при рейт-лимите.

#### retry_on_rate_limits <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
!!! danger "Deprecated"
    Параметр будет удален в 2.4.0. Используйте [retry_enabled](#retry_enabled-bool).
Нужно ли ловить рейт-лимит и автоматически переотправлять вызванную функцию.

#### retry_enabled <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
Нужно ли повторять запрос при ошибке сети или рейт лимите. По умолчанию `True`

#### retry_delay <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">float</span></span>
Задержка перед следующим повтором запроса.

#### retry_max_retries <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-number-16:</span><span class="mdx-badge__text">int</span></span>
Максимальное количество попыток повторов запроса. По умолчанию `None`. `None` - без лимита.

#### retry_exceptions <span class="mdx-badge"><span class="mdx-badge__icon">:octicons-list-unordered-16: :material-close-circle:</span><span class="mdx-badge__text">list[type[Exception]] | tuple[type[Exception]]</span></span>
Список ошибок, при которых нужно повторить запрос. По умолчанию `RateLimitError`, `InternalError` и стандартные ошибки из `requests` (`RequestException`)

#### bypass_auth_level <span class="mdx-badge"><span class="mdx-badge__icon">:material-toggle-switch:</span><span class="mdx-badge__text">bool</span></span>
Bypass пре-валидации на проверку уровня авторизации. По умолчанию `False`.
!!! note
    В sdk существует 3 уровня авторизации:

     - `NO`: **Без авторизации** - доступен поиск
     - `ACCESS`: **Access-токен** - доступно большинство всех возможностей
     - `REFRESH`: **Refresh-token** - то же, что и `ACCESS` + обновление токена и выход

    Если вы попытаетесь выполнить запрос который выше по масти, будет вызвана ошибка `InsufficientAuthLevelError`.  
    Чтобы этой ошибки не было, нужно поставить `bypass_auth_level=True`. Тогда будет вызвана стандартная ошибка от самого ИТД (`RefreshTokenMissingError` / `UnauthorizedError` или похожие)

!!! warning
    При вызове ошибок `RefreshTokenMissingError` и `UnauthorizedError` может попросить оставить Issue на github. Если у вас включен `bypass_auth_level`, игнорируйте эту просьбу.
