# -*- coding: Utf-8 -*

from abc import abstractmethod
from typing import Dict, List, Optional, Tuple, Union

import pygame.draw
from pygame.math import Vector2
from pygame.rect import Rect
import pygame.transform
from pygame.color import Color
from pygame.surface import Surface

from .drawable import ThemedDrawable
from .theme import Theme
from .colors import BLACK, TRANSPARENT
from .surface import create_surface


class Shape(ThemedDrawable, use_parent_theme=False):
    def __init__(self, color: Color, outline: int, outline_color: Color) -> None:
        super().__init__()
        self.__update: bool = True
        self.__image: Surface = create_surface((0, 0))
        self.__shape_image: Surface = self.__image.copy()
        self.__color: Color = BLACK
        self.__outline: int = 0
        self.__outline_color: Color = BLACK
        self.color = color
        self.outline = outline
        self.outline_color = outline_color

    def _need_update(self) -> None:
        self.__update = True

    def __update_shape(self) -> None:
        if self.__update:
            self.__update = False
            center: Tuple[float, float] = self.center
            self.__shape_image = self.make()
            self._apply_rotation_scale()
            self.center = center

    def to_surface(self) -> Surface:
        self.__update_shape()
        return self.__image

    def get_size(self) -> Tuple[float, float]:
        self.__update_shape()
        return self.__image.get_size()

    def _apply_rotation_scale(self) -> None:
        self.__image = pygame.transform.rotozoom(self.__shape_image, self.angle, self.scale)

    @abstractmethod
    def make(self) -> Surface:
        pass

    @abstractmethod
    def get_vertices(self) -> List[Vector2]:
        pass

    @property
    def color(self) -> Color:
        return self.__color

    @color.setter
    def color(self, value: Color) -> None:
        if self.__color != value:
            self.__color = value
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
        return self.__outline_color

    @outline_color.setter
    def outline_color(self, value: Color) -> None:
        if self.__outline_color != value:
            self.__outline_color = value
            self._need_update()


class PolygonShape(Shape):
    def __init__(self, color: Color, *, outline: int = 0, outline_color: Color = BLACK, points: List[Vector2] = []) -> None:
        super().__init__(color, outline, outline_color)
        self.__points: List[Vector2] = []
        self.set_points(points)

    def make(self) -> Surface:
        all_points: List[Vector2] = self.__points
        if len(all_points) < 2:
            return create_surface((0, 0))

        offset: float = self.outline / 2 + (self.outline % 2)
        w, h = self.get_local_size()
        image: Surface = create_surface((w + offset * 2, h + offset * 2))

        if len(all_points) == 2 and self.outline > 0:
            start, end = all_points
            pygame.draw.line(image, self.outline_color, start, end, width=self.outline)

        pygame.draw.polygon(image, self.color, all_points)
        if self.outline > 0:
            pygame.draw.polygon(image, self.outline_color, all_points, width=self.outline)
        return image

    def get_local_size(self) -> Tuple[float, float]:
        left: float = min((point.x for point in self.__points), default=0)
        right: float = max((point.x for point in self.__points), default=0)
        top: float = min((point.y for point in self.__points), default=0)
        bottom: float = max((point.y for point in self.__points), default=0)
        width: float = right - left
        height: float = bottom - top
        return width, height

    def get_vertices(self) -> List[Vector2]:
        left: float = min((point.x for point in self.__points), default=0)
        right: float = max((point.x for point in self.__points), default=0)
        top: float = min((point.y for point in self.__points), default=0)
        bottom: float = max((point.y for point in self.__points), default=0)
        w: float = right - left
        h: float = bottom - top
        local_center = Vector2(left + w / 2, top + h / 2)

        center: Vector2 = Vector2(self.center)
        all_points: List[Vector2] = []
        for point in self.__points:
            offset: Vector2 = (point - local_center).rotate(-self.angle)
            offset.scale_to_length(offset.length() * self.scale)
            all_points.append(center + offset)
        return all_points

    def set_points(self, points: Union[List[Vector2], List[Tuple[float, float]], List[Tuple[int, int]]]) -> None:
        points = [Vector2(p) for p in points]
        left: float = min((point.x for point in points), default=0)
        top: float = min((point.y for point in points), default=0)
        for p in points:
            p.x -= left
            p.y -= top

        if len(points) == len(self.__points) and all(p1 == p2 for p1, p2 in zip(points, self.__points)):
            return

        self.__points = points
        self._need_update()


class RectangleShape(Shape):
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
    ):
        super().__init__(color, outline, outline_color)
        self.__w: float = 0
        self.__h: float = 0
        self.local_size = width, height
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

    def make(self) -> Surface:
        offset: float = self.outline / 2 + (self.outline % 2)
        w, h = self.get_local_size()
        image: Surface = create_surface((w + offset * 2, h + offset * 2))
        default_rect: Rect = image.get_rect()
        rect: Rect = Rect(0, 0, w, h)
        rect.center = default_rect.center
        pygame.draw.rect(image, self.color, rect, **self.__draw_params)
        if self.outline > 0:
            pygame.draw.rect(image, self.outline_color, rect, width=self.outline, **self.__draw_params)
        return image

    def get_local_size(self) -> Tuple[float, float]:
        return self.local_size

    def get_vertices(self) -> List[Vector2]:
        w, h = self.get_local_size()
        w *= self.scale
        h *= self.scale
        local_center: Vector2 = Vector2(w / 2, h / 2)
        corners: List[Vector2] = [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]
        center: Vector2 = Vector2(self.center)
        return [center + (point - local_center).rotate(-self.angle) for point in corners]

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


class CircleShape(Shape):
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
        super().__init__(color, outline, outline_color)
        self.__radius: float = 0
        self.__draw_params: Dict[str, bool] = {
            "draw_top_left": True,
            "draw_top_right": True,
            "draw_bottom_left": True,
            "draw_bottom_right": True,
        }
        self.radius = radius
        self.draw_top_left = draw_top_left
        self.draw_top_right = draw_top_right
        self.draw_bottom_left = draw_bottom_left
        self.draw_bottom_right = draw_bottom_right

    def make(self) -> Surface:
        width, height = self.get_local_size()
        image: Surface = create_surface((width, height))
        center: Tuple[float, float] = (width / 2, height / 2)
        radius: float = self.radius
        pygame.draw.circle(image, self.color, center, radius, **self.__draw_params)
        if self.outline > 0:
            pygame.draw.circle(image, self.outline_color, center, radius, width=self.outline, **self.__draw_params)
        return image

    def get_local_size(self) -> Tuple[float, float]:
        return (self.radius * 2, self.radius * 2)

    def get_vertices(self) -> List[Vector2]:
        center: Vector2 = Vector2(self.center)
        radius: Vector2 = Vector2(self.radius * self.scale, 0)
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


class CrossShape(Shape):
    def __init__(
        self,
        width: float,
        height: float,
        outline_color: Color,
        *,
        outline: int = 2,
        theme: Optional[Theme] = None,
        color: None = None,
    ) -> None:
        super().__init__(TRANSPARENT, outline, outline_color)
        self.__w: float = 0
        self.__h: float = 0
        self.local_size = width, height

    def make(self) -> Surface:
        if self.outline == 0:
            return create_surface((0, 0))

        image: Surface = create_surface(self.get_local_size())
        local_rect: Rect = image.get_rect()
        pygame.draw.line(image, self.outline_color, local_rect.topleft, local_rect.bottomright, width=self.outline)
        pygame.draw.line(image, self.outline_color, local_rect.topright, local_rect.bottomleft, width=self.outline)

        all_points: List[Vector2] = self.__get_points(local_rect, 2)
        if len(all_points) > 2:
            # pygame.draw.lines(image, "white", False, all_points, width=2)
            pygame.draw.polygon(image, "white", all_points, width=2)
        return image

    def get_local_size(self) -> Tuple[float, float]:
        return self.local_size

    def get_vertices(self) -> List[Vector2]:
        w, h = self.get_local_size()
        w *= self.scale
        h *= self.scale
        local_center: Vector2 = Vector2(w / 2, h / 2)
        corners: List[Vector2] = [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]
        center: Vector2 = Vector2(self.center)
        return [center + (point - local_center).rotate(-self.angle) for point in corners]

    def __get_points(self, rect: Rect, outline_size: int) -> List[Vector2]:
        rect = rect.copy()
        outline_size = max(outline_size, 0)
        rect.width -= outline_size if rect.right > outline_size - 1 else 0
        rect.height -= outline_size if rect.bottom > outline_size - 1 else 0
        line_width: float = self.outline
        w_offset: float = line_width
        h_offset: float = line_width
        center_offset: float = line_width
        return [
            Vector2(rect.left, rect.top),
            Vector2(rect.left + w_offset, rect.top),
            Vector2(rect.centerx, rect.centery - center_offset),
            Vector2(rect.right - w_offset, rect.top),
            Vector2(rect.right, rect.top),
            Vector2(rect.right, rect.top + h_offset),
            Vector2(rect.centerx + center_offset, rect.centery),
            Vector2(rect.right, rect.bottom - h_offset),
            Vector2(rect.right, rect.bottom),
            Vector2(rect.right - w_offset, rect.bottom),
            Vector2(rect.centerx, rect.centery + center_offset),
            Vector2(rect.left + w_offset, rect.bottom),
            Vector2(rect.left, rect.bottom),
            Vector2(rect.left, rect.bottom - h_offset),
            Vector2(rect.centerx - center_offset, rect.centery),
            Vector2(rect.left, rect.top + h_offset),
        ]

    @property
    def color(self) -> Color:
        return TRANSPARENT

    @color.setter
    def color(self, color: Color) -> None:
        pass

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
