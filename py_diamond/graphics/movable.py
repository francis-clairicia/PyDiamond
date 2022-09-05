# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Movable objects module"""

from __future__ import annotations

__all__ = ["Movable", "MovableProxy"]


from abc import abstractmethod
from typing import Any, Callable, overload

from ..math import Vector2
from ..system.object import Object, final
from ..system.utils.abc import concreteclass
from ..system.utils.functools import wraps
from .rect import Rect

_SINGLE_COMPONENT_POSITIONS = (
    "x",
    "y",
    "left",
    "right",
    "top",
    "bottom",
    "centerx",
    "centery",
)

_POINT_POSITIONS = (
    "center",
    "topleft",
    "topright",
    "bottomleft",
    "bottomright",
    "midleft",
    "midright",
    "midtop",
    "midbottom",
)

_ALL_VALID_POSITIONS = _SINGLE_COMPONENT_POSITIONS + _POINT_POSITIONS


def _position_decorator(fset: Callable[[Movable, Any], None], fget: Callable[[Movable], Any]) -> Callable[[Movable, Any], None]:
    @wraps(fset)
    def wrapper(self: Movable, /, value: Any) -> None:
        if fget(self) != value:
            fset(self, value)
            self._on_move()

    return wrapper


def __prepare_movable_namespace(mcs: Any, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> None:
    for position in _ALL_VALID_POSITIONS:
        if position not in namespace:
            raise AttributeError(f"Missing {position!r} property")
        prop: property = namespace[position]
        assert prop.fget
        assert prop.fset
        prop = prop.setter(_position_decorator(prop.fset, prop.fget))
        for func in filter(callable, (prop.fget, prop.fset, prop.fdel)):
            final(func)
        namespace[position] = prop


class Movable(Object, prepare_namespace=__prepare_movable_namespace):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__x: float = 0
        self.__y: float = 0

    @overload
    def set_position(
        self,
        *,
        x: float = ...,
        y: float = ...,
        left: float = ...,
        right: float = ...,
        top: float = ...,
        bottom: float = ...,
        centerx: float = ...,
        centery: float = ...,
    ) -> None:
        ...

    @overload
    def set_position(
        self,
        *,
        center: tuple[float, float] = ...,
        topleft: tuple[float, float] = ...,
        topright: tuple[float, float] = ...,
        bottomleft: tuple[float, float] = ...,
        bottomright: tuple[float, float] = ...,
        midleft: tuple[float, float] = ...,
        midright: tuple[float, float] = ...,
        midtop: tuple[float, float] = ...,
        midbottom: tuple[float, float] = ...,
    ) -> None:
        ...

    def set_position(self, **kwargs: Any) -> None:
        if not kwargs:
            return

        if len(kwargs) == 1:
            attr_name, attr_value = next(iter(kwargs.items()))
            if attr_name not in _ALL_VALID_POSITIONS:
                raise TypeError("Bad parameters")
            return self.__setattr__(attr_name, attr_value)

        if len(kwargs) != 2:
            raise TypeError("Bad parameters")

        if "x" in kwargs:
            kwargs["left"] = kwargs.pop("x")
        if "y" in kwargs:
            kwargs["top"] = kwargs.pop("y")

        match kwargs:
            case {"left": left, "top": top}:
                self.topleft = (left, top)
            case {"left": left, "centery": centery}:
                self.midleft = (left, centery)
            case {"left": left, "bottom": bottom}:
                self.bottomleft = (left, bottom)
            case {"centerx": centerx, "top": top}:
                self.midtop = (centerx, top)
            case {"centerx": centerx, "centery": centery}:
                self.center = (centerx, centery)
            case {"centerx": centerx, "bottom": bottom}:
                self.midbottom = (centerx, bottom)
            case {"right": right, "top": top}:
                self.topright = (right, top)
            case {"right": right, "centery": centery}:
                self.midright = (right, centery)
            case {"right": right, "bottom": bottom}:
                self.bottomright = (right, bottom)
            case _:
                raise TypeError("Bad parameters")

    def move(self, dx: float, dy: float) -> None:
        if (dx, dy) == (0, 0):
            return
        self.__x += dx
        self.__y += dy
        self._on_move()

    def translate(self, vector: Vector2 | tuple[float, float]) -> None:
        if (vector[0], vector[1]) == (0, 0):
            return
        self.__x += vector[0]
        self.__y += vector[1]
        self._on_move()

    @final
    def rotate_around_point(self, angle_offset: float, pivot: tuple[float, float] | Vector2 | str) -> None:
        if angle_offset == 0:
            return
        if isinstance(pivot, str):
            if pivot == "center":
                return
            pivot = self._get_pivot_from_attribute(pivot)
        else:
            pivot = Vector2(pivot)
        center: Vector2 = Vector2(self.center)
        if pivot == center:
            return
        center = pivot + (center - pivot).rotate(-angle_offset)
        self.center = center.x, center.y

    @final
    def _get_pivot_from_attribute(self, pivot: str) -> Vector2:
        if pivot not in _POINT_POSITIONS:
            raise ValueError(f"Bad pivot attribute: {pivot!r}")
        return Vector2(getattr(self, pivot))

    @abstractmethod
    def get_size(self) -> tuple[float, float]:
        raise NotImplementedError

    @final
    def get_width(self) -> float:
        return self.get_size()[0]

    @final
    def get_height(self) -> float:
        return self.get_size()[1]

    def get_rect(self, **kwargs: float | tuple[float, float]) -> Rect:
        r: Rect = Rect(self.topleft, self.get_size())
        if kwargs:
            r_setattr = r.__setattr__
            for name, value in kwargs.items():
                r_setattr(name, value)
        return r

    def _on_move(self) -> None:
        pass

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
    def center(self) -> tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + (w / 2), self.__y + (h / 2))

    @center.setter
    def center(self, center: tuple[float, float]) -> None:
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
    def topleft(self) -> tuple[float, float]:
        return (self.__x, self.__y)

    @topleft.setter
    def topleft(self, topleft: tuple[float, float]) -> None:
        self.__x = topleft[0]
        self.__y = topleft[1]

    @property
    def topright(self) -> tuple[float, float]:
        return (self.__x + self.get_size()[0], self.__y)

    @topright.setter
    def topright(self, topright: tuple[float, float]) -> None:
        self.__x = topright[0] - self.get_size()[0]
        self.__y = topright[1]

    @property
    def bottomleft(self) -> tuple[float, float]:
        return (self.__x, self.__y + self.get_size()[1])

    @bottomleft.setter
    def bottomleft(self, bottomleft: tuple[float, float]) -> None:
        self.__x = bottomleft[0]
        self.__y = bottomleft[1] - self.get_size()[1]

    @property
    def bottomright(self) -> tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + w, self.__y + h)

    @bottomright.setter
    def bottomright(self, bottomright: tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = bottomright[0] - w
        self.__y = bottomright[1] - h

    @property
    def midtop(self) -> tuple[float, float]:
        return (self.__x + (self.get_size()[0] / 2), self.__y)

    @midtop.setter
    def midtop(self, midtop: tuple[float, float]) -> None:
        self.__x = midtop[0] - (self.get_size()[0] / 2)
        self.__y = midtop[1]

    @property
    def midbottom(self) -> tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + (w / 2), self.__y + h)

    @midbottom.setter
    def midbottom(self, midbottom: tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = midbottom[0] - (w / 2)
        self.__y = midbottom[1] - h

    @property
    def midleft(self) -> tuple[float, float]:
        return (self.__x, self.__y + (self.get_size()[1] / 2))

    @midleft.setter
    def midleft(self, midleft: tuple[float, float]) -> None:
        self.__x = midleft[0]
        self.__y = midleft[1] - (self.get_size()[1] / 2)

    @property
    def midright(self) -> tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + w, self.__y + (h / 2))

    @midright.setter
    def midright(self, midright: tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = midright[0] - w
        self.__y = midright[1] - (h / 2)


def __prepare_proxy_namespace(mcs: Any, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> None:
    from ..system.utils._mangling import mangle_private_attribute

    for attr in ("x", "y"):
        attr = mangle_private_attribute(Movable, attr)

        def getter(self: MovableProxy, /, *, attr: str = str(attr)) -> Any:
            movable: Movable = object.__getattribute__(self, "_object")
            return getattr(movable, attr)

        def setter(self: MovableProxy, value: Any, /, *, attr: str = str(attr)) -> Any:
            movable: Movable = object.__getattribute__(self, "_object")
            return setattr(movable, attr, value)

        namespace[attr] = property(fget=getter, fset=setter)

    for method_name in (
        "set_position",
        "move",
        "translate",
        "get_rect",
    ):

        @wraps(getattr(Movable, method_name))  # type: ignore[arg-type]
        def wrapper(self: MovableProxy, *args: Any, __method_name: str = str(method_name), **kwargs: Any) -> Any:
            method_name = __method_name
            movable: Movable = object.__getattribute__(self, "_object")
            method: Callable[..., Any] = getattr(movable, method_name)
            return method(*args, **kwargs)

        wrapper.__qualname__ = f"{name}.{wrapper.__name__}"

        namespace[method_name] = wrapper


@concreteclass
class MovableProxy(Movable, prepare_namespace=__prepare_proxy_namespace):
    def __init__(self, movable: Movable) -> None:
        object.__setattr__(self, "_object", movable)

    def get_size(self) -> tuple[float, float]:
        movable: Movable = object.__getattribute__(self, "_object")
        return movable.get_size()

    def _on_move(self) -> None:
        movable: Movable = object.__getattribute__(self, "_object")
        movable._on_move()
        return super()._on_move()

    def __hash__(self) -> int:
        return hash(object.__getattribute__(self, "_object"))

    def __eq__(self, __o: object) -> bool:
        movable: Movable = object.__getattribute__(self, "_object")
        return movable.__eq__(__o)

    def __ne__(self, __o: object) -> bool:
        movable: Movable = object.__getattribute__(self, "_object")
        return movable.__ne__(__o)


del __prepare_movable_namespace, __prepare_proxy_namespace
