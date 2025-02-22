# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Cursor module"""

from __future__ import annotations

__all__ = ["Cursor", "SystemCursor"]

from collections.abc import Sequence
from enum import Enum, auto, unique
from typing import TYPE_CHECKING, Any, Final, Literal, Self, overload

import pygame.constants as _pg_constants
import pygame.cursors as _pg_cursors

from ..system.object import Object
from ..system.utils.enum import EnumObjectMeta

if TYPE_CHECKING:
    from ..graphics.surface import Surface


class Cursor(_pg_cursors.Cursor, Object, no_slots=True):
    if TYPE_CHECKING:
        __slots__: Final[tuple[str, ...]] = ("__dict__",)

    def __new__(cls, *args: Any) -> Cursor:
        if len(args) == 1:
            match args[0]:
                case int(constant) | _pg_cursors.Cursor(type="system", data=(int(constant),)):
                    return SystemCursor(constant)
        return super().__new__(cls)

    type: Literal["system", "color", "bitmap"]
    data: tuple[Any, ...]

    @overload
    def __init__(
        self, size: tuple[int, int], hotspot: tuple[int, int], xormasks: Sequence[int], andmasks: Sequence[int], /
    ) -> None: ...

    @overload
    def __init__(self, hotspot: tuple[int, int], surface: Surface, /) -> None: ...

    @overload
    def __init__(self, cursor: _pg_cursors.Cursor, /) -> None: ...

    @overload
    def __init__(self, system_cursor_constant: int, /) -> None: ...

    def __init__(self, *args: Any) -> None:
        try:
            SystemCursor
        except NameError:
            return super().__init__(*args)

        if isinstance(self, SystemCursor):
            if len(args) != 1 or not isinstance(args[0], (int, _pg_cursors.Cursor)):
                raise TypeError("__init__(): Call twice")
            return
        if hasattr(self, "type"):
            raise TypeError("__init__(): Call twice")
        super().__init__(*args)
        if self.type == "system":
            raise TypeError("system cursors must be instanciated with SystemCursor enum.")

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

    __hash__ = Cursor.__hash__  # type: ignore[assignment,unused-ignore]

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        constant_name = f"SYSTEM_CURSOR_{name}"
        return getattr(_pg_constants, constant_name)

    def __new__(cls, value: int | SystemCursor) -> SystemCursor:
        self = _pg_cursors.Cursor.__new__(cls)
        self._value_ = value
        return self

    if TYPE_CHECKING:

        def __init__(self, value: int | SystemCursor) -> None: ...

    ARROW = auto()
    IBEAM = auto()
    WAIT = auto()
    CROSSHAIR = auto()
    WAITARROW = auto()
    SIZENWSE = auto()
    SIZENESW = auto()
    SIZEWE = auto()
    SIZENS = auto()
    SIZEALL = auto()
    NO = auto()
    HAND = auto()

    if TYPE_CHECKING:

        @property
        def value(self) -> int: ...

    def __deepcopy__(self, memo: Any) -> Self:
        return self

    def __copy__(self) -> Self:
        return self
