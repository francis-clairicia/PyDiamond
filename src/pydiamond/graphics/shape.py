# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Shape module"""

from __future__ import annotations

__all__ = [
    "AbstractCircleShape",
    "AbstractRectangleShape",
    "AbstractRoundedEdgeObject",
    "AbstractShape",
    "CircleShape",
    "DiagonalCrossShape",
    "OutlinedShape",
    "PlusCrossShape",
    "PolygonShape",
    "RectangleShape",
    "SingleColorShape",
]

from abc import abstractmethod
from math import radians, sin, tan
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Mapping, Sequence, TypeAlias, final

from pygame.transform import rotozoom as _surface_rotozoom, smoothscale as _surface_scale

from ..math import Rect, Vector2, compute_rect_from_vertices, compute_size_from_vertices, get_vertices_center, normalize_points
from ..system.configuration import ConfigurationTemplate, OptionAttribute, UnregisteredOptionError, initializer
from ..system.object import Object
from ..system.utils.abc import concreteclass
from ..system.validation import valid_float, valid_integer, valid_sequence
from .color import BLACK, Color
from .drawable import Drawable
from .renderer import AbstractRenderer
from .surface import Surface, SurfaceRenderer, create_surface
from .transformable import Transformable

_FPoint: TypeAlias = tuple[float, float]


class AbstractShape(Drawable, Transformable):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate()

    @initializer
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__image: Surface
        self.__local_size: tuple[float, float] = (0, 0)

    def draw_onto(self, target: AbstractRenderer) -> None:
        target.draw_surface(self.__image, self.topleft)

    def get_local_size(self) -> tuple[float, float]:
        return self.__local_size

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

    def _apply_both_rotation_and_scale(self) -> None:
        self.__compute_shape_size()
        self.__image = self._make(apply_rotation=True, apply_scale=True)

    def _apply_only_rotation(self) -> None:
        self.__compute_shape_size()
        self.__image = self._make(apply_rotation=True, apply_scale=False)

    def _apply_only_scale(self) -> None:
        self.__compute_shape_size()
        self.__image = self._make(apply_rotation=False, apply_scale=True)

    def _freeze_state(self) -> dict[str, Any] | None:
        state = super()._freeze_state()
        if state is None:
            state = {}
        state["image"] = self.__image
        return state

    def _set_frozen_state(self, angle: float, scale: tuple[float, float], state: Mapping[str, Any] | None) -> bool:
        res = super()._set_frozen_state(angle, scale, state)
        if state is None:
            return res
        self.__image = state["image"]
        return True

    def __compute_shape_size(self) -> None:
        self.__local_size = compute_size_from_vertices(self.get_local_vertices())

    @abstractmethod
    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        raise NotImplementedError

    @abstractmethod
    def get_local_vertices(self) -> Sequence[_FPoint]:
        raise NotImplementedError

    def get_vertices(
        self,
        *,
        center: Vector2 | _FPoint | None = None,
        apply_rotation: bool = True,
        apply_scale: bool = True,
    ) -> Sequence[Vector2]:
        angle: float = self.angle
        scale_x, scale_y = self.scale
        if scale_x <= 0 or scale_y <= 0:
            return []
        all_points: Sequence[_FPoint] = self.get_local_vertices()
        if len(all_points) < 2 or (not apply_rotation and not apply_scale):
            return [Vector2(point) for point in all_points]
        vertices: list[Vector2] = []

        local_center: Vector2 = get_vertices_center(all_points)

        if center is None:
            try:
                center = Vector2(self.center)
            except AttributeError:
                center = local_center
        else:
            center = Vector2(center)

        for point in all_points:
            offset: Vector2 = Vector2(point) - local_center
            if apply_scale:
                offset.x *= scale_x
                offset.y *= scale_y
            if apply_rotation:
                offset.rotate_ip(-angle)
            vertices.append(center + offset)

        return vertices

    @config.add_main_update(use_override=False)
    def __update_shape(self) -> None:
        if self.config.has_initialization_context():
            self.update_transform()
        else:
            center: tuple[float, float] = self.center
            self.update_transform()
            self.center = center

    del __update_shape


class SingleColorShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("color", parent=AbstractShape.config)

    color: OptionAttribute[Color] = OptionAttribute()

    @initializer
    def __init__(self, *, color: Color, **kwargs: Any) -> None:
        self.color = color
        super().__init__(**kwargs)

    config.add_value_validator_static("color", Color)


class OutlinedShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "outline",
        "outline_color",
        parent=AbstractShape.config,
    )

    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()

    @initializer
    def __init__(self, *, outline: int, outline_color: Color, **kwargs: Any) -> None:
        self.outline = outline
        self.outline_color = outline_color
        super().__init__(**kwargs)

    config.add_value_converter_on_set_static("outline", valid_integer(min_value=0))
    config.add_value_validator_static("outline_color", Color)


@concreteclass
class PolygonShape(OutlinedShape, SingleColorShape):
    PointList: TypeAlias = Sequence[Vector2] | Sequence[tuple[int | float, int | float]]

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "local_vertices",
        parent=[OutlinedShape.config, SingleColorShape.config],
    )

    local_vertices: OptionAttribute[tuple[_FPoint, ...]] = OptionAttribute()

    @initializer
    def __init__(
        self,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        vertices: PointList = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(color=color, outline=outline, outline_color=outline_color, **kwargs)
        self.set_vertices(vertices)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        outline: int = self.outline
        if apply_scale:
            outline = int(outline * max(self.scale))
        all_points: Sequence[Vector2] = self.get_vertices(apply_rotation=apply_rotation, apply_scale=apply_scale)
        nb_points = len(all_points)

        if nb_points < 2:
            return create_surface((0, 0))

        w, h = normalize_points(all_points)

        if nb_points == 2 and outline < 1:
            return create_surface((w, h))
        image: SurfaceRenderer = SurfaceRenderer.from_size((w + outline * 2, h + outline * 2))

        for p in all_points:
            p.x += outline
            p.y += outline

        rect: Rect
        if nb_points == 2:
            start, end = all_points
            rect = image.draw_line(self.outline_color, start, end, width=outline)
        else:
            rect = image.draw_polygon(self.color, all_points)
            if outline > 0:
                rect = image.draw_polygon(self.outline_color, all_points, width=outline)

        return _surface_scale(image.get_target().subsurface(rect), (w, h))

    @final
    def get_local_vertices(self) -> Sequence[_FPoint]:
        vertices: Sequence[_FPoint] = self.config.get("local_vertices")
        return vertices

    @final
    def set_local_vertices(self, vertices: PointList) -> None:
        self.config.set("local_vertices", vertices)

    @final
    def set_vertices(self, vertices: PointList) -> None:
        left, top, _, _ = compute_rect_from_vertices(vertices)
        self.config.set("local_vertices", vertices)
        self.topleft = (left, top)

    @config.add_value_converter_on_set_static("local_vertices")
    @staticmethod
    def __valid_points(vertices: PointList) -> tuple[_FPoint, ...]:
        vertices = tuple(Vector2(p) for p in vertices)
        normalize_points(vertices)
        return tuple((p.x, p.y) for p in vertices)

    del __valid_points


class AbstractRectangleShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "local_width",
        "local_height",
        "local_size",
        parent=AbstractShape.config,
    )

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[tuple[float, float]] = OptionAttribute()

    @initializer
    def __init__(self, *, width: float, height: float, **kwargs: Any) -> None:
        self.local_size = width, height
        super().__init__(**kwargs)

    @final
    def get_local_vertices(self) -> tuple[()] | tuple[_FPoint, _FPoint, _FPoint, _FPoint]:
        w, h = self.local_size
        if w < 1 or h < 1:
            return ()
        right = w - 1
        bottom = h - 1
        return ((0, 0), (right, 0), (right, bottom), (0, bottom))

    if TYPE_CHECKING:

        def get_vertices(
            self,
            *,
            center: Vector2 | _FPoint | None = ...,
            apply_rotation: bool = ...,
            apply_scale: bool = ...,
        ) -> tuple[()] | tuple[Vector2, Vector2, Vector2, Vector2]:
            ...

    @final
    def get_local_size(self) -> tuple[float, float]:
        return self.local_size

    config.add_value_converter_on_set_static("local_width", valid_float(min_value=0))
    config.add_value_converter_on_set_static("local_height", valid_float(min_value=0))
    config.add_value_converter_on_set_static("local_size", valid_sequence(length=2))

    config.getter("local_size", lambda self: (self.local_width, self.local_height), use_override=False)
    config.setter(
        "local_size", lambda self, size: self.config.update(local_width=size[0], local_height=size[1]), use_override=False
    )


class AbstractSquareShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("local_size", parent=AbstractShape.config)
    config.set_alias("local_size", "local_width", "local_height")

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[float] = OptionAttribute()

    @initializer
    def __init__(self, *, size: float, **kwargs: Any) -> None:
        self.local_size = size
        super().__init__(**kwargs)

    @final
    def get_local_vertices(self) -> tuple[()] | tuple[_FPoint, _FPoint, _FPoint, _FPoint]:
        size = self.local_size
        if size < 1:
            return ()
        right = bottom = size - 1
        return ((0, 0), (right, 0), (right, bottom), (0, bottom))

    if TYPE_CHECKING:

        def get_vertices(
            self,
            *,
            center: Vector2 | _FPoint | None = ...,
            apply_rotation: bool = ...,
            apply_scale: bool = ...,
        ) -> tuple[()] | tuple[Vector2, Vector2, Vector2, Vector2]:
            ...

    @final
    def get_local_size(self) -> tuple[float, float]:
        size = self.local_size
        return (size, size)

    config.add_value_converter_on_set_static("local_size", valid_float(min_value=0))


class AbstractRoundedEdgeObject(Object):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
    )

    @initializer
    def __init__(
        self,
        *,
        border_radius: int = -1,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.__border_params: dict[str, int] = dict()
        self.border_radius = border_radius
        self.border_top_left_radius = border_top_left_radius
        self.border_top_right_radius = border_top_right_radius
        self.border_bottom_left_radius = border_bottom_left_radius
        self.border_bottom_right_radius = border_bottom_right_radius

    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()

    config.add_value_converter_on_set_static("border_radius", valid_integer(min_value=-1))
    config.add_value_converter_on_set_static("border_top_left_radius", valid_integer(min_value=-1))
    config.add_value_converter_on_set_static("border_top_right_radius", valid_integer(min_value=-1))
    config.add_value_converter_on_set_static("border_bottom_left_radius", valid_integer(min_value=-1))
    config.add_value_converter_on_set_static("border_bottom_right_radius", valid_integer(min_value=-1))

    @config.getter_with_key("border_radius", use_override=False)
    @config.getter_with_key("border_top_left_radius", use_override=False)
    @config.getter_with_key("border_top_right_radius", use_override=False)
    @config.getter_with_key("border_bottom_left_radius", use_override=False)
    @config.getter_with_key("border_bottom_right_radius", use_override=False)
    def __get_border_radius(self, border: str) -> int:
        try:
            return self.__border_params[border]
        except KeyError as exc:
            raise UnregisteredOptionError(border) from exc

    @config.setter_with_key("border_radius", use_override=False)
    @config.setter_with_key("border_top_left_radius", use_override=False)
    @config.setter_with_key("border_top_right_radius", use_override=False)
    @config.setter_with_key("border_bottom_left_radius", use_override=False)
    @config.setter_with_key("border_bottom_right_radius", use_override=False)
    def __set_border_radius(self, border: str, radius: int) -> None:
        self.__border_params[border] = radius

    del __get_border_radius, __set_border_radius

    @property
    def border_params(self) -> MappingProxyType[str, int]:
        return MappingProxyType(self.__border_params)


@concreteclass
class RectangleShape(AbstractRectangleShape, OutlinedShape, SingleColorShape, AbstractRoundedEdgeObject):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        parent=[AbstractRectangleShape.config, OutlinedShape.config, SingleColorShape.config, AbstractRoundedEdgeObject.config],
    )

    @initializer
    def __init__(
        self,
        width: float,
        height: float,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        border_radius: int = -1,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            width=width,
            height=height,
            color=color,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            **kwargs,
        )

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        outline: int = self.outline
        w, h = self.local_size
        draw_params = dict(self.border_params)
        if apply_scale:
            scale_x, scale_y = self.scale
            outline = int(outline * max(scale_x, scale_y))
            w *= scale_x
            h *= scale_y
            draw_params = {
                param: round(value * max(scale_x, scale_y)) if value > 0 else value for param, value in draw_params.items()
            }
        image: SurfaceRenderer = SurfaceRenderer.from_size((w + 1, h + 1))
        rect: Rect = image.get_rect()
        image.draw_rect(self.color, rect, **draw_params)
        if outline > 0:
            image.draw_rect(self.outline_color, rect, width=outline, **draw_params)

        surface = image.get_target()
        if apply_rotation and (angle := self.angle) != 0:
            surface = _surface_rotozoom(surface, angle, 1)
        return surface


class AbstractCircleShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("radius", parent=AbstractShape.config)

    radius: OptionAttribute[float] = OptionAttribute()

    @initializer
    def __init__(self, *, radius: float, **kwargs: Any) -> None:
        self.radius = radius
        super().__init__(**kwargs)

    def get_local_vertices(self) -> Sequence[_FPoint]:
        r: float = self.radius
        if r < 1:
            return ()
        center: Vector2 = Vector2(r - 0.5, r - 0.5)
        radius: Vector2 = Vector2(r - 0.5, 0)
        gen = (center + radius.rotate(-i) for i in range(360))
        return tuple((p.x, p.y) for p in gen)

    @final
    def get_local_size(self) -> tuple[float, float]:
        diameter: float = self.radius * 2
        return (diameter, diameter)

    config.add_value_converter_on_set_static("radius", valid_float(min_value=0))


@concreteclass
class CircleShape(AbstractCircleShape, OutlinedShape, SingleColorShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "draw_top_left",
        "draw_top_right",
        "draw_bottom_left",
        "draw_bottom_right",
        parent=[AbstractCircleShape.config, OutlinedShape.config, SingleColorShape.config],
    )

    draw_top_left: OptionAttribute[bool] = OptionAttribute()
    draw_top_right: OptionAttribute[bool] = OptionAttribute()
    draw_bottom_left: OptionAttribute[bool] = OptionAttribute()
    draw_bottom_right: OptionAttribute[bool] = OptionAttribute()

    @initializer
    def __init__(
        self,
        radius: float,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        draw_top_left: bool = True,
        draw_top_right: bool = True,
        draw_bottom_left: bool = True,
        draw_bottom_right: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(radius=radius, color=color, outline=outline, outline_color=outline_color, **kwargs)
        self.__draw_params: dict[str, bool] = dict()
        self.__points: tuple[_FPoint, ...] = ()
        self.radius = radius
        self.draw_top_left = draw_top_left
        self.draw_top_right = draw_top_right
        self.draw_bottom_left = draw_bottom_left
        self.draw_bottom_right = draw_bottom_right

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        radius: float = self.radius
        outline: int = self.outline
        width, height = self.get_local_size()
        if apply_scale:
            scale: float = max(self.scale)
            outline = int(outline * scale)
            radius *= scale
            width *= scale
            height *= scale
        image: SurfaceRenderer = SurfaceRenderer.from_size((width, height))
        width, height = image.get_size()
        center: tuple[float, float] = (width / 2, height / 2)
        draw_params = self.__draw_params
        image.draw_circle(self.color, center, radius, **draw_params)
        if outline > 0:
            image.draw_circle(self.outline_color, center, radius, width=outline, **draw_params)
        surface = image.get_target()
        if apply_rotation and (angle := self.angle) != 0 and not all(drawn for drawn in draw_params.values()):
            surface = _surface_rotozoom(surface, angle, 1)
        return surface

    def get_local_vertices(self) -> Sequence[_FPoint]:
        return self.__points

    config.add_value_converter_on_set_static("draw_top_left", bool)
    config.add_value_converter_on_set_static("draw_top_right", bool)
    config.add_value_converter_on_set_static("draw_bottom_left", bool)
    config.add_value_converter_on_set_static("draw_bottom_right", bool)

    @config.getter_with_key("draw_top_left")
    @config.getter_with_key("draw_top_right")
    @config.getter_with_key("draw_bottom_left")
    @config.getter_with_key("draw_bottom_right")
    def __get_draw_arc(self, side: str) -> bool:
        try:
            return self.__draw_params[side]
        except KeyError as exc:
            raise UnregisteredOptionError(side) from exc

    @config.setter_with_key("draw_top_left")
    @config.setter_with_key("draw_top_right")
    @config.setter_with_key("draw_bottom_left")
    @config.setter_with_key("draw_bottom_right")
    def __set_draw_arc(self, side: str, status: bool) -> None:
        self.__draw_params[side] = status

    @config.on_update("draw_top_left")
    @config.on_update("draw_top_right")
    @config.on_update("draw_bottom_left")
    @config.on_update("draw_bottom_right")
    def __compute_vertices(self) -> None:
        draw_params = self.__draw_params
        center: Vector2 = Vector2(self.radius - 0.5, self.radius - 0.5)
        if all(not drawn for drawn in draw_params.values()):
            self.__points = ((center.x, center.y),)
            return

        radius: Vector2 = Vector2(self.radius - 0.5, 0)

        angle_ranges: dict[str, range] = {
            "draw_top_right": range(0, 90),
            "draw_top_left": range(90, 180),
            "draw_bottom_left": range(180, 270),
            "draw_bottom_right": range(270, 360),
        }

        all_points: list[Vector2] = []

        for draw_side, angle_range in angle_ranges.items():
            if draw_params[draw_side]:
                all_points.extend(center + radius.rotate(-i) for i in angle_range)
            elif not all_points or all_points[-1] != center:
                all_points.append(Vector2(center))

        self.__points = tuple((p.x, p.y) for p in all_points)

    @property
    @final
    def params(self) -> MappingProxyType[str, bool]:
        return MappingProxyType(self.__draw_params)


class _AbstractCrossShape(OutlinedShape, SingleColorShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "local_width",
        "local_height",
        "local_size",
        "line_width_percent",
        parent=[OutlinedShape.config, SingleColorShape.config],
    )

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[tuple[float, float]] = OptionAttribute()
    line_width_percent: OptionAttribute[float] = OptionAttribute()

    @initializer
    def __init__(
        self,
        width: float,
        height: float,
        color: Color,
        *,
        line_width_percent: float = 0.3,
        outline_color: Color = BLACK,
        outline: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(color=color, outline=outline, outline_color=outline_color, **kwargs)
        self.__points: tuple[_FPoint, ...] = ()
        self.local_size = width, height
        self.line_width_percent = line_width_percent

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        outline: int = self.outline
        if apply_scale:
            outline = int(outline * max(self.scale))
        all_points: Sequence[Vector2] = self.get_vertices(apply_rotation=apply_rotation, apply_scale=apply_scale)
        if not all_points:
            return create_surface((0, 0))

        w, h = normalize_points(all_points)

        image: SurfaceRenderer = SurfaceRenderer.from_size((w + outline * 2, h + outline * 2))

        for p in all_points:
            p.x += outline
            p.y += outline

        rect = image.draw_polygon(self.color, all_points)
        if outline > 0:
            rect = image.draw_polygon(self.outline_color, all_points, width=outline)

        return _surface_scale(image.get_target().subsurface(rect), (w, h))

    def get_local_size(self) -> tuple[float, float]:
        return self.local_size

    def get_local_vertices(self) -> Sequence[_FPoint]:
        return self.__points

    @staticmethod
    @abstractmethod
    def get_cross_points(local_size: tuple[float, float], line_width: float) -> tuple[Vector2, ...]:
        raise NotImplementedError

    config.add_value_converter_on_set_static("local_width", valid_float(min_value=0))
    config.add_value_converter_on_set_static("local_height", valid_float(min_value=0))
    config.add_value_converter_on_set_static("local_size", tuple)
    config.add_value_converter_on_set_static("line_width_percent", valid_float(min_value=0, max_value=1))

    config.getter("local_size", lambda self: (self.local_width, self.local_height), use_override=False)
    config.setter(
        "local_size", lambda self, size: self.config.update(local_width=size[0], local_height=size[1]), use_override=False
    )

    @config.on_update("local_width")
    @config.on_update("local_height")
    @config.on_update("line_width_percent")
    def __compute_vertices(self) -> None:
        local_width, local_height = local_size = self.local_size
        line_width_percent = self.line_width_percent
        line_width = min(local_width * line_width_percent, local_height * line_width_percent)
        self.__points = tuple((p.x, p.y) for p in self.get_cross_points(local_size, line_width))


@concreteclass
class DiagonalCrossShape(_AbstractCrossShape):
    @staticmethod
    @final
    def get_cross_points(local_size: tuple[float, float], line_width: float) -> tuple[Vector2, ...]:
        rect: Rect = Rect((0, 0), local_size)

        if line_width <= 0:
            return ()
        line_width /= 2

        w_offset: float = DiagonalCrossShape.__compute_diagonal_width_offset(local_size, line_width)
        h_offset: float = DiagonalCrossShape.__compute_diagonal_height_offset(local_size, line_width)
        if w_offset == 0 or h_offset == 0:
            return ()
        return (
            Vector2(rect.left, rect.top),
            Vector2(rect.left + w_offset, rect.top),
            Vector2(rect.centerx, rect.centery - h_offset),
            Vector2(rect.right - w_offset, rect.top),
            Vector2(rect.right, rect.top),
            Vector2(rect.right, rect.top + h_offset),
            Vector2(rect.centerx + w_offset, rect.centery),
            Vector2(rect.right, rect.bottom - h_offset),
            Vector2(rect.right, rect.bottom),
            Vector2(rect.right - w_offset, rect.bottom),
            Vector2(rect.centerx, rect.centery + h_offset),
            Vector2(rect.left + w_offset, rect.bottom),
            Vector2(rect.left, rect.bottom),
            Vector2(rect.left, rect.bottom - h_offset),
            Vector2(rect.centerx - w_offset, rect.centery),
            Vector2(rect.left, rect.top + h_offset),
        )

    @staticmethod
    def __compute_diagonal_width_offset(local_size: tuple[float, float], half_line_width: float) -> float:
        diagonal: Vector2 = Vector2((0, local_size[0])) - Vector2((local_size[1], 0))
        alpha: float = radians(diagonal.rotate(90).angle_to(Vector2(-1, 0)))
        try:
            return tan(alpha) * half_line_width / sin(alpha)
        except ZeroDivisionError:
            return 0

    @staticmethod
    def __compute_diagonal_height_offset(local_size: tuple[float, float], half_line_width: float) -> float:
        diagonal: Vector2 = Vector2((0, local_size[0])) - Vector2((local_size[1], 0))
        alpha: float = radians(diagonal.rotate(-90).angle_to(Vector2(0, 1)))
        try:
            return tan(alpha) * half_line_width / sin(alpha)
        except ZeroDivisionError:
            return 0


@concreteclass
class PlusCrossShape(_AbstractCrossShape):
    @staticmethod
    @final
    def get_cross_points(local_size: tuple[float, float], line_width: float) -> tuple[Vector2, ...]:
        rect: Rect = Rect((0, 0), local_size)

        if line_width <= 0:
            return ()
        line_width /= 2
        return (
            Vector2(rect.centerx - line_width, rect.top),
            Vector2(rect.centerx + line_width, rect.top),
            Vector2(rect.centerx + line_width, rect.centery - line_width),
            Vector2(rect.right, rect.centery - line_width),
            Vector2(rect.right, rect.centery + line_width),
            Vector2(rect.centerx + line_width, rect.centery + line_width),
            Vector2(rect.centerx + line_width, rect.bottom),
            Vector2(rect.centerx - line_width, rect.bottom),
            Vector2(rect.centerx - line_width, rect.centery + line_width),
            Vector2(rect.left, rect.centery + line_width),
            Vector2(rect.left, rect.centery - line_width),
            Vector2(rect.centerx - line_width, rect.centery - line_width),
        )
