from typing import Any, Callable
from functools import wraps
from time import sleep

from pydantic.fields import FieldInfo
from pydantic import BaseModel

from itd.client import Client as ITDClient, get_default_client


class ITDBaseModel:
    _refreshable: bool = True
    _loaded: bool = False
    _loading: bool = False
    _validator: Callable[[Any], type[BaseModel]] | None = None # callable (pls use lambda), becuase we havent validator at that moment (it depends on this class)

    def __init__(self, client: ITDClient | None = None) -> None:
        self._client = client or get_default_client()

    @property
    def client(self) -> ITDClient:
        return self._client

    def _token(self, client: ITDClient | None = None) -> str: # should be property, but it needs client param
        return (client or self._client).token

    def refresh(self) -> Any:
        if self._refreshable:
            raise NotImplementedError(f"{type(self).__name__} must implement refresh()")
        self._loaded = True


    def __getattribute__(self, name: str) -> Any:
        if object.__getattribute__(self, '_refreshable'):
            try:
                attr = object.__getattribute__(self, name)
            except AttributeError:
                attr = None

            if (attr is not None and not isinstance(attr, FieldInfo)) or name.startswith('_') or callable(attr):
                return attr

            if not self._loaded:
                self.refresh()

        return object.__getattribute__(self, name)


def refresh_wrapper(func):
    @wraps(func)
    def wrapper(self, client: ITDClient | None = None):
        # if self._loading:
        #     return

        # self._loading = True
        data = func(self, client or self.client)
        if self._validator:
            for name, value in self._validator().model_validate(data).__dict__.items():
                setattr(self, name, value)

        # self._loading = False
        self._loaded = True

    return wrapper
