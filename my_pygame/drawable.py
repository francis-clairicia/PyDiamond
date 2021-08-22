# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union
from functools import wraps

import pygame
from pygame.surface import Surface
from pygame.rect import Rect
from pygame.math import Vector2

from .theme import MetaThemedObject, ThemedObject, abstract_theme_class
from .animation import Animation
from .surface import create_surface


def _draw_decorator(func: Callable[[Drawable, Surface], None]) -> Callable[[Drawable, Surface], None]:
    @wraps(func)
    def wrapper(self: Drawable, surface: Surface) -> None:
        if self.is_shown():
            func(self, surface)

    return wrapper


def _can_apply_decorator(func: Callable[..., Any]) -> bool:
    return not getattr(func, "__isabstractmethod__", False)


class MetaDrawable(ABCMeta):
    def __new__(metacls, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any], **kwargs: Any) -> MetaDrawable:
        if "copy" not in attrs:
            attrs["copy"] = Drawable.copy

        draw_method: Optional[Callable[[Drawable, Surface], None]] = attrs.get("draw_onto")
        if callable(draw_method) and _can_apply_decorator(draw_method):
            attrs["draw_onto"] = _draw_decorator(draw_method)

        return super().__new__(metacls, name, bases, attrs, **kwargs)


class Drawable(metaclass=MetaDrawable):
    __DrawableType = TypeVar("__DrawableType", bound="Drawable")

    def __init__(self) -> None:
        self.__x: float = 0
        self.__y: float = 0
        self.__angle: float = 0
        self.__scale: float = 1
        self.__draw: bool = True
        self.__animation: Animation = Animation(self)

    @abstractmethod
    def draw_onto(self, surface: Surface) -> None:
        raise NotImplementedError

    @abstractmethod
    def copy(self: __DrawableType) -> __DrawableType:
        raise NotImplementedError

    def deep_copy(self: __DrawableType) -> __DrawableType:
        copy_self: Drawable.__DrawableType = self.copy()
        copy_self.scale = self.scale
        copy_self.angle = self.angle
        copy_self.center = self.center
        return copy_self

    def to_surface(self) -> Surface:
        topleft: Tuple[float, float] = self.topleft
        image: Surface = create_surface(self.get_size())
        self.topleft = (0, 0)
        self.draw_onto(image)
        self.topleft = topleft
        return image

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)

    def set_visibility(self, status: bool) -> None:
        self.__draw = bool(status)

    def is_shown(self) -> bool:
        return self.__draw

    def set_position(self, **position: Union[float, Tuple[float, float]]) -> None:
        all_valid_positions: Tuple[str, ...] = (
            "x",
            "y",
            "left",
            "right",
            "top",
            "bottom",
            "center",
            "centerx",
            "centery",
            "topleft",
            "topright",
            "bottomleft",
            "bottomright",
            "midtop",
            "midbottom",
            "midleft",
            "midright",
        )
        for name, value in position.items():
            if name not in all_valid_positions:
                raise AttributeError(f"Unknown position attribute {name!r}")
            setattr(self, name, value)

    def move(self, dx: float, dy: float) -> None:
        self.x += dx
        self.y += dy

    def translate(self, vector: Union[Vector2, Tuple[float, float]]) -> None:
        self.x += vector[0]
        self.y += vector[1]

    def rotate(self, angle_offset: float, pivot: Optional[Union[Tuple[float, float], Vector2, str]] = None) -> None:
        self.set_rotation(self.__angle + angle_offset, pivot=pivot)

    def set_rotation(self, angle: float, pivot: Optional[Union[Tuple[float, float], Vector2, str]] = None) -> None:
        angle %= 360
        if angle < 0:
            angle += 360
        if self.angle == angle:
            return
        center: Vector2 = Vector2(self.center)  # type: ignore[arg-type]
        former_angle: float = self.__angle
        self.__angle = angle
        try:
            self._apply_rotation_scale()
        except NotImplementedError:
            self.__angle = 0
            raise
        except pygame.error:
            pass
        if pivot is None:
            pivot = center
        elif isinstance(pivot, str):
            pivot = getattr(self, pivot)
            if not isinstance(pivot, tuple) or len(pivot) != 2:
                raise AttributeError(f"Bad pivot attribute: {pivot}")
        pivot = Vector2(pivot)  # type: ignore[arg-type]
        if pivot != center:
            center = pivot + (center - pivot).rotate(-self.__angle + former_angle)
        self.center = center.x, center.y

    def rotate_around_point(self, angle_offset: float, pivot: Union[Tuple[float, float], Vector2, str]) -> None:
        if angle_offset == 0:
            return
        if isinstance(pivot, str):
            pivot = getattr(self, pivot)
            if not isinstance(pivot, tuple) or len(pivot) != 2:
                raise AttributeError(f"Bad pivot attribute: {pivot}")
        pivot = Vector2(pivot)  # type: ignore[arg-type]
        center: Vector2 = Vector2(self.center)  # type: ignore[arg-type]
        if pivot == center:
            return
        center = pivot + (center - pivot).rotate(-angle_offset)
        self.center = center.x, center.y

    def set_scale(self, scale: float) -> None:
        scale = max(scale, 0)
        if self.scale == scale:
            return
        center: Tuple[float, float] = self.center
        self.__scale = scale
        try:
            self._apply_rotation_scale()
        except NotImplementedError:
            self.__scale = 1
            raise
        except pygame.error:
            pass
        self.center = center

    def scale_to_width(self, width: float) -> None:
        w: float = self.get_local_size()[0]
        self.set_scale(width / w)

    def scale_to_height(self, height: float) -> None:
        h: float = self.get_local_size()[1]
        self.set_scale(height / h)

    def scale_to_size(self, size: Tuple[float, float]) -> None:
        w, h = self.get_local_size()
        scale_width: float = size[0] / w
        scale_height: float = size[1] / h
        self.set_scale(min(scale_width, scale_height))

    def set_min_width(self, width: float) -> None:
        if self.width < width:
            self.scale_to_width(width)

    def set_max_width(self, width: float) -> None:
        if self.width > width:
            self.scale_to_width(width)

    def set_min_height(self, height: float) -> None:
        if self.height < height:
            self.scale_to_height(height)

    def set_max_height(self, height: float) -> None:
        if self.height > height:
            self.scale_to_height(height)

    def set_min_size(self, size: Tuple[float, float]) -> None:
        if self.width < size[0] or self.height < size[1]:
            self.scale_to_size(size)

    def set_max_size(self, size: Tuple[float, float]) -> None:
        if self.width > size[0] or self.height > size[1]:
            self.scale_to_size(size)

    def _apply_rotation_scale(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_local_size(self) -> Tuple[float, float]:
        raise NotImplementedError

    def get_local_width(self) -> float:
        return self.get_local_size()[0]

    def get_local_height(self) -> float:
        return self.get_local_size()[1]

    def get_size(self) -> Tuple[float, float]:
        scale: float = self.__scale
        angle: float = self.__angle
        w, h = self.get_local_size()
        w *= scale
        h *= scale
        if angle == 0 or angle == 180:
            return (w, h)
        if angle == 90 or angle == 270:
            return (h, w)

        center: Vector2 = Vector2(w / 2, h / 2)
        corners: List[Vector2] = [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]
        all_points: List[Vector2] = [center + (point - center).rotate(-angle) for point in corners]
        left: float = min((point.x for point in all_points), default=0)
        right: float = max((point.x for point in all_points), default=0)
        top: float = min((point.y for point in all_points), default=0)
        bottom: float = max((point.y for point in all_points), default=0)
        return (right - left, bottom - top)

    def get_local_rect(self, **kwargs: Union[float, Tuple[float, float]]) -> Rect:
        r: Rect = Rect((0, 0), self.get_local_size())
        for name, value in kwargs.items():
            if not hasattr(r, name):
                raise AttributeError(f"{type(r).__name__!r} has no attribute {name!r}")
            setattr(r, name, value)
        return r

    def get_rect(self, **kwargs: Union[float, Tuple[float, float]]) -> Rect:
        r: Rect = self.rect
        for name, value in kwargs.items():
            if not hasattr(r, name):
                raise AttributeError(f"{type(r).__name__!r} has no attribute {name!r}")
            setattr(r, name, value)
        return r

    @property
    def animation(self) -> Animation:
        return self.__animation

    @property
    def angle(self) -> float:
        return self.__angle

    @angle.setter
    def angle(self, angle: float) -> None:
        self.set_rotation(angle)

    @property
    def scale(self) -> float:
        return self.__scale

    @scale.setter
    def scale(self, scale: float) -> None:
        self.set_scale(scale)

    @property
    def rect(self) -> Rect:
        return Rect(self.topleft, self.size)

    @property
    def x(self) -> float:
        return self.__x

    @x.setter
    def x(self, x: float) -> None:
        self.__x = x

    @property
    def y(self) -> float:
        return self.__y

    @y.setter
    def y(self, y: float) -> None:
        self.__y = y

    @property
    def size(self) -> Tuple[float, float]:
        return self.get_size()

    @size.setter
    def size(self, size: Tuple[float, float]) -> None:
        self.scale_to_size(size)

    @property
    def width(self) -> float:
        return self.get_size()[0]

    @width.setter
    def width(self, width: float) -> None:
        self.scale_to_width(width)

    @property
    def height(self) -> float:
        return self.get_size()[1]

    @height.setter
    def height(self, height: float) -> None:
        self.scale_to_height(height)

    @property
    def left(self) -> float:
        return self.x

    @left.setter
    def left(self, left: float) -> None:
        self.x = left

    @property
    def right(self) -> float:
        return self.x + self.width

    @right.setter
    def right(self, right: float) -> None:
        self.x = right - self.width

    @property
    def top(self) -> float:
        return self.y

    @top.setter
    def top(self, top: float) -> None:
        self.y = top

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @bottom.setter
    def bottom(self, bottom: float) -> None:
        self.y = bottom - self.height

    @property
    def center(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.x + (w / 2), self.y + (h / 2))

    @center.setter
    def center(self, center: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.x = center[0] - (w / 2)
        self.y = center[1] - (h / 2)

    @property
    def centerx(self) -> float:
        return self.x + (self.width / 2)

    @centerx.setter
    def centerx(self, centerx: float) -> None:
        self.x = centerx - (self.width / 2)

    @property
    def centery(self) -> float:
        return self.y + (self.height / 2)

    @centery.setter
    def centery(self, centery: float) -> None:
        self.y = centery - (self.height / 2)

    @property
    def topleft(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @topleft.setter
    def topleft(self, topleft: Tuple[float, float]) -> None:
        self.x = topleft[0]
        self.y = topleft[1]

    @property
    def topright(self) -> Tuple[float, float]:
        return (self.x + self.width, self.y)

    @topright.setter
    def topright(self, topright: Tuple[float, float]) -> None:
        self.x = topright[0] - self.width
        self.y = topright[1]

    @property
    def bottomleft(self) -> Tuple[float, float]:
        return (self.x, self.y + self.height)

    @bottomleft.setter
    def bottomleft(self, bottomleft: Tuple[float, float]) -> None:
        self.x = bottomleft[0]
        self.y = bottomleft[1] - self.height

    @property
    def bottomright(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.x + w, self.y + h)

    @bottomright.setter
    def bottomright(self, bottomright: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.x = bottomright[0] - w
        self.y = bottomright[1] - h

    @property
    def midtop(self) -> Tuple[float, float]:
        return (self.x + (self.width / 2), self.y)

    @midtop.setter
    def midtop(self, midtop: Tuple[float, float]) -> None:
        self.x = midtop[0] - (self.width / 2)
        self.y = midtop[1]

    @property
    def midbottom(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.x + (w / 2), self.y + h)

    @midbottom.setter
    def midbottom(self, midbottom: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.x = midbottom[0] - (w / 2)
        self.y = midbottom[1] - h

    @property
    def midleft(self) -> Tuple[float, float]:
        return (self.x, self.y + (self.height / 2))

    @midleft.setter
    def midleft(self, midleft: Tuple[float, float]) -> None:
        self.x = midleft[0]
        self.y = midleft[1] - (self.height / 2)

    @property
    def midright(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.x + w, self.y + (h / 2))

    @midright.setter
    def midright(self, midright: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.x = midright[0] - w
        self.y = midright[1] - (h / 2)


class MetaThemedDrawable(MetaDrawable, MetaThemedObject):
    pass


@abstract_theme_class
class ThemedDrawable(Drawable, ThemedObject, metaclass=MetaThemedDrawable):
    pass
