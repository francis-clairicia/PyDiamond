# -*- coding: Utf-8 -*

__all__ = [
    "GradientShape",
    "HorizontalGradientShape",
    "RadialGradientShape",
    "SquaredGradientShape",
    "VerticalGradientShape",
]

from typing import Any, Sequence, Tuple

from .color import Color
from ..math import Vector2
from .shape import AbstractCircleShape, AbstractShape, AbstractRectangleShape
from .surface import Surface, create_surface
from ..system.configuration import OptionAttribute, Configuration, initializer
from ..system.utils import valid_float

from ._gradients import (  # type: ignore[attr-defined]
    horizontal as _gradient_horizontal,
    vertical as _gradient_vertical,
    radial as _gradient_radial,
    squared as _gradient_squared,
)


class GradientShape(AbstractShape):
    @initializer
    def __init__(self, /, *, first_color: Color, second_color: Color, **kwargs: Any) -> None:
        self.first_color = first_color
        self.second_color = second_color
        super().__init__(**kwargs)

    config = Configuration("first_color", "second_color", parent=AbstractShape.config)

    config.value_validator_static("first_color", Color)
    config.value_validator_static("second_color", Color)

    first_color: OptionAttribute[Color] = OptionAttribute()
    second_color: OptionAttribute[Color] = OptionAttribute()


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

    def get_local_vertices(self, /) -> Sequence[Vector2]:
        w = h = self.local_width
        return (Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h))

    config = Configuration("local_width", parent=GradientShape.config)
    config.set_alias("local_width", "local_height")

    config.value_converter_static("local_width", valid_float(min_value=0))

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()

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
