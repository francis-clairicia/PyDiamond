# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""AbstractRenderer module"""

from __future__ import annotations

__all__ = ["AbstractRenderer"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from enum import IntEnum, unique
from typing import TYPE_CHECKING, Sequence

import pygame.constants as _pg_constants

from ..math.vector2 import Vector2
from ..system.object import Object
from .rect import Rect

if TYPE_CHECKING:
    from pygame._common import _ColorValue, _Coordinate, _RectValue  # pyright: reportMissingModuleSource=false

    from .surface import Surface


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


del _pg_constants
