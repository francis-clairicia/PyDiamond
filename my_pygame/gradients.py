# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import List, Tuple

from pygame.color import Color
from pygame.math import Vector2
from pygame.surface import Surface

from .shape import AbstractCircleShape, AbstractShape, AbstractRectangleShape
from .surface import create_surface
from .configuration import ConfigAttribute, Configuration, initializer, no_object
from .utils import valid_float

from ._gradients import (  # type: ignore[attr-defined]
    horizontal as _gradient_horizontal,
    vertical as _gradient_vertical,
    radial as _gradient_radial,
    squared as _gradient_squared,
)


class GradientShape(AbstractShape):
    @initializer
    def __init__(self, first_color: Color, second_color: Color) -> None:
        super().__init__()
        self.first_color = first_color
        self.second_color = second_color

    config = Configuration("first_color", "second_color", parent=AbstractShape.config)

    config.validator("first_color", Color)
    config.validator("second_color", Color)

    first_color: ConfigAttribute[Color] = ConfigAttribute()
    second_color: ConfigAttribute[Color] = ConfigAttribute()


class _AbstractRectangleGradientShape(AbstractRectangleShape, GradientShape):
    config = Configuration(parent=[AbstractRectangleShape.config, GradientShape.config])

    @initializer
    def __init__(self, width: float, height: float, first_color: Color, second_color: Color) -> None:
        AbstractRectangleShape.__init__(self, width, height)
        GradientShape.__init__(self, first_color, second_color)


class HorizontalGradientShape(_AbstractRectangleGradientShape):
    def copy(self) -> HorizontalGradientShape:
        return HorizontalGradientShape(self.local_width, self.local_height, self.first_color, self.second_color)

    def _make(self) -> Surface:
        size: Tuple[int, int] = (int(self.local_width), int(self.local_height))
        if size[0] == 0 or size[1] == 0:
            return create_surface(size)
        return _gradient_horizontal(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore


class VerticalGradientShape(_AbstractRectangleGradientShape):
    def copy(self) -> VerticalGradientShape:
        return VerticalGradientShape(self.local_width, self.local_height, self.first_color, self.second_color)

    def _make(self) -> Surface:
        size: Tuple[int, int] = (int(self.local_width), int(self.local_height))
        if size[0] == 0 or size[1] == 0:
            return create_surface(size)
        return _gradient_vertical(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore


class SquaredGradientShape(GradientShape):
    @initializer
    def __init__(self, width: float, first_color: Color, second_color: Color) -> None:
        super().__init__(first_color, second_color)
        self.local_width = width

    def copy(self) -> SquaredGradientShape:
        return SquaredGradientShape(self.local_width, self.first_color, self.second_color)

    def _make(self) -> Surface:
        size: int = int(self.local_width)
        if size == 0:
            return create_surface((0, 0))
        return _gradient_squared(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore

    def get_local_vertices(self) -> List[Vector2]:
        w = h = self.local_width
        return [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]

    config = Configuration("local_width", parent=GradientShape.config)

    config.validator("local_width", no_object(valid_float(min_value=0)))

    local_width: ConfigAttribute[float] = ConfigAttribute()


class RadialGradientShape(AbstractCircleShape, GradientShape):
    config = Configuration(parent=[AbstractCircleShape.config, GradientShape.config])

    @initializer
    def __init__(self, radius: float, first_color: Color, second_color: Color) -> None:
        AbstractCircleShape.__init__(self, radius)
        GradientShape.__init__(self, first_color, second_color)

    def copy(self) -> RadialGradientShape:
        return RadialGradientShape(self.radius, self.first_color, self.second_color)

    def _make(self) -> Surface:
        radius: int = int(self.radius)
        if radius == 0:
            return create_surface((0, 0))
        return _gradient_radial(radius, tuple(self.first_color), tuple(self.second_color))  # type: ignore
