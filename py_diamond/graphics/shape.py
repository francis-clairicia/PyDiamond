# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Shape module"""

__all__ = [
    "AbstractCircleShape",
    "AbstractRectangleShape",
    "AbstractShape",
    "CircleShape",
    "CrossShape",
    "DiagonalCrossShape",
    "OutlinedShape",
    "PlusCrossShape",
    "PolygonShape",
    "RectangleShape",
    "ShapeMeta",
    "SingleColorShape",
    "ThemedShapeMeta",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from enum import auto, unique
from math import radians, sin, tan
from operator import truth
from types import MappingProxyType
from typing import Any, Sequence, TypeAlias

from pygame.transform import rotate as _surface_rotate, rotozoom as _surface_rotozoom

from ..math import Vector2
from ..system._mangling import getattr_pv
from ..system.configuration import ConfigurationTemplate, OptionAttribute, UnregisteredOptionError, initializer
from ..system.enum import AutoLowerNameEnum
from ..system.utils import valid_float, valid_integer
from .color import BLACK, Color
from .drawable import TDrawable, TDrawableMeta
from .rect import Rect
from .renderer import AbstractRenderer, SurfaceRenderer
from .surface import Surface, create_surface
from .theme import ThemedObjectMeta, ThemeType


class ShapeMeta(TDrawableMeta):
    pass


class ThemedShapeMeta(ShapeMeta, ThemedObjectMeta):
    pass


class AbstractShape(TDrawable, metaclass=ShapeMeta):
    config = ConfigurationTemplate(autocopy=True)

    def __init__(self) -> None:
        TDrawable.__init__(self)
        self.__image: Surface = create_surface((0, 0))
        self.__shape_image: Surface = self.__image.copy()
        self.__local_size: tuple[float, float] = (0, 0)

    def draw_onto(self, target: AbstractRenderer) -> None:
        image: Surface = self.__image
        center: tuple[float, float] = self.center
        target.draw_surface(image, image.get_rect(center=center))

    def get_local_size(self) -> tuple[float, float]:
        return self.__local_size

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

    def _apply_both_rotation_and_scale(self) -> None:
        angle: float = self.angle
        scale: float = self.scale
        self.__image = _surface_rotozoom(self.__shape_image, angle, scale)

    def _apply_only_rotation(self) -> None:
        angle: float = self.angle
        self.__image = _surface_rotate(self.__shape_image, angle)

    def _apply_only_scale(self) -> None:
        scale: float = self.scale
        self.__image = _surface_rotozoom(self.__shape_image, 0, scale)

    def __compute_shape_size(self) -> None:
        all_points: Sequence[Vector2] = self.get_local_vertices()

        if not all_points:
            self.__local_size = (0, 0)
            return

        left: float = min((point.x for point in all_points), default=0)
        top: float = min((point.y for point in all_points), default=0)
        right: float = max((point.x for point in all_points), default=0)
        bottom: float = max((point.y for point in all_points), default=0)
        w: float = right - left
        h: float = bottom - top
        self.__local_size = (w, h)

    @abstractmethod
    def _make(self) -> Surface:
        raise NotImplementedError

    @abstractmethod
    def get_local_vertices(self) -> Sequence[Vector2]:
        raise NotImplementedError

    def get_vertices(self) -> Sequence[Vector2]:
        angle: float = self.angle
        scale: float = self.scale
        all_points: Sequence[Vector2] = self.get_local_vertices()
        vertices: list[Vector2] = []

        if all_points:
            left: float = min((point.x for point in all_points), default=0)
            top: float = min((point.y for point in all_points), default=0)
            right: float = max((point.x for point in all_points), default=0)
            bottom: float = max((point.y for point in all_points), default=0)
            w: float = right - left
            h: float = bottom - top

            local_center: Vector2 = Vector2(left + w / 2, top + h / 2)

            center: Vector2 = Vector2(self.center)
            for point in all_points:
                offset: Vector2 = (point - local_center).rotate(-angle)
                try:
                    offset.scale_to_length(offset.length() * scale)
                except ValueError:
                    offset = Vector2(0, 0)
                vertices.append(center + offset)

        return tuple(vertices)

    @config.add_main_update
    def __update_shape(self) -> None:
        if self.config.has_initialization_context():
            self.__compute_shape_size()
            self.__shape_image = self._make()
            self.apply_rotation_scale()
        else:
            center: tuple[float, float] = self.center
            self.__compute_shape_size()
            self.__shape_image = self._make()
            self.apply_rotation_scale()
            self.center = center


class SingleColorShape(AbstractShape):
    config = ConfigurationTemplate("color", parent=AbstractShape.config)

    color: OptionAttribute[Color] = OptionAttribute()

    @initializer
    def __init__(self, *, color: Color, **kwargs: Any) -> None:
        self.color = color
        super().__init__(**kwargs)

    config.add_value_validator_static("color", Color)


class OutlinedShape(AbstractShape):
    config = ConfigurationTemplate("outline", "outline_color", parent=AbstractShape.config)

    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()

    @initializer
    def __init__(self, *, outline: int, outline_color: Color, **kwargs: Any) -> None:
        self.outline = outline
        self.outline_color = outline_color
        super().__init__(**kwargs)

    def get_local_size(self) -> tuple[float, float]:
        w, h = super().get_local_size()
        if self.outline == 0:
            return (w, h)
        return (w + 1, h + 1)

    config.add_value_converter_static("outline", valid_integer(min_value=0))
    config.add_value_validator_static("outline_color", Color)


class PolygonShape(OutlinedShape, SingleColorShape, metaclass=ThemedShapeMeta):
    PointList: TypeAlias = Sequence[Vector2] | Sequence[tuple[float, float]] | Sequence[tuple[int, int]]

    config = ConfigurationTemplate("points", parent=[OutlinedShape.config, SingleColorShape.config])

    points: OptionAttribute[Sequence[Vector2]] = OptionAttribute()

    @initializer
    def __init__(
        self,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        points: PointList = (),
        theme: ThemeType | None = None,
    ) -> None:
        super().__init__(color=color, outline=outline, outline_color=outline_color)
        self.__center: Vector2 = Vector2(0, 0)
        self.set_points(points)

    def _make(self) -> Surface:
        outline: int = self.outline
        all_points: Sequence[Vector2] = self.points

        if len(all_points) < 2:
            return create_surface((0, 0))

        w, h = self.get_local_size()
        image: SurfaceRenderer = SurfaceRenderer((w, h))

        center_diff: Vector2 = Vector2(w / 2, h / 2) - self.__center
        for p in all_points:
            p.x += center_diff.x
            p.y += center_diff.y

        if len(all_points) == 2:
            if outline > 0:
                start, end = all_points
                image.draw_line(self.outline_color, start, end, width=outline)
        else:
            image.draw_polygon(self.color, all_points)
            if outline > 0:
                image.draw_polygon(self.outline_color, all_points, width=outline)

        return image.surface

    def get_local_vertices(self) -> Sequence[Vector2]:
        return self.points

    def set_points(self, points: PointList) -> None:
        self.config.set("points", points)

    @config.add_value_converter_static("points")
    @staticmethod
    def __valid_points(points: PointList) -> tuple[Vector2, ...]:
        points = [Vector2(p) for p in points]
        left: float = min((point.x for point in points), default=0)
        top: float = min((point.y for point in points), default=0)
        for p in points:
            p.x -= left
            p.y -= top
        return tuple(points)

    @config.on_update_value("points")
    def __on_update_points(self, points: Sequence[Vector2]) -> None:
        left: float = 0
        top: float = 0
        right: float = max((point.x for point in points), default=0)
        bottom: float = max((point.y for point in points), default=0)
        w: float = right - left
        h: float = bottom - top

        self.__center = Vector2(left + w / 2, top + h / 2)


class AbstractRectangleShape(AbstractShape):
    config = ConfigurationTemplate("local_width", "local_height", "local_size", parent=AbstractShape.config)

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[tuple[float, float]] = OptionAttribute()

    @initializer
    def __init__(self, *, width: float, height: float, **kwargs: Any) -> None:
        self.local_size = width, height
        super().__init__(**kwargs)

    def get_local_vertices(self) -> tuple[Vector2, Vector2, Vector2, Vector2]:
        w, h = self.local_size
        return (Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h))

    config.add_value_converter_static("local_width", valid_float(min_value=0))
    config.add_value_converter_static("local_height", valid_float(min_value=0))
    config.add_value_converter_static("local_size", tuple)

    config.getter("local_size", lambda self: (self.local_width, self.local_height))
    config.setter("local_size", lambda self, size: self.config(local_width=size[0], local_height=size[1]))


class AbstractSquareShape(AbstractShape):
    config = ConfigurationTemplate("local_size", parent=AbstractShape.config)
    config.set_alias("local_size", "local_width", "local_height")

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[float] = OptionAttribute()

    @initializer
    def __init__(self, *, size: float, **kwargs: Any) -> None:
        self.local_size = size
        super().__init__(**kwargs)

    def get_local_vertices(self) -> tuple[Vector2, Vector2, Vector2, Vector2]:
        w = h = self.local_size
        return (Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h))

    config.add_value_converter_static("local_size", valid_float(min_value=0))


class RectangleShape(AbstractRectangleShape, OutlinedShape, SingleColorShape, metaclass=ThemedShapeMeta):
    config = ConfigurationTemplate(
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
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: ThemeType | None = None,
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

    def _make(self) -> Surface:
        outline: int = self.outline
        w: float = self.local_width
        h: float = self.local_height
        image: SurfaceRenderer = SurfaceRenderer(self.get_local_size())
        rect: Rect = Rect(0, 0, w, h)
        draw_params = self.__draw_params
        image.draw_rect(self.color, rect, **draw_params)
        if outline > 0:
            image.draw_rect(self.outline_color, rect, width=outline, **draw_params)
        return image.surface

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
    config = ConfigurationTemplate("radius", parent=AbstractShape.config)

    radius: OptionAttribute[float] = OptionAttribute()

    @initializer
    def __init__(self, *, radius: float, **kwargs: Any) -> None:
        self.radius = radius
        super().__init__(**kwargs)

    def get_local_vertices(self) -> Sequence[Vector2]:
        r: float = self.radius
        center: Vector2 = Vector2(r, r)
        radius: Vector2 = Vector2(r, 0)
        return tuple(center + radius.rotate(-i) for i in range(360))

    config.add_value_converter_static("radius", valid_float(min_value=0))


class CircleShape(AbstractCircleShape, OutlinedShape, SingleColorShape, metaclass=ThemedShapeMeta):
    config = ConfigurationTemplate(
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
        theme: ThemeType | None = None,
    ) -> None:
        super().__init__(radius=radius, color=color, outline=outline, outline_color=outline_color)
        self.__draw_params: dict[str, bool] = dict()
        self.__points: tuple[Vector2, ...] = ()
        self.radius = radius
        self.draw_top_left = draw_top_left
        self.draw_top_right = draw_top_right
        self.draw_bottom_left = draw_bottom_left
        self.draw_bottom_right = draw_bottom_right

    def _make(self) -> Surface:
        radius: float = self.radius
        outline: int = self.outline
        width, height = self.get_local_size()
        image: SurfaceRenderer = SurfaceRenderer((width, height))
        width, height = image.get_size()
        center: tuple[float, float] = (width / 2, height / 2)
        draw_params = self.__draw_params
        image.draw_circle(self.color, center, radius, **draw_params)
        if outline > 0:
            image.draw_circle(self.outline_color, center, radius, width=outline, **draw_params)
        return image.surface

    def get_local_vertices(self) -> Sequence[Vector2]:
        return self.__points

    config.add_value_converter_static("draw_top_left", truth)
    config.add_value_converter_static("draw_top_right", truth)
    config.add_value_converter_static("draw_bottom_left", truth)
    config.add_value_converter_static("draw_bottom_right", truth)

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
    def __compute_vertices(self) -> None:
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
    def params(self) -> MappingProxyType[str, bool]:
        return MappingProxyType(self.__draw_params)


class CrossShape(OutlinedShape, SingleColorShape, metaclass=ThemedShapeMeta):
    config = ConfigurationTemplate(
        "local_width",
        "local_height",
        "local_size",
        "line_width",
        parent=[OutlinedShape.config, SingleColorShape.config],
    )

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[tuple[float, float]] = OptionAttribute()
    line_width: OptionAttribute[float] = OptionAttribute()

    @unique
    class Type(AutoLowerNameEnum):
        DIAGONAL = auto()
        PLUS = auto()

    @initializer
    def __init__(
        self,
        width: float,
        height: float,
        color: Color,
        type: str,
        *,
        line_width: float = 0.3,
        outline_color: Color = BLACK,
        outline: int = 0,
        theme: ThemeType | None = None,
    ) -> None:
        super().__init__(color=color, outline=outline, outline_color=outline_color)
        self.__type: CrossShape.Type = CrossShape.Type(type)
        self.__points: tuple[Vector2, ...] = ()
        self.local_size = width, height
        self.line_width = line_width

    def _make(self) -> Surface:
        p = PolygonShape(
            self.color,
            outline=self.outline,
            outline_color=self.outline_color,
            points=self.__points,
        )
        image: Surface = getattr_pv(p, "image", owner=AbstractShape)
        return image

    def get_local_vertices(self) -> Sequence[Vector2]:
        return self.__points

    def __get_diagonal_cross_points(self) -> tuple[Vector2, ...]:
        rect: Rect = Rect((0, 0), self.local_size)
        line_width: float = self.line_width

        line_width = min(self.local_width * line_width, self.local_height * line_width) / 2
        if line_width == 0:
            return ()

        diagonal: Vector2 = Vector2(rect.bottomleft) - Vector2(rect.topright)

        def compute_width_offset() -> float:
            alpha: float = radians(diagonal.rotate(90).angle_to(Vector2(-1, 0)))
            try:
                return tan(alpha) * (line_width) / sin(alpha)
            except ZeroDivisionError:
                return 0

        def compute_height_offset() -> float:
            alpha: float = radians(diagonal.rotate(-90).angle_to(Vector2(0, 1)))
            try:
                return tan(alpha) * (line_width) / sin(alpha)
            except ZeroDivisionError:
                return 0

        w_offset: float = compute_width_offset()
        h_offset: float = compute_height_offset()
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

    def __get_plus_cross_points(self) -> tuple[Vector2, ...]:
        rect: Rect = self.get_local_rect()
        line_width: float = self.line_width

        line_width = min(self.local_width * line_width, self.local_height * line_width) / 2
        if line_width == 0:
            return ()
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

    config.add_value_converter_static("local_width", valid_float(min_value=0))
    config.add_value_converter_static("local_height", valid_float(min_value=0))
    config.add_value_converter_static("local_size", tuple)
    config.add_value_converter_static("line_width", valid_float(min_value=0))

    @property
    def type(self) -> str:
        return str(self.__type.value)

    config.getter("local_size", lambda self: (self.local_width, self.local_height))
    config.setter("local_size", lambda self, size: self.config(local_width=size[0], local_height=size[1]))

    @config.on_update("local_width")
    @config.on_update("local_height")
    @config.on_update("local_size")
    @config.on_update("line_width")
    def __compute_vertices(self) -> None:
        compute_vertices = {
            CrossShape.Type.DIAGONAL: self.__get_diagonal_cross_points,
            CrossShape.Type.PLUS: self.__get_plus_cross_points,
        }
        self.__points = compute_vertices[self.__type]()


class DiagonalCrossShape(CrossShape):
    def __init__(
        self,
        width: float,
        height: float,
        color: Color,
        *,
        line_width: float = 0.3,
        outline_color: Color = BLACK,
        outline: int = 0,
        theme: ThemeType | None = None,
    ) -> None:
        super().__init__(
            width,
            height,
            color,
            CrossShape.Type.DIAGONAL,
            line_width=line_width,
            outline_color=outline_color,
            outline=outline,
            theme=theme,
        )


class PlusCrossShape(CrossShape):
    def __init__(
        self,
        width: float,
        height: float,
        color: Color,
        *,
        line_width: float = 0.3,
        outline_color: Color = BLACK,
        outline: int = 0,
        theme: ThemeType | None = None,
    ) -> None:
        super().__init__(
            width,
            height,
            color,
            CrossShape.Type.PLUS,
            line_width=line_width,
            outline_color=outline_color,
            outline=outline,
            theme=theme,
        )
