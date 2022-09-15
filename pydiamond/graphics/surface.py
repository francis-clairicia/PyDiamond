# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Surface module"""

from __future__ import annotations

__all__ = [
    "Surface",
    "SurfaceRenderer",
    "create_surface",
    "load_image",
    "save_image",
]

from typing import TYPE_CHECKING, Iterable, Literal, Sequence, overload

import pygame.image
from pygame import encode_file_path

if pygame.image.get_extended():  # Should be true as we explicitly query for SDL_image at package initialization
    from pygame.image import load_extended as _pg_image_load, save_extended as _pg_image_save
else:
    from pygame.image import load as _pg_image_load, save as _pg_image_save

from pygame.draw import aaline as _draw_antialiased_line, aalines as _draw_multiple_antialiased_lines
from pygame.surface import Surface

from ..system.utils.abc import concreteclass
from ._draw import (
    draw_arc as _draw_arc,
    draw_circle as _draw_circle,
    draw_ellipse as _draw_ellipse,
    draw_line as _draw_line,
    draw_lines as _draw_multiple_lines,
    draw_polygon as _draw_polygon,
    draw_rect as _draw_rect,
)
from .color import TRANSPARENT, Color
from .rect import Rect
from .renderer import AbstractRenderer, BlendMode

if TYPE_CHECKING:
    from pygame._common import _CanBeRect, _ColorValue, _Coordinate, _RectValue  # pyright: reportMissingModuleSource=false

del pygame


def create_surface(size: tuple[float, float], *, convert_alpha: bool = True, default_color: Color = TRANSPARENT) -> Surface:
    size = (max(size[0], 0), max(size[1], 0))
    s: Surface = Surface(size)
    if convert_alpha:
        s = s.convert_alpha()
    else:
        s = s.convert()
    s.fill(default_color)
    return s


def load_image(file: str, convert: bool = True) -> Surface:
    image: Surface = _pg_image_load(encode_file_path(file))
    if convert:
        return image.convert_alpha()
    return image


def save_image(image: Surface, file: str) -> None:
    return _pg_image_save(image, encode_file_path(file))


@concreteclass
class SurfaceRenderer(AbstractRenderer):

    __slots__ = ("__target",)

    @overload
    def __init__(self, size: tuple[float, float], /, *, convert_alpha: bool = True) -> None:
        ...

    @overload
    def __init__(self, target: Surface, /) -> None:
        ...

    def __init__(self, arg: Surface | tuple[float, float], /, *, convert_alpha: bool = True) -> None:
        self.__target: Surface
        try:
            w: float
            h: float
            w, h = arg  # type: ignore[misc]
        except TypeError:
            self.__target = arg  # type: ignore[assignment]
        else:
            self.__target = create_surface((w, h), convert_alpha=convert_alpha)
        # arg if isinstance(arg, Surface) else create_surface(arg, convert_alpha=convert_alpha)

    def get_rect(self, **kwargs: float | Sequence[float]) -> Rect:
        return self.__target.get_rect(**kwargs)

    def get_size(self) -> tuple[int, int]:
        return self.__target.get_size()

    def get_width(self) -> float:
        return self.__target.get_width()

    def get_height(self) -> float:
        return self.__target.get_height()

    def fill(self, color: _ColorValue, rect: _CanBeRect | None = None) -> Rect:
        return self.__target.fill(color, rect=rect)

    def draw_surface(
        self,
        surface: Surface,
        dest: _Coordinate | _CanBeRect,
        area: _CanBeRect | None = None,
        special_flags: int = BlendMode.NONE,
    ) -> Rect:
        return self.__target.blit(surface, dest, area, special_flags)

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, _Coordinate | _CanBeRect]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[True] = ...,
    ) -> list[Rect]:
        ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, _Coordinate | _CanBeRect]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[False],
    ) -> None:
        ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, _Coordinate | _CanBeRect]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool,
    ) -> list[Rect] | None:
        ...

    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, _Coordinate | _CanBeRect]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool = True,
    ) -> list[Rect] | None:
        return self.__target.blits(sequence, doreturn)  # type: ignore[arg-type]

    def draw_rect(
        self,
        color: _ColorValue,
        rect: _RectValue,
        width: int = 0,
        border_radius: int = -1,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
    ) -> Rect:
        return _draw_rect(
            surface=self.__target,
            color=color,
            rect=rect,
            width=width,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )

    def draw_polygon(
        self,
        color: _ColorValue,
        points: Sequence[_Coordinate],
        width: int = 0,
    ) -> Rect:
        return _draw_polygon(surface=self.__target, color=color, points=points, width=width)

    def draw_circle(
        self,
        color: _ColorValue,
        center: _Coordinate,
        radius: float,
        width: int = 0,
        draw_top_right: bool | None = None,
        draw_top_left: bool | None = None,
        draw_bottom_left: bool | None = None,
        draw_bottom_right: bool | None = None,
    ) -> Rect:
        return _draw_circle(
            surface=self.__target,
            color=color,
            center=center,
            radius=radius,
            width=width,
            draw_top_left=draw_top_left,
            draw_top_right=draw_top_right,
            draw_bottom_left=draw_bottom_left,
            draw_bottom_right=draw_bottom_right,
        )

    def draw_ellipse(self, color: _ColorValue, rect: _RectValue, width: int = 0) -> Rect:
        return _draw_ellipse(surface=self.__target, color=color, rect=rect, width=width)

    def draw_arc(
        self,
        color: _ColorValue,
        rect: _RectValue,
        start_angle: float,
        stop_angle: float,
        width: int = 1,
    ) -> Rect:
        return _draw_arc(
            surface=self.__target,
            color=color,
            rect=rect,
            start_angle=start_angle,
            stop_angle=stop_angle,
            width=width,
        )

    def draw_line(
        self,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        width: int = 1,
    ) -> Rect:
        return _draw_line(surface=self.__target, color=color, start_pos=start_pos, end_pos=end_pos, width=width)

    def draw_lines(
        self,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        width: int = 1,
    ) -> Rect:
        return _draw_multiple_lines(surface=self.__target, color=color, closed=closed, points=points, width=width)

    def draw_aaline(
        self,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        blend: int = 1,
    ) -> Rect:
        return _draw_antialiased_line(surface=self.__target, color=color, start_pos=start_pos, end_pos=end_pos, blend=blend)

    def draw_aalines(
        self,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        blend: int = 1,
    ) -> Rect:
        return _draw_multiple_antialiased_lines(
            surface=self.__target,
            color=color,
            closed=closed,
            points=points,
            blend=blend,
        )

    @property
    def surface(self) -> Surface:
        return self.__target

    @surface.setter
    def surface(self, new_target: Surface) -> None:
        self.__target = new_target
