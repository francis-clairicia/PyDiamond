# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Surface module"""

from __future__ import annotations

__all__ = [
    "Surface",
    "SurfaceRenderer",
    "create_surface",
    "load_image",
    "load_image_resource",
    "save_image",
]

from abc import abstractmethod
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterable, Iterator, Literal, Sequence, TypeVar, overload

import pygame.image as _pg_image
from pygame import encode_file_path
from pygame.draw import aaline as _draw_antialiased_line, aalines as _draw_multiple_antialiased_lines
from pygame.surface import Surface

from ..math.rect import Rect
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
from .color import TRANSPARENT
from .font import STYLE_DEFAULT, Font, FontFactory
from .renderer import AbstractRenderer, BlendMode, RendererAnchor

if TYPE_CHECKING:
    from pygame._common import ColorValue, Coordinate, RectValue, _CanBeRect

    from ..resources.abc import Resource
    from .font import _TextFont


def create_surface(size: tuple[float, float], *, convert_alpha: bool = True, default_color: ColorValue = TRANSPARENT) -> Surface:
    size = (max(size[0], 0), max(size[1], 0))
    s: Surface = Surface(size)
    if convert_alpha:
        s = s.convert_alpha()
    else:
        s = s.convert()
    s.fill(default_color)
    return s


def load_image(file: str, convert: bool = True) -> Surface:
    image: Surface = _pg_image.load(encode_file_path(file))
    if convert:
        return image.convert_alpha()
    return image


def load_image_resource(resource: Resource, convert: bool = True) -> Surface:
    with resource.open() as fp:
        image: Surface = _pg_image.load(fp, resource.name)
    if convert:
        return image.convert_alpha()
    return image


def save_image(image: Surface, file: str) -> None:
    return _pg_image.save(image, encode_file_path(file))


class AbstractSurfaceRenderer(AbstractRenderer):
    __slots__ = ()

    @abstractmethod
    def get_target(self) -> Surface:
        raise NotImplementedError

    def get_rect(self, **kwargs: Any) -> Rect:
        return self.get_target().get_rect(**kwargs)

    def get_size(self) -> tuple[int, int]:
        return self.get_target().get_size()

    def get_width(self) -> float:
        return self.get_target().get_width()

    def get_height(self) -> float:
        return self.get_target().get_height()

    def fill(self, color: ColorValue, rect: _CanBeRect | None = None) -> Rect:
        return self.get_target().fill(color, rect=rect)

    def get_clip(self) -> Rect:
        return self.get_target().get_clip()

    @contextmanager
    def using_clip(self, rect: _CanBeRect | None) -> Iterator[None]:
        target = self.get_target()
        set_clip = target.set_clip
        former_rect = target.get_clip()
        set_clip(rect)
        try:
            yield
        finally:
            set_clip(former_rect)

    def to_surface(self, surface: Surface | None = None, area: _CanBeRect | None = None) -> Surface:
        target: Surface = self.get_target()
        match surface:
            case None:
                surface = target
                if area is not None:
                    surface = surface.subsurface(area)
                surface = surface.copy()
            case Surface() if surface.get_width() >= target.get_width() and surface.get_height() >= target.get_height():
                surface.blit(target, (0, 0), area)
            case Surface():
                raise ValueError("Too small surface")
            case _:
                raise TypeError("'surface' must be a regular Surface or None")
        return surface

    def draw_surface(
        self,
        surface: Surface,
        dest: Coordinate | _CanBeRect,
        area: _CanBeRect | None = None,
        special_flags: int = BlendMode.NONE,
        anchor: RendererAnchor = "topleft",
    ) -> Rect:
        if anchor != "topleft":
            dest = surface.get_rect(**{anchor: dest})  # type: ignore[misc]
        return self.get_target().blit(surface, dest, area, special_flags)

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[True] = ...,
    ) -> list[Rect]:
        ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[False],
    ) -> None:
        ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool,
    ) -> list[Rect] | None:
        ...

    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool = True,
    ) -> list[Rect] | None:
        return self.get_target().blits(sequence, doreturn)  # type: ignore[arg-type]

    def draw_text(
        self,
        text: str,
        font: _TextFont,
        dest: Coordinate | _CanBeRect,
        fgcolor: ColorValue,
        bgcolor: ColorValue | None = None,
        style: int = STYLE_DEFAULT,
        rotation: int = 0,
        size: float = 0,
        anchor: RendererAnchor = "topleft",
    ) -> Rect:
        if not isinstance(font, Font):
            font = FontFactory.create_font(font)
        if anchor != "topleft":
            dest = font.get_rect(text, style=style, rotation=rotation, size=size, **{anchor: dest})
        return font.render_to(self.get_target(), dest, text, fgcolor, bgcolor=bgcolor, style=style, rotation=rotation, size=size)

    def draw_rect(
        self,
        color: ColorValue,
        rect: RectValue,
        width: int = 0,
        border_radius: int = -1,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
    ) -> Rect:
        return _draw_rect(
            surface=self.get_target(),
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
        color: ColorValue,
        points: Sequence[Coordinate],
        width: int = 0,
    ) -> Rect:
        return _draw_polygon(surface=self.get_target(), color=color, points=points, width=width)

    def draw_circle(
        self,
        color: ColorValue,
        center: Coordinate,
        radius: float,
        width: int = 0,
        draw_top_right: bool = True,
        draw_top_left: bool = True,
        draw_bottom_left: bool = True,
        draw_bottom_right: bool = True,
    ) -> Rect:
        return _draw_circle(
            surface=self.get_target(),
            color=color,
            center=center,
            radius=radius,
            width=width,
            draw_top_left=draw_top_left,
            draw_top_right=draw_top_right,
            draw_bottom_left=draw_bottom_left,
            draw_bottom_right=draw_bottom_right,
        )

    def draw_ellipse(self, color: ColorValue, rect: RectValue, width: int = 0) -> Rect:
        return _draw_ellipse(surface=self.get_target(), color=color, rect=rect, width=width)

    def draw_arc(
        self,
        color: ColorValue,
        rect: RectValue,
        start_angle: float,
        stop_angle: float,
        width: int = 1,
    ) -> Rect:
        return _draw_arc(
            surface=self.get_target(),
            color=color,
            rect=rect,
            start_angle=start_angle,
            stop_angle=stop_angle,
            width=width,
        )

    def draw_line(
        self,
        color: ColorValue,
        start_pos: Coordinate,
        end_pos: Coordinate,
        width: int = 1,
    ) -> Rect:
        return _draw_line(surface=self.get_target(), color=color, start_pos=start_pos, end_pos=end_pos, width=width)

    def draw_lines(
        self,
        color: ColorValue,
        closed: bool,
        points: Sequence[Coordinate],
        width: int = 1,
    ) -> Rect:
        return _draw_multiple_lines(surface=self.get_target(), color=color, closed=closed, points=points, width=width)

    def draw_aaline(
        self,
        color: ColorValue,
        start_pos: Coordinate,
        end_pos: Coordinate,
        blend: int = 1,
    ) -> Rect:
        return _draw_antialiased_line(surface=self.get_target(), color=color, start_pos=start_pos, end_pos=end_pos, blend=blend)

    def draw_aalines(
        self,
        color: ColorValue,
        closed: bool,
        points: Sequence[Coordinate],
        blend: int = 1,
    ) -> Rect:
        return _draw_multiple_antialiased_lines(
            surface=self.get_target(),
            color=color,
            closed=closed,
            points=points,
            blend=blend,
        )


@concreteclass
class SurfaceRenderer(AbstractSurfaceRenderer):
    __slots__ = ("__target",)

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="SurfaceRenderer")

    def __init__(self, target: Surface) -> None:
        assert isinstance(target, Surface), "target must be a regular surface"
        self.__target: Surface = target

    @classmethod
    def from_size(cls: type[__Self], size: tuple[float, float], *, convert_alpha: bool = True) -> __Self:
        target = create_surface(size, convert_alpha=convert_alpha)
        return cls(target)

    def get_target(self) -> Surface:
        return self.__target
