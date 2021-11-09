# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Any, List, Tuple

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

__all__ = ["GradientShape", "HorizontalGradientShape", "VerticalGradientShape", "SquaredGradientShape", "RadialGradientShape"]


class GradientShape(AbstractShape):
    @initializer
    def __init__(self, /, *, first_color: Color, second_color: Color, **kwargs: Any) -> None:
        self.first_color = first_color
        self.second_color = second_color
        super().__init__(**kwargs)

    config = Configuration("first_color", "second_color", parent=AbstractShape.config)

    config.validator("first_color", Color)
    config.validator("second_color", Color)

    first_color: ConfigAttribute[Color] = ConfigAttribute()
    second_color: ConfigAttribute[Color] = ConfigAttribute()


class HorizontalGradientShape(AbstractRectangleShape, GradientShape):
    @initializer
    def __init__(self, /, width: float, height: float, first_color: Color, second_color: Color) -> None:
        super().__init__(width=width, height=height, first_color=first_color, second_color=second_color)

    def _make(self, /) -> Surface:
        size: Tuple[int, int] = (int(self.local_width), int(self.local_height))
        if size[0] == 0 or size[1] == 0:
            return create_surface(size)
        return _gradient_horizontal(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore

    config = Configuration(parent=[AbstractRectangleShape.config, GradientShape.config])


class VerticalGradientShape(AbstractRectangleShape, GradientShape):
    @initializer
    def __init__(self, /, width: float, height: float, first_color: Color, second_color: Color) -> None:
        super().__init__(width=width, height=height, first_color=first_color, second_color=second_color)

    def _make(self, /) -> Surface:
        size: Tuple[int, int] = (int(self.local_width), int(self.local_height))
        if size[0] == 0 or size[1] == 0:
            return create_surface(size)
        return _gradient_vertical(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore

    config = Configuration(parent=[AbstractRectangleShape.config, GradientShape.config])


@AbstractRectangleShape.register
class SquaredGradientShape(GradientShape):
    @initializer
    def __init__(self, /, width: float, first_color: Color, second_color: Color) -> None:
        super().__init__(first_color=first_color, second_color=second_color)
        self.local_width = width

    def _make(self, /) -> Surface:
        size: int = int(self.local_width)
        if size == 0:
            return create_surface((0, 0))
        return _gradient_squared(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore

    def get_local_vertices(self, /) -> List[Vector2]:
        w = h = self.local_width
        return [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]

    config = Configuration("local_width", parent=GradientShape.config)
    config.set_alias("local_width", "local_height")

    config.validator("local_width", no_object(valid_float(min_value=0)))

    local_width: ConfigAttribute[float] = ConfigAttribute()
    local_height: ConfigAttribute[float] = ConfigAttribute()

    @property
    def local_size(self, /) -> Tuple[float, float]:
        return (self.local_width, self.local_height)


class RadialGradientShape(AbstractCircleShape, GradientShape):
    @initializer
    def __init__(self, /, radius: float, first_color: Color, second_color: Color) -> None:
        super().__init__(radius=radius, first_color=first_color, second_color=second_color)

    def _make(self, /) -> Surface:
        radius: int = int(self.radius)
        if radius == 0:
            return create_surface((0, 0))
        return _gradient_radial(radius, tuple(self.first_color), tuple(self.second_color))  # type: ignore

    config = Configuration(parent=[AbstractCircleShape.config, GradientShape.config])
