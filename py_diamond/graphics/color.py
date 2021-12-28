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
from typing import Any, List, Tuple, Union, overload

from pygame.color import Color as _Color


class Color(_Color):
    @property
    def h(self, /) -> float:
        return self.hsva[0]

    @h.setter
    def h(self, /, value: float) -> None:
        _, S, V, A = self.hsva
        H = value % 360
        self.hsva = (H, S, V, A)

    @property
    def s(self, /) -> float:
        return self.hsva[1]

    @s.setter
    def s(self, /, value: float) -> None:
        H, _, V, A = self.hsva
        S = value
        if S > 100:
            S = 100
        elif S < 0:
            S = 0
        self.hsva = (H, S, V, A)

    @property
    def v(self, /) -> float:
        return self.hsva[2]

    @v.setter
    def v(self, /, value: float) -> None:
        H, S, _, A = self.hsva
        V = value
        if V > 100:
            V = 100
        elif V < 0:
            V = 0
        self.hsva = (H, S, V, A)

    def with_brightness(self, /, value: float) -> Color:
        c = Color(self)
        c.v = value
        return c

    def with_saturation(self, /, value: float) -> Color:
        c = Color(self)
        c.s = value
        return c

    def with_alpha(self, /, value: int) -> Color:
        return Color(self.r, self.g, self.b, value)


_ColorValue = Union[Color, str, Tuple[int, int, int], List[int], int, Tuple[int, int, int, int]]


@dataclass(init=False, repr=False, frozen=True)
class ImmutableColor(Color):
    r: int
    g: int
    b: int
    a: int
    h: float
    s: float
    v: float
    cmy: Tuple[float, float, float]
    hsva: Tuple[float, float, float, float]
    hsla: Tuple[float, float, float, float]
    i1i2i3: Tuple[float, float, float]

    @overload
    def __init__(self, r: int, g: int, b: int, a: int = 255, /) -> None:
        ...

    @overload
    def __init__(self, rgbvalue: _ColorValue, /) -> None:
        ...

    def __init__(self, /, *args: Any) -> None:
        super().__init__(*args)


WHITE: Color = ImmutableColor(255, 255, 255)
BLACK: Color = ImmutableColor(0, 0, 0)
GRAY: Color = ImmutableColor(127, 127, 127)
GRAY_DARK: Color = ImmutableColor(95, 95, 95)
GRAY_LIGHT: Color = ImmutableColor(175, 175, 175)
RED: Color = ImmutableColor(255, 0, 0)
RED_DARK: Color = ImmutableColor(128, 0, 0)
RED_LIGHT: Color = ImmutableColor(255, 128, 128)
ORANGE: Color = ImmutableColor(255, 175, 0)
YELLOW: Color = ImmutableColor(255, 255, 0)
GREEN: Color = ImmutableColor(0, 255, 0)
GREEN_DARK: Color = ImmutableColor(0, 128, 0)
GREEN_LIGHT: Color = ImmutableColor(128, 255, 128)
CYAN: Color = ImmutableColor(0, 255, 255)
BLUE: Color = ImmutableColor(0, 0, 255)
BLUE_DARK: Color = ImmutableColor(0, 0, 128)
BLUE_LIGHT: Color = ImmutableColor(128, 128, 255)
MAGENTA: Color = ImmutableColor(255, 0, 255)
PURPLE: Color = ImmutableColor(165, 0, 255)
TRANSPARENT: Color = ImmutableColor(0, 0, 0, 0)
