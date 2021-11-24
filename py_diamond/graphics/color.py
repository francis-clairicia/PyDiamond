# -*- coding: Utf-8 -*

__all__ = [
    "Color",
    "ImmutableColor",
    "WHITE",
    "BLACK",
    "GRAY",
    "GRAY_DARK",
    "GRAY_LIGHT",
    "RED",
    "RED_DARK",
    "RED_LIGHT",
    "ORANGE",
    "YELLOW",
    "GREEN",
    "GREEN_DARK",
    "GREEN_LIGHT",
    "CYAN",
    "BLUE",
    "BLUE_DARK",
    "BLUE_LIGHT",
    "MAGENTA",
    "PURPLE",
    "TRANSPARENT",
    "change_brightness",
    "change_saturation",
    "set_brightness",
    "set_color_alpha",
    "set_saturation",
]

from dataclasses import dataclass
from pygame.color import Color
from typing import Any, List, Tuple, Union, overload


_ColorValue = Union[Color, str, Tuple[int, int, int], List[int], int, Tuple[int, int, int, int]]


@dataclass(init=False, frozen=True)
class ImmutableColor(Color):
    r: int
    g: int
    b: int
    a: int
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


WHITE = ImmutableColor(255, 255, 255)
BLACK = ImmutableColor(0, 0, 0)
GRAY = ImmutableColor(127, 127, 127)
GRAY_DARK = ImmutableColor(95, 95, 95)
GRAY_LIGHT = ImmutableColor(175, 175, 175)
RED = ImmutableColor(255, 0, 0)
RED_DARK = ImmutableColor(128, 0, 0)
RED_LIGHT = ImmutableColor(255, 128, 128)
ORANGE = ImmutableColor(255, 175, 0)
YELLOW = ImmutableColor(255, 255, 0)
GREEN = ImmutableColor(0, 255, 0)
GREEN_DARK = ImmutableColor(0, 128, 0)
GREEN_LIGHT = ImmutableColor(128, 255, 128)
CYAN = ImmutableColor(0, 255, 255)
BLUE = ImmutableColor(0, 0, 255)
BLUE_DARK = ImmutableColor(0, 0, 128)
BLUE_LIGHT = ImmutableColor(128, 128, 255)
MAGENTA = ImmutableColor(255, 0, 255)
PURPLE = ImmutableColor(165, 0, 255)
TRANSPARENT = ImmutableColor(0, 0, 0, 0)


def set_brightness(color: Color, value: int) -> Color:
    c = Color(color)
    H, S, V, A = c.hsva
    V = value
    if V > 100:
        V = 100
    elif V < 0:
        V = 0
    c.hsva = (H, S, V, A)
    return c


def change_brightness(color: Color, offset: int) -> Color:
    c = Color(color)
    H, S, V, A = c.hsva
    V += offset
    if V > 100:
        V = 100
    elif V < 0:
        V = 0
    c.hsva = (H, S, V, A)
    return c


def set_saturation(color: Color, value: int) -> Color:
    c = Color(color)
    H, S, V, A = c.hsva
    S = value
    if S > 100:
        S = 100
    elif S < 0:
        S = 0
    c.hsva = (H, S, V, A)
    return c


def change_saturation(color: Color, offset: int) -> Color:
    c = Color(color)
    H, S, V, A = c.hsva
    S += offset
    if S > 100:
        S = 100
    elif S < 0:
        S = 0
    c.hsva = (H, S, V, A)
    return c


def set_color_alpha(color: Color, value: int) -> Color:
    return Color(color.r, color.g, color.b, value)
