# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Shape module"""

from __future__ import annotations

__all__ = [
    "AbstractCircleShape",
    "AbstractCrossShape",
    "AbstractRectangleShape",
    "AbstractShape",
    "CircleShape",
    "DiagonalCrossShape",
    "OutlinedShape",
    "PlusCrossShape",
    "PolygonShape",
    "RectangleShape",
    "ShapeMeta",
    "SingleColorShape",
]

from abc import abstractmethod
from math import radians, sin, tan
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, Sequence, TypeAlias, final

from pygame.transform import rotozoom as _surface_rotozoom, smoothscale as _surface_scale

from ..math import Vector2
from ..system.configuration import ConfigurationTemplate, OptionAttribute, UnregisteredOptionError, initializer
from ..system.utils.abc import concreteclass
from ..system.validation import valid_float, valid_integer
from .color import BLACK, Color
from .drawable import TDrawable, TDrawableMeta
from .rect import Rect
from .renderer import AbstractRenderer
from .surface import Surface, SurfaceRenderer, create_surface


class ShapeMeta(TDrawableMeta):
    pass


class AbstractShape(TDrawable, metaclass=ShapeMeta):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate()

    @initializer
    def __init__(self) -> None:
        TDrawable.__init__(self)
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
        self.__image = self._make(apply_rotation=True, apply_scale=False)

    def _apply_only_scale(self) -> None:
        self.__image = self._make(apply_rotation=False, apply_scale=True)

    def _freeze_state(self) -> dict[str, Any] | None:
        state = super()._freeze_state()
        if state is None:
            state = {}
        state["image"] = self.__image
        return state

    def _set_frozen_state(self, angle: float, scale: float, state: Mapping[str, Any] | None) -> bool:
        res = super()._set_frozen_state(angle, scale, state)
        if state is None:
            return res
        self.__image = state["image"]
        return True

    @staticmethod
    @final
    def compute_size_by_edges(edges: Sequence[tuple[float, float]] | Sequence[Vector2]) -> tuple[float, float]:
        if len(edges) < 2:
            return (0, 0)

        left: float = min((point[0] for point in edges))
        top: float = min((point[1] for point in edges))
        right: float = max((point[0] for point in edges))
        bottom: float = max((point[1] for point in edges))

        return (right - left + 1, bottom - top + 2)

    def __compute_shape_size(self) -> None:
        self.__local_size = AbstractShape.compute_size_by_edges(self.get_local_edges())

    @abstractmethod
    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        raise NotImplementedError

    @abstractmethod
    def get_local_edges(self) -> Sequence[Vector2]:
        raise NotImplementedError

    def get_edges(
        self,
        *,
        center: Vector2 | tuple[float, float] | None = None,
        apply_rotation: bool = True,
        apply_scale: bool = True,
    ) -> Sequence[Vector2]:
        angle: float = self.angle
        scale: float = self.scale
        all_points: Sequence[Vector2] = self.get_local_edges()
        if len(all_points) < 2 or (not apply_rotation and not apply_scale):
            return all_points
        edges: list[Vector2] = []

        left: float = min((point.x for point in all_points))
        top: float = min((point.y for point in all_points))
        right: float = max((point.x for point in all_points))
        bottom: float = max((point.y for point in all_points))
        w: float = right - left + 1
        h: float = bottom - top + 2

        local_center: Vector2 = Vector2(left + w / 2, top + h / 2)

        if center is None:
            try:
                center = Vector2(self.center)
            except AttributeError:
                center = local_center
        else:
            center = Vector2(center)

        for point in all_points:
            offset: Vector2 = point - local_center
            if apply_scale:
                try:
                    offset.scale_to_length(offset.length() * scale)
                except ValueError:
                    offset = Vector2(0, 0)
            if apply_rotation:
                offset.rotate_ip(-angle)
            edges.append(center + offset)

        return edges

    @config.add_main_update
    def __update_shape(self) -> None:
        self.__compute_shape_size()
        if self.config.has_initialization_context():
            self.apply_rotation_scale()
        else:
            center: tuple[float, float] = self.center
            self.apply_rotation_scale()
            self.center = center


class SingleColorShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("color", parent=AbstractShape.config)

    color: OptionAttribute[Color] = OptionAttribute()

    @initializer
    def __init__(self, *, color: Color, **kwargs: Any) -> None:
        self.color = color
        super().__init__(**kwargs)

    config.set_autocopy("color", copy_on_get=True, copy_on_set=True)
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

    config.set_autocopy("outline_color", copy_on_get=True, copy_on_set=True)
    config.add_value_converter_static("outline", valid_integer(min_value=0))
    config.add_value_validator_static("outline_color", Color)


@concreteclass
class PolygonShape(OutlinedShape, SingleColorShape):
    PointList: TypeAlias = Sequence[Vector2] | Sequence[tuple[float, float]] | Sequence[tuple[int, int]]

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "points",
        parent=[OutlinedShape.config, SingleColorShape.config],
    )

    points: OptionAttribute[Sequence[Vector2]] = OptionAttribute()

    @initializer
    def __init__(
        self,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        points: PointList = (),
    ) -> None:
        super().__init__(color=color, outline=outline, outline_color=outline_color)
        self.set_points(points)

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        outline: int = self.outline
        if apply_scale:
            outline = int(outline * self.scale)
        all_points: Sequence[Vector2] = self.get_edges(apply_rotation=apply_rotation, apply_scale=apply_scale)
        nb_points = len(all_points)

        if nb_points < 2:
            return create_surface((0, 0))

        PolygonShape.normalize_points(all_points)

        w, h = PolygonShape.compute_size_by_edges(all_points)
        if nb_points == 2 and outline < 1:
            return create_surface((w, h))
        image: SurfaceRenderer = SurfaceRenderer((w + outline * 2, h + outline * 2))

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

        return _surface_scale(image.surface.subsurface(rect), (w, h))

    @final
    def get_local_edges(self) -> Sequence[Vector2]:
        return self.points

    @final
    def set_points(self, points: PointList) -> None:
        self.config.set("points", points)

    config.set_autocopy("points", copy_on_get=True, copy_on_set=False)

    @config.add_value_converter_static("points")
    @staticmethod
    def __valid_points(points: PointList) -> tuple[Vector2, ...]:
        points = tuple(Vector2(p) for p in points)
        PolygonShape.normalize_points(points)
        return points

    @staticmethod
    @final
    def normalize_points(points: Sequence[Vector2]) -> None:
        if not points:
            return
        left: float = min((point.x for point in points))
        top: float = min((point.y for point in points))
        for p in points:
            p.x -= left
            p.y -= top


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
    def get_local_edges(self) -> tuple[Vector2, Vector2, Vector2, Vector2]:
        w, h = self.local_size
        return (Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h))

    @final
    def get_local_size(self) -> tuple[float, float]:
        return self.local_size

    config.add_value_converter_static("local_width", valid_float(min_value=0))
    config.add_value_converter_static("local_height", valid_float(min_value=0))
    config.add_value_converter_static("local_size", tuple)

    config.getter("local_size", lambda self: (self.local_width, self.local_height))
    config.setter("local_size", lambda self, size: self.config(local_width=size[0], local_height=size[1]))


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
    def get_local_edges(self) -> tuple[Vector2, Vector2, Vector2, Vector2]:
        w = h = self.local_size
        return (Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h))

    @final
    def get_local_size(self) -> tuple[float, float]:
        size = self.local_size
        return (size, size)

    config.add_value_converter_static("local_size", valid_float(min_value=0))


@concreteclass
class RectangleShape(AbstractRectangleShape, OutlinedShape, SingleColorShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
        parent=[AbstractRectangleShape.config, OutlinedShape.config, SingleColorShape.config],
    )

    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()

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
    ) -> None:
        super().__init__(
            width=width,
            height=height,
            color=color,
            outline=outline,
            outline_color=outline_color,
        )
        self.__draw_params: dict[str, int] = dict()
        self.border_radius = border_radius
        self.border_top_left_radius = border_top_left_radius
        self.border_top_right_radius = border_top_right_radius
        self.border_bottom_left_radius = border_bottom_left_radius
        self.border_bottom_right_radius = border_bottom_right_radius

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        outline: int = self.outline
        w, h = self.get_local_size()
        draw_params = self.__draw_params
        if apply_scale:
            scale: float = self.scale
            outline = int(outline * scale)
            w *= scale
            h *= scale
            draw_params = {param: round(value * scale) if value > 0 else value for param, value in draw_params.items()}
        image: SurfaceRenderer = SurfaceRenderer((w, h))
        rect: Rect = image.get_rect()
        image.draw_rect(self.color, rect, **draw_params)
        if outline > 0:
            image.draw_rect(self.outline_color, rect, width=outline, **draw_params)

        surface = image.surface
        if apply_rotation and (angle := self.angle) != 0:
            surface = _surface_rotozoom(surface, angle, 1)
        return surface

    config.add_value_converter_static("border_radius", valid_integer(min_value=-1))
    config.add_value_converter_static("border_top_left_radius", valid_integer(min_value=-1))
    config.add_value_converter_static("border_top_right_radius", valid_integer(min_value=-1))
    config.add_value_converter_static("border_bottom_left_radius", valid_integer(min_value=-1))
    config.add_value_converter_static("border_bottom_right_radius", valid_integer(min_value=-1))

    @config.getter_key("border_radius")
    @config.getter_key("border_top_left_radius")
    @config.getter_key("border_top_right_radius")
    @config.getter_key("border_bottom_left_radius")
    @config.getter_key("border_bottom_right_radius")
    def __get_border_radius(self, border: str) -> int:
        try:
            return self.__draw_params[border]
        except KeyError as exc:
            raise UnregisteredOptionError(border) from exc

    @config.setter_key("border_radius")
    @config.setter_key("border_top_left_radius")
    @config.setter_key("border_top_right_radius")
    @config.setter_key("border_bottom_left_radius")
    @config.setter_key("border_bottom_right_radius")
    def __set_border_radius(self, border: str, radius: int) -> None:
        self.__draw_params[border] = radius

    @property
    def params(self) -> MappingProxyType[str, int]:
        return MappingProxyType(self.__draw_params)


class AbstractCircleShape(AbstractShape):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("radius", parent=AbstractShape.config)

    radius: OptionAttribute[float] = OptionAttribute()

    @initializer
    def __init__(self, *, radius: float, **kwargs: Any) -> None:
        self.radius = radius
        super().__init__(**kwargs)

    def get_local_edges(self) -> Sequence[Vector2]:
        r: float = self.radius
        center: Vector2 = Vector2(r, r)
        radius: Vector2 = Vector2(r, 0)
        return tuple(center + radius.rotate(-i) for i in range(360))

    @final
    def get_local_size(self) -> tuple[float, float]:
        diameter: float = self.radius * 2
        return (diameter, diameter)

    config.add_value_converter_static("radius", valid_float(min_value=0))


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
    ) -> None:
        super().__init__(radius=radius, color=color, outline=outline, outline_color=outline_color)
        self.__draw_params: dict[str, bool] = dict()
        self.__points: tuple[Vector2, ...] = ()
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
            scale: float = self.scale
            outline = int(outline * scale)
            radius *= scale
            width *= scale
            height *= scale
        image: SurfaceRenderer = SurfaceRenderer((width, height))
        width, height = image.get_size()
        center: tuple[float, float] = (width / 2, height / 2)
        draw_params = self.__draw_params
        image.draw_circle(self.color, center, radius, **draw_params)
        if outline > 0:
            image.draw_circle(self.outline_color, center, radius, width=outline, **draw_params)
        surface = image.surface
        if apply_rotation and (angle := self.angle) != 0 and not all(drawn for drawn in draw_params.values()):
            surface = _surface_rotozoom(surface, angle, 1)
        return surface

    def get_local_edges(self) -> Sequence[Vector2]:
        return [v.copy() for v in self.__points]

    config.add_value_converter_static("draw_top_left", bool)
    config.add_value_converter_static("draw_top_right", bool)
    config.add_value_converter_static("draw_bottom_left", bool)
    config.add_value_converter_static("draw_bottom_right", bool)

    @config.getter_key("draw_top_left")
    @config.getter_key("draw_top_right")
    @config.getter_key("draw_bottom_left")
    @config.getter_key("draw_bottom_right")
    def __get_draw_arc(self, side: str) -> bool:
        try:
            return self.__draw_params[side]
        except KeyError as exc:
            raise UnregisteredOptionError(side) from exc

    @config.setter_key("draw_top_left")
    @config.setter_key("draw_top_right")
    @config.setter_key("draw_bottom_left")
    @config.setter_key("draw_bottom_right")
    def __set_draw_arc(self, side: str, status: bool) -> None:
        self.__draw_params[side] = status

    @config.on_update("draw_top_left")
    @config.on_update("draw_top_right")
    @config.on_update("draw_bottom_left")
    @config.on_update("draw_bottom_right")
    def __compute_edges(self) -> None:
        draw_params = self.__draw_params
        center: Vector2 = Vector2(self.radius, self.radius)
        if all(not drawn for drawn in draw_params.values()):
            self.__points = (center,)
            return

        radius: Vector2 = Vector2(self.radius, 0)

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

        self.__points = tuple(all_points)

    @property
    @final
    def params(self) -> MappingProxyType[str, bool]:
        return MappingProxyType(self.__draw_params)


class AbstractCrossShape(OutlinedShape, SingleColorShape):
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
    ) -> None:
        super().__init__(color=color, outline=outline, outline_color=outline_color)
        self.__points: tuple[Vector2, ...] = ()
        self.local_size = width, height
        self.line_width_percent = line_width_percent

    def _make(self, *, apply_rotation: bool, apply_scale: bool) -> Surface:
        outline: int = self.outline
        scale: float = self.scale
        if apply_scale:
            outline = int(outline * scale)
        all_points: Sequence[Vector2] = self.get_edges(apply_rotation=apply_rotation, apply_scale=apply_scale)
        if not all_points:
            return create_surface((0, 0))

        PolygonShape.normalize_points(all_points)

        w, h = PolygonShape.compute_size_by_edges(all_points)
        image: SurfaceRenderer = SurfaceRenderer((w + outline * 2, h + outline * 2))

        for p in all_points:
            p.x += outline
            p.y += outline

        rect = image.draw_polygon(self.color, all_points)
        if outline > 0:
            rect = image.draw_polygon(self.outline_color, all_points, width=outline)

        return _surface_scale(image.surface.subsurface(rect), (w, h))

    def get_local_size(self) -> tuple[float, float]:
        return self.local_size

    def get_local_edges(self) -> Sequence[Vector2]:
        return [v.copy() for v in self.__points]

    @staticmethod
    @abstractmethod
    def get_cross_points(local_size: tuple[float, float], line_width: float) -> tuple[Vector2, ...]:
        raise NotImplementedError

    config.add_value_converter_static("local_width", valid_float(min_value=0))
    config.add_value_converter_static("local_height", valid_float(min_value=0))
    config.add_value_converter_static("local_size", tuple)
    config.add_value_converter_static("line_width_percent", valid_float(min_value=0, max_value=1))

    config.getter("local_size", lambda self: (self.local_width, self.local_height))
    config.setter("local_size", lambda self, size: self.config(local_width=size[0], local_height=size[1]))

    @config.on_update("local_width")
    @config.on_update("local_height")
    @config.on_update("line_width_percent")
    def __compute_edges(self) -> None:
        local_width, local_height = local_size = self.local_size
        line_width_percent = self.line_width_percent
        line_width = min(local_width * line_width_percent, local_height * line_width_percent)
        self.__points = self.get_cross_points(local_size, line_width)


@concreteclass
class DiagonalCrossShape(AbstractCrossShape):
    @final
    @staticmethod
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
class PlusCrossShape(AbstractCrossShape):
    @final
    @staticmethod
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
