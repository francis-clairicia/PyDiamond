# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""AbstractCursor module"""

from __future__ import annotations

__all__ = ["AbstractCursor", "Cursor", "SystemCursor"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from enum import Enum, EnumMeta
from types import MethodType
from typing import Any, Callable, ClassVar, Sequence, overload

import pygame.constants as _pg_constants
from pygame.cursors import Cursor as _Cursor, compile as _pg_cursors_compile, load_xbm as _pg_cursors_load_xbm
from pygame.mouse import set_cursor as _pg_mouse_set_cursor

from ..graphics.surface import Surface
from ..system.object import Object, ObjectMeta
from ..system.utils.functools import wraps


class _CursorMeta(ObjectMeta):
    __cursor_setter: ClassVar[Callable[[], None] | None] = None
    __default_cursor: ClassVar[AbstractCursor | None] = None

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _CursorMeta:
        def _set_decorator(func: Callable[[AbstractCursor], None], /) -> Callable[[AbstractCursor], None]:
            actual_cursor: AbstractCursor | None = None

            @wraps(func)
            def wrapper(self: AbstractCursor, /) -> None:
                nonlocal actual_cursor
                if actual_cursor is not self:
                    _CursorMeta.__cursor_setter = MethodType(func, self)
                    actual_cursor = self

            return wrapper

        set_method: Callable[[AbstractCursor], None] | None = namespace.get("set")
        if callable(set_method):
            namespace["set"] = _set_decorator(set_method)

        return super().__new__(mcs, name, bases, namespace, **kwargs)

    @staticmethod
    def _update() -> None:
        cursor_setter = _CursorMeta.__cursor_setter
        if not callable(cursor_setter):
            default_cursor: AbstractCursor = _CursorMeta.__default_cursor or SystemCursor.ARROW
            default_cursor.set()
        if callable(cursor_setter):
            cursor_setter()
            _CursorMeta.__cursor_setter = None

    @staticmethod
    def set_default(cursor: AbstractCursor | None) -> None:
        _CursorMeta.__default_cursor = cursor


class AbstractCursor(Object, metaclass=_CursorMeta):
    @abstractmethod
    def set(self) -> None:
        raise NotImplementedError


class Cursor(AbstractCursor):

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
        self.__cursor: _Cursor
        match args:
            case (size, hotspot, xormask, andmask):
                self.__cursor = _Cursor(size, hotspot, xormask, andmask)
            case (hotspot, Surface() as surface):
                self.__cursor = _Cursor(hotspot, surface)
            case _Cursor() as cursor:
                self.__cursor = cursor
            case _:
                raise TypeError(f"Invalid arguments")

    @staticmethod
    def compile(hotspot: tuple[int, int], strings: Sequence[str], black: str = "X", white: str = ".", xor: str = "o") -> Cursor:
        data, mask = _pg_cursors_compile(strings, black=black, white=white, xor=xor)
        width = max(len(line) for line in strings)
        height = len(strings)
        return Cursor((width, height), hotspot, data, mask)

    @staticmethod
    def load_xbm(cursorfile: str, maskfile: str) -> Cursor:
        size, hotspot, xormasks, andmasks = _pg_cursors_load_xbm(cursorfile, maskfile)
        width, height = size
        x, y = hotspot
        return Cursor((width, height), (x, y), xormasks, andmasks)

    def set(self) -> None:
        _pg_mouse_set_cursor(self.__cursor)


class _SystemCursorMeta(_CursorMeta, EnumMeta):
    pass


class SystemCursor(AbstractCursor, Enum, metaclass=_SystemCursorMeta):
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


del _pg_constants, _SystemCursorMeta
