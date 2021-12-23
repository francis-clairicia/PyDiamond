# -*- coding: Utf-8 -*

__all__ = [
    "GradientShape",
    "HorizontalGradientShape",
    "HorizontalMultiColorShape",
    "MultiColorShape",
    "RadialGradientShape",
    "SquaredGradientShape",
    "VerticalGradientShape",
    "VerticalMultiColorShape",
]

from typing import Any, Sequence, Tuple

from ..system.configuration import Configuration, OptionAttribute, initializer
from ._gradients import (  # type: ignore[attr-defined]
    horizontal as _gradient_horizontal,
    radial as _gradient_radial,
    squared as _gradient_squared,
    vertical as _gradient_vertical,
)
from .color import Color
from .renderer import SurfaceRenderer
from .shape import AbstractCircleShape, AbstractRectangleShape, AbstractShape, AbstractSquareShape
from .surface import Surface, create_surface


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


class SquaredGradientShape(AbstractSquareShape, GradientShape):
    @initializer
    def __init__(self, /, size: float, first_color: Color, second_color: Color) -> None:
        super().__init__(size=size, first_color=first_color, second_color=second_color)

    def _make(self, /) -> Surface:
        size: int = int(self.local_size)
        if size == 0:
            return create_surface((0, 0))
        return _gradient_squared(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore

    config = Configuration(parent=[AbstractSquareShape.config, GradientShape.config])


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


class MultiColorShape(AbstractShape):
    @initializer
    def __init__(self, /, *, colors: Tuple[Color, ...], **kwargs: Any) -> None:
        self.colors = colors
        super().__init__(**kwargs)

    config = Configuration("colors", parent=AbstractShape.config)

    colors: OptionAttribute[Tuple[Color, ...]] = OptionAttribute()

    @config.value_validator_static("colors")
    @staticmethod
    def __valid_colors(value: Any) -> None:
        value = tuple(value)
        if any(not isinstance(v, Color) for v in value):
            raise TypeError("Must be a tuple of Color")
        if len(value) < 2:
            raise ValueError("Must have at least 2 colors")


class HorizontalMultiColorShape(AbstractRectangleShape, MultiColorShape):
    @initializer
    def __init__(self, /, width: float, height: float, colors: Tuple[Color, ...]) -> None:
        super().__init__(width=width, height=height, colors=colors)
        self.__shapes: Sequence[HorizontalGradientShape]

    def _make(self, /) -> Surface:
        width, height = self.local_size
        renderer: SurfaceRenderer = SurfaceRenderer((width, height))
        for i, gradient in enumerate(self.__shapes):
            gradient.topleft = (gradient.width * i, 0)
            gradient.draw_onto(renderer)
        return renderer.surface

    config = Configuration(parent=[AbstractRectangleShape.config, MultiColorShape.config])

    @config.on_update_value("colors")
    def __update_shape(self, /, colors: Tuple[Color, ...]) -> None:
        width, height = self.local_size
        gradient_width: float = round(width / (len(colors) - 1))
        gradient_height: float = height
        self.__shapes = tuple(
            HorizontalGradientShape(gradient_width, gradient_height, first_color=first_color, second_color=second_color)
            for first_color, second_color in zip(colors[:-1], colors[1:])
        )


class VerticalMultiColorShape(AbstractRectangleShape, MultiColorShape):
    @initializer
    def __init__(self, /, width: float, height: float, colors: Tuple[Color, ...]) -> None:
        super().__init__(width=width, height=height, colors=colors)
        self.__shapes: Sequence[VerticalGradientShape]

    def _make(self, /) -> Surface:
        width, height = self.local_size
        renderer: SurfaceRenderer = SurfaceRenderer((width, height))
        for i, gradient in enumerate(self.__shapes):
            gradient.topleft = (0, gradient.height * i)
            gradient.draw_onto(renderer)
        return renderer.surface

    config = Configuration(parent=[AbstractRectangleShape.config, MultiColorShape.config])

    @config.on_update_value("colors")
    def __update_shape(self, /, colors: Tuple[Color, ...]) -> None:
        width, height = self.local_size
        gradient_width: float = width
        gradient_height: float = round(height / (len(colors) - 1))
        self.__shapes = tuple(
            VerticalGradientShape(gradient_width, gradient_height, first_color=first_color, second_color=second_color)
            for first_color, second_color in zip(colors[:-1], colors[1:])
        )
