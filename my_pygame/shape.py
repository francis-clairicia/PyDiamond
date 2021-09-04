# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import abstractmethod
from operator import truth
from typing import Dict, List, Optional, Tuple, Union
from math import sin, tan, radians
from enum import Enum, unique

import pygame.draw
from pygame.math import Vector2
from pygame.rect import Rect
import pygame.transform
from pygame.color import Color
from pygame.surface import Surface

from .drawable import Drawable, ThemedDrawable
from .theme import NoTheme, ThemeType, abstract_theme_class
from .colors import BLACK
from .surface import create_surface
from .configuration import ConfigAttribute, ConfigTemplate, Configuration, initializer, no_object
from .utils import valid_float, valid_integer


class AbstractShape(Drawable):
    config: Configuration = ConfigTemplate(autocopy=True)

    config.register_copy_func(Color, lambda obj: Color(obj))

    def __init__(self) -> None:
        super().__init__()
        self.__image: Surface = create_surface((0, 0))
        self.__shape_image: Surface = self.__image.copy()
        self.__local_size: Tuple[float, float] = (0, 0)
        self.__size: Tuple[float, float] = (0, 0)

    @config.updater
    def __update_shape(self) -> None:
        if self.config.has_initialization_context():
            self.__shape_image = self._make()
            self._apply_rotation_scale()
        else:
            center: Tuple[float, float] = self.center
            self.__shape_image = self._make()
            self._apply_rotation_scale()
            self.center = center

    def to_surface(self) -> Surface:
        return self.__image.copy()

    def draw_onto(self, surface: Surface) -> None:
        image: Surface = self.__image
        surface.blit(image, image.get_rect(center=self.center))

    def get_local_size(self) -> Tuple[float, float]:
        return self.__local_size

    def get_size(self) -> Tuple[float, float]:
        return self.__size

    def _apply_rotation_scale(self) -> None:
        angle: float = self.angle
        scale: float = self.scale
        self.__image = pygame.transform.rotozoom(self.__shape_image, angle, scale)

        all_points: List[Vector2] = self.get_local_vertices()
        vertices: List[Vector2] = []

        if not all_points:
            self.__local_size = self.__size = (0, 0)
            return

        left: float = min((point.x for point in all_points), default=0)
        top: float = min((point.y for point in all_points), default=0)
        right: float = max((point.x for point in all_points), default=0)
        bottom: float = max((point.y for point in all_points), default=0)
        w: float = right - left
        h: float = bottom - top
        self.__local_size = (w, h)

        local_center: Vector2 = Vector2(left + w / 2, top + h / 2)

        center: Vector2 = Vector2(self.center)  # type: ignore[arg-type]
        for point in all_points:
            offset: Vector2 = (point - local_center).rotate(-angle)
            try:
                offset.scale_to_length(offset.length() * scale)
            except ValueError:
                offset = Vector2(0, 0)
            vertices.append(center + offset)

        left = min((point.x for point in vertices), default=0)
        top = min((point.y for point in vertices), default=0)
        right = max((point.x for point in vertices), default=0)
        bottom = max((point.y for point in vertices), default=0)
        self.__size = (right - left, bottom - top)

    @abstractmethod
    def _make(self) -> Surface:
        raise NotImplementedError

    @abstractmethod
    def get_local_vertices(self) -> List[Vector2]:
        raise NotImplementedError

    def get_vertices(self) -> List[Vector2]:
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

            center: Vector2 = Vector2(self.center)  # type: ignore[arg-type]
            for point in all_points:
                offset: Vector2 = (point - local_center).rotate(-angle)
                try:
                    offset.scale_to_length(offset.length() * scale)
                except ValueError:
                    offset = Vector2(0, 0)
                vertices.append(center + offset)

        return vertices


class Shape(AbstractShape):
    @initializer
    def __init__(self, color: Color) -> None:
        super().__init__()
        self.color = color

    config = Configuration("color", parent=AbstractShape.config)

    config.validator("color", Color)

    color: ConfigAttribute[Color] = ConfigAttribute()


@abstract_theme_class
class ThemedShape(AbstractShape, ThemedDrawable):
    pass


class OutlinedShape(Shape):
    @initializer
    def __init__(self, color: Color, outline: int, outline_color: Color) -> None:
        super().__init__(color)
        self.outline = outline
        self.outline_color = outline_color

    config = Configuration("outline", "outline_color", parent=Shape.config)

    config.validator("outline", no_object(valid_integer(min_value=0)))
    config.validator("outline_color", Color)

    outline: ConfigAttribute[int] = ConfigAttribute()
    outline_color: ConfigAttribute[Color] = ConfigAttribute()


class PolygonShape(OutlinedShape, ThemedShape):
    PointList = Union[List[Vector2], List[Tuple[float, float]], List[Tuple[int, int]]]

    @initializer
    def __init__(
        self,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        points: List[Vector2] = [],
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(color, outline, outline_color)
        self.__center: Vector2 = Vector2(0, 0)
        self.__size: Tuple[float, float] = (0, 0)
        self.points = points

    def copy(self) -> PolygonShape:
        return PolygonShape(self.color, outline=self.outline, outline_color=self.outline_color, points=self.points, theme=NoTheme)

    def _make(self) -> Surface:
        outline: int = self.outline
        all_points: List[Vector2] = self.points

        if len(all_points) < 2:
            return create_surface((0, 0))

        offset: float = outline / 2 + 2
        w, h = (self.__size[0] + offset * 2, self.__size[1] + offset * 2)
        image: Surface = create_surface((w, h))

        center_diff: Vector2 = Vector2(w / 2, h / 2) - self.__center
        for p in all_points:
            p.x += center_diff.x
            p.y += center_diff.y

        if len(all_points) == 2:
            if outline > 0:
                start, end = all_points
                pygame.draw.line(image, self.outline_color, start, end, width=outline)
        else:
            pygame.draw.polygon(image, self.color, all_points)
            if outline > 0:
                pygame.draw.polygon(image, self.outline_color, all_points, width=outline)

        return image

    def get_local_vertices(self) -> List[Vector2]:
        return self.points

    def set_points(self, points: PointList) -> None:
        self.config.set("points", points)

    config = Configuration("points", parent=OutlinedShape.config)

    config.set_autocopy("points", copy_on_set=False)

    @config.validator("points")
    @staticmethod
    def __valid_points(points: PointList) -> List[Vector2]:
        points = [Vector2(p) for p in points]  # type: ignore[arg-type]
        left: float = min((point.x for point in points), default=0)
        top: float = min((point.y for point in points), default=0)
        for p in points:
            p.x -= left
            p.y -= top
        return points

    @config.value_updater_no_name("points")
    def __on_update_points(self, points: List[Vector2]) -> None:
        left: float = 0
        top: float = 0
        right: float = max((point.x for point in points), default=0)
        bottom: float = max((point.y for point in points), default=0)
        w: float = right - left
        h: float = bottom - top

        self.__center = Vector2(left + w / 2, top + h / 2)
        self.__size = (w, h)

    points: ConfigAttribute[List[Vector2]] = ConfigAttribute()


class AbstractRectangleShape(AbstractShape):
    @initializer
    def __init__(self, width: float, height: float) -> None:
        AbstractShape.__init__(self)
        self.local_size = width, height

    def get_local_vertices(self) -> List[Vector2]:
        w, h = self.local_size
        return [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]

    config = Configuration("local_width", "local_height", "local_size", parent=AbstractShape.config)

    config.validator("local_width", no_object(valid_float(min_value=0)))
    config.validator("local_height", no_object(valid_float(min_value=0)))
    config.validator("local_size", (tuple, list))

    local_width: ConfigAttribute[float] = ConfigAttribute()
    local_height: ConfigAttribute[float] = ConfigAttribute()
    local_size: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()

    @config.getter_no_name("local_size")
    def __get_local_size(self) -> Tuple[float, float]:
        return (self.local_width, self.local_height)

    @config.setter_no_name("local_size")
    def ___set_local_size(self, size: Tuple[float, float]) -> None:
        self.config(local_width=size[0], local_height=size[1])


class RectangleShape(AbstractRectangleShape, OutlinedShape, ThemedShape):
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
        theme: Optional[ThemeType] = None,
    ) -> None:
        AbstractRectangleShape.__init__(self, width, height)
        OutlinedShape.__init__(self, color, outline, outline_color)
        self.__draw_params: Dict[str, int] = dict()
        self.border_radius = border_radius
        self.border_top_left_radius = border_top_left_radius
        self.border_top_right_radius = border_top_right_radius
        self.border_bottom_left_radius = border_bottom_left_radius
        self.border_bottom_right_radius = border_bottom_right_radius

    def copy(self) -> RectangleShape:
        return RectangleShape(
            self.local_width,
            self.local_height,
            self.color,
            outline=self.outline,
            outline_color=self.outline_color,
            **self.__draw_params,
            theme=NoTheme,
        )

    def _make(self) -> Surface:
        outline: int = self.outline
        offset: float = outline / 2 + 2
        w: float = self.local_width
        h: float = self.local_height
        image: Surface = create_surface((w + offset * 2, h + offset * 2))
        default_rect: Rect = image.get_rect()
        rect: Rect = Rect(0, 0, w, h)
        rect.center = default_rect.center
        draw_params = self.__draw_params
        pygame.draw.rect(image, self.color, rect, **draw_params)
        if outline > 0:
            pygame.draw.rect(image, self.outline_color, rect, width=outline, **draw_params)
        return image

    config = Configuration(
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
        parent=[AbstractRectangleShape.config, OutlinedShape.config],
    )

    config.validator("border_radius", no_object(valid_integer(min_value=-1)))
    config.validator("border_top_left_radius", no_object(valid_integer(min_value=-1)))
    config.validator("border_top_right_radius", no_object(valid_integer(min_value=-1)))
    config.validator("border_bottom_left_radius", no_object(valid_integer(min_value=-1)))
    config.validator("border_bottom_right_radius", no_object(valid_integer(min_value=-1)))

    @config.getter("border_radius")
    @config.getter("border_top_left_radius")
    @config.getter("border_top_right_radius")
    @config.getter("border_bottom_left_radius")
    @config.getter("border_bottom_right_radius")
    def __get_border_radius(self, border: str) -> int:
        try:
            return self.__draw_params[border]
        except KeyError as exc:
            raise AttributeError from exc

    @config.setter("border_radius")
    @config.setter("border_top_left_radius")
    @config.setter("border_top_right_radius")
    @config.setter("border_bottom_left_radius")
    @config.setter("border_bottom_right_radius")
    def __set_border_radius(self, border: str, radius: int) -> None:
        self.__draw_params[border] = radius

    border_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_right_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_right_radius: ConfigAttribute[int] = ConfigAttribute()


class AbstractCircleShape(AbstractShape):
    @initializer
    def __init__(self, radius: float) -> None:
        AbstractShape.__init__(self)
        self.radius = radius

    def get_local_vertices(self) -> List[Vector2]:
        r: float = self.radius
        center: Vector2 = Vector2(r, r)
        radius: Vector2 = Vector2(r, 0)
        return [center + radius.rotate(-i) for i in range(360)]

    config = Configuration("radius", parent=AbstractShape.config)

    config.validator("radius", valid_float(min_value=0))

    radius: ConfigAttribute[float] = ConfigAttribute()


class CircleShape(AbstractCircleShape, OutlinedShape, ThemedShape):
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
        theme: Optional[ThemeType] = None,
    ) -> None:
        AbstractCircleShape.__init__(self, radius)
        OutlinedShape.__init__(self, color, outline, outline_color)
        self.__draw_params: Dict[str, bool] = dict()
        self.__points: List[Vector2] = []
        self.radius = radius
        self.draw_top_left = draw_top_left
        self.draw_top_right = draw_top_right
        self.draw_bottom_left = draw_bottom_left
        self.draw_bottom_right = draw_bottom_right

    def copy(self) -> CircleShape:
        return CircleShape(
            self.radius, self.color, outline=self.outline, outline_color=self.outline_color, **self.__draw_params, theme=NoTheme
        )

    def _make(self) -> Surface:
        self.__points = self.__compute_vertices()
        radius: float = self.radius
        outline: int = self.outline
        offset: float = outline / 2 + 2
        width = height = int(radius * 2 + offset * 2)
        radius += width % 2
        image: Surface = create_surface((width, height))
        width, height = image.get_size()
        center: Tuple[float, float] = (width / 2, height / 2)
        draw_params = self.__draw_params
        pygame.draw.circle(image, self.color, center, radius, **draw_params)
        if outline > 0:
            pygame.draw.circle(image, self.outline_color, center, radius, width=outline, **draw_params)
        return image

    def get_local_vertices(self) -> List[Vector2]:
        return [Vector2(p) for p in self.__points]

    def __compute_vertices(self) -> List[Vector2]:
        draw_params = self.__draw_params
        if all(not drawn for drawn in draw_params.values()):
            return []

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

        return all_points

    config = Configuration(
        "draw_top_left",
        "draw_top_right",
        "draw_bottom_left",
        "draw_bottom_right",
        parent=[AbstractCircleShape.config, OutlinedShape.config],
    )

    config.validator("draw_top_left", truth)
    config.validator("draw_top_right", truth)
    config.validator("draw_bottom_left", truth)
    config.validator("draw_bottom_right", truth)

    @config.getter("draw_top_left")
    @config.getter("draw_top_right")
    @config.getter("draw_bottom_left")
    @config.getter("draw_bottom_right")
    def __get_draw_arc(self, side: str) -> bool:
        try:
            return self.__draw_params[side]
        except KeyError as exc:
            raise AttributeError from exc

    @config.setter("draw_top_left")
    @config.setter("draw_top_right")
    @config.setter("draw_bottom_left")
    @config.setter("draw_bottom_right")
    def __set_draw_arc(self, side: str, status: bool) -> None:
        self.__draw_params[side] = status

    draw_top_left: ConfigAttribute[bool] = ConfigAttribute()
    draw_top_right: ConfigAttribute[bool] = ConfigAttribute()
    draw_bottom_left: ConfigAttribute[bool] = ConfigAttribute()
    draw_bottom_right: ConfigAttribute[bool] = ConfigAttribute()


class CrossShape(OutlinedShape, ThemedShape):
    @unique
    class Type(str, Enum):
        DIAGONAL = "diagonal"
        PLUS = "plus"

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
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(color, outline, outline_color)
        self.__type: CrossShape.Type = CrossShape.Type(type)
        self.__points: List[Vector2] = []
        self.local_size = width, height
        self.line_width = line_width

    def copy(self) -> CrossShape:
        return CrossShape(
            self.local_width,
            self.local_height,
            self.color,
            self.type,
            line_width=self.line_width,
            outline=self.outline,
            outline_color=self.outline_color,
            theme=NoTheme,
        )

    def _make(self) -> Surface:
        compute_vertices = {
            CrossShape.Type.DIAGONAL: self.__get_diagonal_cross_points,
            CrossShape.Type.PLUS: self.__get_plus_cross_points,
        }
        self.__points = compute_vertices[self.__type]()
        return PolygonShape(self.color, outline=self.outline, outline_color=self.outline_color, points=self.__points).to_surface()

    def get_local_vertices(self) -> List[Vector2]:
        return [Vector2(p) for p in self.__points]

    def __get_diagonal_cross_points(self) -> List[Vector2]:
        rect: Rect = Rect((0, 0), self.local_size)
        line_width: float = self.line_width
        if line_width == 0:
            return []

        if line_width < 1:
            line_width = min(self.local_width * line_width, self.local_height * line_width)
            if line_width == 0:
                return []

        line_width /= 2
        diagonal: Vector2 = Vector2(rect.bottomleft) - Vector2(rect.topright)  # type: ignore[arg-type]

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

    def __get_plus_cross_points(self) -> List[Vector2]:
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

    config = Configuration("local_width", "local_height", "local_size", "line_width", parent=OutlinedShape.config)

    config.validator("local_width", no_object(valid_float(min_value=0)))
    config.validator("local_height", no_object(valid_float(min_value=0)))
    config.validator("local_size", (tuple, list))
    config.validator("line_width", no_object(valid_float(min_value=0)))

    local_width: ConfigAttribute[float] = ConfigAttribute()
    local_height: ConfigAttribute[float] = ConfigAttribute()
    local_size: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    line_width: ConfigAttribute[float] = ConfigAttribute()

    @property
    def type(self) -> str:
        return str(self.__type.value)

    @config.getter_no_name("local_size")
    def __get_local_size(self) -> Tuple[float, float]:
        return (self.local_width, self.local_height)

    @config.setter_no_name("local_size")
    def ___set_local_size(self, size: Tuple[float, float]) -> None:
        self.config(local_width=size[0], local_height=size[1])


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
            theme=NoTheme,
        )

    def copy(self) -> DiagonalCrossShape:
        return DiagonalCrossShape(
            self.local_width,
            self.local_height,
            self.color,
            line_width=self.line_width,
            outline=self.outline,
            outline_color=self.outline_color,
            theme=NoTheme,
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
            theme=NoTheme,
        )

    def copy(self) -> PlusCrossShape:
        return PlusCrossShape(
            self.local_width,
            self.local_height,
            self.color,
            line_width=self.line_width,
            outline=self.outline,
            outline_color=self.outline_color,
            theme=NoTheme,
        )
