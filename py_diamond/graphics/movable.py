# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Movable objects module"""

from __future__ import annotations

__all__ = ["MetaMovable", "Movable"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Dict, Tuple, Union, final

from ..math import Vector2
from ..system.utils import wraps
from .rect import ImmutableRect, Rect

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


def _position_decorator(func: Callable[[Movable, Any], None], position: str) -> Callable[[Movable, Any], None]:
    @wraps(func)
    def wrapper(self: Movable, /, value: Any) -> None:
        actual_value: Any = getattr(self, position)
        if actual_value != value:
            func(self, value)
            self._on_move()

    return wrapper


class MetaMovable(ABCMeta):
    def __new__(
        metacls,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        **kwargs: Any,
    ) -> MetaMovable:
        if "Movable" in globals() and not any(issubclass(cls, Movable) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {Movable.__name__} class in order to use {MetaMovable.__name__} metaclass"
            )

        for position in _ALL_VALID_POSITIONS:
            if position not in namespace:
                continue
            if any(hasattr(cls, position) for cls in bases):
                raise TypeError("Override of position attributes is not allowed")
            prop: property = namespace[position]
            if prop.fset:
                namespace[position] = prop.setter(_position_decorator(prop.fset, position))

        return super().__new__(metacls, name, bases, namespace, **kwargs)


class Movable(metaclass=MetaMovable):
    def __init__(self) -> None:
        self.__x: float = 0
        self.__y: float = 0

    def set_position(self, **position: Union[float, Tuple[float, float]]) -> None:
        for name in position:
            if name not in _ALL_VALID_POSITIONS:
                raise AttributeError(f"Unknown position attribute {name!r}")
        for name, value in position.items():
            setattr(self, name, value)

    def move(self, dx: float, dy: float) -> None:
        self.__x += dx
        self.__y += dy

    def translate(self, vector: Union[Vector2, Tuple[float, float]]) -> None:
        self.__x += vector[0]
        self.__y += vector[1]

    @abstractmethod
    def get_size(self) -> Tuple[float, float]:
        raise NotImplementedError

    @final
    def get_width(self) -> float:
        return self.get_size()[0]

    @final
    def get_height(self) -> float:
        return self.get_size()[1]

    def get_rect(self, **kwargs: Union[float, Tuple[float, float]]) -> Rect:
        r: Rect = Rect(self.topleft, self.get_size())
        for name, value in kwargs.items():
            if not hasattr(r, name):
                raise AttributeError(f"{type(r).__name__!r} has no attribute {name!r}")
            setattr(r, name, value)
        return r

    def _on_move(self) -> None:
        pass

    @property
    def rect(self) -> ImmutableRect:
        return ImmutableRect(self.topleft, self.get_size())

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
    def left(self) -> float:
        return self.__x

    @left.setter
    def left(self, left: float) -> None:
        self.__x = left

    @property
    def right(self) -> float:
        return self.__x + self.get_size()[0]

    @right.setter
    def right(self, right: float) -> None:
        self.__x = right - self.get_size()[0]

    @property
    def top(self) -> float:
        return self.__y

    @top.setter
    def top(self, top: float) -> None:
        self.__y = top

    @property
    def bottom(self) -> float:
        return self.__y + self.get_size()[1]

    @bottom.setter
    def bottom(self, bottom: float) -> None:
        self.__y = bottom - self.get_size()[1]

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
        return self.__x + (self.get_size()[0] / 2)

    @centerx.setter
    def centerx(self, centerx: float) -> None:
        self.__x = centerx - (self.get_size()[0] / 2)

    @property
    def centery(self) -> float:
        return self.__y + (self.get_size()[1] / 2)

    @centery.setter
    def centery(self, centery: float) -> None:
        self.__y = centery - (self.get_size()[1] / 2)

    @property
    def topleft(self) -> Tuple[float, float]:
        return (self.__x, self.__y)

    @topleft.setter
    def topleft(self, topleft: Tuple[float, float]) -> None:
        self.__x = topleft[0]
        self.__y = topleft[1]

    @property
    def topright(self) -> Tuple[float, float]:
        return (self.__x + self.get_size()[0], self.__y)

    @topright.setter
    def topright(self, topright: Tuple[float, float]) -> None:
        self.__x = topright[0] - self.get_size()[0]
        self.__y = topright[1]

    @property
    def bottomleft(self) -> Tuple[float, float]:
        return (self.__x, self.__y + self.get_size()[1])

    @bottomleft.setter
    def bottomleft(self, bottomleft: Tuple[float, float]) -> None:
        self.__x = bottomleft[0]
        self.__y = bottomleft[1] - self.get_size()[1]

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
        return (self.__x + (self.get_size()[0] / 2), self.__y)

    @midtop.setter
    def midtop(self, midtop: Tuple[float, float]) -> None:
        self.__x = midtop[0] - (self.get_size()[0] / 2)
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
        return (self.__x, self.__y + (self.get_size()[1] / 2))

    @midleft.setter
    def midleft(self, midleft: Tuple[float, float]) -> None:
        self.__x = midleft[0]
        self.__y = midleft[1] - (self.get_size()[1] / 2)

    @property
    def midright(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + w, self.__y + (h / 2))

    @midright.setter
    def midright(self, midright: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = midright[0] - w
        self.__y = midright[1] - (h / 2)
