# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Gradient shapes module"""

from __future__ import annotations

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

from itertools import pairwise
from typing import Any, Callable, ClassVar, Sequence

from pygame.transform import rotate as _surface_rotate, smoothscale as _surface_scale

from ..system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ._gradients import (  # type: ignore[attr-defined]
    horizontal_func as _gradient_horizontal,
    radial_func as _gradient_radial,
    squared_func as _gradient_squared,
    vertical_func as _gradient_vertical,
)
from .color import Color
from .shape import AbstractCircleShape, AbstractRectangleShape, AbstractShape, AbstractSquareShape
from .surface import Surface, SurfaceRenderer, create_surface


class GradientShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "first_color",
        "second_color",
        parent=AbstractShape.config,
    )

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
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "rfunc",
        "gfunc",
        "bfunc",
        "afunc",
        parent=[AbstractRectangleShape.config, GradientShape.config],
    )

    rfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    gfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    bfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    afunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()

    @initializer
    def __init__(
        self,
        width: float,
        height: float,
        first_color: Color,
        second_color: Color,
        *,
        rfunc: Callable[[float], float] | None = None,
        gfunc: Callable[[float], float] | None = None,
        bfunc: Callable[[float], float] | None = None,
        afunc: Callable[[float], float] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(width=width, height=height, first_color=first_color, second_color=second_color, **kwargs)
        self.rfunc: Callable[[float], float] = rfunc or (lambda x: x)
        self.gfunc: Callable[[float], float] = gfunc or (lambda x: x)
        self.bfunc: Callable[[float], float] = bfunc or (lambda x: x)
        self.afunc: Callable[[float], float] = afunc or (lambda _: 1)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        width, height = self.local_size
        if apply_scale:
            scale_x, scale_y = self.scale
            width *= scale_x
            height *= scale_y
        size: tuple[int, int] = (int(width), int(height))
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        surface: Surface = _gradient_horizontal(
            size,
            tuple(self.first_color),  # type: ignore[arg-type]
            tuple(self.second_color),  # type: ignore[arg-type]
            Rfunc=self.rfunc,
            Gfunc=self.gfunc,
            Bfunc=self.bfunc,
            Afunc=self.afunc,
        )
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface

    config.add_value_validator_static("rfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("gfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("bfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("afunc", predicate=callable, exception=TypeError, message="Must be a callable")


class VerticalGradientShape(AbstractRectangleShape, GradientShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "rfunc",
        "gfunc",
        "bfunc",
        "afunc",
        parent=[AbstractRectangleShape.config, GradientShape.config],
    )

    rfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    gfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    bfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    afunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()

    @initializer
    def __init__(
        self,
        width: float,
        height: float,
        first_color: Color,
        second_color: Color,
        *,
        rfunc: Callable[[float], float] | None = None,
        gfunc: Callable[[float], float] | None = None,
        bfunc: Callable[[float], float] | None = None,
        afunc: Callable[[float], float] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(width=width, height=height, first_color=first_color, second_color=second_color, **kwargs)
        self.rfunc: Callable[[float], float] = rfunc or (lambda x: x)
        self.gfunc: Callable[[float], float] = gfunc or (lambda x: x)
        self.bfunc: Callable[[float], float] = bfunc or (lambda x: x)
        self.afunc: Callable[[float], float] = afunc or (lambda _: 1)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        width, height = self.local_size
        if apply_scale:
            scale_x, scale_y = self.scale
            width *= scale_x
            height *= scale_y
        size: tuple[int, int] = (int(width), int(height))
        if size[0] < 1 or size[1] < 1:
            return create_surface(size)
        surface: Surface = _gradient_vertical(
            size,
            tuple(self.first_color),  # type: ignore[arg-type]
            tuple(self.second_color),  # type: ignore[arg-type]
            Rfunc=self.rfunc,
            Gfunc=self.gfunc,
            Bfunc=self.bfunc,
            Afunc=self.afunc,
        )
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface

    config.add_value_validator_static("rfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("gfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("bfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("afunc", predicate=callable, exception=TypeError, message="Must be a callable")


class SquaredGradientShape(AbstractSquareShape, GradientShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "rfunc",
        "gfunc",
        "bfunc",
        "afunc",
        "center_offset",
        parent=[AbstractSquareShape.config, GradientShape.config],
    )

    rfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    gfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    bfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    afunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    center_offset: OptionAttribute[tuple[float, float]] = OptionAttribute()

    @initializer
    def __init__(
        self,
        size: float,
        first_color: Color,
        second_color: Color,
        *,
        rfunc: Callable[[float], float] | None = None,
        gfunc: Callable[[float], float] | None = None,
        bfunc: Callable[[float], float] | None = None,
        afunc: Callable[[float], float] | None = None,
        center_offset: tuple[float, float] = (0, 0),
        **kwargs: Any,
    ) -> None:
        super().__init__(size=size, first_color=first_color, second_color=second_color, **kwargs)
        self.rfunc: Callable[[float], float] = rfunc or (lambda x: x)
        self.gfunc: Callable[[float], float] = gfunc or (lambda x: x)
        self.bfunc: Callable[[float], float] = bfunc or (lambda x: x)
        self.afunc: Callable[[float], float] = afunc or (lambda _: 1)
        self.center_offset = center_offset

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        size: int = int(self.local_size * max(self.scale) if apply_scale else self.local_size)
        if size < 1:
            return create_surface((0, 0))
        surface: Surface = _gradient_squared(
            size,
            tuple(self.first_color),  # type: ignore[arg-type]
            tuple(self.second_color),  # type: ignore[arg-type]
            Rfunc=self.rfunc,
            Gfunc=self.gfunc,
            Bfunc=self.bfunc,
            Afunc=self.afunc,
            offset=self.center_offset,
        )
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface

    config.add_value_validator_static("rfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("gfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("bfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("afunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_converter_on_set_static("center_offset", tuple)


class RadialGradientShape(AbstractCircleShape, GradientShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "rfunc",
        "gfunc",
        "bfunc",
        "afunc",
        parent=[AbstractCircleShape.config, GradientShape.config],
    )

    rfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    gfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    bfunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()
    afunc: OptionAttribute[Callable[[float], float]] = OptionAttribute()

    @initializer
    def __init__(
        self,
        radius: float,
        first_color: Color,
        second_color: Color,
        *,
        rfunc: Callable[[float], float] | None = None,
        gfunc: Callable[[float], float] | None = None,
        bfunc: Callable[[float], float] | None = None,
        afunc: Callable[[float], float] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(radius=radius, first_color=first_color, second_color=second_color, **kwargs)
        self.rfunc: Callable[[float], float] = rfunc or (lambda x: x)
        self.gfunc: Callable[[float], float] = gfunc or (lambda x: x)
        self.bfunc: Callable[[float], float] = bfunc or (lambda x: x)
        self.afunc: Callable[[float], float] = afunc or (lambda _: 1)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        radius: int = int(self.radius * max(self.scale) if apply_scale else self.radius)
        if radius < 1:
            return create_surface((0, 0))
        surface: Surface = _gradient_radial(
            radius,
            tuple(self.first_color),  # type: ignore[arg-type]
            tuple(self.second_color),  # type: ignore[arg-type]
            Rfunc=self.rfunc,
            Gfunc=self.gfunc,
            Bfunc=self.bfunc,
            Afunc=self.afunc,
        )
        if apply_rotation:
            surface = _surface_rotate(surface, self.angle)
        return surface

    config.add_value_validator_static("rfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("gfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("bfunc", predicate=callable, exception=TypeError, message="Must be a callable")
    config.add_value_validator_static("afunc", predicate=callable, exception=TypeError, message="Must be a callable")


class MultiColorShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("colors", parent=AbstractShape.config)

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
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        parent=[AbstractRectangleShape.config, MultiColorShape.config]
    )

    @initializer
    def __init__(self, width: float, height: float, colors: tuple[Color, ...], **kwargs: Any) -> None:
        super().__init__(width=width, height=height, colors=colors, **kwargs)
        self.__shapes: Sequence[HorizontalGradientShape]

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        width, height = self.local_size
        renderer: SurfaceRenderer = SurfaceRenderer((width, height))
        for i, gradient in enumerate(self.__shapes):
            gradient.topleft = (gradient.width * i, 0)
            gradient.draw_onto(renderer)
        surface = renderer.surface
        if apply_scale:
            scale_x, scale_y = self.scale
            surface = _surface_scale(surface, (width * scale_x, height * scale_y))
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
            for first_color, second_color in pairwise(colors)
        )

    @config.on_update("local_size")
    @config.on_update("local_width")
    @config.on_update("local_height")
    def __update_shape_size(self) -> None:
        return self.config.update_option("colors")


class VerticalMultiColorShape(AbstractRectangleShape, MultiColorShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        parent=[AbstractRectangleShape.config, MultiColorShape.config]
    )

    @initializer
    def __init__(self, width: float, height: float, colors: tuple[Color, ...], **kwargs: Any) -> None:
        super().__init__(width=width, height=height, colors=colors, **kwargs)
        self.__shapes: Sequence[VerticalGradientShape]

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        width, height = self.local_size
        renderer: SurfaceRenderer = SurfaceRenderer((width, height))
        for i, gradient in enumerate(self.__shapes):
            gradient.topleft = (0, gradient.height * i)
            gradient.draw_onto(renderer)
        surface = renderer.surface
        if apply_scale:
            scale_x, scale_y = self.scale
            surface = _surface_scale(surface, (width * scale_x, height * scale_y))
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
            for first_color, second_color in pairwise(colors)
        )

    @config.on_update("local_size")
    @config.on_update("local_width")
    @config.on_update("local_height")
    def __update_shape_size(self) -> None:
        return self.config.update_option("colors")
