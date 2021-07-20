# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import List, Tuple

from pygame.color import Color
from pygame.math import Vector2
from pygame.surface import Surface

from .shape import AbstractShape
from .surface import create_surface

from ._gradients import (  # type: ignore
    horizontal as gradient_horizontal,
    vertical as gradient_vertical,
    radial as gradient_radial,
    squared as gradient_squared,
)


class AbstractGradientShape(AbstractShape):
    def __init__(self, color: Color, second_color: Color) -> None:
        super().__init__(color)
        self.__second_color: Color = self.color
        self.second_color = second_color
        self._need_update()

    @property
    def second_color(self) -> Color:
        return self.__second_color

    @second_color.setter
    def second_color(self, color: Color) -> None:
        color = Color(color)
        if self.__second_color != color:
            self.__second_color = color
            self._need_update()


class AbstractRectangleGradientShape(AbstractGradientShape):
    def __init__(self, width: float, height: float, color: Color, second_color: Color) -> None:
        super().__init__(color, second_color)
        self.__w: float = 0
        self.__h: float = 0
        self.local_size = width, height
        self._need_update()

    def get_local_size(self) -> Tuple[float, float]:
        return self.local_size

    def get_local_vertices(self) -> List[Vector2]:
        w, h = self.get_local_size()
        return [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]

    @property
    def local_size(self) -> Tuple[float, float]:
        return (self.local_width, self.local_height)

    @local_size.setter
    def local_size(self, size: Tuple[float, float]) -> None:
        self.local_width, self.local_height = size

    @property
    def local_width(self) -> float:
        return self.__w

    @local_width.setter
    def local_width(self, width: float) -> None:
        width = max(width, 0)
        if width != self.__w:
            self.__w = width
            self._need_update()

    @property
    def local_height(self) -> float:
        return self.__h

    @local_height.setter
    def local_height(self, height: float) -> None:
        height = max(height, 0)
        if height != self.__h:
            self.__h = height
            self._need_update()


class HorizontalGradientShape(AbstractRectangleGradientShape):
    def make(self) -> Surface:
        size = self.get_local_size()
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        start_color = (self.color.r, self.color.g, self.color.b, self.color.a)
        end_color = (self.second_color.r, self.second_color.g, self.second_color.b, self.second_color.a)
        return gradient_horizontal(size, start_color, end_color)  # type: ignore


class VerticalGradientShape(AbstractRectangleGradientShape):
    def make(self) -> Surface:
        size = self.get_local_size()
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        start_color = (self.color.r, self.color.g, self.color.b, self.color.a)
        end_color = (self.second_color.r, self.second_color.g, self.second_color.b, self.second_color.a)
        return gradient_vertical(size, start_color, end_color)  # type: ignore


class SquaredGradientShape(AbstractGradientShape):
    def __init__(self, width: float, color: Color, second_color: Color) -> None:
        super().__init__(color, second_color)
        self.__w: float = 0
        self.local_width = width
        self._need_update()

    def get_local_size(self) -> Tuple[float, float]:
        return (self.local_width, self.local_width)

    def make(self) -> Surface:
        size: int = int(self.local_width)
        if size < 1:
            return create_surface((0, 0))
        start_color = (self.color.r, self.color.g, self.color.b, self.color.a)
        end_color = (self.second_color.r, self.second_color.g, self.second_color.b, self.second_color.a)
        return gradient_squared(size, start_color, end_color)  # type: ignore

    def get_local_vertices(self) -> List[Vector2]:
        w = h = self.local_width
        return [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]

    @property
    def local_width(self) -> float:
        return self.__w

    @local_width.setter
    def local_width(self, width: float) -> None:
        width = max(width, 0)
        if width != self.__w:
            self.__w = width
            self._need_update()


class RadialGradientShape(AbstractGradientShape):
    def __init__(self, radius: float, color: Color, second_color: Color) -> None:
        super().__init__(color, second_color)
        self.__radius: float = 0
        self.radius = radius
        self._need_update()

    def make(self) -> Surface:
        if self.radius == 0:
            return create_surface((0, 0))
        start_color = (self.color.r, self.color.g, self.color.b, self.color.a)
        end_color = (self.second_color.r, self.second_color.g, self.second_color.b, self.second_color.a)
        return gradient_radial(self.radius, start_color, end_color)  # type: ignore

    def get_local_size(self) -> Tuple[float, float]:
        return (self.radius * 2, self.radius * 2)

    def get_local_vertices(self) -> List[Vector2]:
        center: Vector2 = Vector2(self.radius, self.radius)
        radius: Vector2 = Vector2(self.radius, 0)
        return [center + radius.rotate(-i) for i in range(360)]

    @property
    def radius(self) -> float:
        return self.__radius

    @radius.setter
    def radius(self, radius: float) -> None:
        radius = max(radius, 0)
        if radius != self.__radius:
            self.__radius = radius
            self._need_update()
