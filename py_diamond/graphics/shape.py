# -*- coding: Utf-8 -*

__all__ = [
    "AbstractCircleShape",
    "AbstractRectangleShape",
    "AbstractShape",
    "CircleShape",
    "CrossShape",
    "DiagonalCrossShape",
    "MetaShape",
    "MetaThemedShape",
    "OutlinedShape",
    "PlusCrossShape",
    "PolygonShape",
    "RectangleShape",
    "Shape",
]

from abc import abstractmethod
from operator import truth
from typing import Any, Dict, List, Optional, Tuple, Union
from math import sin, tan, radians
from enum import Enum, unique

import pygame.transform

from .color import Color, BLACK
from .drawable import TDrawable, MetaTDrawable
from ..math import Vector2
from .renderer import Renderer, SurfaceRenderer
from .rect import Rect
from .surface import Surface, create_surface
from ..system.configuration import (
    ConfigAttribute,
    ConfigTemplate,
    Configuration,
    UnregisteredOptionError,
    initializer,
)
from ..system.utils import valid_float, valid_integer
from .theme import MetaThemedObject, ThemeType


class MetaShape(MetaTDrawable):
    pass


class MetaThemedShape(MetaShape, MetaThemedObject):
    pass


class AbstractShape(TDrawable, metaclass=MetaShape):
    def __init__(self, /) -> None:
        TDrawable.__init__(self)
        self.__image: Surface = create_surface((0, 0))
        self.__shape_image: Surface = self.__image.copy()
        self.__local_size: Tuple[float, float] = (0, 0)

    def draw_onto(self, /, target: Renderer) -> None:
        image: Surface = self.__image
        center: Tuple[float, float] = self.center
        target.draw(image, image.get_rect(center=center))

    def get_local_size(self, /) -> Tuple[float, float]:
        return self.__local_size

    def get_size(self, /) -> Tuple[float, float]:
        return self.__image.get_size()

    def _apply_both_rotation_and_scale(self, /) -> None:
        angle: float = self.angle
        scale: float = self.scale
        self.__image = pygame.transform.rotozoom(self.__shape_image, angle, scale)

    def _apply_only_rotation(self, /) -> None:
        angle: float = self.angle
        self.__image = pygame.transform.rotate(self.__shape_image, angle)

    def _apply_only_scale(self, /) -> None:
        scale: float = self.scale
        self.__image = pygame.transform.rotozoom(self.__shape_image, 0, scale)

    def __compute_shape_size(self, /) -> None:
        all_points: List[Vector2] = self.get_local_vertices()

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
    def _make(self, /) -> Surface:
        raise NotImplementedError

    @abstractmethod
    def get_local_vertices(self, /) -> List[Vector2]:
        raise NotImplementedError

    def get_vertices(self, /) -> List[Vector2]:
        angle: float = self.angle
        scale: float = self.scale
        all_points: List[Vector2] = self.get_local_vertices()
        vertices: List[Vector2] = []

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

        return vertices

    config: Configuration = ConfigTemplate(autocopy=True)

    @config.on_update
    def __update_shape(self, /) -> None:
        if self.config.has_initialization_context():
            self.__compute_shape_size()
            self.__shape_image = self._make()
            self._apply_rotation_scale()
        else:
            center: Tuple[float, float] = self.center
            self.__compute_shape_size()
            self.__shape_image = self._make()
            self._apply_rotation_scale()
            self.center = center


class Shape(AbstractShape):
    @initializer
    def __init__(self, /, *, color: Color, **kwargs: Any) -> None:
        self.color = color
        super().__init__(**kwargs)

    config = Configuration("color", parent=AbstractShape.config)

    config.value_validator("color", Color)

    color: ConfigAttribute[Color] = ConfigAttribute()


class OutlinedShape(Shape):
    @initializer
    def __init__(self, /, *, outline: int, outline_color: Color, **kwargs: Any) -> None:
        self.outline = outline
        self.outline_color = outline_color
        super().__init__(**kwargs)

    def get_local_size(self, /) -> Tuple[float, float]:
        w, h = super().get_local_size()
        outline: int = self.outline
        offset: float = outline / 2 + 1
        return (w + offset * 2, h + offset * 2)

    config = Configuration("outline", "outline_color", parent=Shape.config)

    config.value_converter_static("outline", valid_integer(min_value=0))
    config.value_validator("outline_color", Color)

    outline: ConfigAttribute[int] = ConfigAttribute()
    outline_color: ConfigAttribute[Color] = ConfigAttribute()


class PolygonShape(OutlinedShape, metaclass=MetaThemedShape):
    PointList = Union[List[Vector2], List[Tuple[float, float]], List[Tuple[int, int]]]

    @initializer
    def __init__(
        self,
        /,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        points: List[Vector2] = [],
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(color=color, outline=outline, outline_color=outline_color)
        self.__center: Vector2 = Vector2(0, 0)
        self.points = points

    def _make(self, /) -> Surface:
        outline: int = self.outline
        all_points: List[Vector2] = self.points

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

    def get_local_vertices(self, /) -> List[Vector2]:
        return self.points

    def set_points(self, /, points: PointList) -> None:
        self.config.set("points", points)

    config = Configuration("points", parent=OutlinedShape.config)

    config.set_autocopy("points", copy_on_set=False)

    @config.value_converter_static("points")
    @staticmethod
    def __valid_points(points: PointList) -> List[Vector2]:
        points = [Vector2(p) for p in points]
        left: float = min((point.x for point in points), default=0)
        top: float = min((point.y for point in points), default=0)
        for p in points:
            p.x -= left
            p.y -= top
        return points

    @config.on_update_value("points")
    def __on_update_points(self, /, points: List[Vector2]) -> None:
        left: float = 0
        top: float = 0
        right: float = max((point.x for point in points), default=0)
        bottom: float = max((point.y for point in points), default=0)
        w: float = right - left
        h: float = bottom - top

        self.__center = Vector2(left + w / 2, top + h / 2)

    points: ConfigAttribute[List[Vector2]] = ConfigAttribute()


class AbstractRectangleShape(AbstractShape):
    @initializer
    def __init__(self, /, *, width: float, height: float, **kwargs: Any) -> None:
        self.local_size = width, height
        super().__init__(**kwargs)

    def get_local_vertices(self, /) -> List[Vector2]:
        w, h = self.local_size
        return [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]

    config = Configuration("local_width", "local_height", "local_size", parent=AbstractShape.config)

    config.value_converter_static("local_width", valid_float(min_value=0))
    config.value_converter_static("local_height", valid_float(min_value=0))
    config.value_converter("local_size", tuple)

    config.getter("local_size", lambda self: (self.local_width, self.local_height))
    config.setter("local_size", lambda self, size: self.config(local_width=size[0], local_height=size[1]))

    local_width: ConfigAttribute[float] = ConfigAttribute()
    local_height: ConfigAttribute[float] = ConfigAttribute()
    local_size: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()


class RectangleShape(AbstractRectangleShape, OutlinedShape, metaclass=MetaThemedShape):
    @initializer
    def __init__(
        self,
        /,
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
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(
            width=width,
            height=height,
            color=color,
            outline=outline,
            outline_color=outline_color,
        )
        self.__draw_params: Dict[str, int] = dict()
        self.border_radius = border_radius
        self.border_top_left_radius = border_top_left_radius
        self.border_top_right_radius = border_top_right_radius
        self.border_bottom_left_radius = border_bottom_left_radius
        self.border_bottom_right_radius = border_bottom_right_radius

    def _make(self, /) -> Surface:
        outline: int = self.outline
        w: float = self.local_width
        h: float = self.local_height
        image: SurfaceRenderer = SurfaceRenderer(self.get_local_size())
        default_rect: Rect = image.get_rect()
        rect: Rect = Rect(0, 0, w, h)
        rect.center = default_rect.center
        draw_params = self.__draw_params
        image.draw_rect(self.color, rect, **draw_params)
        if outline > 0:
            image.draw_rect(self.outline_color, rect, width=outline, **draw_params)
        return image.surface

    config = Configuration(
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
        parent=[AbstractRectangleShape.config, OutlinedShape.config],
    )

    config.value_converter_static("border_radius", valid_integer(min_value=-1))
    config.value_converter_static("border_top_left_radius", valid_integer(min_value=-1))
    config.value_converter_static("border_top_right_radius", valid_integer(min_value=-1))
    config.value_converter_static("border_bottom_left_radius", valid_integer(min_value=-1))
    config.value_converter_static("border_bottom_right_radius", valid_integer(min_value=-1))

    @config.getter_key("border_radius")
    @config.getter_key("border_top_left_radius")
    @config.getter_key("border_top_right_radius")
    @config.getter_key("border_bottom_left_radius")
    @config.getter_key("border_bottom_right_radius")
    def __get_border_radius(self, /, border: str) -> int:
        try:
            return self.__draw_params[border]
        except KeyError as exc:
            raise UnregisteredOptionError(border) from exc

    @config.setter_key("border_radius")
    @config.setter_key("border_top_left_radius")
    @config.setter_key("border_top_right_radius")
    @config.setter_key("border_bottom_left_radius")
    @config.setter_key("border_bottom_right_radius")
    def __set_border_radius(self, /, border: str, radius: int) -> None:
        self.__draw_params[border] = radius

    border_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_right_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_right_radius: ConfigAttribute[int] = ConfigAttribute()


class AbstractCircleShape(AbstractShape):
    @initializer
    def __init__(self, /, *, radius: float, **kwargs: Any) -> None:
        self.radius = radius
        super().__init__(**kwargs)

    def get_local_vertices(self, /) -> List[Vector2]:
        r: float = self.radius
        center: Vector2 = Vector2(r, r)
        radius: Vector2 = Vector2(r, 0)
        return [center + radius.rotate(-i) for i in range(360)]

    config = Configuration("radius", parent=AbstractShape.config)

    config.value_converter_static("radius", valid_float(min_value=0))

    radius: ConfigAttribute[float] = ConfigAttribute()


class CircleShape(AbstractCircleShape, OutlinedShape, metaclass=MetaThemedShape):
    @initializer
    def __init__(
        self,
        /,
        radius: float,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        draw_top_left: bool = True,
        draw_top_right: bool = True,
        draw_bottom_left: bool = True,
        draw_bottom_right: bool = True,
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(radius=radius, color=color, outline=outline, outline_color=outline_color)
        self.__draw_params: Dict[str, bool] = dict()
        self.__points: List[Vector2] = []
        self.radius = radius
        self.draw_top_left = draw_top_left
        self.draw_top_right = draw_top_right
        self.draw_bottom_left = draw_bottom_left
        self.draw_bottom_right = draw_bottom_right

    def _make(self, /) -> Surface:
        radius: float = self.radius
        outline: int = self.outline
        width, height = self.get_local_size()
        radius += width % 2
        image: SurfaceRenderer = SurfaceRenderer((width, height))
        width, height = image.get_size()
        center: Tuple[float, float] = (width / 2, height / 2)
        draw_params = self.__draw_params
        image.draw_circle(self.color, center, radius, **draw_params)
        if outline > 0:
            image.draw_circle(self.outline_color, center, radius, width=outline, **draw_params)
        return image.surface

    def get_local_vertices(self, /) -> List[Vector2]:
        return [Vector2(p) for p in self.__points]

    config = Configuration(
        "draw_top_left",
        "draw_top_right",
        "draw_bottom_left",
        "draw_bottom_right",
        parent=[AbstractCircleShape.config, OutlinedShape.config],
    )

    config.value_converter_static("draw_top_left", truth)
    config.value_converter_static("draw_top_right", truth)
    config.value_converter_static("draw_bottom_left", truth)
    config.value_converter_static("draw_bottom_right", truth)

    @config.getter_key("draw_top_left")
    @config.getter_key("draw_top_right")
    @config.getter_key("draw_bottom_left")
    @config.getter_key("draw_bottom_right")
    def __get_draw_arc(self, /, side: str) -> bool:
        try:
            return self.__draw_params[side]
        except KeyError as exc:
            raise UnregisteredOptionError(side) from exc

    @config.setter_key("draw_top_left")
    @config.setter_key("draw_top_right")
    @config.setter_key("draw_bottom_left")
    @config.setter_key("draw_bottom_right")
    def __set_draw_arc(self, /, side: str, status: bool) -> None:
        self.__draw_params[side] = status

    @config.on_update("draw_top_left")
    @config.on_update("draw_top_right")
    @config.on_update("draw_bottom_left")
    @config.on_update("draw_bottom_right")
    def __compute_vertices(self, /) -> None:
        draw_params = self.__draw_params
        if all(not drawn for drawn in draw_params.values()):
            self.__points = []
            return

        center: Vector2 = Vector2(self.radius, self.radius)
        radius: Vector2 = Vector2(self.radius, 0)

        angle_ranges: Dict[str, range] = {
            "draw_top_right": range(0, 90),
            "draw_top_left": range(90, 180),
            "draw_bottom_left": range(180, 270),
            "draw_bottom_right": range(270, 360),
        }

        all_points: List[Vector2] = []

        for draw_side, angle_range in angle_ranges.items():
            if draw_params[draw_side]:
                all_points.extend(center + radius.rotate(-i) for i in angle_range)
            elif not all_points or all_points[-1] != center:
                all_points.append(Vector2(center))

        self.__points = all_points

    draw_top_left: ConfigAttribute[bool] = ConfigAttribute()
    draw_top_right: ConfigAttribute[bool] = ConfigAttribute()
    draw_bottom_left: ConfigAttribute[bool] = ConfigAttribute()
    draw_bottom_right: ConfigAttribute[bool] = ConfigAttribute()


class CrossShape(OutlinedShape, metaclass=MetaThemedShape):
    @unique
    class Type(str, Enum):
        DIAGONAL = "diagonal"
        PLUS = "plus"

    @initializer
    def __init__(
        self,
        /,
        width: float,
        height: float,
        color: Color,
        type: str,
        *,
        line_width: float = 0.3,
        outline_color: Color = BLACK,
        outline: int = 0,
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(color=color, outline=outline, outline_color=outline_color)
        self.__type: CrossShape.Type = CrossShape.Type(type)
        self.__points: List[Vector2] = []
        self.local_size = width, height
        self.line_width = line_width

    def _make(self, /) -> Surface:
        p = PolygonShape(
            self.color,
            outline=self.outline,
            outline_color=self.outline_color,
            points=self.__points,
        )
        image: Surface = getattr(p, f"_{AbstractShape.__name__}__image")
        return image

    def get_local_vertices(self, /) -> List[Vector2]:
        return [Vector2(p) for p in self.__points]

    def __get_diagonal_cross_points(self, /) -> List[Vector2]:
        rect: Rect = Rect((0, 0), self.local_size)
        line_width: float = self.line_width
        if line_width == 0:
            return []

        if line_width < 1:
            line_width = min(self.local_width * line_width, self.local_height * line_width)
            if line_width == 0:
                return []

        line_width /= 2
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
            return []
        return [
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
        ]

    def __get_plus_cross_points(self, /) -> List[Vector2]:
        rect: Rect = self.get_local_rect()
        line_width: float = self.line_width
        if line_width == 0:
            return []

        if line_width < 1:
            line_width = min(self.local_width * line_width, self.local_height * line_width)

        line_width /= 2

        return [
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
        ]

    config = Configuration(
        "local_width",
        "local_height",
        "local_size",
        "line_width",
        parent=OutlinedShape.config,
    )

    config.value_converter_static("local_width", valid_float(min_value=0))
    config.value_converter_static("local_height", valid_float(min_value=0))
    config.value_converter("local_size", tuple)
    config.value_converter_static("line_width", valid_float(min_value=0))

    local_width: ConfigAttribute[float] = ConfigAttribute()
    local_height: ConfigAttribute[float] = ConfigAttribute()
    local_size: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    line_width: ConfigAttribute[float] = ConfigAttribute()

    @property
    def type(self, /) -> str:
        return str(self.__type.value)

    config.getter("local_size", lambda self: (self.local_width, self.local_height))
    config.setter("local_size", lambda self, size: self.config(local_width=size[0], local_height=size[1]))

    @config.on_update("local_width")
    @config.on_update("local_height")
    @config.on_update("local_size")
    @config.on_update("line_width")
    def __compute_vertices(self, /) -> None:
        compute_vertices = {
            CrossShape.Type.DIAGONAL: self.__get_diagonal_cross_points,
            CrossShape.Type.PLUS: self.__get_plus_cross_points,
        }
        self.__points = compute_vertices[self.__type]()


class DiagonalCrossShape(CrossShape):
    def __init__(
        self,
        /,
        width: float,
        height: float,
        color: Color,
        *,
        line_width: float = 0.3,
        outline_color: Color = BLACK,
        outline: int = 0,
        theme: Optional[ThemeType] = None,
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
        /,
        width: float,
        height: float,
        color: Color,
        *,
        line_width: float = 0.3,
        outline_color: Color = BLACK,
        outline: int = 0,
        theme: Optional[ThemeType] = None,
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
