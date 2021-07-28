# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import List, Tuple

from pygame.color import Color
from pygame.math import Vector2
from pygame.surface import Surface

from .shape import Shape
from .surface import create_surface

from ._gradients import (  # type: ignore
    horizontal as _gradient_horizontal,
    vertical as _gradient_vertical,
    radial as _gradient_radial,
    squared as _gradient_squared,
)


class GradientShape(Shape):
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
        if self.__second_color != color:
            self.__second_color = Color(color)
            self._need_update()


class _AbstractRectangleGradientShape(GradientShape):
    def __init__(self, width: float, height: float, color: Color, second_color: Color) -> None:
        super().__init__(color, second_color)
        self.__w: float = 0
        self.__h: float = 0
        self.local_size = width, height
        self._need_update()

    def get_local_vertices(self) -> List[Vector2]:
        w, h = self.local_size
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


class HorizontalGradientShape(_AbstractRectangleGradientShape):
    def copy(self) -> HorizontalGradientShape:
        return HorizontalGradientShape(self.local_width, self.local_height, self.color, self.second_color)

    def _make(self) -> Surface:
        size = self.local_size
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        return _gradient_horizontal(size, tuple(self.color), tuple(self.second_color))  # type: ignore


class VerticalGradientShape(_AbstractRectangleGradientShape):
    def copy(self) -> VerticalGradientShape:
        return VerticalGradientShape(self.local_width, self.local_height, self.color, self.second_color)

    def _make(self) -> Surface:
        size = self.local_size
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        return _gradient_vertical(size, tuple(self.color), tuple(self.second_color))  # type: ignore


class SquaredGradientShape(GradientShape):
    def __init__(self, width: float, color: Color, second_color: Color) -> None:
        super().__init__(color, second_color)
        self.__w: float = 0
        self.local_width = width
        self._need_update()

    def copy(self) -> SquaredGradientShape:
        return SquaredGradientShape(self.local_width, self.color, self.second_color)

    def _make(self) -> Surface:
        size: int = int(self.local_width)
        if size < 1:
            return create_surface((0, 0))
        return _gradient_squared(size, tuple(self.color), tuple(self.second_color))  # type: ignore

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


class RadialGradientShape(GradientShape):
    def __init__(self, radius: float, color: Color, second_color: Color) -> None:
        super().__init__(color, second_color)
        self.__radius: float = 0
        self.radius = radius
        self._need_update()

    def copy(self) -> RadialGradientShape:
        return RadialGradientShape(self.radius, self.color, self.second_color)

    def _make(self) -> Surface:
        if self.radius == 0:
            return create_surface((0, 0))
        return _gradient_radial(self.radius, tuple(self.color), tuple(self.second_color))  # type: ignore

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
