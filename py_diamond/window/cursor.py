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
from enum import IntEnum
from types import MethodType
from typing import Any, Callable, ClassVar, Dict, Final, Optional, Sequence, Tuple, overload

import pygame
import pygame.cursors
import pygame.mouse
from pygame.cursors import Cursor as _Cursor

from ..graphics.surface import Surface
from ..system.utils import cache, wraps


class _MetaCursor(ABCMeta):
    __cursor_setter: ClassVar[Optional[Callable[[], None]]] = None
    __default_cursor: ClassVar[Optional[Cursor]] = None

    def __new__(metacls, /, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any) -> _MetaCursor:
        def _set_decorator(func: Callable[[Cursor], None], /) -> Callable[[Cursor], None]:
            actual_cursor: Optional[Cursor] = None

            @wraps(func)
            def wrapper(self: Cursor, /) -> None:
                nonlocal actual_cursor
                if actual_cursor is not self:
                    _MetaCursor.__cursor_setter = MethodType(func, self)
                    actual_cursor = self

            return wrapper

        set_method: Optional[Callable[[Cursor], None]] = namespace.get("set")
        if callable(set_method):
            namespace["set"] = _set_decorator(set_method)

        return super().__new__(metacls, name, bases, namespace, **kwargs)

    @cache
    def __call__(cls, /, *args: Any, **kwargs: Any) -> Any:
        return super().__call__(*args, **kwargs)

    @staticmethod
    def update() -> None:
        cursor_setter = _MetaCursor.__cursor_setter
        if not callable(cursor_setter):
            default_cursor = (
                _MetaCursor.__default_cursor if isinstance(_MetaCursor.__default_cursor, Cursor) else SystemCursor.CURSOR_ARROW
            )
            default_cursor.set()
        if callable(cursor_setter):
            cursor_setter()
            _MetaCursor.__cursor_setter = None

    @staticmethod
    def set_default(cursor: Optional[Cursor]) -> None:
        _MetaCursor.__default_cursor = cursor


class Cursor(metaclass=_MetaCursor):
    @abstractmethod
    def set(self, /) -> None:
        raise NotImplementedError


class CustomCursor(Cursor):
    @overload
    def __init__(
        self, size: Tuple[int, int], hotspot: Tuple[int, int], xormasks: Tuple[int, ...], andmasks: Tuple[int, ...], /
    ) -> None:
        ...

    @overload
    def __init__(self, hotspot: Tuple[int, int], surface: Surface, /) -> None:
        ...

    @overload
    def __init__(self, cursor: _Cursor, /) -> None:
        ...

    def __init__(self, /, *args: Any) -> None:
        super().__init__()
        self.__cursor: _Cursor = _Cursor(*args)

    @staticmethod
    def compile(
        hotspot: Tuple[int, int], strings: Sequence[str], black: str = "X", white: str = ".", xor: str = "o"
    ) -> CustomCursor:
        data, mask = pygame.cursors.compile(strings, black=black, white=white, xor=xor)
        width = max(len(line) for line in strings)
        height = len(strings)
        return CustomCursor((width, height), hotspot, tuple(data), tuple(mask))

    @staticmethod
    def load_xbm(cursorfile: str, maskfile: str) -> CustomCursor:
        size, hotspot, xormasks, andmasks = pygame.cursors.load_xbm(cursorfile, maskfile)
        width, height = size
        x, y = hotspot
        return CustomCursor((width, height), (x, y), tuple(xormasks), tuple(andmasks))

    def set(self, /) -> None:
        pygame.mouse.set_cursor(self.__cursor)


class SystemCursor(Cursor):
    def __init__(self, constant: int, /) -> None:
        super().__init__()
        self.__constant: int = SystemCursor.Type(constant).value

    def set(self, /) -> None:
        pygame.mouse.set_system_cursor(self.__constant)

    class Type(IntEnum):
        ARROW = pygame.SYSTEM_CURSOR_ARROW
        IBEAM = pygame.SYSTEM_CURSOR_IBEAM
        WAIT = pygame.SYSTEM_CURSOR_WAIT
        CROSSHAIR = pygame.SYSTEM_CURSOR_CROSSHAIR
        WAITARROW = pygame.SYSTEM_CURSOR_WAITARROW
        SIZENWSE = pygame.SYSTEM_CURSOR_SIZENWSE
        SIZENESW = pygame.SYSTEM_CURSOR_SIZENESW
        SIZEWE = pygame.SYSTEM_CURSOR_SIZEWE
        SIZENS = pygame.SYSTEM_CURSOR_SIZENS
        SIZEALL = pygame.SYSTEM_CURSOR_SIZEALL
        NO = pygame.SYSTEM_CURSOR_NO
        HAND = pygame.SYSTEM_CURSOR_HAND

    CURSOR_ARROW: Final[SystemCursor]  # type: ignore
    CURSOR_IBEAM: Final[SystemCursor]  # type: ignore
    CURSOR_WAIT: Final[SystemCursor]  # type: ignore
    CURSOR_CROSSHAIR: Final[SystemCursor]  # type: ignore
    CURSOR_WAITARROW: Final[SystemCursor]  # type: ignore
    CURSOR_SIZENWSE: Final[SystemCursor]  # type: ignore
    CURSOR_SIZENESW: Final[SystemCursor]  # type: ignore
    CURSOR_SIZEWE: Final[SystemCursor]  # type: ignore
    CURSOR_SIZENS: Final[SystemCursor]  # type: ignore
    CURSOR_SIZEALL: Final[SystemCursor]  # type: ignore
    CURSOR_NO: Final[SystemCursor]  # type: ignore
    CURSOR_HAND: Final[SystemCursor]  # type: ignore


SystemCursor.CURSOR_ARROW = SystemCursor(SystemCursor.Type.ARROW)  # type: ignore
SystemCursor.CURSOR_IBEAM = SystemCursor(SystemCursor.Type.IBEAM)  # type: ignore
SystemCursor.CURSOR_WAIT = SystemCursor(SystemCursor.Type.WAIT)  # type: ignore
SystemCursor.CURSOR_CROSSHAIR = SystemCursor(SystemCursor.Type.CROSSHAIR)  # type: ignore
SystemCursor.CURSOR_WAITARROW = SystemCursor(SystemCursor.Type.WAITARROW)  # type: ignore
SystemCursor.CURSOR_SIZENWSE = SystemCursor(SystemCursor.Type.SIZENWSE)  # type: ignore
SystemCursor.CURSOR_SIZENESW = SystemCursor(SystemCursor.Type.SIZENESW)  # type: ignore
SystemCursor.CURSOR_SIZEWE = SystemCursor(SystemCursor.Type.SIZEWE)  # type: ignore
SystemCursor.CURSOR_SIZENS = SystemCursor(SystemCursor.Type.SIZENS)  # type: ignore
SystemCursor.CURSOR_SIZEALL = SystemCursor(SystemCursor.Type.SIZEALL)  # type: ignore
SystemCursor.CURSOR_NO = SystemCursor(SystemCursor.Type.NO)  # type: ignore
SystemCursor.CURSOR_HAND = SystemCursor(SystemCursor.Type.HAND)  # type: ignore
