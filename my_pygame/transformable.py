# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pygame.rect import Rect
from pygame import error as PygameError
from pygame.math import Vector2

__all__ = ["MetaTransformable", "Transformable"]


_ALL_VALID_POSITIONS: Tuple[str, ...] = (
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
    "midleft",
    "midright",
    "midtop",
    "midbottom",
)


def _position_decorator(position: property) -> property:
    if position.fset is None:
        return position

    setter: Callable[[Any, Any], None] = position.fset

    if position.fget is None:

        @wraps(setter)
        def setter_wrapper(self: Transformable, /, _value: Any) -> None:
            setter(self, _value)
            self._on_move()

        return position.setter(setter_wrapper)

    getter: Callable[[Any], Any] = position.fget

    @wraps(setter)  # type: ignore
    def setter_wrapper(self: Transformable, /, _value: Any) -> None:
        if getter(self) != _value:
            setter(self, _value)
            self._on_move()

    return position.setter(setter_wrapper)


class MetaTransformable(ABCMeta):
    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any) -> MetaTransformable:
        if "Transformable" in globals() and not any(issubclass(cls, Transformable) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {Transformable.__name__} class in order to use {MetaTransformable.__name__} metaclass"
            )

        for position in _ALL_VALID_POSITIONS:
            if position in namespace and any(hasattr(cls, position) for cls in bases):
                raise TypeError("Override of position attributes is not allowed")

        for position in filter(lambda pos: pos in namespace, _ALL_VALID_POSITIONS):
            obj: Any = namespace[position]
            if isinstance(obj, property):
                namespace[position] = _position_decorator(obj)

        return super().__new__(metacls, name, bases, namespace, **kwargs)


class Transformable(metaclass=MetaTransformable):
    def __init__(self) -> None:
        self.__x: float = 0
        self.__y: float = 0
        self.__angle: float = 0
        self.__scale: float = 1

    def set_position(self, **position: Union[float, Tuple[float, float]]) -> None:
        for name in position:
            if name not in _ALL_VALID_POSITIONS:
                raise AttributeError(f"Unknown position attribute {name!r}")
        for name, value in position.items():
            setattr(self, name, value)

    def move(self, dx: float, dy: float) -> None:
        if dx == 0 and dy == 0:
            return
        self.__x += dx
        self.__y += dy
        self._on_move()

    def translate(self, vector: Union[Vector2, Tuple[float, float]]) -> None:
        if vector[0] == 0 and vector[1] == 0:
            return
        self.__x += vector[0]
        self.__y += vector[1]
        self._on_move()

    def rotate(self, angle_offset: float, pivot: Optional[Union[Tuple[float, float], Vector2, str]] = None) -> None:
        self.set_rotation(self.__angle + angle_offset, pivot=pivot)

    def set_rotation(self, angle: float, pivot: Optional[Union[Tuple[float, float], Vector2, str]] = None) -> None:
        angle = float(angle)
        angle %= 360
        if angle < 0:
            angle += 360
        if self.angle == angle:
            return
        center: Vector2 = Vector2(self.center)
        former_angle: float = self.__angle
        self.__angle = angle
        try:
            self._apply_rotation_scale()
        except NotImplementedError:
            self.__angle = 0
            raise
        except PygameError:
            pass
        if pivot is None:
            pivot = center
        elif isinstance(pivot, str):
            pivot = getattr(self, pivot)
            if not isinstance(pivot, tuple) or len(pivot) != 2:
                raise AttributeError(f"Bad pivot attribute: {pivot}")
        pivot = Vector2(pivot)
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
        pivot = Vector2(pivot)
        center: Vector2 = Vector2(self.center)
        if pivot == center:
            return
        center = pivot + (center - pivot).rotate(-angle_offset)
        self.center = center.x, center.y

    def set_scale(self, scale: float) -> None:
        scale = max(float(scale), 0)
        if self.scale == scale:
            return
        center: Tuple[float, float] = self.center
        self.__scale = scale
        try:
            self._apply_rotation_scale()
        except NotImplementedError:
            self.__scale = 1
            raise
        except PygameError:
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
        return self.get_area()

    def get_area(self, *, apply_scale: bool = True, apply_rotation: bool = True) -> Tuple[float, float]:
        if not apply_scale and not apply_rotation:
            return self.get_local_size()

        scale: float = self.__scale
        angle: float = self.__angle
        w, h = self.get_local_size()
        if apply_scale:
            w *= scale
            h *= scale
        if not apply_rotation or angle == 0 or angle == 180:
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

    def get_width(self) -> float:
        return self.get_size()[0]

    def get_height(self) -> float:
        return self.get_size()[1]

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

    def _on_move(self) -> None:
        pass

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
        return Rect(self.topleft, self.get_size())

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
        return self.__x

    @left.setter
    def left(self, left: float) -> None:
        self.__x = left

    @property
    def right(self) -> float:
        return self.__x + self.width

    @right.setter
    def right(self, right: float) -> None:
        self.__x = right - self.width

    @property
    def top(self) -> float:
        return self.__y

    @top.setter
    def top(self, top: float) -> None:
        self.__y = top

    @property
    def bottom(self) -> float:
        return self.__y + self.height

    @bottom.setter
    def bottom(self, bottom: float) -> None:
        self.__y = bottom - self.height

    @property
    def center(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + (w / 2), self.__y + (h / 2))

    @center.setter
    def center(self, center: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = center[0] - (w / 2)
        self.__y = center[1] - (h / 2)

    @property
    def centerx(self) -> float:
        return self.__x + (self.width / 2)

    @centerx.setter
    def centerx(self, centerx: float) -> None:
        self.__x = centerx - (self.width / 2)

    @property
    def centery(self) -> float:
        return self.__y + (self.height / 2)

    @centery.setter
    def centery(self, centery: float) -> None:
        self.__y = centery - (self.height / 2)

    @property
    def topleft(self) -> Tuple[float, float]:
        return (self.__x, self.__y)

    @topleft.setter
    def topleft(self, topleft: Tuple[float, float]) -> None:
        self.__x = topleft[0]
        self.__y = topleft[1]

    @property
    def topright(self) -> Tuple[float, float]:
        return (self.__x + self.width, self.__y)

    @topright.setter
    def topright(self, topright: Tuple[float, float]) -> None:
        self.__x = topright[0] - self.width
        self.__y = topright[1]

    @property
    def bottomleft(self) -> Tuple[float, float]:
        return (self.__x, self.__y + self.height)

    @bottomleft.setter
    def bottomleft(self, bottomleft: Tuple[float, float]) -> None:
        self.__x = bottomleft[0]
        self.__y = bottomleft[1] - self.height

    @property
    def bottomright(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + w, self.__y + h)

    @bottomright.setter
    def bottomright(self, bottomright: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = bottomright[0] - w
        self.__y = bottomright[1] - h

    @property
    def midtop(self) -> Tuple[float, float]:
        return (self.__x + (self.width / 2), self.__y)

    @midtop.setter
    def midtop(self, midtop: Tuple[float, float]) -> None:
        self.__x = midtop[0] - (self.width / 2)
        self.__y = midtop[1]

    @property
    def midbottom(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + (w / 2), self.__y + h)

    @midbottom.setter
    def midbottom(self, midbottom: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = midbottom[0] - (w / 2)
        self.__y = midbottom[1] - h

    @property
    def midleft(self) -> Tuple[float, float]:
        return (self.__x, self.__y + (self.height / 2))

    @midleft.setter
    def midleft(self, midleft: Tuple[float, float]) -> None:
        self.__x = midleft[0]
        self.__y = midleft[1] - (self.height / 2)

    @property
    def midright(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + w, self.__y + (h / 2))

    @midright.setter
    def midright(self, midright: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = midright[0] - w
        self.__y = midright[1] - (h / 2)
