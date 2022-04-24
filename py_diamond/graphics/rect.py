# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Rect module"""

from __future__ import annotations

__all__ = ["ImmutableRect", "Rect"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from dataclasses import dataclass
from typing import Any, overload

from pygame.rect import Rect

from ..math.vector2 import Vector2


@dataclass(init=False, repr=False, eq=False, frozen=True)
class ImmutableRect(Rect):
    @overload
    def __init__(self, left: float, top: float, width: float, height: float) -> None:
        ...

    @overload
    def __init__(
        self,
        left_top: list[float] | tuple[float, float] | Vector2,
        width_height: list[float] | tuple[float, float] | Vector2,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        left_top_width_height: Rect | tuple[float, float, float, float] | list[float],
    ) -> None:
        ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @staticmethod
    def convert(pygame_rect: Rect) -> ImmutableRect:
        return ImmutableRect(pygame_rect.topleft, pygame_rect.size)
