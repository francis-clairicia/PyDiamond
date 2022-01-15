# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Color module"""

from __future__ import annotations

__all__ = [
    "BLACK",
    "BLUE",
    "BLUE_DARK",
    "BLUE_LIGHT",
    "COLOR_DICT",
    "CYAN",
    "Color",
    "GRAY",
    "GRAY_DARK",
    "GRAY_LIGHT",
    "GREEN",
    "GREEN_DARK",
    "GREEN_LIGHT",
    "ImmutableColor",
    "MAGENTA",
    "ORANGE",
    "PURPLE",
    "RED",
    "RED_DARK",
    "RED_LIGHT",
    "TRANSPARENT",
    "WHITE",
    "YELLOW",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final, List, Mapping, Tuple, TypeAlias, overload

from pygame.color import Color as _Color
from pygame.colordict import THECOLORS as _PG_ALL_COLORS


class Color(_Color):
    @property
    def h(self) -> float:
        return self.hsva[0]

    @h.setter
    def h(self, value: float) -> None:
        _, S, V, A = self.hsva
        H = value % 360
        self.hsva = (H, S, V, A)

    @property
    def s(self) -> float:
        return self.hsva[1]

    @s.setter
    def s(self, value: float) -> None:
        H, _, V, A = self.hsva
        S = value
        if S > 100:
            S = 100
        elif S < 0:
            S = 0
        self.hsva = (H, S, V, A)

    @property
    def v(self) -> float:
        return self.hsva[2]

    @v.setter
    def v(self, value: float) -> None:
        H, S, _, A = self.hsva
        V = value
        if V > 100:
            V = 100
        elif V < 0:
            V = 0
        self.hsva = (H, S, V, A)

    def with_brightness(self, value: float) -> Color:
        c = Color(self)
        c.v = value
        return c

    def with_saturation(self, value: float) -> Color:
        c = Color(self)
        c.s = value
        return c

    def with_alpha(self, value: int) -> Color:
        return Color(self.r, self.g, self.b, value)


_ColorValue: TypeAlias = Color | str | Tuple[int, int, int] | List[int] | int | Tuple[int, int, int, int]


@dataclass(init=False, repr=False, frozen=True)
class ImmutableColor(Color):
    @overload
    def __init__(self, r: int, g: int, b: int, a: int = 255) -> None:
        ...

    @overload
    def __init__(self, rgbvalue: _ColorValue) -> None:
        ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


COLOR_DICT: Final[Mapping[str, Color]] = MappingProxyType({c: ImmutableColor(c) for c in _PG_ALL_COLORS})

WHITE: Final[Color] = COLOR_DICT.get("white", ImmutableColor(255, 255, 255, 255))
BLACK: Final[Color] = COLOR_DICT.get("black", ImmutableColor(0, 0, 0, 255))
GRAY: Final[Color] = COLOR_DICT.get("gray50", ImmutableColor(127, 127, 127, 255))
GRAY_DARK: Final[Color] = COLOR_DICT.get("gray37", ImmutableColor(95, 95, 95, 255))
GRAY_LIGHT: Final[Color] = COLOR_DICT.get("gray69", ImmutableColor(175, 75, 175, 255))
RED: Final[Color] = COLOR_DICT.get("red", ImmutableColor(255, 0, 0, 255))
RED_DARK: Final[Color] = COLOR_DICT.get("darkred", ImmutableColor(140, 0, 0, 255))
RED_LIGHT: Final[Color] = ImmutableColor(255, 128, 128)
ORANGE: Final[Color] = COLOR_DICT.get("orange", ImmutableColor(255, 165, 0, 255))
YELLOW: Final[Color] = COLOR_DICT.get("yellow", ImmutableColor(255, 255, 0, 255))
GREEN: Final[Color] = COLOR_DICT.get("green", ImmutableColor(0, 255, 0, 255))
GREEN_DARK: Final[Color] = COLOR_DICT.get("darkgreen", ImmutableColor(0, 128, 0, 255))
GREEN_LIGHT: Final[Color] = COLOR_DICT.get("lightgreen", ImmutableColor(128, 255, 128, 255))
CYAN: Final[Color] = COLOR_DICT.get("cyan", ImmutableColor(0, 255, 255, 255))
BLUE: Final[Color] = COLOR_DICT.get("blue", ImmutableColor(0, 0, 255, 255))
BLUE_DARK: Final[Color] = COLOR_DICT.get("darkblue", ImmutableColor(0, 0, 128, 255))
BLUE_LIGHT: Final[Color] = COLOR_DICT.get("deepskyblue", ImmutableColor(0, 128, 255, 255))
MAGENTA: Final[Color] = COLOR_DICT.get("magenta", ImmutableColor(255, 0, 255, 255))
PURPLE: Final[Color] = COLOR_DICT.get("purple", ImmutableColor(165, 0, 255, 255))
TRANSPARENT: Final[Color] = ImmutableColor(0, 0, 0, 0)

del _PG_ALL_COLORS
