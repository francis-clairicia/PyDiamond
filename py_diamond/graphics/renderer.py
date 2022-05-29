# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""AbstractRenderer module"""

from __future__ import annotations

__all__ = ["AbstractRenderer", "SurfaceRenderer"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from enum import IntEnum, unique
from typing import TYPE_CHECKING, Sequence, overload

import pygame.constants as _pg_constants
from pygame.draw import aaline as _draw_antialiased_line, aalines as _draw_multiple_antialiased_lines

from ..math.vector2 import Vector2
from ..system.object import Object
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
from .rect import Rect
from .surface import Surface, create_surface

if TYPE_CHECKING:
    from pygame._common import _ColorValue, _Coordinate, _RectValue  # pyright: reportMissingModuleSource=false


@unique
class BlendMode(IntEnum):
    NONE = 0
    ADD = _pg_constants.BLEND_RGB_ADD
    SUB = _pg_constants.BLEND_RGB_SUB
    MULT = _pg_constants.BLEND_RGB_MULT
    MIN = _pg_constants.BLEND_RGB_MIN
    MAX = _pg_constants.BLEND_RGB_MAX
    RGBA_ADD = _pg_constants.BLEND_RGBA_ADD
    RGBA_SUB = _pg_constants.BLEND_RGBA_SUB
    RGBA_MULT = _pg_constants.BLEND_RGBA_MULT
    RGBA_MIN = _pg_constants.BLEND_RGBA_MIN
    RGBA_MAX = _pg_constants.BLEND_RGBA_MAX
    PREMULTIPLIED = _pg_constants.BLEND_PREMULTIPLIED
    ALPHA_SDL2 = _pg_constants.BLEND_ALPHA_SDL2


class AbstractRenderer(Object):

    __slots__ = ()

    @abstractmethod
    def get_rect(self, **kwargs: float | Sequence[float]) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def get_size(self) -> tuple[float, float]:
        raise NotImplementedError

    @abstractmethod
    def get_width(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_height(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def fill(self, color: _ColorValue) -> None:
        raise NotImplementedError

    @abstractmethod
    def draw_surface(
        self,
        obj: Surface,
        dest: tuple[float, float] | Vector2 | Rect,
        /,
        *,
        area: Rect | None = None,
        special_flags: BlendMode = BlendMode.NONE,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def draw_polygon(
        self,
        color: _ColorValue,
        points: Sequence[_Coordinate],
        width: int = 0,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def draw_ellipse(self, color: _ColorValue, rect: _RectValue, width: int = 0) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_arc(
        self,
        color: _ColorValue,
        rect: _RectValue,
        start_angle: float,
        stop_angle: float,
        width: int = 1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_line(
        self,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        width: int = 1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_lines(
        self,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        width: int = 1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_aaline(
        self,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_aalines(
        self,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
    ) -> Rect:
        raise NotImplementedError


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
        self.__target: Surface = arg if isinstance(arg, Surface) else create_surface(arg, convert_alpha=convert_alpha)

    def get_rect(self, **kwargs: float | Sequence[float]) -> Rect:
        target: Surface = self.__target
        return target.get_rect(**kwargs)

    def get_size(self) -> tuple[int, int]:
        target: Surface = self.__target
        return target.get_size()

    def get_width(self) -> float:
        target: Surface = self.__target
        return target.get_width()

    def get_height(self) -> float:
        target: Surface = self.__target
        return target.get_height()

    def fill(self, color: _ColorValue) -> None:
        target: Surface = self.__target
        target.fill(color)

    def draw_surface(
        self,
        obj: Surface,
        dest: tuple[float, float] | Vector2 | Rect,
        /,
        *,
        area: Rect | None = None,
        special_flags: BlendMode = BlendMode.NONE,
    ) -> Rect:
        target: Surface = self.__target
        return target.blit(obj, dest, area, special_flags)

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
        target: Surface = self.__target
        output_rect: Rect = _draw_rect(
            surface=target,
            color=color,
            rect=rect,
            width=width,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )
        return output_rect

    def draw_polygon(
        self,
        color: _ColorValue,
        points: Sequence[_Coordinate],
        width: int = 0,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: Rect = _draw_polygon(surface=target, color=color, points=points, width=width)
        return output_rect

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
        target: Surface = self.__target
        output_rect: Rect = _draw_circle(
            surface=target,
            color=color,
            center=center,
            radius=radius,
            width=width,
            draw_top_left=draw_top_left,
            draw_top_right=draw_top_right,
            draw_bottom_left=draw_bottom_left,
            draw_bottom_right=draw_bottom_right,
        )
        return output_rect

    def draw_ellipse(self, color: _ColorValue, rect: _RectValue, width: int = 0) -> Rect:
        target: Surface = self.__target
        output_rect: Rect = _draw_ellipse(surface=target, color=color, rect=rect, width=width)
        return output_rect

    def draw_arc(
        self,
        color: _ColorValue,
        rect: _RectValue,
        start_angle: float,
        stop_angle: float,
        width: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: Rect = _draw_arc(
            surface=target, color=color, rect=rect, start_angle=start_angle, stop_angle=stop_angle, width=width
        )
        return output_rect

    def draw_line(
        self,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        width: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: Rect = _draw_line(surface=target, color=color, start_pos=start_pos, end_pos=end_pos, width=width)
        return output_rect

    def draw_lines(
        self,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        width: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: Rect = _draw_multiple_lines(surface=target, color=color, closed=closed, points=points, width=width)
        return output_rect

    def draw_aaline(
        self,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        blend: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: Rect = _draw_antialiased_line(surface=target, color=color, start_pos=start_pos, end_pos=end_pos, blend=blend)
        return output_rect

    def draw_aalines(
        self,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        blend: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: Rect = _draw_multiple_antialiased_lines(
            surface=target, color=color, closed=closed, points=points, blend=blend
        )
        return output_rect

    @property
    def surface(self) -> Surface:
        return self.__target


del _pg_constants
