# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""defaultdict-like module"""

from __future__ import annotations

__all__ = ["WeakKeyDefaultDictionary", "WeakValueDefaultDictionary"]

import weakref
from collections.abc import Callable
from typing import Any


class WeakKeyDefaultDictionary[_KT, _VT](weakref.WeakKeyDictionary[_KT, _VT]):
    __slots__ = ("__default_factory",)

    def __init__(self, __default_factory: Callable[[], Any] | None = None, /, dict: Any | None = None):
        assert __default_factory is None or callable(__default_factory)
        self.__default_factory: Callable[[], Any] | None = __default_factory
        super().__init__(dict)

    def __missing__(self, key: Any) -> Any:
        default_factory = self.__default_factory
        if default_factory is None:
            raise KeyError(key)
        self[key] = value = default_factory()
        return value

    def __getitem__(self, key: Any) -> Any:
        try:
            return super().__getitem__(key)
        except KeyError:
            pass
        return self.__missing__(key)

    @property
    def default_factory(self) -> Callable[[], Any] | None:
        return self.__default_factory


class WeakValueDefaultDictionary[_KT, _VT](weakref.WeakValueDictionary[_KT, _VT]):
    __slots__ = ("__default_factory",)

    def __init__(self, __default_factory: Callable[[], Any] | None = None, __other: Any = (), /, **kw: Any):
        assert __default_factory is None or callable(__default_factory)
        self.__default_factory: Callable[[], Any] | None = __default_factory
        super().__init__(__other, **kw)

    def __missing__(self, key: Any) -> Any:
        default_factory = self.__default_factory
        if default_factory is None:
            raise KeyError(key)
        self[key] = value = default_factory()
        return value

    def __getitem__(self, key: Any) -> Any:
        try:
            return super().__getitem__(key)
        except KeyError:
            pass
        return self.__missing__(key)

    @property
    def default_factory(self) -> Callable[[], Any] | None:
        return self.__default_factory
