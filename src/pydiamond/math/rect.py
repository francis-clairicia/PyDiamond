# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Rect module"""

from __future__ import annotations

__all__ = ["ImmutableRect", "Rect"]

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, SupportsIndex, overload

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


@overload
def modify_rect(r: Rect, /) -> Rect: ...


@overload
def modify_rect(
    r: Rect,
    /,
    *,
    x: float | None = ...,
    y: float | None = ...,
    top: float | None = ...,
    left: float | None = ...,
    bottom: float | None = ...,
    right: float | None = ...,
    topleft: tuple[float, float] | None = ...,
    bottomleft: tuple[float, float] | None = ...,
    topright: tuple[float, float] | None = ...,
    bottomright: tuple[float, float] | None = ...,
    midtop: tuple[float, float] | None = ...,
    midleft: tuple[float, float] | None = ...,
    midbottom: tuple[float, float] | None = ...,
    midright: tuple[float, float] | None = ...,
    center: tuple[float, float] | None = ...,
    centerx: float | None = ...,
    centery: float | None = ...,
    size: tuple[float, float] | None = ...,
    width: float | None = ...,
    height: float | None = ...,
    w: float | None = ...,
    h: float | None = ...,
) -> Rect: ...


def modify_rect(r: Rect, /, **kwargs: float | tuple[float, float] | None) -> Rect:
    r_copy = Rect(r.topleft, r.size)
    r_copy_setattr = r_copy.__setattr__
    for name, value in kwargs.items():
        if value is None:
            continue
        r_copy_setattr(name, value)
    return r_copy


@overload
def modify_rect_in_place(r: Rect, /) -> None: ...


@overload
def modify_rect_in_place(
    r: Rect,
    /,
    *,
    x: float | None = ...,
    y: float | None = ...,
    top: float | None = ...,
    left: float | None = ...,
    bottom: float | None = ...,
    right: float | None = ...,
    topleft: tuple[float, float] | None = ...,
    bottomleft: tuple[float, float] | None = ...,
    topright: tuple[float, float] | None = ...,
    bottomright: tuple[float, float] | None = ...,
    midtop: tuple[float, float] | None = ...,
    midleft: tuple[float, float] | None = ...,
    midbottom: tuple[float, float] | None = ...,
    midright: tuple[float, float] | None = ...,
    center: tuple[float, float] | None = ...,
    centerx: float | None = ...,
    centery: float | None = ...,
    size: tuple[float, float] | None = ...,
    width: float | None = ...,
    height: float | None = ...,
    w: float | None = ...,
    h: float | None = ...,
) -> None: ...


def modify_rect_in_place(r: Rect, /, **kwargs: float | tuple[float, float] | None) -> None:
    r_setattr = r.__setattr__
    for name, value in kwargs.items():
        if value is None:
            continue
        r_setattr(name, value)


@overload
def move_rect(r: Rect, /) -> Rect: ...


@overload
def move_rect(
    r: Rect,
    /,
    *,
    x: float | None = ...,
    y: float | None = ...,
    top: float | None = ...,
    left: float | None = ...,
    bottom: float | None = ...,
    right: float | None = ...,
    topleft: tuple[float, float] | None = ...,
    bottomleft: tuple[float, float] | None = ...,
    topright: tuple[float, float] | None = ...,
    bottomright: tuple[float, float] | None = ...,
    midtop: tuple[float, float] | None = ...,
    midleft: tuple[float, float] | None = ...,
    midbottom: tuple[float, float] | None = ...,
    midright: tuple[float, float] | None = ...,
    center: tuple[float, float] | None = ...,
    centerx: float | None = ...,
    centery: float | None = ...,
) -> Rect: ...


def move_rect(r: Rect, /, **kwargs: Any) -> Rect:
    return modify_rect(r, size=None, width=None, height=None, w=None, h=None, **kwargs)


@overload
def move_rect_in_place(r: Rect, /) -> None: ...


@overload
def move_rect_in_place(
    r: Rect,
    /,
    *,
    x: float | None = ...,
    y: float | None = ...,
    top: float | None = ...,
    left: float | None = ...,
    bottom: float | None = ...,
    right: float | None = ...,
    topleft: tuple[float, float] | None = ...,
    bottomleft: tuple[float, float] | None = ...,
    topright: tuple[float, float] | None = ...,
    bottomright: tuple[float, float] | None = ...,
    midtop: tuple[float, float] | None = ...,
    midleft: tuple[float, float] | None = ...,
    midbottom: tuple[float, float] | None = ...,
    midright: tuple[float, float] | None = ...,
    center: tuple[float, float] | None = ...,
    centerx: float | None = ...,
    centery: float | None = ...,
) -> None: ...


def move_rect_in_place(r: Rect, /, **kwargs: Any) -> None:
    modify_rect_in_place(r, size=None, width=None, height=None, w=None, h=None, **kwargs)
