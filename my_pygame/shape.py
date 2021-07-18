# -*- coding: Utf-8 -*

from typing import Dict, List, Optional, Tuple

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
        self.color = color
        self.outline = outline
        self.outline_color = outline_color

    @property
    def color(self) -> Color:
        return self.__color

    @color.setter
    def color(self, value: Color) -> None:
        self.__color = Color(value)

    @property
    def outline(self) -> int:
        return self.__outline

    @outline.setter
    def outline(self, value: int) -> None:
        self.__outline = max(value, 0)

    @property
    def outline_color(self) -> Color:
        return self.__outline_color

    @outline_color.setter
    def outline_color(self, value: Color) -> None:
        self.__outline_color = Color(value)


class PolygonShape(Shape):
    def __init__(self, color: Color, *, outline: int = 0, outline_color: Color = BLACK, points: List[Vector2] = []) -> None:
        super().__init__(color, outline, outline_color)
        self.points = points

    def draw_onto(self, surface: Surface) -> None:
        all_points: List[Vector2] = self.get_vertices()
        if len(all_points) <= 2:
            return

        pygame.draw.polygon(surface, self.color, all_points)
        outline: int = max(round(self.outline * self.scale), 1) if self.outline > 0 else 0
        if outline > 0:
            pygame.draw.polygon(surface, self.outline_color, all_points, width=outline)

    def get_local_size(self) -> Tuple[float, float]:
        left: float = min((point.x for point in self.points), default=0)
        right: float = max((point.x for point in self.points), default=0)
        top: float = min((point.y for point in self.points), default=0)
        bottom: float = max((point.y for point in self.points), default=0)
        width: float = right - left
        height: float = bottom - top
        return width, height

    def get_vertices(self) -> List[Vector2]:
        left: float = min((point.x for point in self.points), default=0)
        right: float = max((point.x for point in self.points), default=0)
        top: float = min((point.y for point in self.points), default=0)
        bottom: float = max((point.y for point in self.points), default=0)
        w: float = right - left
        h: float = bottom - top
        local_center = Vector2(left + w / 2, top + h / 2)

        center: Vector2 = Vector2(self.center)
        all_points: List[Vector2] = []
        for point in self.points:
            offset: Vector2 = (point - local_center).rotate(-self.angle)
            offset.scale_to_length(offset.length() * self.scale)
            all_points.append(center + offset)
        return all_points

    @property
    def points(self) -> List[Vector2]:
        return self.__points

    @points.setter
    def points(self, points: List[Vector2]) -> None:
        self.__points = [Vector2(p) for p in points]


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

    def draw_onto(self, surface: Surface) -> None:
        image: Surface = create_surface((self.local_width * self.scale, self.local_height * self.scale))
        pygame.draw.rect(image, self.color, image.get_rect(), **self.__draw_params)
        outline: int = max(round(self.outline * self.scale), 1) if self.outline > 0 else 0
        if outline > 0:
            pygame.draw.rect(image, self.outline_color, image.get_rect(), width=outline, **self.__draw_params)
        image = pygame.transform.rotate(image, self.angle)
        surface.blit(image, self.topleft)

    def get_local_size(self) -> Tuple[float, float]:
        return self.local_size

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
        self.__w = max(width, 0)

    @property
    def local_height(self) -> float:
        return self.__h

    @local_height.setter
    def local_height(self, height: float) -> None:
        self.__h = max(height, 0)

    @property
    def border_radius(self) -> int:
        return self.__draw_params["border_radius"]

    @border_radius.setter
    def border_radius(self, radius: int) -> None:
        self.__draw_params["border_radius"] = max(radius, -1)

    @property
    def border_top_left_radius(self) -> int:
        return self.__draw_params["border_top_left_radius"]

    @border_top_left_radius.setter
    def border_top_left_radius(self, radius: int) -> None:
        self.__draw_params["border_top_left_radius"] = max(radius, -1)

    @property
    def border_top_right_radius(self) -> int:
        return self.__draw_params["border_top_right_radius"]

    @border_top_right_radius.setter
    def border_top_right_radius(self, radius: int) -> None:
        self.__draw_params["border_top_right_radius"] = max(radius, -1)

    @property
    def border_bottom_left_radius(self) -> int:
        return self.__draw_params["border_bottom_left_radius"]

    @border_bottom_left_radius.setter
    def border_bottom_left_radius(self, radius: int) -> None:
        self.__draw_params["border_bottom_left_radius"] = max(radius, -1)

    @property
    def border_bottom_right_radius(self) -> int:
        return self.__draw_params["border_bottom_right_radius"]

    @border_bottom_right_radius.setter
    def border_bottom_right_radius(self, radius: int) -> None:
        self.__draw_params["border_bottom_right_radius"] = max(radius, -1)


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
        self.radius = radius
        self.__draw_params: Dict[str, bool] = {
            "draw_top_left": True,
            "draw_top_right": True,
            "draw_bottom_left": True,
            "draw_bottom_right": True,
        }
        self.draw_top_left = draw_top_left
        self.draw_top_right = draw_top_right
        self.draw_bottom_left = draw_bottom_left
        self.draw_bottom_right = draw_bottom_right

    def draw_onto(self, surface: Surface) -> None:
        radius: float = self.radius * self.scale
        outline = max(round(self.outline * self.scale), 1) if self.outline > 0 else 0

        if all(self.__draw_params.values()):
            center: Tuple[float, float] = self.center
            pygame.draw.circle(surface, self.color, center, radius)
            if outline > 0:
                pygame.draw.circle(surface, self.outline_color, center, radius, width=outline)
        elif any(self.__draw_params.values()):
            image: Surface = create_surface((radius * 2, radius * 2))
            center = radius, radius
            pygame.draw.circle(image, self.color, center, radius, **self.__draw_params)
            if outline > 0:
                pygame.draw.circle(image, self.outline_color, center, radius, width=outline, **self.__draw_params)
            image = pygame.transform.rotate(image, self.angle)
            surface.blit(image, self.topleft)

    def get_local_size(self) -> Tuple[float, float]:
        return (self.radius * 2, self.radius * 2)

    @property
    def radius(self) -> float:
        return self.__radius

    @radius.setter
    def radius(self, radius: float) -> None:
        self.__radius = max(radius, 0)

    @property
    def draw_top_left(self) -> int:
        return self.__draw_params["draw_top_left"]

    @draw_top_left.setter
    def draw_top_left(self, status: bool) -> None:
        self.__draw_params["draw_top_left"] = bool(status)

    @property
    def draw_top_right(self) -> int:
        return self.__draw_params["draw_top_right"]

    @draw_top_right.setter
    def draw_top_right(self, status: bool) -> None:
        self.__draw_params["draw_top_right"] = bool(status)

    @property
    def draw_bottom_left(self) -> int:
        return self.__draw_params["draw_bottom_left"]

    @draw_bottom_left.setter
    def draw_bottom_left(self, status: bool) -> None:
        self.__draw_params["draw_bottom_left"] = bool(status)

    @property
    def draw_bottom_right(self) -> int:
        return self.__draw_params["draw_bottom_right"]

    @draw_bottom_right.setter
    def draw_bottom_right(self, status: bool) -> None:
        self.__draw_params["draw_bottom_right"] = bool(status)


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
        self.local_size = width, height

    def draw_onto(self, surface: Surface) -> None:
        outline: int = max(round(self.outline * self.scale), 1) if self.outline > 0 else 0
        if outline == 0:
            return

        image: Surface = create_surface((self.local_width * self.scale, self.local_height * self.scale))
        local_rect: Rect = image.get_rect()
        pygame.draw.line(image, self.outline_color, local_rect.topleft, local_rect.bottomright, width=outline)
        pygame.draw.line(image, self.outline_color, local_rect.topright, local_rect.bottomleft, width=outline)
        image = pygame.transform.rotate(image, self.angle)
        surface.blit(image, self.topleft)

    def get_local_size(self) -> Tuple[float, float]:
        return self.local_size

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
        self.__w = max(width, 0)

    @property
    def local_height(self) -> float:
        return self.__h

    @local_height.setter
    def local_height(self, height: float) -> None:
        self.__h = max(height, 0)
