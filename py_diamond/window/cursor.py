# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Cursor module"""

from __future__ import annotations

__all__ = ["Cursor", "CustomCursor", "SystemCursor"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta, abstractmethod
from enum import Enum, EnumMeta
from types import MethodType
from typing import Any, Callable, ClassVar, Sequence, overload

import pygame.constants as _pg_constants
from pygame.cursors import Cursor as _Cursor, compile as _pg_cursors_compile, load_xbm as _pg_cursors_load_xbm
from pygame.mouse import set_cursor as _pg_mouse_set_cursor

from ..graphics.surface import Surface
from ..system.utils import wraps


class _MetaCursor(ABCMeta):
    __cursor_setter: ClassVar[Callable[[], None] | None] = None
    __default_cursor: ClassVar[Cursor | None] = None

    def __new__(metacls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _MetaCursor:
        def _set_decorator(func: Callable[[Cursor], None], /) -> Callable[[Cursor], None]:
            actual_cursor: Cursor | None = None

            @wraps(func)
            def wrapper(self: Cursor, /) -> None:
                nonlocal actual_cursor
                if actual_cursor is not self:
                    _MetaCursor.__cursor_setter = MethodType(func, self)
                    actual_cursor = self

            return wrapper

        set_method: Callable[[Cursor], None] | None = namespace.get("set")
        if callable(set_method):
            namespace["set"] = _set_decorator(set_method)

        return super().__new__(metacls, name, bases, namespace, **kwargs)

    @staticmethod
    def update() -> None:
        cursor_setter = _MetaCursor.__cursor_setter
        if not callable(cursor_setter):
            default_cursor: Cursor = _MetaCursor.__default_cursor or SystemCursor.ARROW
            default_cursor.set()
        if callable(cursor_setter):
            cursor_setter()
            _MetaCursor.__cursor_setter = None

    @staticmethod
    def set_default(cursor: Cursor | None) -> None:
        _MetaCursor.__default_cursor = cursor


class Cursor(metaclass=_MetaCursor):
    @abstractmethod
    def set(self) -> None:
        raise NotImplementedError


class CustomCursor(Cursor):

    __slots__ = ("__cursor",)

    @overload
    def __init__(
        self, size: tuple[int, int], hotspot: tuple[int, int], xormasks: Sequence[int], andmasks: Sequence[int], /
    ) -> None:
        ...

    @overload
    def __init__(self, hotspot: tuple[int, int], surface: Surface, /) -> None:
        ...

    @overload
    def __init__(self, cursor: _Cursor, /) -> None:
        ...

    def __init__(self, *args: Any) -> None:
        super().__init__()
        self.__cursor: _Cursor = _Cursor(*args)

    @staticmethod
    def compile(
        hotspot: tuple[int, int], strings: Sequence[str], black: str = "X", white: str = ".", xor: str = "o"
    ) -> CustomCursor:
        data, mask = _pg_cursors_compile(strings, black=black, white=white, xor=xor)
        width = max(len(line) for line in strings)
        height = len(strings)
        return CustomCursor((width, height), hotspot, data, mask)

    @staticmethod
    def load_xbm(cursorfile: str, maskfile: str) -> CustomCursor:
        size, hotspot, xormasks, andmasks = _pg_cursors_load_xbm(cursorfile, maskfile)
        width, height = size
        x, y = hotspot
        return CustomCursor((width, height), (x, y), xormasks, andmasks)

    def set(self) -> None:
        _pg_mouse_set_cursor(self.__cursor)


class _MetaSystemCursor(_MetaCursor, EnumMeta):
    pass


class SystemCursor(Cursor, Enum, metaclass=_MetaSystemCursor):
    ARROW = _pg_constants.SYSTEM_CURSOR_ARROW
    IBEAM = _pg_constants.SYSTEM_CURSOR_IBEAM
    WAIT = _pg_constants.SYSTEM_CURSOR_WAIT
    CROSSHAIR = _pg_constants.SYSTEM_CURSOR_CROSSHAIR
    WAITARROW = _pg_constants.SYSTEM_CURSOR_WAITARROW
    SIZENWSE = _pg_constants.SYSTEM_CURSOR_SIZENWSE
    SIZENESW = _pg_constants.SYSTEM_CURSOR_SIZENESW
    SIZEWE = _pg_constants.SYSTEM_CURSOR_SIZEWE
    SIZENS = _pg_constants.SYSTEM_CURSOR_SIZENS
    SIZEALL = _pg_constants.SYSTEM_CURSOR_SIZEALL
    NO = _pg_constants.SYSTEM_CURSOR_NO
    HAND = _pg_constants.SYSTEM_CURSOR_HAND

    value: int

    def set(self) -> None:
        _pg_mouse_set_cursor(self.value)


del _pg_constants, _MetaSystemCursor
