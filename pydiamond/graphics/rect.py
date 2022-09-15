# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Rect module"""

from __future__ import annotations

__all__ = ["ImmutableRect", "Rect"]


from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, SupportsIndex

from pygame.rect import Rect

if TYPE_CHECKING:
    from _typeshed import Self


@dataclass(init=False, repr=False, eq=False, frozen=True, unsafe_hash=True)
class ImmutableRect(Rect):
    x: int
    y: int
    top: int
    left: int
    bottom: int
    right: int
    topleft: tuple[int, int]
    bottomleft: tuple[int, int]
    topright: tuple[int, int]
    bottomright: tuple[int, int]
    midtop: tuple[int, int]
    midleft: tuple[int, int]
    midbottom: tuple[int, int]
    midright: tuple[int, int]
    center: tuple[int, int]
    centerx: int
    centery: int
    size: tuple[int, int]
    width: int
    height: int
    w: int
    h: int

    if not TYPE_CHECKING:

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)

    @classmethod
    def convert(cls: type[Self], pygame_rect: Rect) -> Self:
        return cls(pygame_rect.topleft, pygame_rect.size)  # type: ignore[call-arg]

    def __reduce_ex__(self, __protocol: SupportsIndex) -> str | tuple[Any, ...]:
        return type(self), (self.x, self.y, self.w, self.h)

    def __reduce__(self) -> str | tuple[Any, ...]:
        return type(self), (self.x, self.y, self.w, self.h)
