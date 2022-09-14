# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Cursor module"""

from __future__ import annotations

__all__ = ["Cursor", "SystemCursor", "make_cursor_from_pygame_cursor"]


from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Literal, Sequence, overload

import pygame.constants as _pg_constants
import pygame.cursors as _pg_cursors

from ..system.enum import EnumObjectMeta
from ..system.object import Object

if TYPE_CHECKING:
    from ..graphics.surface import Surface


class Cursor(_pg_cursors.Cursor, Object):
    __hash__ = _pg_cursors.Cursor.__hash__

    type: str
    data: tuple[Any, ...]  # type: ignore[assignment]

    @overload
    def __init__(
        self, size: tuple[int, int], hotspot: tuple[int, int], xormasks: Sequence[int], andmasks: Sequence[int], /
    ) -> None:
        ...

    @overload
    def __init__(self, hotspot: tuple[int, int], surface: Surface, /) -> None:
        ...

    @overload
    def __init__(self, cursor: _pg_cursors.Cursor, /) -> None:
        ...

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        if self.type == "system" and "SystemCursor" in globals():
            raise TypeError("system cursors must be used with SystemCursor enum.")

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name in ("type", "data") and hasattr(self, name):
            raise AttributeError(f"{name}: Read-only attribute")
        return super().__setattr__(name, value)

    def __delattr__(self, name: str, /) -> None:
        if name in ("type", "data"):
            raise AttributeError(f"{name}: Read-only attribute")
        return super().__delattr__(name)

    @staticmethod
    def compile(hotspot: tuple[int, int], strings: Sequence[str], black: str = "X", white: str = ".", xor: str = "o") -> Cursor:
        data, mask = _pg_cursors.compile(strings, black=black, white=white, xor=xor)
        width = max(len(line) for line in strings)
        height = len(strings)
        return Cursor((width, height), hotspot, data, mask)

    @staticmethod
    def load_xbm(cursorfile: str, maskfile: str) -> Cursor:
        (width, height), (x, y), xormasks, andmasks = _pg_cursors.load_xbm(cursorfile, maskfile)
        return Cursor((width, height), (x, y), xormasks, andmasks)


@unique
class SystemCursor(Cursor, Enum, metaclass=EnumObjectMeta):
    type: Literal["system"]
    data: tuple[int]

    __hash__ = Cursor.__hash__

    def __new__(cls, value: int | SystemCursor) -> SystemCursor:
        self = Cursor.__new__(cls)
        self._value_ = value
        return self

    if TYPE_CHECKING:

        def __init__(self, value: int | SystemCursor) -> None:
            ...

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

    if TYPE_CHECKING:

        @property
        def value(self) -> int:
            ...


def make_cursor_from_pygame_cursor(pygame_cursor: _pg_cursors.Cursor) -> Cursor:
    cursor: Cursor
    if pygame_cursor.type == "system":
        cursor = SystemCursor(*pygame_cursor.data)
    else:
        cursor = Cursor(pygame_cursor)
    return cursor


del _pg_constants
