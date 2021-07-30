# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import List, Tuple

from pygame.color import Color
from pygame.math import Vector2
from pygame.surface import Surface

from .shape import AbstractCircleShape, AbstractShape, AbstractRectangleShape
from .surface import create_surface
from .colors import BLACK

from ._gradients import (  # type: ignore
    horizontal as _gradient_horizontal,
    vertical as _gradient_vertical,
    radial as _gradient_radial,
    squared as _gradient_squared,
)


class GradientShape(AbstractShape):
    def __init__(self, first_color: Color, second_color: Color) -> None:
        super().__init__()
        self.__first_color: Color = Color(BLACK)
        self.__second_color: Color = Color(BLACK)
        self.first_color = first_color
        self.second_color = second_color
        self._need_update()

    @property
    def first_color(self) -> Color:
        return self.__first_color

    @first_color.setter
    def first_color(self, color: Color) -> None:
        if self.__first_color != color:
            self.__first_color = Color(color)
            self._need_update()

    @property
    def second_color(self) -> Color:
        return self.__second_color

    @second_color.setter
    def second_color(self, color: Color) -> None:
        if self.__second_color != color:
            self.__second_color = Color(color)
            self._need_update()


class _AbstractRectangleGradientShape(AbstractRectangleShape, GradientShape):
    def __init__(self, width: float, height: float, first_color: Color, second_color: Color) -> None:
        AbstractRectangleShape.__init__(self, width, height)
        GradientShape.__init__(self, first_color, second_color)


class HorizontalGradientShape(_AbstractRectangleGradientShape):
    def copy(self) -> HorizontalGradientShape:
        return HorizontalGradientShape(self.local_width, self.local_height, self.first_color, self.second_color)

    def _make(self) -> Surface:
        size: Tuple[int, int] = (int(self.local_width), int(self.local_height))
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        return _gradient_horizontal(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore


class VerticalGradientShape(_AbstractRectangleGradientShape):
    def copy(self) -> VerticalGradientShape:
        return VerticalGradientShape(self.local_width, self.local_height, self.first_color, self.second_color)

    def _make(self) -> Surface:
        size: Tuple[int, int] = (int(self.local_width), int(self.local_height))
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        return _gradient_vertical(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore


class SquaredGradientShape(GradientShape):
    def __init__(self, width: float, first_color: Color, second_color: Color) -> None:
        super().__init__(first_color, second_color)
        self.__w: float = 0
        self.local_width = width
        self._need_update()

    def copy(self) -> SquaredGradientShape:
        return SquaredGradientShape(self.local_width, self.first_color, self.second_color)

    def _make(self) -> Surface:
        size: int = int(self.local_width)
        if size < 1:
            return create_surface((0, 0))
        return _gradient_squared(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore

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


class RadialGradientShape(AbstractCircleShape, GradientShape):
    def __init__(self, radius: float, first_color: Color, second_color: Color) -> None:
        AbstractCircleShape.__init__(self, radius)
        GradientShape.__init__(self, first_color, second_color)

    def copy(self) -> RadialGradientShape:
        return RadialGradientShape(self.radius, self.first_color, self.second_color)

    def _make(self) -> Surface:
        radius: int = int(self.radius)
        if radius < 1:
            return create_surface((0, 0))
        return _gradient_radial(radius, tuple(self.first_color), tuple(self.second_color))  # type: ignore
