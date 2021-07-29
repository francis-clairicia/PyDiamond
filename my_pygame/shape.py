# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import abstractmethod
from typing import Dict, List, Optional, Tuple, Union, final
from math import sin, tan, radians
from enum import Enum, unique

import pygame.draw
from pygame.math import Vector2
from pygame.rect import Rect
import pygame.transform
from pygame.color import Color
from pygame.surface import Surface

from .drawable import Drawable, ThemedDrawable
from .theme import NoTheme, Theme, abstract_theme_class
from .colors import BLACK
from .surface import create_surface


class AbstractShape(Drawable):
    def __init__(self) -> None:
        super().__init__()
        self.__update: bool = True
        self.__image: Surface = create_surface((0, 0))
        self.__shape_image: Surface = self.__image.copy()
        self.__local_size: Tuple[float, float] = (0, 0)
        self.__size: Tuple[float, float] = (0, 0)
        self._need_update()

    def _need_update(self) -> None:
        self.__update = True

    def __update_shape(self) -> None:
        if self.__update:
            self.__update = False
            center: Tuple[float, float] = self.center
            self.__shape_image = self._make()
            self._apply_rotation_scale()
            self.center = center

    def to_surface(self) -> Surface:
        self.__update_shape()
        return self.__image.copy()

    def draw_onto(self, surface: Surface) -> None:
        self.__update_shape()
        image: Surface = self.__image
        surface.blit(image, image.get_rect(center=self.center))

    @final
    def get_local_size(self) -> Tuple[float, float]:
        self.__update_shape()
        return self.__local_size

    @final
    def get_size(self) -> Tuple[float, float]:
        self.__update_shape()
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

        center: Vector2 = Vector2(self.center)
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

            center: Vector2 = Vector2(self.center)
            for point in all_points:
                offset: Vector2 = (point - local_center).rotate(-angle)
                try:
                    offset.scale_to_length(offset.length() * scale)
                except ValueError:
                    offset = Vector2(0, 0)
                vertices.append(center + offset)

        return vertices

    @property
    def x(self) -> float:
        self.__update_shape()
        return super().x

    @x.setter
    def x(self, x: float) -> None:
        self.__update_shape()
        Drawable.x.fset(self, x)  # type: ignore

    @property
    def y(self) -> float:
        self.__update_shape()
        return super().y

    @y.setter
    def y(self, y: float) -> None:
        self.__update_shape()
        Drawable.y.fset(self, y)  # type: ignore


class Shape(AbstractShape):
    def __init__(self, color: Color) -> None:
        super().__init__()
        self.__color: Color = BLACK
        self.color = color
        self._need_update()

    @property
    def color(self) -> Color:
        return Color(self.__color)

    @color.setter
    def color(self, value: Color) -> None:
        if self.__color != value:
            self.__color = Color(value)
            self._need_update()


@abstract_theme_class
class ThemedShape(AbstractShape, ThemedDrawable):
    pass


class OutlinedShape(Shape):
    def __init__(self, color: Color, outline: int, outline_color: Color) -> None:
        super().__init__(color)
        self.__outline: int = 0
        self.__outline_color: Color = BLACK
        self.outline = outline
        self.outline_color = outline_color
        self._need_update()

    @property
    def outline(self) -> int:
        return self.__outline

    @outline.setter
    def outline(self, value: int) -> None:
        value = max(int(value), 0)
        if self.__outline != value:
            self.__outline = value
            self._need_update()

    @property
    def outline_color(self) -> Color:
        return Color(self.__outline_color)

    @outline_color.setter
    def outline_color(self, value: Color) -> None:
        if self.__outline_color != value:
            self.__outline_color = Color(value)
            self._need_update()


class PolygonShape(OutlinedShape, ThemedShape):
    PointList = Union[List[Vector2], List[Tuple[float, float]], List[Tuple[int, int]]]

    def __init__(
        self,
        color: Color,
        *,
        outline: int = 0,
        outline_color: Color = BLACK,
        points: List[Vector2] = [],
        theme: Optional[Theme] = None,
    ) -> None:
        super().__init__(color, outline, outline_color)
        self.__points: List[Vector2] = []
        self.__center: Vector2 = Vector2(0, 0)
        self.__size: Tuple[float, float] = (0, 0)
        self.set_points(points)
        self._need_update()

    def copy(self) -> PolygonShape:
        return PolygonShape(
            self.color, outline=self.outline, outline_color=self.outline_color, points=self.__points, theme=NoTheme
        )

    def _make(self) -> Surface:
        outline: int = self.outline
        all_points: List[Vector2] = self.__points

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
        return self.get_points()

    def get_points(self) -> List[Vector2]:
        return [Vector2(p) for p in self.__points]

    def set_points(self, points: PointList) -> None:
        points = [Vector2(p) for p in points]
        left: float = min((point.x for point in points), default=0)
        top: float = min((point.y for point in points), default=0)
        for p in points:
            p.x -= left
            p.y -= top

        if len(points) == len(self.__points) and all(p1 == p2 for p1, p2 in zip(points, self.__points)):
            return

        left = 0
        top = 0
        right: float = max((point.x for point in points), default=0)
        bottom: float = max((point.y for point in points), default=0)
        w: float = right - left
        h: float = bottom - top

        self.__points = points
        self.__center = Vector2(left + w / 2, top + h / 2)
        self.__size = (w, h)
        self._need_update()


class AbstractRectangleShape(AbstractShape):
    def __init__(self, width: float, height: float) -> None:
        AbstractShape.__init__(self)
        self.__w: float = 0
        self.__h: float = 0
        self.local_size = width, height
        self._need_update()

    def get_local_vertices(self) -> List[Vector2]:
        w, h = self.local_size
        return [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]

    @property
    def local_size(self) -> Tuple[float, float]:
        return (self.local_width, self.local_height)

    @local_size.setter
    def local_size(self, size: Tuple[float, float]) -> None:
        self.local_width, self.local_height = size

    @property
    def local_width(self) -> float:
        return self.__w

    @local_width.setter
    def local_width(self, width: float) -> None:
        width = max(width, 0)
        if width != self.__w:
            self.__w = width
            self._need_update()

    @property
    def local_height(self) -> float:
        return self.__h

    @local_height.setter
    def local_height(self, height: float) -> None:
        height = max(height, 0)
        if height != self.__h:
            self.__h = height
            self._need_update()


class RectangleShape(AbstractRectangleShape, OutlinedShape, ThemedShape):
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
        theme: Optional[Theme] = None,
    ) -> None:
        AbstractRectangleShape.__init__(self, width, height)
        OutlinedShape.__init__(self, color, outline, outline_color)
        self.__draw_params: Dict[str, int] = {
            "border_radius": -1,
            "border_top_left_radius": -1,
            "border_top_right_radius": -1,
            "border_bottom_left_radius": -1,
            "border_bottom_right_radius": -1,
        }
        self.border_radius = border_radius
        self.border_top_left_radius = border_top_left_radius
        self.border_top_right_radius = border_top_right_radius
        self.border_bottom_left_radius = border_bottom_left_radius
        self.border_bottom_right_radius = border_bottom_right_radius
        self._need_update()

    def copy(self) -> RectangleShape:
        return RectangleShape(
            self.__w,
            self.__h,
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

    @property
    def border_radius(self) -> int:
        return self.__draw_params["border_radius"]

    @border_radius.setter
    def border_radius(self, radius: int) -> None:
        self.__set_border_radius("border_radius", radius)

    @property
    def border_top_left_radius(self) -> int:
        return self.__draw_params["border_top_left_radius"]

    @border_top_left_radius.setter
    def border_top_left_radius(self, radius: int) -> None:
        self.__set_border_radius("border_top_left_radius", radius)

    @property
    def border_top_right_radius(self) -> int:
        return self.__draw_params["border_top_right_radius"]

    @border_top_right_radius.setter
    def border_top_right_radius(self, radius: int) -> None:
        self.__set_border_radius("border_top_right_radius", radius)

    @property
    def border_bottom_left_radius(self) -> int:
        return self.__draw_params["border_bottom_left_radius"]

    @border_bottom_left_radius.setter
    def border_bottom_left_radius(self, radius: int) -> None:
        self.__set_border_radius("border_bottom_left_radius", radius)

    @property
    def border_bottom_right_radius(self) -> int:
        return self.__draw_params["border_bottom_right_radius"]

    @border_bottom_right_radius.setter
    def border_bottom_right_radius(self, radius: int) -> None:
        self.__set_border_radius("border_bottom_right_radius", radius)

    def __set_border_radius(self, border: str, radius: int) -> None:
        radius = max(int(radius), -1)
        if self.__draw_params[border] != radius:
            self.__draw_params[border] = radius
            self._need_update()


class AbstractCircleShape(AbstractShape):
    def __init__(self, radius: float) -> None:
        AbstractShape.__init__(self)
        self.__radius: float = 0
        self.radius = radius
        self._need_update()

    def get_local_vertices(self) -> List[Vector2]:
        r: float = self.__radius
        center: Vector2 = Vector2(r, r)
        radius: Vector2 = Vector2(r, 0)
        return [center + radius.rotate(-i) for i in range(360)]

    @property
    def radius(self) -> float:
        return self.__radius

    @radius.setter
    def radius(self, radius: float) -> None:
        radius = max(radius, 0)
        if radius != self.__radius:
            self.__radius = radius
            self._need_update()


class CircleShape(AbstractCircleShape, OutlinedShape, ThemedShape):
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
        theme: Optional[Theme] = None,
    ) -> None:
        AbstractCircleShape.__init__(self, radius)
        OutlinedShape.__init__(self, color, outline, outline_color)
        self.__draw_params: Dict[str, bool] = {
            "draw_top_left": True,
            "draw_top_right": True,
            "draw_bottom_left": True,
            "draw_bottom_right": True,
        }
        self.__points: List[Vector2] = []
        self.radius = radius
        self.draw_top_left = draw_top_left
        self.draw_top_right = draw_top_right
        self.draw_bottom_left = draw_bottom_left
        self.draw_bottom_right = draw_bottom_right
        self._need_update()

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

    @property
    def draw_top_left(self) -> int:
        return self.__draw_params["draw_top_left"]

    @draw_top_left.setter
    def draw_top_left(self, status: bool) -> None:
        self.__draw_arc("draw_top_left", status)

    @property
    def draw_top_right(self) -> int:
        return self.__draw_params["draw_top_right"]

    @draw_top_right.setter
    def draw_top_right(self, status: bool) -> None:
        self.__draw_arc("draw_top_right", status)

    @property
    def draw_bottom_left(self) -> int:
        return self.__draw_params["draw_bottom_left"]

    @draw_bottom_left.setter
    def draw_bottom_left(self, status: bool) -> None:
        self.__draw_arc("draw_bottom_left", status)

    @property
    def draw_bottom_right(self) -> int:
        return self.__draw_params["draw_bottom_right"]

    @draw_bottom_right.setter
    def draw_bottom_right(self, status: bool) -> None:
        self.__draw_arc("draw_bottom_right", status)

    def __draw_arc(self, side: str, status: bool) -> None:
        status = bool(status)
        if status is not self.__draw_params[side]:
            self.__draw_params[side] = status
            self._need_update()


class CrossShape(OutlinedShape, ThemedShape):
    @unique
    class Type(str, Enum):
        DIAGONAL = "diagonal"
        PLUS = "plus"

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
        theme: Optional[Theme] = None,
    ) -> None:
        super().__init__(color, outline, outline_color)
        self.__w: float = 0
        self.__h: float = 0
        self.__line_width: float = 0
        self.__type: CrossShape.Type = CrossShape.Type(type)
        self.__points: List[Vector2] = []
        self.local_size = width, height
        self.line_width = line_width
        self._need_update()

    def copy(self) -> CrossShape:
        return CrossShape(
            self.__w,
            self.__h,
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

    @property
    def line_width(self) -> float:
        return self.__line_width

    @line_width.setter
    def line_width(self, width: float) -> None:
        width = max(width, 0)
        if self.__line_width != width:
            self.__line_width = width
            self._need_update()

    @property
    def type(self) -> str:
        return str(self.__type.value)

    @property
    def local_size(self) -> Tuple[float, float]:
        return (self.local_width, self.local_height)

    @local_size.setter
    def local_size(self, size: Tuple[float, float]) -> None:
        self.local_width, self.local_height = size

    @property
    def local_width(self) -> float:
        return self.__w

    @local_width.setter
    def local_width(self, width: float) -> None:
        width = max(width, 0)
        if width != self.__w:
            self.__w = width
            self._need_update()

    @property
    def local_height(self) -> float:
        return self.__h

    @local_height.setter
    def local_height(self, height: float) -> None:
        height = max(height, 0)
        if height != self.__h:
            self.__h = height
            self._need_update()


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
        theme: Optional[Theme] = None,
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
        theme: Optional[Theme] = None,
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
