# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Rect module"""

from __future__ import annotations

__all__ = ["ImmutableRect", "Rect"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from dataclasses import dataclass
from typing import Any, List, Tuple, Union, overload

from pygame.rect import Rect as _Rect

from ..math.vector2 import Vector2


class Rect(_Rect):
    @staticmethod
    def convert(pygame_rect: _Rect) -> Rect:
        return Rect(pygame_rect.topleft, pygame_rect.size)


@dataclass(init=False, repr=False, frozen=True)
class ImmutableRect(Rect):
    x: int
    y: int
    top: int
    left: int
    bottom: int
    right: int
    topleft: Tuple[int, int]
    bottomleft: Tuple[int, int]
    topright: Tuple[int, int]
    bottomright: Tuple[int, int]
    midtop: Tuple[int, int]
    midleft: Tuple[int, int]
    midbottom: Tuple[int, int]
    midright: Tuple[int, int]
    center: Tuple[int, int]
    centerx: int
    centery: int
    size: Tuple[int, int]
    width: int
    height: int
    w: int
    h: int

    @overload
    def __init__(self, left: float, top: float, width: float, height: float) -> None:
        ...

    @overload
    def __init__(
        self,
        left_top: Union[List[float], Tuple[float, float], Vector2],
        width_height: Union[List[float], Tuple[float, float], Vector2],
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        left_top_width_height: Union[Rect, Tuple[float, float, float, float], List[float]],
    ) -> None:
        ...

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @staticmethod
    def convert(pygame_rect: _Rect) -> ImmutableRect:
        return ImmutableRect(pygame_rect.topleft, pygame_rect.size)
