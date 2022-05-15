# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Gradient shapes module"""

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

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import Any, Sequence

from pygame.transform import rotate as _surface_rotate, smoothscale as _surface_scale

from ..system.configuration import ConfigurationTemplate, OptionAttribute, initializer
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
    config = ConfigurationTemplate("first_color", "second_color", parent=AbstractShape.config)

    first_color: OptionAttribute[Color] = OptionAttribute()
    second_color: OptionAttribute[Color] = OptionAttribute()

    @initializer
    def __init__(self, *, first_color: Color, second_color: Color, **kwargs: Any) -> None:
        self.first_color = first_color
        self.second_color = second_color
        super().__init__(**kwargs)

    config.add_value_validator_static("first_color", Color)
    config.add_value_validator_static("second_color", Color)


class HorizontalGradientShape(AbstractRectangleShape, GradientShape):
    config = ConfigurationTemplate(parent=[AbstractRectangleShape.config, GradientShape.config])

    @initializer
    def __init__(self, width: float, height: float, first_color: Color, second_color: Color) -> None:
        super().__init__(width=width, height=height, first_color=first_color, second_color=second_color)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        width, height = self.local_size
        if apply_scale:
            scale: float = self.scale
            width *= scale
            height *= scale
        size: tuple[int, int] = (int(width), int(height))
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        surface: Surface = _gradient_horizontal(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore[arg-type]
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface


class VerticalGradientShape(AbstractRectangleShape, GradientShape):
    config = ConfigurationTemplate(parent=[AbstractRectangleShape.config, GradientShape.config])

    @initializer
    def __init__(self, width: float, height: float, first_color: Color, second_color: Color) -> None:
        super().__init__(width=width, height=height, first_color=first_color, second_color=second_color)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        width, height = self.local_size
        if apply_scale:
            scale: float = self.scale
            width *= scale
            height *= scale
        size: tuple[int, int] = (int(width), int(height))
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        surface: Surface = _gradient_vertical(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore[arg-type]
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface


class SquaredGradientShape(AbstractSquareShape, GradientShape):
    config = ConfigurationTemplate(parent=[AbstractSquareShape.config, GradientShape.config])

    @initializer
    def __init__(self, size: float, first_color: Color, second_color: Color) -> None:
        super().__init__(size=size, first_color=first_color, second_color=second_color)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        size: int = int(self.local_size * self.scale if apply_scale else self.local_size)
        if size < 1:
            return create_surface((0, 0))
        surface: Surface = _gradient_squared(size, tuple(self.first_color), tuple(self.second_color))  # type: ignore[arg-type]
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface


class RadialGradientShape(AbstractCircleShape, GradientShape):
    config = ConfigurationTemplate(parent=[AbstractCircleShape.config, GradientShape.config])

    @initializer
    def __init__(self, radius: float, first_color: Color, second_color: Color) -> None:
        super().__init__(radius=radius, first_color=first_color, second_color=second_color)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        radius: int = int(self.radius * self.scale if apply_scale else self.radius)
        if radius < 1:
            return create_surface((0, 0))
        surface: Surface = _gradient_radial(radius, tuple(self.first_color), tuple(self.second_color))  # type: ignore[arg-type]
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface


class MultiColorShape(AbstractShape):
    config = ConfigurationTemplate("colors", parent=AbstractShape.config)

    colors: OptionAttribute[tuple[Color, ...]] = OptionAttribute()

    @initializer
    def __init__(self, *, colors: tuple[Color, ...], **kwargs: Any) -> None:
        self.colors = colors
        super().__init__(**kwargs)

    @config.add_value_validator_static("colors")
    @staticmethod
    def __valid_colors(value: Any) -> None:
        match value:
            case tuple() if all(isinstance(v, Color) for v in value) and len(value) >= 2:
                return
            case tuple():
                if len(value) < 2:
                    raise ValueError("Must have at least 2 colors")
                raise TypeError("Must be a tuple of Color")
            case _:
                raise TypeError("Invalid value type")


class HorizontalMultiColorShape(AbstractRectangleShape, MultiColorShape):
    config = ConfigurationTemplate(parent=[AbstractRectangleShape.config, MultiColorShape.config])

    @initializer
    def __init__(self, width: float, height: float, colors: tuple[Color, ...]) -> None:
        super().__init__(width=width, height=height, colors=colors)
        self.__shapes: Sequence[HorizontalGradientShape]

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        width, height = self.local_size
        renderer: SurfaceRenderer = SurfaceRenderer((width, height))
        for i, gradient in enumerate(self.__shapes):
            gradient.topleft = (gradient.width * i, 0)
            gradient.draw_onto(renderer)
        surface = renderer.surface
        if apply_scale:
            surface = _surface_scale(surface, (width * self.scale, height * self.scale))
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface

    @config.on_update_value("colors")
    def __update_shape(self, colors: tuple[Color, ...]) -> None:
        width, height = self.local_size
        gradient_width: float = round(width / (len(colors) - 1))
        gradient_height: float = height
        self.__shapes = tuple(
            HorizontalGradientShape(gradient_width, gradient_height, first_color=first_color, second_color=second_color)
            for first_color, second_color in zip(colors[:-1], colors[1:])
        )


class VerticalMultiColorShape(AbstractRectangleShape, MultiColorShape):
    config = ConfigurationTemplate(parent=[AbstractRectangleShape.config, MultiColorShape.config])

    @initializer
    def __init__(self, width: float, height: float, colors: tuple[Color, ...]) -> None:
        super().__init__(width=width, height=height, colors=colors)
        self.__shapes: Sequence[VerticalGradientShape]

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        width, height = self.local_size
        renderer: SurfaceRenderer = SurfaceRenderer((width, height))
        for i, gradient in enumerate(self.__shapes):
            gradient.topleft = (0, gradient.height * i)
            gradient.draw_onto(renderer)
        surface = renderer.surface
        if apply_scale:
            surface = _surface_scale(surface, (width * self.scale, height * self.scale))
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface

    @config.on_update_value("colors")
    def __update_shape(self, colors: tuple[Color, ...]) -> None:
        width, height = self.local_size
        gradient_width: float = width
        gradient_height: float = round(height / (len(colors) - 1))
        self.__shapes = tuple(
            VerticalGradientShape(gradient_width, gradient_height, first_color=first_color, second_color=second_color)
            for first_color, second_color in zip(colors[:-1], colors[1:])
        )
