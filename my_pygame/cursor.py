# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from enum import IntEnum
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, overload
from functools import cache, wraps

import pygame
import pygame.mouse
import pygame.cursors

from pygame.surface import Surface
from pygame.cursors import Cursor as _Cursor


def _set_decorator(func: Callable[[Cursor], None]) -> Callable[[Cursor], None]:
    actual_cursor: Optional[Cursor] = None

    @wraps(func)
    def wrapper(self: Cursor) -> None:
        nonlocal actual_cursor
        if actual_cursor is not self:
            func(self)
            actual_cursor = self

    return wrapper


class MetaCursor(ABCMeta):
    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any) -> MetaCursor:
        set_method: Optional[Callable[[Cursor], None]] = namespace.get("set")
        if callable(set_method) and not getattr(set_method, "__isabstractmethod__", False):
            namespace["set"] = _set_decorator(set_method)

        return super().__new__(metacls, name, bases, namespace, **kwargs)

    @cache
    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        return super().__call__(*args, **kwds)


class Cursor(metaclass=MetaCursor):
    @abstractmethod
    def set(self) -> None:
        raise NotImplementedError


class CustomCursor(Cursor):
    @overload
    def __init__(
        self, size: Tuple[int, int], hotspot: Tuple[int, int], xormasks: Sequence[int], andmasks: Sequence[int], /
    ) -> None:
        ...

    @overload
    def __init__(self, hotspot: Tuple[int, int], surface: Surface, /) -> None:
        ...

    @overload
    def __init__(self, cursor: _Cursor, /) -> None:
        ...

    def __init__(self, *args: Any) -> None:
        super().__init__()
        self.__cursor: _Cursor = _Cursor(*args)

    @staticmethod
    def compile(
        hotspot: Tuple[int, int], strings: Sequence[str], black: str = "X", white: str = ".", xor: str = "o"
    ) -> CustomCursor:
        data, mask = pygame.cursors.compile(strings, black=black, white=white, xor=xor)
        width = max(len(line) for line in strings)
        height = len(strings)
        return CustomCursor((width, height), hotspot, data, mask)

    @staticmethod
    def load_xbm(cursorfile: str, maskfile: str) -> CustomCursor:
        return CustomCursor(pygame.cursors.load_xbm(cursorfile, maskfile))

    def set(self) -> None:
        pygame.mouse.set_cursor(self.__cursor)


class SystemCursor(Cursor):
    def __init__(self, constant: int, /) -> None:
        super().__init__()
        self.__constant: int = SystemCursor.Type(constant).value

    def set(self) -> None:
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

    CURSOR_ARROW = Type.ARROW
    CURSOR_IBEAM = Type.IBEAM
    CURSOR_WAIT = Type.WAIT
    CURSOR_CROSSHAIR = Type.CROSSHAIR
    CURSOR_WAITARROW = Type.WAITARROW
    CURSOR_SIZENWSE = Type.SIZENWSE
    CURSOR_SIZENESW = Type.SIZENESW
    CURSOR_SIZEWE = Type.SIZEWE
    CURSOR_SIZENS = Type.SIZENS
    CURSOR_SIZEALL = Type.SIZEALL
    CURSOR_NO = Type.NO
    CURSOR_HAND = Type.HAND
