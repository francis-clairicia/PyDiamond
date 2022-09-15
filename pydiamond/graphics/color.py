# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, SupportsIndex

import pygame.color
import pygame.colordict


class Color(pygame.color.Color):
    @property
    def h(self) -> float:
        return self.hsva[0]

    @h.setter
    def h(self, value: float) -> None:
        _, S, V, A = self.hsva
        self.hsva = (value, S, V, A)

    @property
    def s(self) -> float:
        return self.hsva[1]

    @s.setter
    def s(self, value: float) -> None:
        H, _, V, A = self.hsva
        self.hsva = (H, value, V, A)

    @property
    def v(self) -> float:
        return self.hsva[2]

    @v.setter
    def v(self, value: float) -> None:
        H, S, _, A = self.hsva
        self.hsva = (H, S, value, A)

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

    def __reduce_ex__(self, __protocol: SupportsIndex) -> str | tuple[Any, ...]:
        return type(self), (self.r, self.g, self.b, self.a)

    def __reduce__(self) -> str | tuple[Any, ...]:
        return type(self), (self.r, self.g, self.b, self.a)


@dataclass(init=False, repr=False, eq=False, frozen=True, unsafe_hash=True)
class ImmutableColor(Color):
    r: int
    g: int
    b: int
    a: int
    h: float
    s: float
    v: float
    cmy: tuple[float, float, float]
    hsva: tuple[float, float, float, float]
    hsla: tuple[float, float, float, float]
    i1i2i3: tuple[float, float, float]

    if not TYPE_CHECKING:

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)


COLOR_DICT: Final[dict[str, tuple[int, int, int, int]]] = pygame.colordict.THECOLORS

COLOR_DICT.update(
    {
        "lightred": (255, 128, 128, 255),
        "transparent": (0, 0, 0, 0),
    }
)

WHITE: Final[ImmutableColor] = ImmutableColor("white")
BLACK: Final[ImmutableColor] = ImmutableColor("black")
GRAY: Final[ImmutableColor] = ImmutableColor("gray50")
GRAY_DARK: Final[ImmutableColor] = ImmutableColor("gray37")
GRAY_LIGHT: Final[ImmutableColor] = ImmutableColor("gray69")
RED: Final[ImmutableColor] = ImmutableColor("red")
RED_DARK: Final[ImmutableColor] = ImmutableColor("darkred")
RED_LIGHT: Final[ImmutableColor] = ImmutableColor("lightred")
ORANGE: Final[ImmutableColor] = ImmutableColor("orange")
YELLOW: Final[ImmutableColor] = ImmutableColor("yellow")
GREEN: Final[ImmutableColor] = ImmutableColor("green")
GREEN_DARK: Final[ImmutableColor] = ImmutableColor("darkgreen")
GREEN_LIGHT: Final[ImmutableColor] = ImmutableColor("lightgreen")
CYAN: Final[ImmutableColor] = ImmutableColor("cyan")
BLUE: Final[ImmutableColor] = ImmutableColor("blue")
BLUE_DARK: Final[ImmutableColor] = ImmutableColor("darkblue")
BLUE_LIGHT: Final[ImmutableColor] = ImmutableColor("deepskyblue")
MAGENTA: Final[ImmutableColor] = ImmutableColor("magenta")
PURPLE: Final[ImmutableColor] = ImmutableColor("purple")
TRANSPARENT: Final[ImmutableColor] = ImmutableColor("transparent")

del pygame
